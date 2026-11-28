#!/usr/bin/env python3
"""Blocco 5 Cima Becco: GeoNames summit/group pilot, SOLO staging.

Reads the existing public/data/peaks shards (no new GeoNames download).
Never changes public data, permalinks or the SEO index. QID resolution requires
an independently audited Wikidata P1566 crosswalk; proximity is not identity.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
import uuid

ROOT = Path(__file__).resolve().parents[1]
PEAKS = ROOT / "public/data/peaks"
PHOTO_FILE = PEAKS / "photos.json"
OUT = ROOT / "build/import-summits-v1"
CODES = {
    "PK": ("summit", "peak"),
    "MT": ("summit", "mountain"),
    "HLL": ("summit", "hill"),
    "MTS": ("mountain_group", "mountain_group"),
    "HLLS": ("mountain_group", "hill_group"),
}
LICENSE = "CC BY 4.0"
SOURCE = "https://www.geonames.org/"


def slugify(value):
    value = unicodedata.normalize("NFKD", value).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", value)).strip("-")[:100]


def valid_row(row):
    if not isinstance(row, list) or len(row) != 8:
        return False
    ident, name, lat, lng, ele, source, country, feature = row
    return (
        type(ident) is int and ident > 0
        and isinstance(name, str) and bool(slugify(name))
        and all(type(n) in (float, int) and math.isfinite(n) for n in (lat, lng))
        and -90 <= lat <= 90 and -180 <= lng <= 180
        and type(ele) in (int, float) and math.isfinite(ele)
        and source in ("s", "d") and isinstance(country, str)
        and re.fullmatch(r"[A-Z]{2}", country) is not None
        and feature in CODES
    )


def tile_names(index, bbox):
    south, west, north, east = bbox
    step = index.get("tile")
    if type(step) is not int or not 1 <= step <= 10:
        raise ValueError("Invalid GeoNames index tile size")
    if not (-90 <= south < north <= 90 and -180 <= west < east <= 180):
        raise ValueError("Invalid bounding box (antimeridian needs separate batches)")
    names = []
    for lat in range(math.floor(south / step) * step, math.ceil(north / step) * step, step):
        for lng in range(math.floor(west / step) * step, math.ceil(east / step) * step, step):
            key = f"{lat}_{lng}"
            if key in index.get("cells", {}):
                names.append(key + ".json")
    return sorted(names)


def load_candidates(directory, bbox, country=None):
    index_file = directory / "index.json"
    index_bytes = index_file.read_bytes()
    index = json.loads(index_bytes)
    snapshots = {"index.json": hashlib.sha256(index_bytes).hexdigest()}
    unique, rejected, conflicts = {}, Counter(), []
    for filename in tile_names(index, bbox):
        raw = (directory / filename).read_bytes()
        snapshots[filename] = hashlib.sha256(raw).hexdigest()
        rows = json.loads(raw)
        if not isinstance(rows, list):
            raise ValueError("GeoNames tile is not a list: " + filename)
        for row in rows:
            if not valid_row(row):
                rejected["invalid_or_unsupported"] += 1
                continue
            ident, name, lat, lng, ele, src, cc, code = row
            if not (bbox[0] <= lat <= bbox[2] and bbox[1] <= lng <= bbox[3]):
                continue
            if country and country != cc:
                continue
            old = unique.get(ident)
            if old is None:
                unique[ident] = row
            elif old != row:
                conflicts.append({"geonameid": ident, "reason": "contradictory_tile_rows"})
                del unique[ident]
                rejected["duplicate_identity_conflict"] += 1
    for conflict in conflicts:
        unique.pop(conflict["geonameid"], None)
    return sorted(unique.values(), key=lambda r: (-r[4], r[0])), snapshots, rejected, conflicts


def read_crosswalk(path):
    if not path:
        return {}
    entries = json.loads(Path(path).read_text(encoding="utf-8")).get("links", [])
    out = {}
    for row in entries:
        ident = str(row.get("geonameid", ""))
        qid = str(row.get("qid", ""))
        if not (re.fullmatch(r"[1-9][0-9]*", ident)
                and re.fullmatch(r"Q[1-9][0-9]*", qid)
                and row.get("verified") is True
                and row.get("wdtP1566") == ident
                and row.get("sourceUrl") == f"https://www.wikidata.org/wiki/{qid}"):
            raise ValueError("Unverified Wikidata P1566 crosswalk")
        if ident in out and out[ident] != qid:
            raise ValueError("One GeoNames ID maps to multiple QIDs")
        out[ident] = qid
    if len(set(out.values())) != len(out):
        raise ValueError("Two GeoNames IDs map to the same QID: manual review required")
    return out


def fact(value, unit, source_id, url, checked_at, method):
    return {
        "value": value, "unit": unit, "sourceId": source_id,
        "sourceUrl": url, "licence": LICENSE, "retrievedAt": checked_at,
        "sourceUpdatedAt": None, "validFrom": None, "validUntil": None,
        "method": method, "confidence": 0.85 if method == "reported" else 0.6,
    }


def legacy_slug(row, step):
    ident, _, lat, lng = row[:4]
    token = lambda n: f"m{-n}" if n < 0 else str(n)
    return f"gn{ident}-{token(math.floor(lat / step) * step)}x{token(math.floor(lng / step) * step)}"


def create_entity(row, *, checked_at, tile_size, duplicate_name=False, qid=None, photo=None):
    ident, name, lat, lng, ele, provenance, cc, feature = row
    kind, subtype = CODES[feature]
    stable_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"https://www.geonames.org/{ident}"))
    base_slug = slugify(name)
    provisional = f"{base_slug}-{stable_id[:8]}" if duplicate_name else base_slug
    url = SOURCE + str(ident) + "/"
    quality = "G0" if duplicate_name or kind == "mountain_group" else "G1"
    facts = {
        "featureClass": fact(feature, None, "geonames:" + str(ident),
                             url, checked_at, "reported")
    }
    if 0 < ele < 9000:
        facts["elevationM"] = fact(
            ele, "m", "geonames:" + str(ident), url, checked_at,
            "reported" if provenance == "s" else "estimated"
        )
    entity = {
        "id": stable_id, "kind": kind, "subtype": subtype,
        "name": name.strip(), "displayName": name.strip(),
        "aliases": [], "localNames": [], "slug": provisional,
        "slugAliases": [legacy_slug(row, tile_size)],
        "sourceIds": {"geonames": str(ident), **({"wikidata": qid,
            "wikidataVerifiedBy": "P1566"} if qid else {})},
        "geo": {"point": {"lat": lat, "lng": lng},
                "area": None, "method": "geonames_point",
                "sourceUrl": url, "precision": "provider_not_declared"},
        "facts": facts, "factsAlternatives": [],
        "administrativeHierarchy": {"country": cc},
        "shortSummary": None, "description": None, "history": None,
        "relations": [], "media": [], "textSources": [],
        "restrictions": [], "alerts": [],
        "editorialStatus": "linked" if quality == "G1" else "raw",
        "quality": {"gate": quality, "seoIndexable": False,
                    "reviewRequired": duplicate_name,
                    "slugRequiresReview": duplicate_name,
                    "groupAreaNotVerified": kind == "mountain_group"},
        "checkedAt": checked_at, "updatedAt": checked_at,
    }
    # GeoNames photo cache is useful but does not prove the exact mountain
    # is depicted. Keep as a review candidate, never as licensed live media.
    if photo and len(photo) >= 4 and str(photo[1]).startswith("https://"):
        entity["mediaCandidates"] = [{
            "url": photo[0], "sourceUrl": photo[1],
            "author": photo[2], "licence": photo[3],
            "subjectVerified": False, "reuseAllowed": False,
            "reviewRequired": True, "method": "legacy_peak_photo_cache",
        }]
    return entity


def distance_km(a, b):
    lat1, lng1 = map(math.radians, (a["lat"], a["lng"]))
    lat2, lng2 = map(math.radians, (b["lat"], b["lng"]))
    dlat, dlng = lat2 - lat1, lng2 - lng1
    return 12742.0 * math.asin(min(1.0, math.sqrt(
        math.sin(dlat / 2) ** 2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2)))


def nearby(entity, catalogs, max_each=3):
    pt = entity["geo"]["point"]
    for label, filename in catalogs:
        if not Path(filename).exists():
            continue
        catalog = json.loads(Path(filename).read_text(encoding="utf-8"))
        scored = []
        for other in catalog.get("entities", []):
            geo = other.get("geo") or {}
            op = geo.get("point")
            if not isinstance(op, dict) or not all(
                type(op.get(c)) in (float, int) for c in ("lat", "lng")
            ):
                continue
            if (other.get("quality") or {}).get("gate") not in ("G2", "G3"):
                continue
            km = distance_km(pt, op)
            if km <= 15.0:
                scored.append((km, other))
        for km, other in sorted(scored, key=lambda t: (t[0], t[1]["id"]))[:max_each]:
            entity["relations"].append({
                "type": "near",
                "target": {"id": other["id"], "kind": other["kind"],
                           "slug": other["slug"], "name": other["name"]},
                "straightLineKm": round(km, 2),
                "method": "haversine",
                "sourceUrl": entity["geo"]["sourceUrl"],
                "verified": False, "accessVerified": False,
                "notes": "Distanza in linea d'aria, NON percorso o accesso",
            })


def build(peak_dir, bbox, out, limit=250, country=None,
          crosswalk=None, photo_file=None, catalogs=(), min_count=1):
    checked_at = datetime.now(timezone.utc).isoformat()
    rows, sha, rejected, conflicts = load_candidates(Path(peak_dir), bbox, country)
    names = Counter(slugify(r[1]) for r in rows)
    all_count = len(rows)
    rows = rows[:limit] if limit else rows
    links = read_crosswalk(crosswalk)
    index = json.loads((Path(peak_dir) / "index.json").read_text())
    photos = json.loads(Path(photo_file).read_text()).get("photos", {}) if photo_file and Path(photo_file).exists() else {}
    entities = []
    for row in rows:
        slug = legacy_slug(row, index["tile"])
        entity = create_entity(row, checked_at=checked_at,
                               tile_size=index["tile"],
                               duplicate_name=names[slugify(row[1])] > 1,
                               qid=links.get(str(row[0])),
                               photo=photos.get(slug))
        nearby(entity, catalogs)
        entities.append(entity)
    if len(entities) < min_count:
        raise ValueError(f"Too few GeoNames entities: {len(entities)} < {min_count}")
    if len({e["id"] for e in entities}) != len(entities):
        raise ValueError("Entity ID collision")
    if len({e["slug"] for e in entities}) != len(entities):
        raise ValueError("Slug collision")
    out = Path(out)
    (out / "raw").mkdir(parents=True, exist_ok=True)
    def dump(path, doc):
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    dump(out / "raw/geonames-candidates.json",
         {"retrievedAt": checked_at, "sourceDataset": "committed GeoNames tiles",
          "sourceSnapshotsSha256": sha, "rows": rows})
    dump(out / "summits.json", {
        "releaseChannel": "GEONAMES_SUMMITS_STAGING_V1",
        "isPublished": False, "generatedAt": checked_at,
        "entities": entities,
    })
    review = [{"geonameid": row[0], "name": row[1],
               "reason": "ambiguous_name_slug"}
              for row in rows if names[slugify(row[1])] > 1]
    review.extend(conflicts)
    dump(out / "review.json", review)
    report = {"source": "GeoNames", "license": LICENSE,
              "sourceSnapshotsSha256": sha,
              "bbox": bbox, "eligible": all_count,
              "staged": len(entities), "crosswalkMatched": sum(
                  bool(e["sourceIds"].get("wikidata")) for e in entities),
              "summits": sum(e["kind"] == "summit" for e in entities),
              "groups": sum(e["kind"] == "mountain_group" for e in entities),
              "ambiguousSlugs": sum(e["quality"]["slugRequiresReview"] for e in entities),
              "mediaCandidatesUnverified": sum(bool(e.get("mediaCandidates")) for e in entities),
              "graphNearEdgesNotAccess": sum(len(e["relations"]) for e in entities),
              "published": 0, "indexable": 0, "rejected": dict(rejected)}
    dump(out / "report.json", report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--peak-dir", type=Path, default=PEAKS)
    parser.add_argument("--bbox", nargs=4, type=float, default=(46.1, 11.2, 47.1, 13.0))
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--max-entities", type=int, default=250)
    parser.add_argument("--min-entities", type=int, default=30)
    parser.add_argument("--country", default=None)
    parser.add_argument("--wikidata-map", type=Path)
    parser.add_argument("--photos", type=Path, default=PHOTO_FILE)
    parser.add_argument("--with-near", action="store_true")
    args = parser.parse_args()
    if args.max_entities < 0 or args.min_entities < 0:
        parser.error("Batch sizes must be nonnegative")
    catalogs = []
    if args.with_near:
        catalogs = [
            ("refuges", ROOT / "public/data/atlas/refuges-v1.json"),
            ("shelters", ROOT / "public/data/atlas/shelters-v1.json"),
            ("settlements", ROOT / "public/data/atlas/settlements-v1.json"),
        ]
    result = build(args.peak_dir, args.bbox, args.out, args.max_entities,
                   args.country, args.wikidata_map, args.photos, catalogs,
                   args.min_entities)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
