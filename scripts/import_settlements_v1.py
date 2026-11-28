#!/usr/bin/env python3
"""Blocco 4 Cima Becco: localita ISTAT 2021 e abitati OSM, solo staging.

Specifica vincolante: docs/MODELLO_METADATI_E_LAYOUT.md sezioni 1, 3, 30, 31.
Una localita censuaria NON e automaticamente una frazione amministrativa.
Prossimita e uguaglianza dei nomi NON dimostrano identita, appartenenza o accesso.
Questo adapter non scrive public/data e non crea pagine SEO.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import math
import re
from uuid import UUID, uuid5
from zipfile import ZipFile, BadZipFile

from import_municipalities_v1 import (
    load, save, slugify, header, code6, csv_matrix, headered_rows, fact, near_links,
)

NAMESPACE = UUID("0ee60b2e-1cb4-4ee8-bcb0-f35194f6a267")
ISTAT_BASE = "https://www.istat.it/storage/cartografia/basi_territoriali/2021/"
ISTAT_DOC = "https://www.istat.it/notizia/basi-territoriali-e-variabili-censuarie/"
SUBTYPES = {"1": "centro_abitato", "2": "nucleo_abitato",
            "3": "localita_produttiva", "4": "case_sparse"}
OSM_RE = re.compile(r"^https://www[.]openstreetmap[.]org/(node|way|relation)/([1-9][0-9]*)$")
QID_RE = re.compile(r"^Q[1-9][0-9]*$")
CSV_RE = re.compile(r"(^|/)LOC_R([0-9]{2})_21(?:_P)?[.]csv$", re.I)

def official_csvs(path):
    """Read documented 2021 LOC_Rxx_21 CSVs, never unrelated census tables."""
    raw = Path(path).read_bytes()
    digest = sha256(raw).hexdigest()
    if path.suffix.lower() == ".csv":
        if not CSV_RE.search(path.name):
            raise ValueError("CSV non riconosciuto come LOC_Rxx_21: " + path.name)
        return [(path.name, raw, digest)]
    if path.suffix.lower() != ".zip":
        raise ValueError("Input ISTAT: serve ZIP ufficiale Rxx_21 o LOC_Rxx_21.csv")
    results = []
    try:
        with ZipFile(BytesIO(raw)) as archive:
            for member in archive.infolist():
                if not CSV_RE.search(member.filename):
                    continue
                if member.file_size > 30_000_000:
                    raise ValueError("CSV localita troppo grande: " + member.filename)
                data = archive.read(member)
                results.append((member.filename, data, digest))
    except BadZipFile as exc:
        raise ValueError("Archivio ISTAT ZIP non valido") from exc
    if not results:
        raise ValueError("ZIP ISTAT privo di LOC_Rxx_21.csv: " + path.name)
    return results

def official_rows(data):
    required = [
        ("pro_com", "pro com"),
        ("loc21_id", "loc21 id"),
        ("tipo_loc", "tipo loc"),
        ("nome",),
    ]
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        # I file reali LOC_Rxx_21.csv sono UTF-16 con colonne TAB.
        data = data.decode("utf-16").encode("utf-8")
    elif b"\x00" in data[:128]:
        raise ValueError("CSV ISTAT con codifica non riconosciuta")
    # Il parser condiviso usa anche match "contains" sulle intestazioni, percio
    # puo scegliere un separatore errato se tutta la header TAB risulta in una
    # singola cella. Qui il tracciato ufficiale richiede match ESATTO dei campi.
    required_exact = {"pro com", "loc21 id", "tipo loc", "nome"}
    for matrix in csv_matrix(data):
        for index, titles in enumerate(matrix[:25]):
            cols = [header(x) for x in titles]
            if not required_exact.issubset(set(cols)):
                continue
            if len(cols) != len(set(cols)):
                raise ValueError("Intestazioni duplicate nel CSV ISTAT")
            return [{key: (row[i] if i < len(row) else None)
                     for i, key in enumerate(cols) if key}
                    for row in matrix[index + 1:]
                    if any(x is not None and str(x).strip() for x in row)]
    preview = data.decode("utf-8-sig", errors="replace").splitlines()[:3]
    raise ValueError("Intestazioni LOC 2021 non riconosciute; anteprima: " + repr([x[:240] for x in preview]))

def value(row, *keys):
    for key in keys:
        item = row.get(header(key))
        if item is not None and str(item).strip():
            return str(item).strip()
    return None

def digits(value, count):
    if value is None:
        return None
    s = str(value).strip()
    if not re.fullmatch(r"[0-9]+(?:[.]0)?", s):
        return None
    return s.split(".")[0].zfill(count)

def unique_slug(entities):
    """Stable staged collision suffixes; never depend on arbitrary batch order.

    A duplicated base slug can also collide with an existing literal name
    ending in -1 or -2, so ordinal suffixes are not safe. All such records
    remain G0/noindex and flagged before any URL is minted in production.
    """
    by_slug = defaultdict(list)
    for entity in entities:
        by_slug[entity["slug"]].append(entity)
    reserved = {slug for slug, group in by_slug.items() if len(group) == 1}
    groups = 0
    for slug, group in sorted(by_slug.items()):
        if len(group) < 2:
            continue
        groups += 1
        for entity in sorted(group, key=lambda row: row["id"]):
            stable = entity["id"].replace("-", "")
            for length in (8, 12, 16, 32):
                candidate = slug + "-" + stable[:length]
                if candidate not in reserved:
                    entity["slug"] = candidate
                    reserved.add(candidate)
                    break
            else:
                raise ValueError("Collisione slug con ID distinto: " + slug)
            entity["quality"]["slugRequiresReview"] = True
    return groups

def locality(row, *, source_url, checked_at, municipality_by_code):
    code = code6(value(row, "PRO_COM"))
    raw_id = digits(value(row, "LOC21_ID"), 11)
    raw_subcode = digits(value(row, "COD_LOC"), 5)
    subtype_code = digits(value(row, "TIPO_LOC"), 1)
    name = value(row, "NOME")
    if not (code and raw_id and re.fullmatch(r"[0-9]{11}", raw_id)
            and raw_id.startswith(code) and subtype_code in SUBTYPES and name
            and header(name)):
        return None, "invalid_istat_identity"
    if raw_subcode and raw_id != code + raw_subcode:
        return None, "conflicting_istat_locality_codes"
    if subtype_code in ("3", "4"):
        return None, "not_a_settlement"
    parent = municipality_by_code.get(code)
    source_id = "istat:locality:2021:" + raw_id
    source_fact = fact(SUBTYPES[subtype_code], source_id, source_url,
                       as_of=checked_at, valid_at="2021-12-31", licence="ISTAT open data")
    capital_raw = digits(value(row, "CENTRO_CL"), 1)
    capital = capital_raw == "1" if capital_raw in {"0", "1"} else None
    aliases = []
    if parent:
        base_slug = slugify(name + " " + parent["name"])
    else:
        base_slug = slugify(name)
    entity = {
        "id": str(uuid5(NAMESPACE, source_id)),
        "kind": "settlement",
        "subtype": SUBTYPES[subtype_code],
        "name": name,
        "displayName": name,
        "aliases": aliases,
        "slug": base_slug or "localita",
        "slugAliases": [],
        "shortSummary": None,
        "description": None,
        "history": None,
        "sourceIds": {"istatLocality": raw_id, "istatMunicipality": code},
        "administrativeHierarchy": {
            "country": "IT", "municipalityCodeISTAT": code,
            "municipalityName": parent["name"] if parent else None,
            "referenceDate": "2021-12-31",
        },
        "parentMunicipalityId": parent["id"] if parent else None,
        "parentMunicipalityName": parent["name"] if parent else None,
        "isMunicipalCapital": capital,
        "geo": {"point": None, "area": None, "method": None, "sourceUrl": None},
        "facts": {
            "istatLocalityType": source_fact,
            "istatReferenceDate": fact("2021-12-31", source_id, source_url,
                                       as_of=checked_at, licence="ISTAT open data"),
        },
        "relations": [],
        "media": [],
        "textSources": [],
        "editorialStatus": "raw",
        "quality": {"gate": "G0", "seoIndexable": False, "reviewRequired": False,
                    "geolocationMissing": True},
        "checkedAt": checked_at,
    }
    altitude_raw = value(row, "ALTITUDINE (in metri slm)", "ALTITUDINE")
    if altitude_raw and re.fullmatch(r"[0-9]+(?:[.,][0-9]+)?", altitude_raw):
        altitude = float(altitude_raw.replace(",", "."))
        if math.isfinite(altitude) and 0 <= altitude < 5000:
            entity["elevationM"] = altitude
            entity["elevationMethod"] = "istat_reported_locality_2021"
            entity["facts"]["elevationM"] = fact(
                altitude, source_id, source_url, unit="m", as_of=checked_at,
                valid_at="2021-12-31", licence="ISTAT open data")
    if capital is not None:
        entity["facts"]["isMunicipalCapital"] = fact(
            capital, source_id, source_url, as_of=checked_at,
            valid_at="2021-12-31", licence="ISTAT open data")
    if parent:
        entity["relations"].append({
            "type": "part_of",
            "target": {"id": parent["id"], "kind": "municipality",
                       "name": parent["name"], "slug": parent["slug"]},
            "verified": True, "method": "istat_loc21_pro_com",
            "sourceId": source_id, "sourceUrl": source_url,
            "validFrom": "2021-12-31",
            "notes": "Appartenenza censuaria 2021, non prova di frazione amministrativa",
        })
    return entity, None

def osm_settlement(place, *, checked_at, municipality_by_qid):
    if place.get("kind") != "borgo":
        return None, "not_settlement"
    match = OSM_RE.fullmatch(str(place.get("osmUrl") or ""))
    name = str(place.get("name") or "").strip()
    lat, lng = place.get("lat"), place.get("lng")
    if not (match and name and header(name)
            and isinstance(lat, (int, float)) and not isinstance(lat, bool)
            and isinstance(lng, (int, float)) and not isinstance(lng, bool)
            and math.isfinite(lat) and math.isfinite(lng)
            and -90 <= lat <= 90 and -180 <= lng <= 180):
        return None, "invalid_osm_identity_or_geo"
    qid = place.get("wikidata")
    parent_shadow = municipality_by_qid.get(qid)
    # Municipi gia identificati non diventano automaticamente frazioni.
    if parent_shadow:
        return None, "municipality_shadow_not_a_frazione"
    source_id = match.group(1) + "/" + match.group(2)
    facts = {}
    elevation = place.get("elevationM")
    if (isinstance(elevation, (int, float)) and not isinstance(elevation, bool)
            and math.isfinite(elevation) and -500 < elevation < 5000):
        method = "estimated" if place.get("elevationSource") == "dem" else "reported"
        facts["elevationM"] = fact(elevation, "osm:" + source_id,
            place["osmUrl"], unit="m", as_of=checked_at,
            method=method, licence="ODbL")
    entity = {
        "id": str(uuid5(NAMESPACE, "osm:" + source_id)),
        "kind": "settlement",
        "subtype": "abitato_osm_non_classificato",
        "name": name, "displayName": name,
        "aliases": [], "slug": slugify(name) or "abitato", "slugAliases": [],
        "shortSummary": None, "description": None, "history": None,
        "sourceIds": {"osm": source_id, **({"wikidata": qid}
                           if isinstance(qid, str) and QID_RE.fullmatch(qid) else {})},
        "administrativeHierarchy": {"country": "IT",
                                    "municipalityCodeISTAT": None},
        "parentMunicipalityId": None, "parentMunicipalityName": None,
        "isMunicipalCapital": None,
        "geo": {"point": {"lat": lat, "lng": lng},
                "area": None, "method": "osm_element_center",
                "sourceUrl": place["osmUrl"]},
        "facts": facts, "relations": [], "media": [], "textSources": [],
        "editorialStatus": "raw",
        "quality": {"gate": "G0", "seoIndexable": False, "reviewRequired": True,
                    "municipalityNotVerified": True},
        "checkedAt": checked_at,
    }
    return entity, None

def build(istat_sources, osm, municipalities, refuges=None, shelters=None, *,
          checked_at=None):
    checked_at = checked_at or datetime.now(timezone.utc).isoformat()
    muni = municipalities.get("entities") or []
    municipality_by_code = {
        str(x.get("sourceIds", {}).get("istat")): x for x in muni
        if re.fullmatch(r"[0-9]{6}", str(x.get("sourceIds", {}).get("istat") or ""))
    }
    municipality_by_qid = {
        x["sourceIds"]["wikidata"]: x for x in muni
        if QID_RE.fullmatch(str(x.get("sourceIds", {}).get("wikidata") or ""))
    }
    entities = []
    rejected = Counter()
    official_seen = set()
    manifest = []
    for path in istat_sources:
        for member, raw, archive_digest in official_csvs(Path(path)):
            region = CSV_RE.search(member).group(2)
            source_url = ISTAT_BASE + "R" + region + "_21.zip"
            rows = official_rows(raw)
            accepted = 0
            for row in rows:
                entity, reason = locality(row, source_url=source_url,
                    checked_at=checked_at, municipality_by_code=municipality_by_code)
                if reason:
                    rejected[reason] += 1
                    continue
                ident = entity["sourceIds"]["istatLocality"]
                if ident in official_seen:
                    rejected["duplicate_official_id"] += 1
                    continue
                official_seen.add(ident)
                entities.append(entity)
                accepted += 1
            manifest.append({"member": member, "sourceUrl": source_url,
                "archiveSha256": archive_digest, "rows": len(rows), "accepted": accepted})
    places = osm.get("places") or osm.get("entities") or []
    osm_count = 0
    for place in places:
        entity, reason = osm_settlement(place, checked_at=checked_at,
            municipality_by_qid=municipality_by_qid)
        if reason:
            if reason != "not_settlement":
                rejected[reason] += 1
            continue
        entities.append(entity)
        osm_count += 1
    # Mantenere identita separate: una localita ISTAT non viene fusa con
    # un punto OSM omonimo. Questo e un problema di entity resolution successivo.
    near_count = near_links(entities, (refuges or {}).get("entities", [])
                            + (shelters or {}).get("entities", []), max_km=10, limit=4)
    collisions = unique_slug(entities)
    entity_ids = [x["id"] for x in entities]
    if len(entity_ids) != len(set(entity_ids)):
        raise ValueError("Collisione ID: import sospeso")
    kinds = Counter(x["subtype"] for x in entities)
    linked = sum(bool(x["parentMunicipalityId"]) for x in entities)
    document = {
        "schemaVersion": "1.0",
        "canonicalSpec": "docs/MODELLO_METADATI_E_LAYOUT.md",
        "generatedAt": checked_at,
        "isPublished": False,
        "releaseChannel": "STAGING_ISTAT21_OSM_SETTLEMENTS",
        "entities": sorted(entities, key=lambda e: (e["name"].casefold(), e["id"])),
    }
    report = {
        "isPublished": False, "seoIndexable": 0, "officialRecords": len(official_seen),
        "osmRecords": osm_count, "totalEntities": len(entities),
        "subtypes": dict(sorted(kinds.items())),
        "documentedMunicipalityRelations": linked,
        "nearUnverified": near_count, "slugCollisionGroups": collisions,
        "rejected": dict(sorted(rejected.items())),
        "sources": manifest,
        "missing": {
            "officialGeolocation": "CSV LOC_Rxx_21 lacks reliable WGS84 point; GIS layer required",
            "frazioneStatus": "ISTAT locality is not proof of administrative frazione",
            "istatPopulation": "not imported; requires dated census data and locality ID",
            "municipalityForOsm": "not inferred by name, geography or province",
            "historicalPhotos": "not acquired without licensed Commons subject and capture date",
        },
    }
    return document, report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--istat-source", action="append", default=[])
    parser.add_argument("--osm", required=True)
    parser.add_argument("--municipalities", required=True)
    parser.add_argument("--refuges")
    parser.add_argument("--shelters")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out)
    doc, report = build(args.istat_source, load(args.osm),
        load(args.municipalities),
        load(args.refuges) if args.refuges else None,
        load(args.shelters) if args.shelters else None)
    out.mkdir(parents=True, exist_ok=True)
    save(out / "settlements.json", doc)
    save(out / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))

if __name__ == "__main__":
    main()
