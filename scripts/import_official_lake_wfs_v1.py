#!/usr/bin/env python3
"""Bounded OFFICIAL lake-shape WFS pilot, independent of OSM (Bible §§1,5,30-31).

Outputs *only* non-public G0 source evidence. No name/distance crosswalk, no
subtype guess, no SEO, no public/data writes. WFS feature IDs are provisional
until the provider's schema and stability have been independently audited.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

from enrich_natural_water_geometry_v1 import (
    MAX_VERTICES, point_inside_polygon, ring_area_km2, valid_ring,
)

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = "OFFICIAL_LAKE_WFS_G0_STAGING_V1"
PILOT_BBOX = (11.15, 46.28, 12.95, 46.95)  # W,S,E,N, Dolomiti pilot
MAX_FEATURES = 20
MAX_BYTES = 6_000_000
PROVIDERS = {
    "bolzano_lakes": {
        "endpoint": "https://geoservices1.civis.bz.it/geoserver/p_bz-Hydrology/ows",
        "wfsVersion": "2.0.0",
        "layerSuffix": "Lakes",
        "sourceUrl": "https://data.civis.bz.it/dataset/laghi",
        "licence": "CC0 1.0",
        "sourceDatasetId": "p_bz:Hydrology:Lakes",
        "sourceScale": None,  # Do not infer a scale from the WFS endpoint
    },
    "arpav_water_surfaces": {
        "endpoint": "https://gaia.arpa.veneto.it/geoserver/ows",
        "wfsVersion": "1.0.0",
        "layerSuffix": "idrografia_specchio_acqua",
        "sourceUrl": (
            "https://geodati.gov.it/geoportale/visualizzazione-metadati/"
            "scheda-metadati?metadataid=arpa_ve:idrografia_specchio_acqua"
        ),
        "licence": "CC BY 3.0",
        "sourceDatasetId": "arpa_ve:idrografia_specchio_acqua",
        "sourceScale": "1:10000",
    },
}


def now_utc():
    return datetime.now(timezone.utc).isoformat()


def fetch_limited(url: str, *, limit=MAX_BYTES):
    req = Request(url, headers={
        "User-Agent": "CimaBecco/1.0 (+https://github.com/MatteoCurro/cima-becco)",
        "Accept": "application/json, application/xml, text/xml",
    })
    with urlopen(req, timeout=45) as response:
        raw = response.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("Official WFS response exceeds bounded pilot size")
    return raw


def discover_typename(capabilities: bytes, provider: str):
    """Discover exactly one advertised layer; never guess a WFS namespace."""
    root = ET.fromstring(capabilities)
    if not root.tag.lower().endswith("capabilities"):
        raise ValueError("WFS GetCapabilities did not return capabilities XML")
    expected = PROVIDERS[provider]["layerSuffix"].lower()
    matches = []
    for node in root.iter():
        if node.tag.split("}")[-1] != "FeatureType":
            continue
        names = [n.text.strip() for n in node
                 if n.tag.split("}")[-1] == "Name" and n.text]
        if len(names) == 1 and names[0].split(":")[-1].lower() == expected:
            matches.append(names[0])
    if len(matches) != 1:
        raise ValueError("Official source layer missing or ambiguous in WFS")
    return matches[0]


def wfs_urls(provider: str, typename: str, *, bbox_mode="native"):
    p = PROVIDERS[provider]
    base = p["endpoint"]
    version = p["wfsVersion"]
    cap = base + "?" + urlencode({
        "service": "WFS", "version": version, "request": "GetCapabilities",
    })
    # WFS 2.0 EPSG:4326 advertises latitude/longitude axis ordering in
    # BBOX; WFS 1.0 uses longitude/latitude. GeoJSON output is always lon/lat.
    west, south, east, north = PILOT_BBOX
    if bbox_mode not in ("native", "alternate", "none"):
        raise ValueError("Unsupported WFS BBOX probe mode")
    latlon = version == "2.0.0"
    if bbox_mode == "alternate":
        latlon = not latlon
    bounds = (south, west, north, east) if latlon else (west, south, east, north)
    params = {
        "service": "WFS", "version": version, "request": "GetFeature",
        ("typeNames" if version == "2.0.0" else "typeName"): typename,
        ("count" if version == "2.0.0" else "maxFeatures"): MAX_FEATURES,
        "srsName": "EPSG:4326", "outputFormat": "application/json",
    }
    if bbox_mode != "none":
        params["bbox"] = ",".join(map(str, bounds)) + ",EPSG:4326"
    return cap, base + "?" + urlencode(params)


def _coords(points):
    if not isinstance(points, list) or not (4 <= len(points) <= MAX_VERTICES + 1):
        raise ValueError("Unclosed or oversized official boundary")
    result = []
    for pair in points:
        if (not isinstance(pair, (list, tuple)) or len(pair) < 2
            or any(type(v) not in (int, float) or not math.isfinite(v)
                   for v in pair[:2])):
            raise ValueError("Non-numeric official polygon coordinate")
        lon, lat = float(pair[0]), float(pair[1])
        if not (6 <= lon <= 20 and 35 <= lat <= 48):
            raise ValueError("Non-WGS84 or out-of-scope official coordinate")
        result.append([round(lon, 7), round(lat, 7)])
    return valid_ring(result)


def validate_geometry(geometry):
    if not isinstance(geometry, dict):
        raise ValueError("No area geometry in WFS feature")
    typ = geometry.get("type")
    raw = geometry.get("coordinates")
    if typ == "Polygon":
        raw = [raw]
    elif typ != "MultiPolygon":
        raise ValueError("WFS geometry is not a polygon")
    if not isinstance(raw, list) or not (1 <= len(raw) <= 24):
        raise ValueError("No polygons or oversized MultiPolygon")
    groups = []
    area = 0.0
    for polygon in raw:
        if not isinstance(polygon, list) or not (1 <= len(polygon) <= 15):
            raise ValueError("Invalid ring count")
        rings = [_coords(r) for r in polygon]
        outer = rings[0]
        for hole in rings[1:]:
            if not all(point_inside_polygon(p, {"type": "MultiPolygon",
                    "coordinates": [[outer]]}) for p in hole[:-1]):
                raise ValueError("WFS island outside mapped lake")
        if any(point_inside_polygon(a[0], {"type": "MultiPolygon",
               "coordinates": [[b]]}) or
               point_inside_polygon(b[0], {"type": "MultiPolygon",
               "coordinates": [[a]]})
               for i, a in enumerate(rings[1:])
               for b in rings[i+2:]):
            raise ValueError("WFS islands overlap")
        part = ring_area_km2(outer) - sum(ring_area_km2(r) for r in rings[1:])
        if part <= 0:
            raise ValueError("WFS islands exceed mapped water")
        groups.append(rings)
        area += part
    if not 0.00001 < area < 350:
        raise ValueError("Implausible mapped water surface in bounded pilot")
    return {"type": "MultiPolygon", "coordinates": groups}, round(area, 6)


def parse_geojson(raw: bytes, provider: str, *, at=None, request_url=None):
    p = PROVIDERS[provider]
    at = at or now_utc()
    doc = json.loads(raw)
    if doc.get("type") != "FeatureCollection" or not isinstance(doc.get("features"), list):
        raise ValueError("WFS did not return a GeoJSON FeatureCollection")
    crs = doc.get("crs")
    if crs:
        crs_name = (crs.get("properties") or {}).get("name", "")
        if not (crs_name.endswith("4326") or "CRS84" in crs_name):
            raise ValueError("WFS geometry CRS is not confirmed WGS84")
    if len(doc["features"]) > MAX_FEATURES:
        raise ValueError("WFS feature limit was ignored")
    candidates, rejected, seen = [], Counter(), set()
    for feature in doc["features"]:
        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            rejected["not_a_feature"] += 1
            continue
        props = feature.get("properties")
        if not isinstance(props, dict):
            rejected["missing_properties"] += 1
            continue
        source_fid = feature.get("id")
        if not isinstance(source_fid, (int, str)) or not str(source_fid).strip():
            rejected["missing_provider_feature_id"] += 1
            continue
        source_fid = str(source_fid)
        if source_fid in seen:
            raise ValueError("Duplicate WFS feature identifier; source pagination unsafe")
        seen.add(source_fid)
        try:
            geometry, area = validate_geometry(feature.get("geometry"))
        except ValueError as exc:
            rejected[str(exc)] += 1
            continue
        # Dataset name or coordinates are NOT an identity proof for OSM/GN.
        # Preserve a small scalar raw-field evidence inventory, without
        # assigning any unverified environmental or access interpretation.
        attrs = {str(k): v for k, v in props.items()
                 if isinstance(k, str) and len(k) <= 80
                 and (v is None or type(v) in (str, int, float, bool))
                 and len(str(v)) <= 250}
        candidates.append({
            "sourceFeatureId": source_fid,
            "sourceIds": {provider: source_fid},
            "kind": "natural_feature",
            "subtype": None,
            "sourceLayerClass": p["layerSuffix"],
            "sourcePropertiesRaw": attrs,
            "geo": {
                "area": geometry, "areaSourceUrl": request_url or p["sourceUrl"],
                "areaMethod": "official_WFS_polygon_as_reported",
                "crs": "EPSG:4326", "precision": p["sourceScale"],
            },
            "facts": {
                "providerMappedWaterSurfaceKm2": {
                    "value": area, "unit": "km2", "method": "derived",
                    "sourceId": provider + ":" + source_fid,
                    "sourceUrl": p["sourceUrl"], "licence": p["licence"],
                    "retrievedAt": at,
                    "notes": "Area computed from WFS geometry; NOT the agency's official area value",
                }
            },
            "quality": {
                "gate": "G0", "seoIndexable": False,
                "providerIdStabilityVerified": False,
                "osmWikidataGeonamesIdentityVerified": False,
                "subtypeConfirmed": False,
                "needsReview": True,
            },
            "relations": [], "restrictions": [], "media": [],
        })
    return ({
        "releaseChannel": CHANNEL, "isPublished": False,
        "sourceProvider": provider, "sourceDatasetId": p["sourceDatasetId"],
        "licence": p["licence"], "retrievedAt": at,
        "requestUrl": request_url, "rawSha256": sha256(raw).hexdigest(),
        "sampleOnly": True, "completeDataset": False, "entities": candidates,
    }, {
        "provider": provider, "received": len(doc["features"]),
        "acceptedG0": len(candidates), "rejectedOrReview": dict(rejected),
        "published": 0, "seoIndexable": 0, "sourceFeatureIdsUnique": True,
        "independentFromOSM": True, "completeDataset": False,
    })


def run_live(provider: str):
    # Only fixed known government endpoints are queried; no user-supplied URLs.
    p = PROVIDERS[provider]
    cap_url, _ = wfs_urls(provider, p["layerSuffix"])
    capabilities = fetch_limited(cap_url, limit=2_000_000)
    typename = discover_typename(capabilities, provider)
    # Some GeoServers disagree on EPSG:4326 BBOX axis order in WFS 2.0.
    # Probe both *bounded* interpretations before a last, at-most-20-feature
    # non-geographic diagnostic. Never silently assert sample completeness.
    for mode in ("native", "alternate", "none"):
        _, get_url = wfs_urls(provider, typename, bbox_mode=mode)
        raw = fetch_limited(get_url)
        response = json.loads(raw)
        if response.get("type") != "FeatureCollection" or not isinstance(response.get("features"), list):
            raise ValueError("Unexpected response from official WFS GetFeature")
        if response["features"]:
            print("WFS live source probe mode:", mode, "sample:", len(response["features"]), flush=True)
            return raw, get_url, sha256(capabilities).hexdigest(), typename
    raise RuntimeError("Official WFS returned zero features in both BBOX orders and capped diagnostic")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", required=True, choices=sorted(PROVIDERS))
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--input-file", type=Path)
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--out", type=Path,
                        default=ROOT / "build/import-official-lakes-wfs-g0")
    args = parser.parse_args()
    if args.live:
        raw, url, cap_hash, typename = run_live(args.provider)
    else:
        raw = args.input_file.read_bytes()
        url = None
        cap_hash = None
        typename = None
    staged, report = parse_geojson(raw, args.provider, request_url=url)
    staged["capabilitiesSha256"] = cap_hash
    staged["advertisedLayerName"] = typename
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "official-lake-source-g0.json").write_text(
        json.dumps(staged, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.out / "official-lake-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    # Preserve exact source snapshot for future replay; never publish it.
    (args.out / "official-lake-raw.geojson").write_bytes(raw)
    print(json.dumps(report, ensure_ascii=False))
    if args.live and not report["acceptedG0"]:
        raise SystemExit("No usable WFS feature: source must be investigated, not published")


if __name__ == "__main__":
    main()
