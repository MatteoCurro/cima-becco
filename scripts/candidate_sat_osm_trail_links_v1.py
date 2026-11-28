#!/usr/bin/env python3
"""Cima Becco: SAT↔OSM source-specific crosswalk candidates, strictly G0.

Compares SAT original KML lines with *physical* OSM node-ID graph geometry.
OSM route relations are descriptive; a matching number or overlapping
geometry is evidence for review, NOT a same_as, certified access or routing.
Only independently verified IDs may later become canonical relationships.
Never writes public/, sitemaps or legacy itineraries.

Reference: docs/MODELLO_METADATI_E_LAYOUT.md §8.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/trail-crosswalk-g0-pilot"
SAT_FILE = ROOT / "build/sat-trails-g0-source-audit/sat-trails-normalized-g0.json"
OSM_FILE = ROOT / "build/trail-network-g0-pilot/physical-graph-g0.json"
CHANNEL = "TRAIL_SAT_OSM_CROSSWALK_CANDIDATES_G0_V1"
REF_TOKEN = re.compile(r"^[EO]?[0-9]{3}[A-Z]?$")
REF_SPLIT = re.compile(r"[;,\s/]+")
MAX_SAT_RECORDS = 3000
MAX_OSM_SEGMENTS = 6000


def ref_tokens(raw):
    if not isinstance(raw, str):
        return set()
    # Never turn ranges ("630-631") or descriptive strings into exact refs.
    return {t.upper() for t in REF_SPLIT.split(raw.strip())
            if REF_TOKEN.fullmatch(t.upper())}


def geometry_lines(geo):
    if not isinstance(geo, dict):
        return []
    kind = geo.get("type")
    coords = geo.get("coordinates")
    if kind == "LineString" and isinstance(coords, list):
        return [coords]
    if kind == "MultiLineString" and isinstance(coords, list):
        return coords
    return []


def point_in_bbox(p, bbox, pad=0.0):
    s, w, n, e = bbox
    return w-pad <= p[0] <= e+pad and s-pad <= p[1] <= n+pad


def valid_point(p):
    return (isinstance(p, list) and len(p) >= 2 and
            all(type(v) in (float, int) and math.isfinite(v) for v in p[:2]) and
            6 <= p[0] <= 20 and 35 <= p[1] <= 48)


def relevant_lines(geo, bbox):
    selected = []
    for coords in geometry_lines(geo):
        if (not isinstance(coords, list) or len(coords) < 2 or
            any(not valid_point(p) for p in coords)):
            continue
        if any(point_in_bbox(p, bbox, .002) for p in coords):
            selected.append(coords)
    return selected


def sampled_points(lines, bbox, max_points=72):
    points = [p for line in lines for p in line if point_in_bbox(p, bbox)]
    if len(points) > max_points:
        step = (len(points)-1)/(max_points-1)
        points = [points[round(i*step)] for i in range(max_points)]
    return points


def metres_xy(p, lat_ref):
    return (p[0] * 111194.93 * math.cos(math.radians(lat_ref)),
            p[1] * 111194.93)


def distance_to_segment(p, a, b, lat_ref):
    x, y = metres_xy(p, lat_ref)
    ax, ay = metres_xy(a, lat_ref)
    bx, by = metres_xy(b, lat_ref)
    dx, dy = bx-ax, by-ay
    if dx*dx+dy*dy == 0:
        return math.hypot(x-ax, y-ay)
    t = max(0.0, min(1.0, ((x-ax)*dx+(y-ay)*dy)/(dx*dx+dy*dy)))
    return math.hypot(x-ax-t*dx, y-ay-t*dy)


def distances_to_lines(points, lines, lat_ref):
    result = []
    for point in points:
        best = float("inf")
        for line in lines:
            for a, b in zip(line, line[1:]):
                d = distance_to_segment(point, a, b, lat_ref)
                if d < best:
                    best = d
        result.append(best)
    return result


def percentile(values, q):
    if not values:
        return None
    ordered = sorted(values)
    return ordered[math.ceil((len(ordered)-1)*q)]


def comparison(sat_lines, osm_lines, bbox):
    sat_points = sampled_points(sat_lines, bbox)
    osm_points = sampled_points(osm_lines, bbox)
    if len(sat_points) < 2 or len(osm_points) < 2:
        return None
    lat_ref = (bbox[0]+bbox[2])/2
    # Two directional checks: a short OSM coincident fragment must not be
    # misreported as a complete SAT trail, or vice versa.
    sat_dist = distances_to_lines(sat_points, osm_lines, lat_ref)
    osm_dist = distances_to_lines(osm_points, sat_lines, lat_ref)
    return {
        "satSamples": len(sat_dist),
        "osmSamples": len(osm_dist),
        "satWithin40mFraction": round(sum(d <= 40 for d in sat_dist)/len(sat_dist), 3),
        "osmWithin40mFraction": round(sum(d <= 40 for d in osm_dist)/len(osm_dist), 3),
        "satP90DistanceM": round(percentile(sat_dist, .90), 1),
        "osmP90DistanceM": round(percentile(osm_dist, .90), 1),
        "distanceMethod": "local_equirectangular_point_to_polyline_2d_v1",
        "bboxSampledNotFullTrail": True,
    }


def candidate_strength(metrics, ref_kind):
    # Numeric-only refs are never strong identity evidence (E/O SAT ambiguity).
    if (ref_kind == "source_full_ref" and
        metrics["satWithin40mFraction"] >= .85 and
        metrics["osmWithin40mFraction"] >= .85 and
        metrics["satP90DistanceM"] <= 40 and
        metrics["osmP90DistanceM"] <= 40):
        return "strong_review"
    if (metrics["satWithin40mFraction"] >= .50 and
        metrics["osmWithin40mFraction"] >= .50 and
        metrics["satP90DistanceM"] <= 90 and
        metrics["osmP90DistanceM"] <= 90):
        return "candidate_review"
    return "geometry_conflict"


def source_ref_kind(sat_number, target_ref):
    tokens = ref_tokens(target_ref)
    if sat_number in tokens:
        return "source_full_ref"
    if sat_number[1:] in tokens:
        return "numeric_only_ref"
    return None


def build_candidates(sat, osm):
    if (sat.get("releaseChannel") != "SAT_TRAILS_TYPED_SOURCE_G0_V1" or
        osm.get("releaseChannel") != "OSM_TRAIL_PHYSICAL_GRAPH_G0_STAGING_V1" or
        sat.get("isPublished") is not False or osm.get("isPublished") is not False or
        sat.get("quality", {}).get("osmCrosswalkVerified") is not False):
        raise ValueError("Missing source-only G0 inputs")
    if (not sat.get("sourceArchiveSha256") or not osm.get("sourceSnapshotSha256") or
        not isinstance(sat.get("records"), list) or
        not isinstance(osm.get("segments"), list) or
        not isinstance(osm.get("routeRelations"), list)):
        raise ValueError("Missing source snapshot identity or graph")
    bbox = osm.get("bbox")
    if (not isinstance(bbox, list) or len(bbox) != 4 or
        not all(type(v) in (int, float) and math.isfinite(v) for v in bbox) or
        not (bbox[0] < bbox[2] and bbox[1] < bbox[3])):
        raise ValueError("Invalid or absent OSM pilot bbox")
    if len(sat["records"]) > MAX_SAT_RECORDS or len(osm["segments"]) > MAX_OSM_SEGMENTS:
        raise ValueError("Crosswalk bounded pilot size exceeded")

    # A relation's member ways are *mapped* only when present in this OSM
    # snapshot. Missing way IDs are never backfilled with a nearby line.
    way_segments = defaultdict(list)
    for seg in osm["segments"]:
        source_id = seg.get("sourceIds", {}).get("osmWay")
        if (not isinstance(source_id, str) or
            not re.fullmatch(r"way/[1-9][0-9]*", source_id)):
            raise ValueError("Untraceable OSM physical segment")
        lines = relevant_lines(seg.get("geometry"), bbox)
        if lines:
            way_segments[int(source_id.split("/")[1])].extend(lines)

    targets = []
    for rel in osm["routeRelations"]:
        ref = rel.get("ref")
        if not ref_tokens(ref):
            continue
        members = rel.get("members") or []
        way_ids = {m["osmWayId"] for m in members
                   if isinstance(m, dict) and type(m.get("osmWayId")) is int}
        lines = [line for wid in sorted(way_ids) for line in way_segments.get(wid, [])]
        if lines:
            targets.append({
                "kind": "osm_route_relation",
                "id": "relation/" + str(rel["osmRelationId"]),
                "ref": ref, "lines": lines,
                "sourceUrl": rel.get("sourceUrl"),
                "incompleteMembership": bool(rel.get("missingMemberWayIds")),
                "missingMemberWayIds": rel.get("missingMemberWayIds") or [],
                "mappedWays": len(set(way_ids) & set(way_segments)),
                "ferrataRelationOnly": rel.get("routeType") in ("via_ferrata", "ferrata"),
            })
    # The way-level ref is only evidence for an individual physical span.
    # Multiple split spans of the same source way are one reference target.
    for seg in osm["segments"]:
        ref = seg.get("sourceTags", {}).get("ref")
        if not ref_tokens(ref):
            continue
        wid = seg["sourceIds"]["osmWay"]
        if any(t["id"] == wid for t in targets):
            continue
        lines = way_segments.get(int(wid.split("/")[1]), [])
        if lines:
            targets.append({
                "kind": "osm_physical_way", "id": wid, "ref": ref, "lines": lines,
                "sourceUrl": "https://www.openstreetmap.org/" + wid,
                "incompleteMembership": None, "missingMemberWayIds": [],
                "mappedWays": 1, "ferrataRelationOnly": False,
            })
    # Do not treat duplicate spans as separate target identities.
    targets = list({(x["kind"], x["id"]): x for x in targets}.values())

    candidates = []
    counts = Counter()
    original_numbers = Counter(
        r.get("sourceIds", {}).get("satTrailNumberReported")
        for r in sat["records"] if r.get("sourceIds", {}).get("satTrailNumberReported"))
    for record in sat["records"]:
        sat_number = record.get("sourceIds", {}).get("satTrailNumberReported")
        if (not isinstance(sat_number, str) or
            not re.fullmatch(r"[EO][0-9]{3}[A-Z]?", sat_number)):
            counts["satInvalidRef"] += 1
            continue
        if original_numbers[sat_number] > 1:
            counts["satDuplicateRefHeld"] += 1
            continue
        geo = (record.get("geo") or {}).get("geometry")
        lines = relevant_lines(geo, bbox)
        if not lines or len(sampled_points(lines, bbox)) < 2:
            counts["satOutsideOrInsufficientOverlap"] += 1
            continue
        counts["satWithSampleGeometry"] += 1
        matched_ref = False
        for target in targets:
            ref_kind = source_ref_kind(sat_number, target["ref"])
            if not ref_kind:
                continue
            matched_ref = True
            metrics = comparison(lines, target["lines"], bbox)
            if not metrics:
                counts["insufficientTargetSamples"] += 1
                continue
            level = candidate_strength(metrics, ref_kind)
            counts[level] += 1
            candidates.append({
                "sourceIds": {
                    "satSourceNumber": sat_number,
                    "satSourceRecordFingerprint": record["sourceRecordFingerprint"],
                    "osmSourceId": target["id"],
                },
                "sources": {
                    "sat": {"url": sat["sourceUrl"], "sha256": sat["sourceArchiveSha256"]},
                    "osm": {"url": target["sourceUrl"], "sha256": osm["sourceSnapshotSha256"]},
                },
                "targetKind": target["kind"],
                "referenceEvidence": {"method": ref_kind, "osmRefOriginal": target["ref"]},
                "geometryEvidence": metrics,
                "mappedMemberWays": target["mappedWays"],
                "osmRelationMembershipIncomplete": target["incompleteMembership"],
                "missingMemberWayIds": target["missingMemberWayIds"],
                "relationFerrataOnly": target["ferrataRelationOnly"],
                "reviewStatus": level,
                "quality": {
                    "gate": "G0", "crosswalkVerified": False,
                    "canonicalIdentityVerified": False,
                    "routeContinuityVerified": False, "accessibleFromVerified": False,
                    "ferrataSubtypeVerified": False,
                    "satSourceRecordRequiresReview": bool(
                        record.get("quality", {}).get("requiresReview")),
                },
            })
        if not matched_ref:
            counts["satNoRefMatch"] += 1

    # A candidate is not unique if two SAT or OSM source objects compete,
    # irrespective of coordinate proximity or rank.
    by_sat = Counter(x["sourceIds"]["satSourceNumber"] for x in candidates
                     if x["reviewStatus"] != "geometry_conflict")
    by_osm = Counter(x["sourceIds"]["osmSourceId"] for x in candidates
                     if x["reviewStatus"] != "geometry_conflict")
    for row in candidates:
        conflict = (by_sat[row["sourceIds"]["satSourceNumber"]] > 1 or
                    by_osm[row["sourceIds"]["osmSourceId"]] > 1)
        row["quality"]["ambiguousCandidate"] = conflict
        if conflict and row["reviewStatus"] == "strong_review":
            row["reviewStatus"] = "ambiguous_review"
        # Never set true automatically: a common number + nearby geometry
        # is not a two-way independent official identifier.
        row["quality"]["crosswalkVerified"] = False
    candidates.sort(key=lambda c: (
        c["sourceIds"]["satSourceNumber"], c["targetKind"],
        c["sourceIds"]["osmSourceId"]))
    counts["candidatesTotal"] = len(candidates)
    counts["ambiguousCandidates"] = sum(x["quality"]["ambiguousCandidate"] for x in candidates)
    counts["relationCandidates"] = sum(x["targetKind"] == "osm_route_relation" for x in candidates)
    counts["wayCandidates"] = sum(x["targetKind"] == "osm_physical_way" for x in candidates)
    counts["candidateCrosswalksVerified"] = 0
    return {
        "schemaVersion": "1.0", "releaseChannel": CHANNEL,
        "isPublished": False, "seoIndexable": False, "routeCatalogueModified": False,
        "sourceArchiveSha256": sat["sourceArchiveSha256"],
        "osmSourceSnapshotSha256": osm["sourceSnapshotSha256"],
        "bbox": bbox,
        "quality": {"gate": "G0", "crosswalkVerified": False,
                    "canonicalLinksCreated": False, "routingAllowed": False,
                    "safetyVerified": False, "publicationAllowed": False,
                    "officialFerrataSubtypeVerified": False},
        "counts": dict(sorted(counts.items())),
        "candidates": candidates,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sat", type=Path, default=SAT_FILE)
    parser.add_argument("--osm", type=Path, default=OSM_FILE)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    sat = json.loads(args.sat.read_text(encoding="utf-8"))
    osm = json.loads(args.osm.read_text(encoding="utf-8"))
    result = build_candidates(sat, osm)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "sat-osm-crosswalk-candidates-g0.json").write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8")
    print(json.dumps(result["counts"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as exc:
        sys.exit(str(exc))
