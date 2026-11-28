#!/usr/bin/env python3
"""SAT 2026 trail-source schema audit (G0 only; no publication, no crosswalk).

Purpose: inspect real SAT source records before defining an importer schema.
A SAT trail (official catalogue entry) is NOT an OSM way, route or verified
connection. The SAT source may contain paths, equipped paths and ferrate;
their category may be imported only when an explicit original field proves it.

Official download and ODbL: https://www.sat.tn.it/sentieri/mappa-sentieri/
KML/GPX coordinates are EPSG:4326; SHP source is EPSG:25832.
The output lives in build/ exclusively. No production writes.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import shutil
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import xml.etree.ElementTree as ET
from zipfile import BadZipFile, ZipFile

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUT = ROOT / "build/sat-trails-g0-source-audit"
SOURCE_URL = "https://sentieri.sat.tn.it/download/sentierisat.kml.zip"
SOURCE_PAGE = "https://www.sat.tn.it/sentieri/mappa-sentieri/"
CHANNEL = "SAT_TRAIL_SOURCE_G0_SCHEMA_AUDIT_V1"
MAX_ZIP_BYTES = 90 * 1024 * 1024
MAX_ENTRY_BYTES = 190 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED = 260 * 1024 * 1024
MAX_ZIP_ENTRIES = 2000
MAX_EXAMPLES = 16


def fetch_zip(url=SOURCE_URL):
    if url != SOURCE_URL:
        raise ValueError("Network pilot supports only the verified SAT download URL")
    req = Request(url, headers={
        "User-Agent": "CimaBecco-SAT-schema-audit/1.0 (+https://www.cimabecco.it)",
        "Referer": SOURCE_PAGE,
        "Accept": "application/zip, application/octet-stream;q=0.9",
    })
    try:
        with urlopen(req, timeout=105) as response:
            data = response.read(MAX_ZIP_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"SAT KML source unavailable; do not fabricate source data: {exc}") from exc
    if len(data) > MAX_ZIP_BYTES:
        raise ValueError("SAT archive exceeded bounded source-audit size")
    if not data.startswith(b"PK"):
        raise ValueError("SAT download was not a ZIP archive")
    return data


def local_name(name):
    return name.rsplit("}", 1)[-1]


def safe_zip_members(data):
    try:
        with ZipFile(BytesIO(data)) as z:
            infos = z.infolist()
            if not 1 <= len(infos) <= MAX_ZIP_ENTRIES:
                raise ValueError("Unexpected ZIP directory count")
            if any(i.flag_bits & 1 for i in infos):
                raise ValueError("Encrypted SAT archive unsupported")
            if any(i.file_size > MAX_ENTRY_BYTES for i in infos):
                raise ValueError("ZIP entry exceeded decompression bound")
            if sum(i.file_size for i in infos) > MAX_TOTAL_UNCOMPRESSED:
                raise ValueError("ZIP uncompressed total exceeded bound")
            entries = []
            for i in infos:
                p = Path(i.filename)
                if i.filename.startswith("/") or ".." in p.parts or "\\" in i.filename:
                    raise ValueError("Unsafe ZIP entry path")
                if i.is_dir() or not i.filename.lower().endswith(".kml"):
                    continue
                with z.open(i) as stream:
                    xml = stream.read(MAX_ENTRY_BYTES + 1)
                if len(xml) != i.file_size or len(xml) > MAX_ENTRY_BYTES:
                    raise ValueError("ZIP entry size mismatch")
                if b"<!DOCTYPE" in xml[:4096].upper() or b"<!ENTITY" in xml[:4096].upper():
                    raise ValueError("DTD/entity declarations are prohibited")
                entries.append((i.filename, xml))
    except BadZipFile as exc:
        raise ValueError("SAT source archive is not a valid ZIP") from exc
    if not entries:
        raise ValueError("No KML file found inside SAT source ZIP")
    return entries


def properties_from_placemark(placemark):
    props = {}
    for e in placemark.iter():
        lname = local_name(e.tag)
        if lname == "Data" and e.get("name"):
            value = next((v.text for v in e if local_name(v.tag) == "value"), None)
            if value is not None:
                props[e.get("name")] = value.strip()
        elif lname == "SimpleData" and e.get("name"):
            props[e.get("name")] = (e.text or "").strip()
    return props


def name_from_placemark(placemark):
    return next(((e.text or "").strip() for e in placemark
                 if local_name(e.tag) == "name"), "")


def inspect_coordinates(value):
    """Count coordinate vertices; verify syntax and geographic bounds only.

    This DOES NOT claim source topological continuity or route traversability.
    """
    if not value or not value.strip():
        return 0, False
    count = 0
    for item in value.strip().split():
        coords = item.split(",")
        if len(coords) < 2:
            return count, False
        try:
            lon, lat = float(coords[0]), float(coords[1])
        except ValueError:
            return count, False
        if not (math.isfinite(lon) and math.isfinite(lat) and
                6 <= lon <= 20 and 35 <= lat <= 48):
            return count, False
        count += 1
    return count, count >= 2


def inspect_kml(xml_bytes, filename, max_examples=MAX_EXAMPLES):
    total = 0
    line_features = 0
    invalid_lines = 0
    no_line = 0
    empty_name = 0
    geometry_points = 0
    key_counts = Counter()
    sample = []
    try:
        for _, element in ET.iterparse(BytesIO(xml_bytes), events=("end",)):
            if local_name(element.tag) != "Placemark":
                continue
            total += 1
            name = name_from_placemark(element)
            if not name:
                empty_name += 1
            props = properties_from_placemark(element)
            key_counts.update(props.keys())
            lines = []
            for e in element.iter():
                if local_name(e.tag) != "LineString":
                    continue
                coordinates = next(((v.text or "") for v in e.iter()
                                    if local_name(v.tag) == "coordinates"), "")
                points, valid = inspect_coordinates(coordinates)
                geometry_points += points
                lines.append(valid)
            if not lines:
                no_line += 1
            elif all(lines):
                line_features += 1
            else:
                invalid_lines += 1
            if len(sample) < max_examples:
                # Raw original attribute names and bounded values; no identity
                # reconciliation and no assignment of an OSM/CAI identifier.
                sample.append({
                    "name": name[:180] or None,
                    "kmlPlacemarkId": element.get("id"),
                    "originalProperties": {k: v[:220] for k, v in props.items()},
                    "lineStringCount": len(lines),
                    "lineStringsValid": bool(lines) and all(lines),
                    "qualityGate": "G0",
                    "identityMatchedWithOSM": False,
                })
            element.clear()
    except ET.ParseError as exc:
        raise ValueError(f"Malformed SAT KML in {filename}: {exc}") from exc
    return {
        "file": filename,
        "placemarks": total,
        "featuresWithValidLineStrings": line_features,
        "featuresWithInvalidLineStrings": invalid_lines,
        "featuresWithoutLineStrings": no_line,
        "featuresWithoutName": empty_name,
        "lineStringVertexObservations": geometry_points,
        "sourcePropertyKeys": dict(sorted(key_counts.items())),
        "examples": sample,
    }


def audit_archive(data, *, retrieved_at):
    if not isinstance(data, bytes) or len(data) > MAX_ZIP_BYTES:
        raise ValueError("Raw SAT ZIP bytes required")
    if not data.startswith(b"PK"):
        raise ValueError("Raw SAT input must be a ZIP, not a web error page")
    entries = safe_zip_members(data)
    files = [inspect_kml(xml, name) for name, xml in entries]
    total = sum(x["placemarks"] for x in files)
    if total < 1:
        raise ValueError("SAT ZIP contains no Placemarks")
    return {
        "schemaVersion": "1.0",
        "releaseChannel": CHANNEL,
        "isPublished": False,
        "seoIndexable": False,
        "routeCatalogueModified": False,
        "sourceName": "Societa degli Alpinisti Tridentini (SAT)",
        "sourcePage": SOURCE_PAGE,
        "sourceDownloadUrl": SOURCE_URL,
        "licence": "ODbL 1.0",
        "sourceCrs": "EPSG:4326",
        "retrievedAt": retrieved_at,
        "sourceArchiveSha256": sha256(data).hexdigest(),
        "archiveBytes": len(data),
        "files": files,
        "counts": {
            "kmlFiles": len(files),
            "sourcePlacemarks": total,
            "validLineStringFeatures": sum(f["featuresWithValidLineStrings"] for f in files),
            "invalidLineStringFeatures": sum(f["featuresWithInvalidLineStrings"] for f in files),
            "featuresWithoutLineStrings": sum(f["featuresWithoutLineStrings"] for f in files),
        },
        "quality": {
            "gate": "G0",
            "sourceSchemaInspected": True,
            "canonicalTrailIdsAssigned": False,
            "osmCrosswalkVerified": False,
            "officialCategoryFieldVerified": False,
            "routingAllowed": False,
            "safetyVerified": False,
            "publicationAllowed": False,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, help="Offline SAT ZIP, no HTTP call")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    raw = args.input.read_bytes() if args.input else fetch_zip()
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    report = audit_archive(raw, retrieved_at=timestamp)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "source-sat-official.kml.zip").write_bytes(raw)
    (args.out / "source-schema-audit-g0.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError) as exc:
        sys.exit(str(exc))
