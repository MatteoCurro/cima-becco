#!/usr/bin/env python3
"""Georeferenzia località del blocco 4 con punti e dati censuari ISTAT 2021.

Archivio ufficiale LocalitaPuntuali_21.zip: DBF con LOC_ID, PRO_COM, LOC,
TIPO_LOC, NOME, POINT_X/Y e POP21/FAM21/ABI21/EDI21.
CRS dichiarato nel .prj WGS 84 / UTM zone 32N (EPSG:32632).
Un nome vicino, da solo, non è una relazione, né una prova d'identità.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import io
import json
import math
from pathlib import Path
import re
import struct
from zipfile import ZipFile

from import_municipalities_v1 import load, save, fact, code6, header
from import_settlements_v1 import digits

URL = "https://www.istat.it/storage/cartografia/basi_territoriali/2021/LocalitaPuntuali_21.zip"
REQUIRED = {"PRO_COM", "LOC_ID", "LOC", "TIPO_LOC", "NOME",
            "POINT_X", "POINT_Y", "POP21", "FAM21", "ABI21", "EDI21"}
COUNT_FIELDS = {"POP21": "popolazione", "FAM21": "famiglie",
                "ABI21": "abitazioni", "EDI21": "edifici"}

def normalize_numeric(value, width=None):
    """Integer represented by decimal with zero fractional part; no rounding."""
    if value is None:
        return None
    s = str(value).strip()
    if not re.fullmatch(r"[0-9]+(?:[.]0+)?", s):
        return None
    digits_only = s.split(".")[0]
    return digits_only.zfill(width) if width else int(digits_only)

def dbf_records(raw):
    """Minimal strict DBF reader: native fixed-width fields, no GIS dependency."""
    if len(raw) < 64:
        raise ValueError("DBF nazionale ISTAT incompleto")
    n = struct.unpack_from("<I", raw, 4)[0]
    header_length = struct.unpack_from("<H", raw, 8)[0]
    record_length = struct.unpack_from("<H", raw, 10)[0]
    if not (1 <= n <= 150_000 and 64 <= header_length < 5000 and
            32 <= record_length < 4000 and
            header_length + n * record_length <= len(raw)):
        raise ValueError("Dimensioni DBF incoerenti")
    fields = []
    position = 32
    while position + 32 <= header_length and raw[position] != 0x0d:
        field = raw[position:position+32]
        key = field[:11].split(b"\x00", 1)[0].decode("ascii", errors="strict").strip()
        fields.append((key, field[16]))
        position += 32
    keys = [key for key, _ in fields]
    if len(keys) != len(set(keys)) or not REQUIRED.issubset(set(keys)):
        raise ValueError("Tracciato DBF ISTAT inatteso: " + ",".join(keys))
    if sum(width for _, width in fields) + 1 != record_length:
        raise ValueError("Lunghezza record DBF incompatibile con i campi")
    for index in range(n):
        record = memoryview(raw)[header_length+record_length*index:
                                 header_length+record_length*(index+1)]
        if record[0] == 0x2a:  # deleted DBF record
            continue
        if record[0] != 0x20:
            raise ValueError("Indicatore DBF non riconosciuto")
        offset = 1
        row = {}
        for key, width in fields:
            rawvalue = bytes(record[offset:offset+width])
            row[key] = rawvalue.decode("utf-8", errors="replace").strip()
            offset += width
        yield row

def records_from_archive(path):
    raw = Path(path).read_bytes()
    digest = sha256(raw).hexdigest()
    with ZipFile(io.BytesIO(raw)) as z:
        files = [n for n in z.namelist() if n.lower().endswith("/localita_2021_point.dbf")]
        prjs = [n for n in z.namelist() if n.lower().endswith("/localita_2021_point.prj")]
        if len(files) != 1 or len(prjs) != 1:
            raise ValueError("Mancano il DBF e il PRJ delle località puntuali 2021")
        prj = z.read(prjs[0]).decode("utf-8-sig", errors="replace")
        if "WGS_1984_UTM_Zone_32N" not in prj or "Central_Meridian" not in prj:
            raise ValueError("CRS puntuale diverso da WGS84 UTM Zone 32N")
        rows = list(dbf_records(z.read(files[0])))
    return rows, digest

def enrich(document, rows, *, xy_to_lonlat, retrieved_at=None, digest=None):
    """Join unicamente per LOC_ID+PRO_COM+LOC+TIPO_LOC+nome coerenti."""
    if document.get("releaseChannel") != "STAGING_ISTAT21_OSM_SETTLEMENTS" or document.get("isPublished"):
        raise ValueError("Input deve essere staging del blocco 4")
    retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    by_id = {e["sourceIds"]["istatLocality"]: e for e in document["entities"]
             if e.get("sourceIds",{}).get("istatLocality")}
    seen = set()
    changes = Counter()
    quarantined = []
    matched = 0
    for row in rows:
        code = code6(row.get("PRO_COM"))
        local = digits(row.get("LOC"), 5)
        official_id = normalize_numeric(row.get("LOC_ID"), 11)
        if not (code and local and official_id and code + local == official_id):
            changes["point_invalid_identity"] += 1
            continue
        entity = by_id.get(official_id)
        if entity is None:
            changes["outside_pilot"] += 1
            continue
        if official_id in seen:
            changes["duplicate_locality_point"] += 1
            quarantined.append({"id":official_id,"reason":"duplicate_point"})
            continue
        seen.add(official_id)
        if (entity["sourceIds"]["istatMunicipality"] != code or
            entity["subtype"] != {"1":"centro_abitato","2":"nucleo_abitato"}.get(str(row.get("TIPO_LOC")).strip()) or
            header(entity["name"]) != header(row.get("NOME"))):
            changes["identity_mismatch"] += 1
            quarantined.append({"id":official_id,"reason":"name_or_type_mismatch"})
            continue
        try:
            x = float(row["POINT_X"])
            y = float(row["POINT_Y"])
            if not (250000 < x < 850000 and 3800000 < y < 5500000):
                raise ValueError("Coordinate UTM fuori dominio")
            longitude, latitude = xy_to_lonlat(x,y)
            if not (math.isfinite(latitude) and math.isfinite(longitude) and
                    35.0 <= latitude <= 48.5 and 5.0 <= longitude <= 20.0):
                raise ValueError("WGS84 fuori Italia")
        except (ValueError, TypeError, OverflowError):
            changes["invalid_geometry"] += 1
            quarantined.append({"id":official_id,"reason":"invalid_geometry"})
            continue
        entity["geo"] = {
            "point":{"lat":round(latitude,6),"lng":round(longitude,6)},
            "area":None, "method":"reported",
            "sourceId":"istat:point2021:"+official_id,
            "sourceUrl":URL, "coordinateReferenceSystem":"EPSG:4326",
            "sourceCoordinateReferenceSystem":"EPSG:32632",
            "sourceReferenceDate":"2021-12-31",
            "coordinateMethod":"official_point_transformed_epsg32632_to_epsg4326",
        }
        entity["facts"]["istatPointVerified"] = fact(
            True, "istat:point2021:"+official_id, URL,
            as_of=retrieved_at, valid_at="2021-12-31", licence="ISTAT open data")
        for field,key in COUNT_FIELDS.items():
            count = normalize_numeric(row.get(field))
            if count is not None and count >= 0:
                entity["facts"][key] = fact(
                    count, "istat:point2021:"+official_id+":"+field,
                    URL, as_of=retrieved_at, valid_at="2021-12-31",
                    licence="ISTAT open data", method="reported")
                changes["facts_"+key] += 1
        if "popolazione" in entity["facts"]:
            entity["facts"]["populationReferenceDate"] = fact(
                "2021-12-31", "istat:point2021:"+official_id+":POP21", URL,
                as_of=retrieved_at,valid_at="2021-12-31",licence="ISTAT open data")
        if "elevationM" not in entity.get("facts",{}):
            altitude = normalize_numeric(row.get("ALTITUDINE"))
            if altitude is not None and 0 <= altitude < 5000:
                entity["facts"]["elevationM"] = fact(
                    altitude, "istat:point2021:"+official_id+":ALTITUDINE", URL,
                    as_of=retrieved_at,valid_at="2021-12-31",unit="m",
                    licence="ISTAT open data")
                entity["elevationM"] = altitude
                entity["elevationMethod"] = "istat_locality_point_reported_2021"
        entity["quality"] = {
            **entity["quality"],"gate":"G1","seoIndexable":False,
            "geolocationMissing":False,"pointAndIdentityVerified":True,
        }
        entity["editorialStatus"] = "linked"
        matched += 1
    missing = len(by_id) - matched
    changes["matched"] = matched
    changes["missing_or_quarantined"] = missing
    report = {
        "source":URL, "sourceArchiveSha256":digest, "referenceDate":"2021-12-31",
        "crsInput":"EPSG:32632", "crsOutput":"EPSG:4326",
        "nationalPointRows":len(rows), "candidatesForJoin":len(by_id),
        "counts":dict(sorted(changes.items())),
        "quarantineExamples":quarantined[:60],
        "seoIndexable":0,
    }
    return document,report

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--settlements", required=True)
    parser.add_argument("--points", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--report", required=True)
    args=parser.parse_args()
    from pyproj import Transformer
    to_wgs84=Transformer.from_crs("EPSG:32632","EPSG:4326",always_xy=True).transform
    rows,digest=records_from_archive(args.points)
    doc, report = enrich(load(args.settlements),rows,
                         xy_to_lonlat=to_wgs84,digest=digest)
    save(args.out,doc)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))

if __name__ == "__main__":
    main()
