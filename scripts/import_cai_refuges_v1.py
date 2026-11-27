#!/usr/bin/env python3
"""Import incrementale del catalogo pubblico CAI Unico Rifugi per Cima Becco.

Il titolare del progetto conferma il riuso dei dati CAI. Conserviamo comunque
fonte, tipologia, revisione e informazioni sull'autore, ove presenti.
La lista CAI comprende anche bivacchi e altre strutture: NON si deduce il tipo
dal nome. Ogni campo pubblicato passa attraverso un'allowlist; nomi e dati
personali di gestione/contratti non entrano nell'export. Un errore di rete non
deve mai cancellare una scheda già raccolta.

Supporta --limit per i test (senza promuovere una raccolta parziale a completa).
No nuove dipendenze, no scritture a alpine-places.json.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from html import unescape
import json
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from normalize_cai_refuge_v1 import normalized

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rifugi.cai.it/api/v1/shelters"
CAI_CREDIT = "CAI · riuso confermato dal titolare del progetto"
USER_AGENT = "CimaBecco/1.0 (https://www.cimabecco.it; dati pubblici CAI)"
KNOWN_TYPES = {
    "rifugio custodito": ("rifugio", "custodito"),
    "rifugio incustodito": ("rifugio", "incustodito"),
    "bivacco": ("bivacco", "non_custodito"),
    "capanna sociale": ("other", "capanna_sociale"),
    "punto d'appoggio": ("other", "punto_appoggio"),
}
RISKY_FIELD_PREFIXES = ("taxCode_", "pec_", "contract_", "user_", "role_")
HISTORY_HTML_RE = re.compile(r"<[^>]+>")
VALID_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif"}
SAFE_ID = re.compile(r"^\d{1,20}$")


def valid_url(url):
    return isinstance(url, str) and url.startswith("https://") and not re.search(r"\s", url)


def text_value(value, max_chars=320):
    if isinstance(value, (dict, list, bool)) or value is None:
        return None
    text = unescape(HISTORY_HTML_RE.sub(" ", str(value)))
    text = " ".join(text.split())[:max_chars]
    if text.casefold() in {"", "-1", "n.d.", "n/d", "n/a", "null", "unknown"}:
        return None
    return text


def geo_point(row):
    p = row.get("geo")
    if not isinstance(p, dict) or p.get("type") != "Point":
        return None
    c = p.get("coordinates")
    if not isinstance(c, list) or len(c) != 2:
        return None
    lng, lat = c
    if (isinstance(lng, bool) or isinstance(lat, bool) or
        not isinstance(lng, (float, int)) or not isinstance(lat, (float, int)) or
        not -180 <= lng <= 180 or not -90 <= lat <= 90):
        return None
    return {"lat": lat, "lng": lng}


def field_fact(key, value, cai_id, *, unit=None, updated=None, label=None, notes=None):
    out = {
        "value": value, "sourceId": "cai:shelter:" + cai_id,
        "sourceUrl": "https://rifugi.cai.it/shelters/" + cai_id,
        "licence": CAI_CREDIT, "method": "reported",
    }
    if unit:
        out["unit"] = unit
    if updated:
        out["sourceUpdatedAt"] = updated
    if label:
        out["label"] = label
    if notes:
        out["notes"] = notes
    return out


def map_detail(detail, mapping, proposals):
    code = str(detail.get("id_cai", ""))
    if not SAFE_ID.fullmatch(code):
        raise ValueError("Dettaglio CAI senza id_cai")
    if not isinstance(detail.get("fields"), list):
        raise ValueError("Dettaglio CAI senza fields[]")
    by_field = {e.get("name"): e for e in detail["fields"]
                if isinstance(e, dict) and isinstance(e.get("name"), str)}
    rules = {x["sourceField"]: x for x in mapping["fields"]}
    private = set(mapping["sensitiveExact"])
    prefix = tuple(mapping["sensitivePrefixes"]) + RISKY_FIELD_PREFIXES
    proposals = {x["sourceField"]: x for x in proposals["proposals"]}
    result, alt, unknown = {}, [], set()
    schedule_present = False
    for source_field, obj in sorted(by_field.items()):
        if source_field in private or source_field.startswith(prefix):
            continue
        raw = obj.get("value")
        if source_field == "openingTime_contact" and isinstance(obj.get("data"), list) and obj["data"]:
            schedule_present = True
        rule = rules.get(source_field)
        extra = proposals.get(source_field)
        if rule:
            field_name = rule["target"]
            value = normalized(raw, rule["converter"])
            if isinstance(value, dict) and "label" in value:
                value = value["label"]
            if field_name == "description":
                value = text_value(raw, 2400)
            if field_name == "aliases":
                value = text_value(raw, 320)
            if value is None:
                continue
            # Non chiamare ID un nome di comune/gruppo non riconciliato.
            if rule["converter"] == "name_candidate_not_id":
                field_name = field_name.replace("Id", "NameReported")
            if field_name == "openingHours":
                field_name = "openingHoursReported"  # no apertura corrente
            note = rule.get("notes")
            if field_name == "description":
                note = "Descrizione CAI, versione dichiarata nel catalogo."
            unit = "m" if field_name == "elevationM" else "posti" if field_name in {
                "bedsTotal", "bedsWinter", "managerBeds"} else None
            entry = field_fact(field_name, value, code, updated=obj.get("updated_at"),
                               unit=unit, notes=note)
        elif extra:
            mode = extra["normalization"]
            if mode in {"hold_for_technical_verification", "numeric_or_boolean_requires_shape",
                        "categorical_or_boolean_requires_shape", "name_requires_entity_resolution"}:
                unknown.add(source_field)
                continue
            field_name = extra["suggestedField"]
            if mode == "tri_state_boolean":
                value = normalized(raw, "reported_bool")
            elif mode == "nonnegative_integer":
                value = normalized(raw, "nonnegative_int")
            else:
                value = text_value(raw, 280)
            if value is None:
                continue
            entry = field_fact(field_name, value, code, updated=obj.get("updated_at"),
                               notes=extra.get("reviewNote"))
        else:
            unknown.add(source_field)
            continue
        if field_name in result:
            if result[field_name]["value"] != entry["value"]:
                alt.append({"key": field_name, "fact": entry, "reason": "CAI ha più campi relativi alla stessa proprietà"})
        else:
            result[field_name] = entry
    return result, alt, schedule_present, sorted(unknown)


def media_from_detail(detail):
    code = str(detail["id_cai"])
    result, seen = [], set()
    for row in detail.get("media") or []:
        if not isinstance(row, dict) or row.get("mime_type") not in VALID_IMAGE_TYPES:
            continue
        url = row.get("original_url")
        if not valid_url(url):
            continue
        key = row.get("uuid")
        if not isinstance(key, str) or not key or key in seen:
            continue
        seen.add(key)
        props = row.get("custom_properties") if isinstance(row.get("custom_properties"), dict) else {}
        author = text_value(props.get("author") or props.get("photographer"), 120)
        description = text_value(row.get("name"), 180)
        kind = "logo" if "logo" in str(row.get("collection_name", "")).casefold() else "photo"
        result.append({
            "id": "cai:media:" + key, "kind": kind, "url": url,
            "sourceUrl": "https://rifugi.cai.it/shelters/" + code,
            "author": author or "Autore non specificato · catalogo CAI",
            "licence": CAI_CREDIT, "caption": description or "",
            "subjectVerified": True, "reuseAllowed": True,
        })
    return result


def normalize_detail(row, detail, mapping, proposals):
    code = str(row.get("id_cai", ""))
    if not SAFE_ID.fullmatch(code) or str(detail.get("id_cai")) != code:
        raise ValueError("ID CAI elenco e dettaglio diversi")
    if not row.get("published") or row.get("deleted_at") not in (None, ""):
        return None
    p = geo_point(row) or geo_point(detail)
    if p is None:
        return None
    values = {f["name"]: f.get("value") for f in detail["fields"]
              if isinstance(f, dict) and f.get("name") in ("type", "status", "category")}
    original_type = text_value(values.get("type"), 120)
    definition = KNOWN_TYPES.get((original_type or "").casefold())
    if definition is None:
        return {"caiId": code, "kind": "unclassified", "originalType": original_type,
                "revision": row.get("updated_at")}
    kind, subtype = definition
    facts, alternatives, schedule, unknown = map_detail(detail, mapping, proposals)
    altitude = row.get("altitude_geo")
    altitude = altitude if isinstance(altitude, (int, float)) and not isinstance(altitude, bool) and 0 < altitude < 9000 else None
    if altitude is not None and "elevationM" not in facts:
        facts["elevationM"] = field_fact("elevationM", int(altitude), code, unit="m",
                                        updated=row.get("updated_at"))
    original_status = text_value(values.get("status"), 90)
    if original_status:
        facts["caiCatalogueStatus"] = field_fact(
            "caiCatalogueStatus", original_status, code,
            updated=row.get("updated_at"),
            notes="Stato dichiarato nel catalogo CAI; non attesta l'apertura oggi.")
    category = text_value(values.get("category"), 24)
    if category:
        facts["caiCategory"] = field_fact("caiCategory", category, code)
    photos = media_from_detail(detail)
    name = text_value(row.get("title"), 220) or text_value(detail.get("title"), 220)
    if not name:
        raise ValueError("Rifugio CAI senza nome")
    url = "https://rifugi.cai.it/shelters/" + code
    description = facts.get("description", {}).get("value")
    return {
        "id": "cai:" + code, "caiId": code,
        "slug": "cai-" + code, "name": name,
        "kind": kind, "subtype": subtype, "originalType": original_type,
        "lat": p["lat"], "lng": p["lng"], "sourceUrl": url,
        "revision": row.get("updated_at"),
        "sourceIds": {"cai": code},
        "facts": facts, "factsAlternatives": alternatives,
        "description": description,
        "openingScheduleStructured": schedule,
        "media": photos,
        "webcams": [], "quality": {"gate": "G1", "seoIndexable": False},
        "unmappedFieldNames": unknown,
    }


def fetch_json(url):
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    last = None
    for retry in range(4):
        try:
            with urlopen(request, timeout=45) as response:
                if response.status != 200:
                    raise ValueError("CAI HTTP " + str(response.status))
                blob = response.read(2_500_001)
                if len(blob) > 2_500_000:
                    raise ValueError("JSON CAI oltre 2,5 MB")
                return json.loads(blob)
        except (URLError, HTTPError, TimeoutError, json.JSONDecodeError) as e:
            last = e
            time.sleep(min(12, 0.7 * 2 ** retry))
    raise RuntimeError("CAI fetch non riuscito per " + url) from last


def fetch_catalogue(api=fetch_json, page_size=80):
    first = api(BASE + "?" + urlencode({"per_page": page_size, "page": 1}))
    if not isinstance(first, dict) or not isinstance(first.get("data"), list):
        raise ValueError("CAI pagination cambiata")
    total = first.get("total")
    if not isinstance(total, int) or total < 1 or total > 100_000:
        raise ValueError("CAI count non plausibile")
    pages = (total + page_size - 1) // page_size
    result = first["data"][:]
    for page in range(2, pages + 1):
        payload = api(BASE + "?" + urlencode({"per_page": page_size, "page": page}))
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            raise ValueError("CAI pagination incompleta")
        result.extend(payload["data"])
    if len(result) != total:
        raise ValueError("CAI catalogo incompleto: " + str(len(result)) + "/" + str(total))
    # Il listato reale CAI ha mostrato un ID ripetuto tra 764 righe.
    # Se identità interna, nome e coordinate coincidono, è una doppia riga
    # della stessa struttura. Altrimenti il codice CAI è ambiguo: accantoniamo
    # tutto il gruppo, senza scegliere il primo e senza fondere due strutture.
    from collections import defaultdict
    groups = defaultdict(list)
    missing = 0
    for row in result:
        code = str(row.get("id_cai", ""))
        if not SAFE_ID.fullmatch(code) or code == "0":
            missing += 1
            continue
        groups[code].append(row)
    selected, collisions, repeats = [], [], 0
    for code, variants in sorted(groups.items()):
        if len(variants) == 1:
            selected.append(variants[0])
            continue
        fingerprints = {(str(v.get("id")), str(v.get("title")),
                         json.dumps(v.get("geo"), sort_keys=True)) for v in variants}
        if len(fingerprints) == 1:
            repeats += len(variants)-1
            # Preferisci la versione con updated_at più recente SOLO se identità uguale.
            selected.append(max(variants, key=lambda x: str(x.get("updated_at") or "")))
        else:
            collisions.append(code)
    if len(collisions) + missing > max(10, total // 20):
        raise ValueError("CAI anomalie identità troppo numerose: " +
                         str(len(collisions)) + " collisioni, " +
                         str(missing) + " righe senza ID")
    if collisions or repeats or missing:
        print(json.dumps({"catalogueIdentityReview": {
            "rows": total, "repeatedIdentical": repeats,
            "ambiguousIdsQuarantined": collisions[:30],
            "invalidIdRows": missing, "selected": len(selected)}}, sort_keys=True))
    return selected


def build_catalogue(rows, details_by_id, mapping, proposals, previous=None, *, complete=True):
    previous_by_id = {x["caiId"]: x for x in (previous or {}).get("records", [])
                      if x.get("caiId")}
    records, errors = [], []
    for row in rows:
        if row.get("published") is False or row.get("deleted_at") not in (None, ""):
            continue
        key = str(row["id_cai"])
        old = previous_by_id.get(key)
        if old and old.get("revision") == row.get("updated_at"):
            records.append(old)
            continue
        doc = details_by_id.get(key)
        if doc is None:
            errors.append(key)
            continue
        result = normalize_detail(row, doc, mapping, proposals)
        if result:
            records.append(result)
    if errors:
        raise ValueError("Dettagli CAI mancanti (" + str(len(errors)) + "): " + ", ".join(errors[:8]))
    if complete and len(rows) < 100:
        raise ValueError("Inizializzazione CAI non completa: meno di 100 record")
    records.sort(key=lambda x: x["caiId"])
    clean = {
        "schemaVersion": "1.0", "source": "CAI Unico Rifugi REST API",
        "sourceUrl": "https://rifugi.cai.it/api-info",
        "reuseAcknowledgement": "Riuso dati CAI confermato dal titolare Cima Becco",
        "isCompleteSnapshot": complete,
        "records": records,
    }
    digest = hashlib.sha256(json.dumps(clean, ensure_ascii=False, sort_keys=True,
                                       separators=(",", ":")).encode()).hexdigest()
    clean["contentSha256"] = digest
    return clean


def collect(previous=None, *, limit=None, api=fetch_json, workers=5):
    mapping = json.loads((ROOT / "scripts" / "cai_refuge_field_map_v1.json").read_text())
    proposals = json.loads((ROOT / "scripts" / "cai_unmapped_fields_review_plan_v1.json").read_text())
    rows = fetch_catalogue(api)
    complete = limit is None
    if limit is not None:
        rows = rows[:limit]
    previous_by_id = {r.get("caiId"): r for r in (previous or {}).get("records", [])}
    fetch_rows = [r for r in rows if r.get("published") and r.get("deleted_at") in (None, "")
                  and not (previous_by_id.get(str(r["id_cai"]), {}).get("revision") == r.get("updated_at"))]
    details = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(api, BASE + "/" + str(row["id_cai"])): str(row["id_cai"])
            for row in fetch_rows
        }
        errors = []
        for future in as_completed(futures):
            key = futures[future]
            try:
                details[key] = future.result()
            except Exception as exc:
                errors.append((key, type(exc).__name__))
        if errors:
            raise RuntimeError("CAI detail fetch error: " + repr(errors[:12]))
    result = build_catalogue(rows, details, mapping, proposals, previous, complete=complete)
    kinds = {}
    for rec in result["records"]:
        kinds[rec["kind"]] = kinds.get(rec["kind"], 0) + 1
    return result, {"catalogueRows": len(rows), "detailRequests": len(fetch_rows),
                    "reused": len(rows) - len(fetch_rows),
                    "exported": len(result["records"]),
                    "byKind": kinds, "bytes": len(json.dumps(result))}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=ROOT / "public" / "data" /
                   "atlas" / "cai-refuges-v1.json")
    p.add_argument("--limit", type=int, default=None, help="Solo campione CI, non completo")
    p.add_argument("--workers", type=int, default=5)
    args = p.parse_args()
    if args.workers < 1 or args.workers > 7:
        p.error("--workers deve essere 1–7")
    previous = json.loads(args.out.read_text(encoding="utf-8")) if args.out.is_file() else None
    if previous and not previous.get("isCompleteSnapshot"):
        previous = None
    result, report = collect(previous, limit=args.limit, workers=args.workers)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(result, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":")) + "\n"
    if not args.out.is_file() or args.out.read_text(encoding="utf-8") != payload:
        tmp = args.out.with_suffix(".tmp")
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(args.out)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
