#!/usr/bin/env python3
"""CAI ↔ OSM refuge identity candidates, offline and strictly NON-PUBLISHING.

Consumes existing CAI pilot listing (records[]), and the canonical OSM refuge
staging entities. A name+distance suggestion NEVER authorizes merging, and
catalog rows without explicit type cannot prove a "refuge" rather than bivouac.
No network, no media, no personal fields, no front-end changes.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
GENERIC = {"rifugio", "bivacco", "capanna", "casa", "alpina", "alpin", "albergo", "cai",
           "mountain", "hut", "hutte", "huette", "refuge", "chalet", "il", "la",
           "lo", "dei", "degli", "della", "del", "di", "da", "d", "the"}
CANDIDATE_RADIUS_M = 250
STRONG_NAME_SCORE = 0.75
ELEVATION_TOLERANCE_M = 120
EXCLUDED_TYPES = {"bivacco", "bivouac", "capanna sociale", "punto d'appoggio",
                  "punto di appoggio", "emergency shelter"}


def tokens(name):
    if not isinstance(name, str):
        return frozenset()
    normalized = "".join(c for c in unicodedata.normalize("NFKD", name.casefold())
                         if not unicodedata.combining(c))
    terms = re.findall(r"[a-z0-9]+", normalized)
    return frozenset(t for t in terms if t not in GENERIC)


def name_score(a, b):
    aa, bb = tokens(a), tokens(b)
    if not aa or not bb:
        return 0.0
    return round(len(aa & bb) / len(aa | bb), 4)


def valid_geojson_point(geo):
    if not isinstance(geo, dict) or geo.get("type") != "Point":
        return None
    xy = geo.get("coordinates")
    if (not isinstance(xy, list) or len(xy) != 2 or
        any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v)
            for v in xy)):
        return None
    lon, lat = xy
    if not -180 <= lon <= 180 or not -90 <= lat <= 90:
        return None
    return (lat, lon)  # GeoJSON is longitude, latitude; atlas uses lat, lon


def osm_point(hut):
    p = hut.get("geo", {}).get("point", {})
    lat, lon = p.get("lat"), p.get("lon")
    if any(isinstance(x, bool) or not isinstance(x, (int, float)) or
           not math.isfinite(x) for x in (lat, lon)):
        return None
    if -90 <= lat <= 90 and -180 <= lon <= 180:
        return (lat, lon)
    return None


def distance_m(p, q):
    p1, p2 = math.radians(p[0]), math.radians(q[0])
    dp, dl = p2-p1, math.radians(q[1]-p[1])
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return round(12742017.6 * math.asin(min(1, math.sqrt(a))), 1)


def category(entry):
    # Page-1 catalog omits this: None means a hard identity-type blocker.
    kind = entry.get("category") or entry.get("type") or entry.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        return "unverified"
    clean = kind.strip().casefold()
    if clean in EXCLUDED_TYPES:
        return "excluded_non_refuge"
    if clean in {"rifugio", "rifugio custodito", "rifugio incustodito",
                 "alpine hut", "refuge", "refuge_hut"}:
        return "confirmed_refuge_type"
    return "unverified"


def cai_source_id(entry):
    value = entry.get("caiId", entry.get("id_cai"))
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError("CAI ID assente/illeggibile")
    if not re.fullmatch(r"[0-9]{1,20}", str(value)):
        raise ValueError("CAI ID non numerico")
    return str(value)


def strict_catalog(records):
    if isinstance(records, dict):
        records = records.get("records")
    if not isinstance(records, list):
        raise ValueError("CAI pilot catalog deve contenere records[]")
    ids = [cai_source_id(x) for x in records]
    if len(ids) != len(set(ids)):
        raise ValueError("CAI ID duplicati nel pilot")
    return sorted(records, key=cai_source_id)


def official_type_evidence(evidence):
    """Validate human-reviewed public CAI page evidence, never raw type guesses."""
    if evidence is None:
        return {}
    if isinstance(evidence, dict):
        evidence = evidence.get("records")
    if not isinstance(evidence, list):
        raise ValueError("Evidenze ufficiali CAI devono contenere records[]")
    mapping = {}
    for item in evidence:
        if not isinstance(item, dict):
            raise ValueError("Voce evidenza CAI invalida")
        code = cai_source_id(item)
        page = item.get("officialPage")
        if page != "https://rifugi.cai.it/shelters/" + code:
            raise ValueError("La fonte ufficiale non corrisponde al CAI ID: " + code)
        classification = item.get("classification")
        normalized_type = str(item.get("officialType", "")).strip().casefold()
        if ((classification == "refuge" and normalized_type not in
             {"rifugio custodito", "rifugio incustodito"}) or
            (classification == "bivouac" and normalized_type != "bivacco")):
            raise ValueError("Tipologia CAI discordante con evidenza: " + code)
        if classification not in ("refuge", "bivouac") or code in mapping:
            raise ValueError("Classificazione CAI non accettata o duplicata")
        mapping[code] = item
    return mapping


def identity_candidates(cai_records, osm_entities, verified_types=None):
    cai_records = strict_catalog(cai_records)
    type_evidence = official_type_evidence(verified_types)
    if isinstance(osm_entities, dict):
        osm_entities = osm_entities.get("entities")
    if not isinstance(osm_entities, list):
        raise ValueError("Catalogo OSM canonical entities[] assente")
    osm_ids = [h.get("id") for h in osm_entities]
    if None in osm_ids or len(osm_ids) != len(set(osm_ids)):
        raise ValueError("ID canonici OSM duplicati o assenti")
    osm = [(h, osm_point(h)) for h in osm_entities if h.get("kind") == "refuge"]
    categories = {"excluded_non_refuge": 0, "unverified": 0,
                  "confirmed_refuge_type": 0}
    matches, unmatched, type_conflicts = [], [], []
    for row in cai_records:
        source_id = "cai:shelter:" + cai_source_id(row)
        verified = type_evidence.get(cai_source_id(row))
        source_type = dict(row)
        if verified:
            source_type["category"] = verified["officialType"]
        kind_status = category(source_type)
        categories[kind_status] += 1
        # Il listino API può includere elementi non pubblicati; non derivare
        # candidati di pagina da record non visibili sul catalogo pubblico.
        if row.get("published") is False or row.get("deletedAt") not in (None, ""):
            unmatched.append({"sourceId": source_id, "reason": "not_public_or_deleted",
                              "typeReview": kind_status})
            continue
        if kind_status == "excluded_non_refuge":
            # Track potential OSM category problem for future bivouac module
            # without creating any typed refuge link.
            point = valid_geojson_point(row.get("geo"))
            name = row.get("name", row.get("title", ""))
            if verified and point and tokens(name):
                for hut, loc in osm:
                    if loc is None:
                        continue
                    d = distance_m(point, loc)
                    if d <= CANDIDATE_RADIUS_M and name_score(name, hut.get("name", "")) >= STRONG_NAME_SCORE:
                        type_conflicts.append({
                            "sourceId": source_id,
                            "officialType": verified["officialType"],
                            "officialPage": verified["officialPage"],
                            "osmRefugeId": hut["id"],
                            "distanceM": d,
                            "reviewStatus": "wrong_kind_review_required",
                            "autoReclassified": False,
                        })
            unmatched.append({"sourceId": source_id, "reason": "non_refuge_type",
                              "typeReview": "confirmed_non_refuge",
                              "officialPage": verified["officialPage"] if verified else None})
            continue
        point = valid_geojson_point(row.get("geo"))
        name = row.get("name", row.get("title", ""))
        if not point or not tokens(name):
            unmatched.append({"sourceId": source_id, "reason": "missing_name_or_geometry",
                              "typeReview": kind_status})
            continue
        nearby = []
        for hut, loc in osm:
            if loc is None:
                continue
            d = distance_m(point, loc)
            if d > CANDIDATE_RADIUS_M:
                continue
            similarity = name_score(name, hut.get("name", ""))
            if similarity < STRONG_NAME_SCORE:
                continue
            elev = row.get("altitudeM")
            elev_fact = hut.get("facts", {}).get("elevationM")
            elev_osm = elev_fact.get("value") if isinstance(elev_fact, dict) else None
            diff = (abs(elev-elev_osm) if isinstance(elev, (float, int))
                    and not isinstance(elev, bool)
                    and isinstance(elev_osm, (float, int))
                    and not isinstance(elev_osm, bool) else None)
            if diff is not None and diff > ELEVATION_TOLERANCE_M:
                continue
            nearby.append({
                "targetId": hut["id"],
                "osmSourceId": hut.get("sourceIds", {}).get("osm"),
                "distanceM": d, "nameSimilarity": similarity,
                "elevationDifferenceM": diff,
                "geographicMethod": "haversine_WGS84",
                "nameMethod": "normalized_token_jaccard",
                "identityStatus": "review_candidate_only",
                "autoMerged": False,
            })
        nearby.sort(key=lambda c: (-c["nameSimilarity"], c["distanceM"], c["targetId"]))
        if not nearby:
            unmatched.append({"sourceId": source_id, "reason": "no_corroborated_pair",
                              "typeReview": kind_status})
        else:
            matches.append({
                "sourceId": source_id,
                "sourceUrl": "https://rifugi.cai.it/api/v1/shelters/" + cai_source_id(row),
                "typeReview": kind_status,
                "suggestions": nearby,
                "conflict": len(nearby) > 1,
                "reviewStatus": "manual_review_required",
                "linkEstablished": False,
            })
    return {
        "schemaVersion": "1.0", "source": "CAI pilot listing vs OSM refuge staging",
        "status": "REVIEW_ONLY_NO_MERGES",
        "matchPolicy": {
            "candidateRadiusM": CANDIDATE_RADIUS_M,
            "minimumNormalizedNameSimilarity": STRONG_NAME_SCORE,
            "maxElevationDifferenceM": ELEVATION_TOLERANCE_M,
            "categoryUnknownRequiresDetail": True,
            "manualReviewAlwaysRequired": True,
            "licenseClearanceRequired": True,
        },
        "summary": {
            "sourceCount": len(cai_records),
            "osmRefuges": len(osm),
            "categoryStatus": categories,
            "recordsWithCandidates": len(matches),
            "candidatePairs": sum(len(x["suggestions"]) for x in matches),
            "officiallyVerifiedTypes": sum(1 for r in cai_records if cai_source_id(r) in type_evidence),
            "osmCategoryConflicts": len(type_conflicts),
            "ambiguousRecords": sum(x["conflict"] for x in matches),
            "unmatchedRecords": len(unmatched),
            "establishedLinks": 0,
        },
        "candidateMatches": matches, "unmatched": unmatched,
        "typeConflicts": sorted(type_conflicts, key=lambda x: (x["sourceId"], x["osmRefugeId"])),
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cai-sample", type=Path, required=True)
    p.add_argument("--osm-staging", type=Path, default=ROOT / "build" /
                   "import-refuges-v1" / "refuges.json")
    p.add_argument("--output", type=Path, default=ROOT / "build" /
                   "restricted-cai" / "candidate-identity-links.json")
    p.add_argument("--official-type-evidence", type=Path,
                   default=ROOT / "scripts" / "cai_official_type_evidence_v1.json")
    args = p.parse_args()
    cai = json.loads(args.cai_sample.read_text(encoding="utf-8"))
    osm = json.loads(args.osm_staging.read_text(encoding="utf-8"))
    evidence = (json.loads(args.official_type_evidence.read_text(encoding="utf-8"))
                if args.official_type_evidence and args.official_type_evidence.is_file()
                else None)
    report = identity_candidates(cai, osm, verified_types=evidence)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2)
                           + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
