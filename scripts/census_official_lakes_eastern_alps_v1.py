#!/usr/bin/env python3
"""Bounded multi-cell census of *official* eastern Alpine lake/water polygons.

Never confuse WFS source records with unique physical lakes. G0 only, no
cross-source merge, no publishing/SEO, no inference of access or bathing.
Cell splitting avoids both global 20-feature samples and unstable WFS paging.
"""
from __future__ import annotations

import argparse
from collections import Counter, deque
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import time
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from xml.etree import ElementTree as ET

from import_official_lake_wfs_v1 import (
    MAX_FEATURES, PROVIDERS, CHANNEL, discover_typename, fetch_limited,
    now_utc, parse_geojson, wfs_urls,
)
from normalize_official_lake_wfs_facts_v1 import enrich_staged

ROOT = Path(__file__).resolve().parents[1]
REGION = "eastern_alps"
REGION_BBOX = {
    # Including *all* South Tyrol + immediately adjacent Alpine margins;
    # source provider's territorial coverage remains its own authority.
    "bolzano_lakes": (10.30, 46.18, 12.58, 47.15),
    # Veneto Alpine and Prealpine belt, not Venice lagoon.
    "arpav_water_surfaces": (10.70, 45.55, 13.35, 46.85),
}
MAX_REQUESTS = 76
MAX_DEPTH = 3
MAX_TOTAL_BYTES = 45_000_000
RESPONSE_LIMIT = 5_000_000
PAUSE_SECONDS = 0.2


def _bbox_string(provider, box):
    west, south, east, north = box
    if not (6 <= west < east <= 20 and 35 <= south < north <= 48):
        raise ValueError("Region box outside Italian Alpine geographic bounds")
    conf = PROVIDERS[provider]
    latlon = conf["wfsVersion"] == "2.0.0"
    if conf["preferredBboxMode"] == "alternate":
        latlon = not latlon
    vals = (south, west, north, east) if latlon else (west, south, east, north)
    return ",".join(map(str, vals)) + ",EPSG:4326"


def wfs_census_url(provider, typename, box=None, *, hits=False):
    """Re-use proven WFS URL/CRS/layer semantics, never arbitrary endpoints."""
    if provider not in PROVIDERS or not typename:
        raise ValueError("Unrecognized WFS source")
    _, template = wfs_urls(provider, typename,
                           bbox_mode=PROVIDERS[provider]["preferredBboxMode"])
    split = urlsplit(template)
    params = dict(parse_qsl(split.query))
    params.pop("bbox", None)
    if box is not None:
        params["bbox"] = _bbox_string(provider, box)
    if hits:
        params["resultType"] = "hits"
        params.pop("outputFormat", None)
        params.pop("srsName", None)
    return urlunsplit(split._replace(query=urlencode(params)))


def parse_wfs_hits(raw):
    """Return unknown if provider doesn't advertise a count; never invent."""
    try:
        root = ET.fromstring(raw)
    except ET.ParseError:
        return None
    if root.tag.rsplit("}", 1)[-1] != "FeatureCollection":
        return None
    for key in ("numberMatched", "numberOfFeatures"):
        n = root.attrib.get(key)
        if n is not None and n.isdigit():
            return int(n)
    return None


def split4(box):
    w, s, e, n = box
    m_lon, m_lat = (w + e) / 2, (s + n) / 2
    return (
        (w, s, m_lon, m_lat), (m_lon, s, e, m_lat),
        (w, m_lat, m_lon, n), (m_lon, m_lat, e, n),
    )


def bbox_overlap(polygon, box):
    w, s, e, n = box
    points = [
        pair for outer in polygon.get("coordinates", [])
        for ring in outer for pair in ring
    ]
    if not points:
        return False
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return max(xs) >= w and min(xs) <= e and max(ys) >= s and min(ys) <= n


def source_name(entity, provider):
    attrs = entity.get("sourcePropertiesRaw", {})
    keys = ("NAME_IT", "NAME_DE") if provider == "bolzano_lakes" else ("nome",)
    return next((
        v.strip() for k in keys if isinstance((v := attrs.get(k)), str)
        and v.strip() and len(v.strip()) <= 180
    ), None)


def census(provider, *, fetcher=fetch_limited, max_requests=MAX_REQUESTS,
           max_depth=MAX_DEPTH, pause=PAUSE_SECONDS, bbox=None):
    if provider not in PROVIDERS:
        raise ValueError("Unknown WFS source")
    if not 1 <= max_requests <= MAX_REQUESTS or not 0 <= max_depth <= MAX_DEPTH:
        raise ValueError("Census budget outside hard limits")
    bbox = bbox or REGION_BBOX[provider]
    _bbox_string(provider, bbox)
    at = now_utc()
    cap_url, _ = wfs_urls(provider, PROVIDERS[provider]["layerSuffix"])
    cap_raw = fetcher(cap_url, limit=2_000_000)
    typename = discover_typename(cap_raw, provider)
    hits = {}
    for key, region in (("layer", None), ("region", bbox)):
        url = wfs_census_url(provider, typename, region, hits=True)
        try:
            hits[key] = parse_wfs_hits(fetcher(url, limit=1_000_000))
        except (OSError, TimeoutError, ValueError) as exc:
            hits[key] = None
            print("WFS hits unavailable for", provider, key, type(exc).__name__, flush=True)
        if pause:
            time.sleep(pause)
    todo = deque([(bbox, 0)])
    staged_by_id = {}
    seen_raw_fids = set()
    snapshots = []
    unresolved = []
    rejected = Counter()
    total_bytes = 0
    count = 0
    duplicate_count = 0
    while todo and count < max_requests and total_bytes < MAX_TOTAL_BYTES:
        tile, depth = todo.popleft()
        url = wfs_census_url(provider, typename, tile)
        try:
            raw = fetcher(url, limit=RESPONSE_LIMIT)
        except (OSError, TimeoutError, ValueError) as exc:
            unresolved.append({"bbox":tile, "depth":depth,
                               "reason":"WFS request failed: " + type(exc).__name__})
            count += 1
            continue
        count += 1
        total_bytes += len(raw)
        # Parser independently enforces hard cap of MAX_FEATURES, WGS84,
        # valid source IDs and correct polygon topology.
        parsed, diagnostic = parse_geojson(raw, provider, at=at, request_url=url)
        received = diagnostic["received"]
        if received >= MAX_FEATURES:
            # Do NOT assume a capped request exhausts a cell. Split into
            # four non-overlapping cells and deduplicate by the original FID.
            # Keep the capped parent evidence as well, in case its large
            # polygon straddles the child cell boundaries.
            if depth < max_depth:
                todo.extend((child, depth + 1) for child in split4(tile))
            else:
                unresolved.append({"bbox":tile, "depth":depth,
                                   "reason":"feature cap at maximum split depth"})
        seen_before = len(seen_raw_fids)
        for entity in parsed["entities"]:
            fid = entity["sourceFeatureId"]
            seen_raw_fids.add(fid)
            if not bbox_overlap(entity["geo"]["area"], tile):
                rejected["geometry_bbox_does_not_intersect_requested_tile"] += 1
                continue
            if fid in staged_by_id:
                previous = staged_by_id[fid]
                if (previous["sourcePropertiesRaw"] != entity["sourcePropertiesRaw"] or
                        previous["geo"]["area"] != entity["geo"]["area"]):
                    raise ValueError("Same provider FID has conflicting snapshots")
                duplicate_count += 1
            else:
                staged_by_id[fid] = entity
        for reason, qty in diagnostic["rejectedOrReview"].items():
            rejected[reason] += qty
        snapshots.append({
            "bbox": tile, "depth":depth, "received":received,
            "acceptedInResponse":diagnostic["acceptedG0"],
            "sha256":sha256(raw).hexdigest(),
            "requestUrl":url, "atFeatureCap":received >= MAX_FEATURES,
        })
        print(json.dumps({
            "provider":provider, "request":count,
            "received":received, "uniqueAccepted":len(staged_by_id),
            "queued":len(todo), "depth":depth,
        }), flush=True)
        if pause:
            time.sleep(pause)
    for tile, depth in todo:
        unresolved.append({"bbox":tile, "depth":depth,
                           "reason":"request/byte budget exhausted"})
    result = {
        "releaseChannel":CHANNEL, "isPublished":False,
        "sourceProvider":provider,
        "sourceDatasetId":PROVIDERS[provider]["sourceDatasetId"],
        "licence":PROVIDERS[provider]["licence"],
        "retrievedAt":at, "requestedRegion":REGION, "requestedBbox":bbox,
        "sampleOnly":True, "completeDataset":False,
        "capabilitiesSha256":sha256(cap_raw).hexdigest(),
        "advertisedLayerName":typename,
        "entities":[staged_by_id[k] for k in sorted(staged_by_id)],
    }
    normalized, norm_report = enrich_staged(result)
    classifications = Counter()
    named = 0
    for entity in normalized["entities"]:
        if source_name(entity,provider):
            named += 1
        if provider == "arpav_water_surfaces":
            typ = entity.get("providerWaterClassRaw")
            classifications[typ if typ else "unknown"] += 1
    # Total raw feature count is inferred only if the tiles are provably
    # exhaustive and repeat/edge features do not change identity.
    census_is_complete = not unresolved
    region_hits = hits.get("region")
    if region_hits is not None and len(seen_raw_fids) < region_hits:
        census_is_complete = False
        unresolved.append({"reason":"matched features in hits exceed returned unique IDs",
                           "hits":region_hits, "rawUniqueIds":len(seen_raw_fids)})
    report = {
        "provider":provider, "requestedRegion":REGION, "requestedBbox":bbox,
        "sourceLayerNumberMatched":hits.get("layer"),
        "requestedRegionNumberMatched":region_hits,
        "featuresRawDistinctSeen":len(seen_raw_fids),
        "acceptedIndependentSourceRecordsG0":len(normalized["entities"]),
        "namedAcceptedRecords":named,
        "providerClassifications":dict(classifications),
        "duplicateTileAppearances":duplicate_count,
        "geometryReviewReasons":dict(rejected),
        "numericReviewReasons":norm_report["numericAnomalies"],
        "requests":count, "bytesFetched":total_bytes,
        "remainingUnresolvedCells":len(unresolved),
        "unresolvedCells":unresolved,
        "regionEnumerationComplete":census_is_complete,
        "regionEnumerationProvenByHits":(
            census_is_complete and region_hits is not None and
            len(seen_raw_fids) == region_hits
        ),
        "sampleOnly":True, "completeDataset":False,
        "crossSourceIdentityVerified":False,
        "published":0, "seoIndexable":0,
        "recordsAreNotUniquePhysicalLakes":True,
        "snapshots":snapshots,
    }
    return normalized, report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--provider",required=True,choices=sorted(PROVIDERS))
    p.add_argument("--max-requests",type=int,default=MAX_REQUESTS)
    p.add_argument("--max-depth",type=int,default=MAX_DEPTH)
    p.add_argument("--out",type=Path,
                   default=ROOT / "build/official-lake-eastern-alps-census")
    args = p.parse_args()
    doc, audit = census(args.provider, max_requests=args.max_requests,
                        max_depth=args.max_depth)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"regional-lake-records-g0.json").write_text(
        json.dumps(doc,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"
    )
    (args.out/"regional-lake-census-audit.json").write_text(
        json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"
    )
    print("CENSUS_SUMMARY",json.dumps({
        k:audit[k] for k in (
            "provider", "sourceLayerNumberMatched",
            "requestedRegionNumberMatched","acceptedIndependentSourceRecordsG0",
            "namedAcceptedRecords","providerClassifications",
            "regionEnumerationComplete","regionEnumerationProvenByHits",
            "remainingUnresolvedCells","published",
        )
    },ensure_ascii=False),flush=True)


if __name__=="__main__":
    main()
