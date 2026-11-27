#!/usr/bin/env python3
"""Cima Becco: pilot OSM climbing metadata-only (no GPX, no route geometry).

One bounded Overpass query per execution. Outputs in experiments/climbing-pilot/.
Stdlib only; no frontend, no production files modified.
"""
from __future__ import annotations
import argparse
import collections
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DEFAULT_BBOX = (45.87, 10.82, 45.99, 11.03)  # south,west,north,east: Arco/Sarca
OUT = Path(__file__).resolve().parents[1] / "experiments" / "climbing-pilot"
SERVERS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]
UA = "CimaBecco-Climbing-Research/0.1 (https://www.cimabecco.it; small-scale research only)"
TAGS = {
    "grade": "climbing:grade:french",
    "lengthM": "climbing:length",
    "pitchesCount": "climbing:pitches",
    "boltsCount": "climbing:bolts",
    "bolted": "climbing:bolted",
    "orientation": "climbing:orientation",
    "rock": "climbing:rock",
    "routeCountDeclared": "climbing:routes",
    "quality": "climbing:quality",
    "heightM": "height",
    "openingHours": "opening_hours",
    "website": "website",
    "phone": "phone",
}
# Some are useful raw OSM tags, but NOT interchangeable with quickdraw count.
SAFE_GRADE_PREFIX = "climbing:grade:"
MAX_TAG_LEN = 900


def number(value, *, integer=False, minimum=0, maximum=5000):
    if value is None:
        return None
    raw = str(value).strip()
    if not re.fullmatch(r"\d+" if integer else r"\d+(?:[.,]\d+)?", raw):
        return None
    val = float(raw.replace(",", "."))
    if not minimum <= val <= maximum:
        return None
    return int(val) if integer else val


def slug(text):
    value = unicodedata.normalize("NFKD", str(text or "").strip().lower())
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value or None


def text_or_none(x):
    if not isinstance(x, str) or not x.strip():
        return None
    return x.strip()[:MAX_TAG_LEN]


def category(tags):
    c = (tags.get("climbing") or "").lower()
    sport = (tags.get("sport") or "").lower()
    leisure = (tags.get("leisure") or "").lower()
    if sport == "climbing" and leisure in {"sports_centre", "sports_hall"}:
        return "climbing_gym"
    if c in {"route", "route_bottom"}:
        return "climbing_route"
    if c in {"boulder", "boulder_problem"}:
        return "boulder"
    if c in {"crag", "area"}:
        return "crag"
    if c == "sector":
        return "sector"
    if c in {"bolt", "route_top"}:
        return "technical_point"
    if c in {"via_ferrata", "ferrata"}:
        return "via_ferrata"
    if sport == "climbing":
        if tags.get("indoor") == "yes" or tags.get("building"):
            return "climbing_gym"
        return "climbing_site_unspecified"
    return "unclassified"


def normalize(osm):
    tags = osm.get("tags") or {}
    loc = osm if osm.get("type") == "node" else osm.get("center", {})
    lat, lon = loc.get("lat"), loc.get("lon")
    # Centers of polygons are only locator coordinates, not exact route starts.
    kind = category(tags)
    src_id = f"osm:{osm.get('type')}:{osm.get('id')}"
    source_url = f"https://www.openstreetmap.org/{osm.get('type')}/{osm.get('id')}"
    name = text_or_none(tags.get("name"))
    grades = {k[len(SAFE_GRADE_PREFIX):]: text_or_none(v)
              for k, v in tags.items() if k.startswith(SAFE_GRADE_PREFIX) and text_or_none(v)}
    bolts_raw = text_or_none(tags.get("climbing:bolts"))
    pitch_raw = text_or_none(tags.get("climbing:pitches"))
    fields = {key: text_or_none(tags.get(tag)) for key, tag in TAGS.items()}
    fields["boltsCount"] = number(bolts_raw, integer=True, maximum=500)
    fields["pitchesCount"] = number(pitch_raw, integer=True, minimum=1, maximum=150)
    fields["lengthM"] = number(fields["lengthM"], maximum=3000)
    fields["routeCountDeclared"] = number(fields["routeCountDeclared"], integer=True, maximum=100000)
    fields["heightM"] = number(fields["heightM"], maximum=8000)
    fields["grades"] = grades or None
    fields["fixedProtectionReported"] = bolts_raw if bolts_raw in ("yes", "no") else None
    # OSM 'climbing:bolted' is yes/no OR average bolt spacing, keep verbatim.
    fields["boltingSpacingOrYesNo"] = fields.pop("bolted")
    fields.pop("grade", None)
    fields["author"] = text_or_none(tags.get("author"))
    fields["description"] = text_or_none(tags.get("description"))
    fields["access"] = text_or_none(tags.get("access"))
    fields["indoor"] = text_or_none(tags.get("indoor"))
    fields["nameAlt"] = text_or_none(tags.get("alt_name"))
    fields["osmClimbingTags"] = {k: text_or_none(v) for k, v in tags.items()
                                   if k.startswith("climbing:") and k not in TAGS.values()}
    if not fields["osmClimbingTags"]:
        fields.pop("osmClimbingTags")
    # These are deliberately null: do not invent a number from bolt count or length!
    fields["quickdrawsRecommended"] = None
    fields["anchorType"] = None
    fields["ropeLengthRecommendedM"] = None
    fields["pitchDetails"] = []
    fields = {k: v for k, v in fields.items() if v is not None}
    technical = kind in ("climbing_route", "boulder", "via_ferrata")
    return {
        "id": src_id, "kind": kind, "name": name,
        "proposedSlug": slug(name) if name else None,
        "geo": {"lat": lat, "lon": lon} if isinstance(lat, (float, int)) and isinstance(lon, (float, int)) else None,
        "metadata": fields,
        "source": {"provider": "osm", "sourceId": src_id, "url": source_url,
                   "licence": "ODbL-1.0", "observedAt": osm.get("timestamp")},
        "quality": {"hasName": bool(name), "technicalRoute": technical,
                    "importStatus": "metadata_only_not_editorially_reviewed"},
    }


def query_for(bbox):
    south, west, north, east = bbox
    bb = ",".join(str(x) for x in (south, west, north, east))
    return (
        "[out:json][timeout:75];("
        f'nwr["sport"="climbing"]({bb});'
        f'nwr["climbing"]({bb});'
        ");out center meta;"
    )


def fetch(bbox):
    query = query_for(bbox)
    attempts = []
    for server in SERVERS:
        req = Request(server + "?" + urlencode({"data": query}),
                      headers={"User-Agent": UA, "Accept": "application/json"})
        try:
            with urlopen(req, timeout=110) as resp:
                payload = json.loads(resp.read(30_000_000).decode("utf-8"))
            if "elements" not in payload:
                raise RuntimeError("missing elements field")
            return payload, server, attempts
        except HTTPError as err:
            attempts.append({"server": server, "http": err.code, "error": str(err)[:250]})
            if err.code in (429, 406):
                # Do not keep hitting a throttled endpoint.
                continue
        except (URLError, TimeoutError, RuntimeError, ValueError, OSError) as err:
            attempts.append({"server": server, "error": str(err)[:250]})
    raise RuntimeError("No Overpass response: " + json.dumps(attempts))


def build(raw, bbox, provider):
    elements = raw.get("elements", [])
    records = [normalize(osm) for osm in elements if osm.get("type") in ("node", "way", "relation")]
    unique = list({r["id"]: r for r in records}.values())
    types = collections.Counter(r["kind"] for r in unique)
    fields = collections.Counter(k for r in unique for k, v in r["metadata"].items()
                                 if v is not None and v != [] and v != {})
    routes = [r for r in unique if r["kind"] == "climbing_route"]
    sample = sorted((r for r in unique if r["name"]), key=lambda r: (
        -(len(r["metadata"]) + (5 if r["kind"] == "climbing_route" else 0)), r["name"]))[:25]
    report = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "provider": provider, "bbox": list(bbox),
        "inputElements": len(elements), "distinctRecords": len(unique),
        "types": dict(sorted(types.items())),
        "fieldsPresent": dict(fields.most_common()),
        "namedCount": sum(bool(r["name"]) for r in unique),
        "routeCount": len(routes),
        "routeGradeAvailable": sum(bool(r["metadata"].get("grades")) for r in routes),
        "routeBoltsCountAvailable": sum("boltsCount" in r["metadata"] for r in routes),
        "routePitchesCountAvailable": sum("pitchesCount" in r["metadata"] for r in routes),
        "routeLengthAvailable": sum("lengthM" in r["metadata"] for r in routes),
        "routeQuickdrawsAvailable": 0,  # intentionally not inferred from bolts
        "note": "OSM pilot. Metadata-only, not field-verified. No safety claims.",
        "sample": [{
            "name": r["name"], "kind": r["kind"], "source": r["source"]["url"],
            "metadata": {k: v for k, v in r["metadata"].items() if k != "osmClimbingTags"}
        } for r in sample],
    }
    return unique, report


def run():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--bbox", default=",".join(str(x) for x in DEFAULT_BBOX))
    cli.add_argument("--fixture", type=Path, help="offline source response")
    cli.add_argument("--output", type=Path, default=OUT)
    args = cli.parse_args()
    try:
        bbox = tuple(float(x) for x in args.bbox.split(","))
        if len(bbox) != 4:
            raise ValueError()
        s, w, n, e = bbox
        if not (35 <= s < n <= 49 and 5 <= w < e <= 20 and (n - s) * (e - w) <= .15):
            raise ValueError()
    except ValueError:
        cli.error("bbox must be south,west,north,east (small Italian/Alpine bbox)")
    provider = "offline_fixture"
    if args.fixture:
        payload = json.loads(args.fixture.read_text(encoding="utf-8"))
    else:
        payload, provider, attempts = fetch(bbox)
    records, report = build(payload, bbox, provider)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / "metadata-records.json").write_text(
        json.dumps({"schemaVersion": 1, "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (args.output / "import-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "sample"}, indent=2, ensure_ascii=False))
    if not records:
        raise RuntimeError("no features: query or area probably requires review")


if __name__ == "__main__":
    run()
