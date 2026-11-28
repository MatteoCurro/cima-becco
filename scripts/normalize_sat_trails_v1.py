#!/usr/bin/env python3
"""Normalize VERIFIED SAT 2026 KML source fields to source-only G0 trail records.

No canonical trail IDs, no OSM conflation, no SEO and no routing.
Use the bounded original SAT ZIP from pilot_sat_trail_source_v1.py.
The source uses 16 known SimpleData attributes; future unknown keys survive
unmodified in sourceProperties and enter audit before typed promotion.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import json
import math
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

from import_osm_routes import haversine
from pilot_sat_trail_source_v1 import (
    CHANNEL as SAT_PROBE_CHANNEL,
    SOURCE_PAGE, SOURCE_URL, safe_zip_members,
)

ROOT = Path(__file__).resolve().parents[1]
STAGING = ROOT / "build/sat-trails-g0-source-audit"
CHANNEL = "SAT_TRAILS_TYPED_SOURCE_G0_V1"
KNOWN_KEYS = {
    "numero", "competenza", "denominaz", "difficolta", "loc_inizio",
    "loc_fine", "quota_iniz", "quota_fine", "quota_min", "quota_max",
    "lun_planim", "lun_inclin", "t_andata", "t_ritorno", "gr_mont",
    "comuni_toc",
}
NUMBER = re.compile(r"^[EO][0-9]{3}[A-Z]?$")
DIFFICULTIES = {"T", "E", "EE", "EEA-F", "EEA-PD", "EEA-D", "EEA-MD", "EEA-E"}
REPORTED_NUMERIC = {
    "quota_iniz": "elevationStartReportedM",
    "quota_fine": "elevationEndReportedM",
    "quota_min": "elevationMinReportedM",
    "quota_max": "elevationMaxReportedM",
    "lun_planim": "lengthPlanimetricReportedM",
    "lun_inclin": "lengthInclinedReportedM",
}
DURATION_FIELDS = {
    "t_andata": "durationOutReportedMin",
    "t_ritorno": "durationBackReportedMin",
}
PUBLIC_CATALOGUE_COUNT_2026 = 1081
CATALOGUE_PAGE = "https://www.sat.tn.it/sentieri/catasto/"


def source_properties(placemark):
    props = {}
    for tag in placemark.iter():
        local = tag.tag.rsplit("}", 1)[-1]
        if local == "SimpleData" and tag.get("name"):
            props[tag.get("name")] = (tag.text or "").strip()
        elif local == "Data" and tag.get("name"):
            value = next((x.text for x in tag if x.tag.rsplit("}", 1)[-1] == "value"), None)
            if value is not None:
                props[tag.get("name")] = value.strip()
    return props


def parse_line(text):
    if not text:
        return None
    points = []
    for coord in text.split():
        pair = coord.split(",")
        if len(pair) < 2:
            return None
        try:
            lon, lat = float(pair[0]), float(pair[1])
        except ValueError:
            return None
        if not (math.isfinite(lon) and math.isfinite(lat)
                and 6 <= lon <= 20 and 35 <= lat <= 48):
            return None
        points.append([lon, lat])
    return points if len(points) >= 2 and any(a != b for a, b in zip(points, points[1:])) else None


def geometry_from_placemark(placemark):
    geometries = []
    lines_present = 0
    for line in placemark.iter():
        if line.tag.rsplit("}", 1)[-1] != "LineString":
            continue
        lines_present += 1
        coords = next((x.text for x in line.iter()
                       if x.tag.rsplit("}", 1)[-1] == "coordinates"), None)
        points = parse_line(coords)
        if points is None:
            return None, "invalid_coordinates"
        geometries.append(points)
    if not lines_present:
        return None, "no_linestring"
    geom = {"type": "LineString", "coordinates": geometries[0]} if len(geometries) == 1 else {
        "type": "MultiLineString", "coordinates": geometries,
    }
    return geom, None


def as_nonnegative_integer(value):
    if value is None or str(value).strip() == "":
        return None
    value = str(value).strip()
    if not re.fullmatch(r"[0-9]+", value):
        return None
    return int(value)


def as_minutes(value):
    if not value or not re.fullmatch(r"[0-9]{1,3}:[0-5][0-9]", value.strip()):
        return None
    hours, minutes = (int(x) for x in value.strip().split(":"))
    return hours * 60 + minutes


def reported_fact(value, unit, original_key, retrieved_at):
    return {
        "value": value,
        "unit": unit,
        "method": "reported",
        "sourceId": "sat:trail-catasto-kml",
        "sourceUrl": SOURCE_PAGE,
        "licence": "ODbL 1.0",
        "retrievedAt": retrieved_at,
        "sourceUpdatedAt": None,
        "rawValue": original_key[1],
        "rawFieldName": original_key[0],
    }


def normalize_one(props, geometry, index, archive_hash, retrieved_at):
    original = {str(k): str(v) for k, v in props.items()}
    number = props.get("numero") or None
    difficulty = props.get("difficolta") or None
    name = props.get("denominaz") or None
    issues = []
    if not number or not NUMBER.fullmatch(number):
        issues.append("number_missing_or_unrecognized")
    if difficulty not in DIFFICULTIES:
        issues.append("technical_difficulty_missing_or_unrecognized")
    if geometry is None:
        issues.append("geometry_unusable")
    unknown = sorted(set(props) - KNOWN_KEYS)
    if unknown:
        issues.append("unmapped_original_attributes")
    facts = {}
    for raw_field, canonical in REPORTED_NUMERIC.items():
        raw_value = props.get(raw_field)
        n = as_nonnegative_integer(raw_value)
        if n is not None:
            facts[canonical] = reported_fact(n, "m", (raw_field, raw_value), retrieved_at)
        else:
            issues.append("missing_or_invalid_" + raw_field)
    for raw_field, canonical in DURATION_FIELDS.items():
        raw_value = props.get(raw_field)
        n = as_minutes(raw_value)
        if n is not None:
            facts[canonical] = reported_fact(n, "min", (raw_field, raw_value), retrieved_at)
        else:
            issues.append("missing_or_invalid_" + raw_field)
    min_alt = facts.get("elevationMinReportedM", {}).get("value")
    max_alt = facts.get("elevationMaxReportedM", {}).get("value")
    if min_alt is not None and max_alt is not None and max_alt < min_alt:
        issues.append("elevation_range_inverted")
    # Source number is a candidate locator, NOT a stable canonical ID.
    # Fingerprint is a snapshot identity hint, not a permalink or same_as.
    fingerprint = sha256(json.dumps(
        {"sourceProperties": original, "geometry": geometry},
        ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    derived = None
    if geometry:
        sections = [geometry["coordinates"]] if geometry["type"] == "LineString" else geometry["coordinates"]
        distance = sum(haversine(a, b) for sec in sections for a, b in zip(sec, sec[1:]))
        derived = reported_fact(round(distance, 1), "m",
                                ("geometry", "WGS84 source coordinates"), retrieved_at)
        derived["method"] = "derived"
        derived["sourceUrl"] = SOURCE_URL
    return {
        "sourceRow": index,
        "sourceRecordFingerprint": fingerprint,
        "kind": "official_trail_source_record",
        "sourceIds": {"satTrailNumberReported": number},
        "displayNameReported": name,
        "originalDifficulty": {"value": difficulty, "scale": "CAI/SAT source value",
                               "sourceId": "sat:trail-catasto-kml",
                               "sourceUrl": SOURCE_PAGE, "licence": "ODbL 1.0",
                               "retrievedAt": retrieved_at} if difficulty else None,
        "officialCatalogueSubtype": None,  # SA/SAA/VF not in the audited KML fields.
        "originalContext": {
            "competentEntity": props.get("competenza") or None,
            "mountainGroup": props.get("gr_mont") or None,
            "municipalitiesTouchedAsText": props.get("comuni_toc") or None,
            "startPlaceAsText": props.get("loc_inizio") or None,
            "endPlaceAsText": props.get("loc_fine") or None,
        },
        "geo": {
            "geometry": geometry, "crs": "EPSG:4326",
            "sourceId": "sat:trail-catasto-kml", "sourceUrl": SOURCE_URL,
            "licence": "ODbL 1.0", "method": "source_original",
        } if geometry else None,
        "facts": facts,
        "lengthFromSourceGeometryM": derived,
        "sourceProperties": original,
        "sourceArchiveSha256": archive_hash,
        "quality": {
            "gate": "G0", "seoIndexable": False,
            "canonicalIdentityVerified": False,
            "crosswalkVerified": False, "safetyVerified": False,
            "traversableVerified": False, "routeContinuityVerified": False,
            "sourceNumberUniqueInSnapshot": None,
            "requiresReview": bool(issues),
            "issues": issues,
        },
    }


def normalize_archive(data, *, retrieved_at):
    if not isinstance(data, bytes):
        raise ValueError("Expected original SAT ZIP bytes")
    archive_hash = sha256(data).hexdigest()
    records = []
    source_no = 0
    for filename, xml in safe_zip_members(data):
        try:
            for _, element in ET.iterparse(BytesIO(xml), events=("end",)):
                if element.tag.rsplit("}", 1)[-1] != "Placemark":
                    continue
                source_no += 1
                props = source_properties(element)
                geom, geom_issue = geometry_from_placemark(element)
                record = normalize_one(props, geom, source_no, archive_hash, retrieved_at)
                if geom_issue and geom_issue not in record["quality"]["issues"]:
                    record["quality"]["issues"].append(geom_issue)
                    record["quality"]["requiresReview"] = True
                record["sourceArchiveEntry"] = filename
                records.append(record)
                element.clear()
        except ET.ParseError as exc:
            raise ValueError(f"SAT source XML invalid ({filename}): {exc}") from exc
    if not records:
        raise ValueError("No SAT records in the original archive")
    numbers = Counter(r["sourceIds"]["satTrailNumberReported"] for r in records
                      if r["sourceIds"]["satTrailNumberReported"])
    duplicates = {key: count for key, count in numbers.items() if count > 1}
    fingerprint_counts = Counter(x["sourceRecordFingerprint"] for x in records)
    for record in records:
        num = record["sourceIds"]["satTrailNumberReported"]
        q = record["quality"]
        q["sourceNumberUniqueInSnapshot"] = bool(num and numbers[num] == 1)
        if num and numbers[num] > 1:
            q["issues"].append("duplicate_sat_number")
        if fingerprint_counts[record["sourceRecordFingerprint"]] > 1:
            q["issues"].append("exact_source_record_duplicate")
        q["requiresReview"] = bool(q["issues"])
    counts = {
        "sourcePlacemarks": len(records),
        "uniqueNumbers": len(numbers),
        "duplicateNumberGroups": len(duplicates),
        "duplicateNumberExcess": sum(x - 1 for x in duplicates.values()),
        "exactDuplicateExcess": sum(x - 1 for x in fingerprint_counts.values() if x > 1),
        "validOriginalGeometries": sum(x["geo"] is not None for x in records),
        "recordsRequiringReview": sum(x["quality"]["requiresReview"] for x in records),
        "recordsWithReportedDifficulties": sum(x["originalDifficulty"] is not None for x in records),
        "originalDifficultyDistribution": dict(sorted(Counter(
            r["originalDifficulty"]["value"] if r["originalDifficulty"] else "missing"
            for r in records).items())),
        "officialPublic2026CatalogueReferenceCount": PUBLIC_CATALOGUE_COUNT_2026,
        "deltaToPublic2026Reference": len(records) - PUBLIC_CATALOGUE_COUNT_2026,
    }
    return {
        "schemaVersion": "1.0",
        "releaseChannel": CHANNEL,
        "originSchemaAuditChannel": SAT_PROBE_CHANNEL,
        "isPublished": False,
        "seoIndexable": False,
        "routeCatalogueModified": False,
        "sourceName": "Societa degli Alpinisti Tridentini (SAT)",
        "sourceArchiveSha256": archive_hash,
        "sourceUrl": SOURCE_URL,
        "sourceLicence": "ODbL 1.0",
        "retrievedAt": retrieved_at,
        "counts": counts,
        "unresolvedDuplicateNumbers": duplicates,
        "quality": {
            "gate": "G0", "canonicalIdsCreated": False,
            "officialCategorySA_SAA_VFVerified": False,
            "osmCrosswalkVerified": False,
            "routingAllowed": False, "safetyVerified": False,
            "publicationAllowed": False, "officialListReconciled": False,
            "noAutomaticMergingOfExactSourceDuplicates": True,
        },
        "records": records,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-zip", type=Path, default=STAGING / "source-sat-official.kml.zip")
    parser.add_argument("--out", type=Path, default=STAGING)
    args = parser.parse_args()
    data = args.source_zip.read_bytes()
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    result = normalize_archive(data, retrieved_at=now)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sat-trails-normalized-g0.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    audit = {key: result[key] for key in (
        "schemaVersion", "releaseChannel", "sourceArchiveSha256", "counts",
        "unresolvedDuplicateNumbers", "quality", "isPublished", "seoIndexable")}
    (args.out / "sat-trails-normalization-audit-g0.json").write_text(
        json.dumps(audit, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
