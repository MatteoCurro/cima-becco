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
        try:
            rows = list(csv.reader(io.StringIO(text, newline=""), delimiter=delimiter))
        except csv.Error:
            # DAIT usa righe introduttive e campi citati: un separatore sbagliato
            # puo' fallire. Provare gli altri anziche' abortire lo snapshot.
            continue
        if rows:
            variants.append(rows)
    require(variants, "CSV ufficiale senza un separatore decodificabile")
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
DAIT_OFFICE_START = ("data entrata in carica",)
DAIT_REGION_CODE = ("codice regione",)
DAIT_PROVINCE_SIGLA = ("sigla provincia",)
DAIT_PROVINCE_CODE = ("codice provincia",)
DAIT_MUNICIPAL_NAME = ("denominazione comune",)

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
    # Registry is additive: retaining official identifiers for administrative,
    # cadastral and NUTS reconciliation does not invent geography or chronology.
    # Year-qualified legacy codes must remain strings, never numeric measures.
    field_map = [
        ("regionName", "denominazione regione"),
        ("provinceName", "denominazione dell unita territoriale sovracomunale"),
        ("italianName", "denominazione in italiano"),
        ("fullOfficialName", "denominazione italiana e straniera"),
        ("localName", "denominazione altra lingua"),
        ("regionCodeISTAT", "codice regione"),
        ("statisticalTerritorialUnitCode", "codice dell unita territoriale sovracomunale valida a fini statistici"),
        ("provinceCodeHistorical", "codice provincia storico 1"),
        ("municipalityProgressive", "progressivo del comune 2"),
        ("geographicalMacroRegionCode", "codice ripartizione geografica"),
        ("geographicalMacroRegionName", "ripartizione geografica"),
        ("statisticalTerritorialUnitTypeCode", "tipologia di unita territoriale sovracomunale"),
        ("vehicleRegistrationProvinceCode", "sigla automobilistica"),
        ("municipalityNumericCode", "codice comune formato numerico"),
        ("municipalityNumericCode2017to2025", "codice comune numerico con 107 province dal 2017 al 2025"),
        ("municipalityNumericCode2010to2016", "codice comune numerico con 110 province dal 2010 al 2016"),
        ("municipalityNumericCode2006to2009", "codice comune numerico con 107 province dal 2006 al 2009"),
        ("municipalityNumericCode1995to2005", "codice comune numerico con 103 province dal 1995 al 2005"),
        ("cadastralCode", "codice catastale del comune"),
        ("nuts1_2021", "codice nuts1 2021"),
        ("nuts2_2021", "codice nuts2 2021"),
        ("nuts3_2021", "codice nuts3 2021"),
        ("nuts1_2024", "codice nuts1 2024"),
        ("nuts2_2024", "codice nuts2 2024"),
        ("nuts3_2024", "codice nuts3 2024"),
    ]
    numeric_code_keys = {
        "municipalityNumericCode", "municipalityNumericCode2017to2025",
        "municipalityNumericCode2010to2016", "municipalityNumericCode2006to2009",
        "municipalityNumericCode1995to2005",
    }
    values = [(key, code6(v) if key in numeric_code_keys else v, None)
              for key, candidate in field_map
              for v in [field(row, cols, candidate)]]
    values += [
        ("quotaCentroM", number(field(row, cols, "altitudine del centro metri", "altitudine del centro")), "m"),
        ("superficieKm2", number(field(row, cols, "superficie territoriale kmq", "superficie territoriale km2")), "km2"),
    ]
    capital = field(row, cols, "flag comune capoluogo di provincia citta metropolitana libero consorzio")
    if capital in ("0", "1"):
        values.append(("provinceCapitalFlag", capital == "1", None))
    for key, value, unit in values:
        if value is not None:
            facts[key] = fact(value, source_id, ISTAT_URL, unit=unit, as_of=retrieved_at)
    region_code = field(row, cols, "codice regione")
    province_sigla = field(row, cols, "sigla automobilistica")
    cadastral = field(row, cols, "codice catastale del comune")
    local_name = field(row, cols, "denominazione altra lingua")
    aliases = ([{"name": local_name, "language": None,
                 "sourceId": source_id, "sourceUrl": ISTAT_URL}]
               if local_name and header(local_name) != header(name) else [])
    return {
        "id": "municipality:" + str(uuid5(NAMESPACE, "IT/ISTAT/" + code)),
        "kind": "municipality", "subtype": "italian_municipality",
        "name": name, "slug": slugify(name), "slugAliases": [],
        "sourceIds": {"istat": code, **({"cadastral": cadastral} if cadastral else {})},
        "geo": {"point": None, "area": None},
        "administrativeHierarchy": {"countryCode": "IT", "region": region, "province": province,
                                    "regionCodeISTAT": region_code, "provinceAbbreviation": province_sigla,
                                    "municipalityCodeISTAT": code},
        "facts": facts, "factsAlternatives": [], "relations": [], "media": [],
        "aliases": aliases, "editorialStatus": "raw",
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
    """Build an audited DAIT->ISTAT crosswalk; DAIT codice_comune IS NOT ISTAT.

    The DAIT CSV uses codice_regione + its own codice_provincia +
    codice_comune (often four characters). Never pad this municipal code to
    six digits and pretend it is ISTAT. Join on an unambiguous triple of
    official (regionCode, provinceAbbreviation, officialMunicipalityName),
    record the mapping between source registries and quarantine conflicts.
    """
    keys = set(cols)
    role_key = find_col(keys, *DAIT_ROLE)
    date_key = find_col(keys, *DAIT_ELECTION)
    office_key = find_col(keys, *DAIT_OFFICE_START)
    region_key = find_col(keys, *DAIT_REGION_CODE)
    sigla_key = find_col(keys, *DAIT_PROVINCE_SIGLA)
    name_key = find_col(keys, *DAIT_MUNICIPAL_NAME)
    province_code_key = find_col(keys, *DAIT_PROVINCE_CODE)
    commune_code_key = find_col(keys, *DAIT_CODE)
    require(all((role_key, region_key, sigla_key, name_key, province_code_key, commune_code_key)),
            "DAIT intestazioni insufficienti per crosswalk ISTAT verificabile")
    by_official_name = defaultdict(list)
    for entity in entities:
        info = entity["administrativeHierarchy"]
        region = str(info.get("regionCodeISTAT") or "").zfill(2)
        province = str(info.get("provinceAbbreviation") or "").strip().upper()
        require(re.fullmatch(r"\d{2}", region) and re.fullmatch(r"[A-Z]{2}", province),
                "ISTAT privo di regione/sigla per crosswalk DAIT: " + entity["sourceIds"]["istat"])
        by_official_name[(region, province, header(entity["name"]))].append(entity)

    found = defaultdict(list)
    rejected = []
    dait_ids_seen = {}
    candidate_count = 0
    for row in rows:
        role = header(get(row, role_key))
        if role not in ("sindaco", "sindaca"):
            continue
        candidate_count += 1
        region = str(get(row, region_key) or "").zfill(2)
        sigla = str(get(row, sigla_key) or "").upper().strip()
        dait_province = str(get(row, province_code_key) or "").zfill(3)
        dait_municipality = str(get(row, commune_code_key) or "").zfill(4)
        legal_name = str(get(row, name_key) or "").strip()
        dait_id = "/".join([region, dait_province, dait_municipality])
        surname = field(row, cols, *DAIT_SURNAME)
        given = field(row, cols, *DAIT_NAME)
        if not (re.fullmatch(r"\d{2}", region) and re.fullmatch(r"\d{3}", dait_province)
                and re.fullmatch(r"\d{4}", dait_municipality)
                and re.fullmatch(r"[A-Z]{2}", sigla) and legal_name and given and surname):
            rejected.append({"daitId": dait_id, "name": legal_name, "reason": "invalid_identity_fields"})
            continue
        official_matches = by_official_name.get((region, sigla, header(legal_name)), [])
        if len(official_matches) != 1:
            rejected.append({"daitId": dait_id, "name": legal_name, "province": sigla,
                             "reason": "official_crosswalk_not_unique" if official_matches else "official_crosswalk_not_found"})
            continue
        matched = official_matches[0]
        code = matched["sourceIds"]["istat"]
        prior = dait_ids_seen.get(dait_id)
        if prior is not None and prior != code:
            rejected.append({"daitId": dait_id, "reason": "dait_id_collision"})
            continue
        dait_ids_seen[dait_id] = code
        found[code].append({
            "person": given + " " + surname, "daitId": dait_id,
            "election": valid_date(get(row, date_key)) if date_key else None,
            "officeStart": valid_date(get(row, office_key)) if office_key else None,
            "legalName": legal_name, "regionCode": region,
            "provinceAbbreviation": sigla,
        })
    attached = ambiguous = 0
    for entity in entities:
        code = entity["sourceIds"]["istat"]
        records = found.get(code, [])
        fingerprints = {(x["person"], x["daitId"], x["election"], x["officeStart"]) for x in records}
        if len(fingerprints) > 1:
            ambiguous += 1
            entity["quality"]["reviewRequired"] = True
            continue
        if not records:
            continue
        candidate = records[0]
        source_id = "dait:mayors:" + candidate["daitId"]
        entity["sourceIds"]["dait"] = candidate["daitId"]
        entity["facts"]["sindacoNome"] = fact(candidate["person"], source_id, DAIT_URL,
                                               as_of=retrieved_at)
        entity["facts"]["carica"] = fact("Sindaco", source_id, DAIT_URL,
                                         as_of=retrieved_at)
        if candidate["election"]:
            entity["facts"]["dataElezione"] = fact(candidate["election"], source_id, DAIT_URL,
                                                   as_of=retrieved_at)
        if candidate["officeStart"]:
            entity["facts"]["mandatoInizio"] = fact(candidate["officeStart"], source_id, DAIT_URL,
                                                    as_of=retrieved_at)
        # Source identity is explicit, but tenure end is unknown; a mayor
        # recorded in a dated snapshot does not mean "currently mayor" forever.
        attached += 1
    return {"mayorsMatched": attached, "mayorsAmbiguous": ambiguous,
            "daitRowsOfficialCrosswalkReview": rejected[:200],
            "daitRowsOfficialCrosswalkRejected": len(rejected),
            "daitOfficialCrosswalkType": "ISTAT_REGION_PLUS_PROVINCE_SIGLA_PLUS_EXACT_NAME",
            "daitMayorCandidates": candidate_count,
            "daitCodesMatchedToISTAT": len(dait_ids_seen)}

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
