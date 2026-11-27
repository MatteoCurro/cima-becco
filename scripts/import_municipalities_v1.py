#!/usr/bin/env python3
"""Blocco 3: comuni ISTAT + sindaci DAIT, staging soltanto.

Specifica vincolante: docs/MODELLO_METADATI_E_LAYOUT.md (sez. 1, 2, 30, 31).
Non trasforma i borghi OSM in comuni per nome o distanza; non pubblica SEO.
Accetta uno snapshot ISTAT .xlsx/.csv e un CSV DAIT opzionale: nessuna fonte
viene interrogata da questo normalizzatore, per ripetibilita' e audit.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
from datetime import date, datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import re
import unicodedata
from uuid import UUID, uuid5
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
ISTAT_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx"
DAIT_URL = "https://dait.interno.gov.it/documenti/sindaciincarica.csv"
NAMESPACE = UUID("b1c52f9e-6ed4-4d40-acbb-d9a02df32a35")
EXCEL_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
UNKNOWN = {"", "-", "--", "n.d.", "nd", "non disponibile", "non pervenuto", "-1"}

def require(value, message):
    if not value:
        raise ValueError(message)

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def canonical_bytes(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")

def save(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))

def header(value):
    s = unicodedata.normalize("NFKD", str(value or ""))
    s = "".join(c for c in s if not unicodedata.combining(c)).lower()
    return re.sub(r"[^a-z0-9]+", " ", s).strip()

def slugify(value):
    return header(value).replace(" ", "-")[:110].rstrip("-")

def get(row, *terms):
    for term in terms:
        if term in row:
            v = row[term]
            if v is None:
                return None
            value = str(v).strip()
            return None if value.casefold() in UNKNOWN else value
    return None

def find_col(keys, *options):
    """An exact normalized header wins; contains matches only if unambiguous."""
    for option in options:
        k = header(option)
        if k in keys:
            return k
    for option in options:
        k = header(option)
        found = [x for x in keys if k in x and ("storico" not in x)]
        if len(found) == 1:
            return found[0]
    return None

def code6(value):
    v = str(value or "").strip()
    if re.fullmatch(r"\d{1,6}(?:\.0)?", v):
        code = v.split(".")[0].zfill(6)
        if code != "000000":
            return code
    return None

def number(value, *, integer=False):
    v = str(value or "").strip()
    if v.casefold() in UNKNOWN:
        return None
    v = v.replace(" ", "").replace("\u00a0", "")
    if "," in v and "." in v:
        v = v.replace(".", "").replace(",", ".")
    elif "," in v:
        v = v.replace(",", ".")
    try:
        n = float(v)
    except ValueError:
        return None
    if not math.isfinite(n) or n < 0:
        return None
    if integer:
        return int(n) if n.is_integer() else None
    return n

def csv_matrix(raw):
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    variants = []
    for delimiter in (";", ",", "\t"):
        rows = list(csv.reader(io.StringIO(text), delimiter=delimiter))
        variants.append(rows)
    return variants

def xlsx_matrices(raw):
    """Read only cell values from the official XLSX; no office runtime needed."""
    with ZipFile(io.BytesIO(raw)) as book:
        members = set(book.namelist())
        strings = []
        if "xl/sharedStrings.xml" in members:
            root = ET.fromstring(book.read("xl/sharedStrings.xml"))
            for si in root.findall(EXCEL_NS + "si"):
                strings.append("".join(t.text or "" for t in si.iter(EXCEL_NS + "t")))
        sheets = sorted(p for p in members
                        if re.fullmatch(r"xl/worksheets/sheet\d+\.xml", p))
        require(sheets, "XLSX senza fogli leggibili")
        matrices = []
        for sheet in sheets:
            root = ET.fromstring(book.read(sheet))
            matrix = []
            for row in root.iter(EXCEL_NS + "row"):
                cells = {}
                for cell in row.findall(EXCEL_NS + "c"):
                    ref = cell.get("r", "")
                    match = re.match(r"([A-Z]+)", ref)
                    if not match:
                        continue
                    idx = 0
                    for letter in match.group(1):
                        idx = idx * 26 + (ord(letter) - 64)
                    idx -= 1
                    v = cell.find(EXCEL_NS + "v")
                    inline = cell.find(EXCEL_NS + "is")
                    raw_value = v.text if v is not None else None
                    if cell.get("t") == "s" and raw_value is not None:
                        value = strings[int(raw_value)]
                    elif cell.get("t") == "inlineStr" and inline is not None:
                        value = "".join(t.text or "" for t in inline.iter(EXCEL_NS + "t"))
                    else:
                        value = raw_value
                    cells[idx] = value
                if cells:
                    matrix.append([cells.get(i) for i in range(max(cells) + 1)])
            matrices.append(matrix)
        return matrices

def headered_rows(matrices, required):
    for matrix in matrices:
        for index, titles in enumerate(matrix[:25]):
            names = [header(x) for x in titles]
            keys = [set(names) for _ in (0,)]
            if all(find_col(keys[0], *alternatives) for alternatives in required):
                used = [(i, n) for i, n in enumerate(names) if n]
                rows = [
                    {name: row[i] if i < len(row) else None for i, name in used}
                    for row in matrix[index + 1:] if any(x is not None and str(x).strip() for x in row)
                ]
                return rows, names, matrix[:index]
    raise ValueError("Intestazioni ufficiali non riconosciute; nessun import parziale")

ISTAT_CODE = ("codice comune formato alfanumerico", "codice istat del comune alfanumerico",
              "codice istat comune", "codice comune", "codice istat")
ISTAT_NAME = ("denominazione in italiano e straniero", "denominazione italiana e straniera",
              "denominazione in italiano", "denominazione del comune", "denominazione comune", "comune")
ISTAT_REGION = ("denominazione regione", "regione")
ISTAT_PROVINCE = ("denominazione dell unita territoriale sovracomunale",
                  "denominazione unita territoriale sovracomunale", "provincia")
DAIT_CODE = ("codice istat comune", "codice comune", "codice istat", "cod com")
DAIT_SURNAME = ("cognome",)
DAIT_NAME = ("nome",)
DAIT_ROLE = ("carica", "carica ricoperta", "descrizione carica", "funzione", "qualifica")
DAIT_ELECTION = ("data elezione", "data di elezione", "eletto il")

def rows_istat(raw):
    matrices = xlsx_matrices(raw) if raw[:2] == b"PK" else csv_matrix(raw)
    rows, cols, preamble = headered_rows(matrices, [ISTAT_CODE, ISTAT_NAME, ISTAT_REGION, ISTAT_PROVINCE])
    return rows, cols, preamble

def rows_dait(raw):
    rows, cols, preamble = headered_rows(csv_matrix(raw), [DAIT_CODE, DAIT_SURNAME, DAIT_NAME, DAIT_ROLE])
    return rows, cols, preamble

def field(row, columns, *names):
    key = find_col(set(columns), *names)
    return get(row, key) if key else None

def fact(value, source_id, source_url, *, unit=None, as_of=None, valid_at=None, method="reported", licence=None):
    return {
        "value": value, "unit": unit, "sourceId": source_id,
        "sourceUrl": source_url, "licence": licence,
        "retrievedAt": as_of, "sourceUpdatedAt": None,
        "validFrom": valid_at, "validUntil": None,
        "method": method, "confidence": 1.0,
    }

def municipality(row, cols, retrieved_at):
    code = code6(field(row, cols, *ISTAT_CODE))
    name = field(row, cols, *ISTAT_NAME)
    if not code or not name:
        return None
    region = field(row, cols, *ISTAT_REGION)
    province = field(row, cols, *ISTAT_PROVINCE)
    require(region and province, "Comune ISTAT senza gerarchia " + code)
    source_id = "istat:municipality:" + code
    facts = {}
    values = [
        ("regionName", region, None),
        ("provinceName", province, None),
        ("italianName", field(row, cols, "denominazione in italiano"), None),
        ("localName", field(row, cols, "denominazione altra lingua"), None),
        ("quotaCentroM", number(field(row, cols, "altitudine del centro metri", "altitudine del centro")), "m"),
        ("superficieKm2", number(field(row, cols, "superficie territoriale kmq", "superficie territoriale km2")), "km2"),
    ]
    for key, value, unit in values:
        if value is not None:
            facts[key] = fact(value, source_id, ISTAT_URL, unit=unit, as_of=retrieved_at)
    return {
        "id": "municipality:" + str(uuid5(NAMESPACE, "IT/ISTAT/" + code)),
        "kind": "municipality", "subtype": "italian_municipality",
        "name": name, "slug": slugify(name), "slugAliases": [],
        "sourceIds": {"istat": code}, "geo": {"point": None, "area": None},
        "administrativeHierarchy": {"countryCode": "IT", "region": region, "province": province,
                                    "municipalityCodeISTAT": code},
        "facts": facts, "factsAlternatives": [], "relations": [], "media": [],
        "aliases": [], "editorialStatus": "raw",
        "quality": {"gate": "G0", "seoIndexable": False, "reviewRequired": True},
    }

def valid_date(value):
    v = str(value or "").strip()
    if not v or v in UNKNOWN:
        return None
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(v, fmt).date().isoformat()
        except ValueError:
            continue
    return None

def attach_mayors(entities, rows, cols, retrieved_at):
    keys = set(cols)
    kind_key = find_col(keys, *DAIT_ROLE)
    date_key = find_col(keys, *DAIT_ELECTION)
    require(kind_key, "DAIT privo della colonna carica")
    index = defaultdict(list)
    count_unmatched = 0
    for row in rows:
        role = header(get(row, kind_key))
        if role not in ("sindaco", "sindaca"):
            continue
        code = code6(field(row, cols, *DAIT_CODE))
        if not code:
            count_unmatched += 1
            continue
        surname = field(row, cols, *DAIT_SURNAME)
        given = field(row, cols, *DAIT_NAME)
        if not surname or not given:
            continue
        index[code].append((given + " " + surname, valid_date(get(row, date_key)) if date_key else None))
    attached = ambiguous = 0
    for entity in entities:
        code = entity["sourceIds"]["istat"]
        entries = sorted(set(index.get(code, [])))
        if len(entries) > 1:
            ambiguous += 1
            entity["quality"]["reviewRequired"] = True
            continue
        if not entries:
            continue
        person, election_day = entries[0]
        attached += 1
        entity["facts"]["sindacoNome"] = fact(person, "dait:mayors:" + code, DAIT_URL,
                                                     as_of=retrieved_at, valid_at=election_day)
        entity["facts"]["carica"] = fact("Sindaco", "dait:mayors:" + code, DAIT_URL,
                                            as_of=retrieved_at)
        if election_day:
            entity["facts"]["dataElezione"] = fact(election_day, "dait:mayors:" + code,
                                                         DAIT_URL, as_of=retrieved_at)
        # A DAIT snapshot documents the office at extraction, NOT open-ended current tenure.
    return {"mayorsMatched": attached, "mayorsAmbiguous": ambiguous,
            "daitCodesUnmatched": sorted(set(index) - {e["sourceIds"]["istat"] for e in entities})[:100],
            "daitRowsWithoutCode": count_unmatched, "daitMayorCandidates": sum(map(len, index.values()))}

def reconcile_osm(entities, places, qid_map):
    """Only verified WD ISTAT ID -> QID -> unique OSM QID, never a name-based merge."""
    municipality_by_code = {e["sourceIds"]["istat"]: e for e in entities}
    qid_to_code = {}
    contested = set()
    for record in qid_map:
        code = code6(record.get("istatCode"))
        qid = str(record.get("wikidata") or "")
        if not code or not re.fullmatch(r"Q[1-9]\d*", qid) or code not in municipality_by_code:
            continue
        if qid in qid_to_code and qid_to_code[qid] != code:
            contested.add(qid)
        qid_to_code[qid] = code
    by_qid = defaultdict(list)
    for place in places:
        if place.get("kind") == "borgo" and place.get("wikidata") in qid_to_code:
            by_qid[place["wikidata"]].append(place)
    linked = 0
    review = []
    for qid, code in sorted(qid_to_code.items()):
        if qid in contested:
            review.append({"qid": qid, "reason": "conflicting_istat_id"})
            continue
        found = by_qid.get(qid, [])
        if len(found) != 1:
            if found:
                review.append({"qid": qid, "reason": "non_unique_osm_entity", "count": len(found)})
            continue
        place = found[0]
        lat, lng = place.get("lat"), place.get("lng")
        if not (isinstance(lat, (int, float)) and not isinstance(lat, bool) and
                isinstance(lng, (int, float)) and not isinstance(lng, bool)
                and math.isfinite(lat) and math.isfinite(lng) and -90 <= lat <= 90 and -180 <= lng <= 180):
            continue
        entity = municipality_by_code[code]
        if header(place.get("name")) != header(entity["name"]):
            review.append({"qid": qid, "reason": "name_discrepancy", "istatCode": code})
            continue
        osm_match = re.fullmatch(r"https://www[.]openstreetmap[.]org/(node|way|relation)/([1-9][0-9]*)", str(place.get("osmUrl") or ""))
        if not osm_match:
            review.append({"qid": qid, "reason": "invalid_osm_source", "istatCode": code})
            continue
        entity["sourceIds"].update({"wikidata": qid, "osm": osm_match.group(1) + "/" + osm_match.group(2)})
        entity["geo"]["point"] = {"lat": lat, "lng": lng}
        entity["geo"]["method"] = "osm_settlement_point_not_administrative_centroid"
        entity["geo"]["sourceUrl"] = place.get("osmUrl")
        entity["quality"].update({"gate": "G1", "reviewRequired": False})
        entity["editorialStatus"] = "linked"
        linked += 1
    return {"osmLinkedByVerifiedIds": linked, "osmIdentityReview": review}

def near_links(entities, resources, max_km=20, limit=6):
    """Proximity from an OSM settlement point, NOT municipal inclusion or access."""
    linked = 0
    for entity in entities:
        origin = entity["geo"].get("point")
        if not origin:
            continue
        results = []
        for target in resources:
            point = target.get("geo", {}).get("point")
            if not point or target.get("kind") not in ("refuge", "bivouac", "shelter"):
                continue
            a = math.radians(origin["lat"])
            b = math.radians(point["lat"])
            dlat = b - a
            dlng = math.radians(point["lng"] - origin["lng"])
            hav = math.sin(dlat / 2) ** 2 + math.cos(a) * math.cos(b) * math.sin(dlng / 2) ** 2
            km = 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(max(0, hav))))
            if km <= max_km:
                results.append((km, target))
        results.sort(key=lambda x: (x[0], x[1]["id"]))
        for km, target in results[:limit]:
            entity["relations"].append({
                "type": "near",
                "target": {"id": target["id"], "kind": target["kind"],
                           "name": target["name"], "slug": target["slug"]},
                "straightLineKm": round(km, 2), "method": "haversine",
                "verified": False, "accessVerified": False,
                "sourceUrl": entity["geo"]["sourceUrl"],
                "notes": "Distanza dal punto OSM dell'abitato, non dal confine comunale",
            })
            linked += 1
    return linked

def slug_uniqueness(entities, previous=None):
    previous_map = {e["sourceIds"]["istat"]: e for e in (previous or {}).get("entities", [])}
    for entity in entities:
        old = previous_map.get(entity["sourceIds"]["istat"])
        if old:
            entity["id"] = old["id"]
            entity["slug"] = old["slug"]
            entity["slugAliases"] = old.get("slugAliases", [])
    grouped = defaultdict(list)
    for entity in entities:
        grouped[entity["slug"]].append(entity)
    for group in grouped.values():
        if len(group) <= 1:
            continue
        for entity in group:
            if entity["sourceIds"]["istat"] in previous_map:
                continue
            suffix = slugify(entity["administrativeHierarchy"]["province"])
            entity["slug"] += "-" + suffix
    require(len({x["slug"] for x in entities}) == len(entities),
            "Slug omonimi ancora ambigui: revisione necessaria (nessun ID pubblico)")

def build(istat_raw, dait_raw=None, *, retrieved_at, osm_places=None, qid_map=None, previous=None,
          nearby_entities=None, min_municipalities=7800):
    rows, cols, _ = rows_istat(istat_raw)
    entities = []
    codes = set()
    duplicates = []
    for row in rows:
        entity = municipality(row, cols, retrieved_at)
        if entity is None:
            continue
        code = entity["sourceIds"]["istat"]
        if code in codes:
            duplicates.append(code)
            continue
        codes.add(code)
        entities.append(entity)
    require(not duplicates, "ISTAT contiene codici duplicati: " + str(duplicates[:10]))
    require(len(entities) >= min_municipalities,
            "Numero comuni ISTAT insufficiente: " + str(len(entities)))
    require(len(entities) <= 9000, "Anagrafe ISTAT sospettosamente grande")
    mayors = {"mayorsMatched": 0, "mayorsAmbiguous": 0, "daitInputAvailable": dait_raw is not None}
    if dait_raw is not None:
        dait_rows, dait_cols, _ = rows_dait(dait_raw)
        mayors.update(attach_mayors(entities, dait_rows, dait_cols, retrieved_at))
    links = reconcile_osm(entities, osm_places or [], qid_map or [])
    links["nearbyRefugesAndShelters"] = near_links(entities, nearby_entities or [])
    slug_uniqueness(entities, previous)
    entities.sort(key=lambda e: e["sourceIds"]["istat"])
    report = {
        "stageOnly": True, "municipalities": len(entities),
        "istatRowsParsed": len(rows), "istatBytesSha256": hashlib.sha256(istat_raw).hexdigest(),
        "daitBytesSha256": hashlib.sha256(dait_raw).hexdigest() if dait_raw else None,
        **mayors, **links,
        "missingMunicipalGeometry": sum(e["geo"]["point"] is None for e in entities),
        "indexed": sum(e["quality"]["seoIndexable"] for e in entities),
        "rejectedUnknownPopulationOrMandate": True,
        "removedComparedWithPrevious": sorted({e["sourceIds"]["istat"] for e in (previous or {}).get("entities", [])} - codes),
    }
    result = {"schemaVersion": "1.0", "releaseChannel": "ISTAT_DAIT_MUNICIPALITIES_STAGING",
              "isPublished": False, "retrievedAt": retrieved_at,
              "sources": [{"id": "istat", "url": ISTAT_URL, "sha256": report["istatBytesSha256"]}] +
                ([{"id": "dait", "url": DAIT_URL, "sha256": report["daitBytesSha256"]}] if dait_raw else []),
              "entities": entities}
    return result, report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--istat-file", type=Path, required=True)
    parser.add_argument("--dait-file", type=Path)
    parser.add_argument("--osm-places", type=Path)
    parser.add_argument("--qid-map", type=Path, help="Mappe QID/ISTAT con P635 verificato; mai match per nome")
    parser.add_argument("--previous", type=Path)
    parser.add_argument("--refuges-file", type=Path)
    parser.add_argument("--shelters-file", type=Path)
    parser.add_argument("--out", type=Path, default=ROOT / "build/import-municipalities-v1")
    parser.add_argument("--retrieved-at", default=datetime.now(timezone.utc).isoformat(timespec="seconds"))
    parser.add_argument("--min-municipalities", type=int, default=7800)
    args = parser.parse_args()
    raw_istat = args.istat_file.read_bytes()
    raw_dait = args.dait_file.read_bytes() if args.dait_file else None
    osm = load(args.osm_places).get("places", []) if args.osm_places else None
    qid_map = load(args.qid_map) if args.qid_map else None
    if isinstance(qid_map, dict):
        qid_map = qid_map.get("associations", [])
    nearby = []
    for data_file in (args.refuges_file, args.shelters_file):
        if data_file:
            nearby.extend(load(data_file).get("entities", []))
    previous = load(args.previous) if args.previous else None
    result, report = build(raw_istat, raw_dait, retrieved_at=args.retrieved_at,
                           osm_places=osm, qid_map=qid_map, previous=previous,
                           nearby_entities=nearby, min_municipalities=args.min_municipalities)
    # Immutable raw inputs identified by content digest; no overwrite on collision.
    raw_dir = args.out / "raw"
    for name, content in (("istat", raw_istat), ("dait", raw_dait)):
        if content is None:
            continue
        path = raw_dir / (name + "-" + hashlib.sha256(content).hexdigest() + (".xlsx" if content[:2] == b"PK" else ".csv"))
        if path.exists():
            require(path.read_bytes() == content, "Collisione snapshot raw")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
    save(args.out / "municipalities.json", result)
    save(args.out / "report.json", report)
    print(json.dumps({k: v for k, v in report.items() if k not in ("osmIdentityReview", "daitCodesUnmatched")},
                     ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
