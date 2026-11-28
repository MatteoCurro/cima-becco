#!/usr/bin/env python3
"""Wikidata P1566 enrichment for the GeoNames summit pilot (staging only).

Wikidata claims are checked by exact GeoNames ID and coordinate compatibility.
This deliberately returns no crosswalk for ambiguous or coordinate-less items.
Nothing is written under public/; the report distinguishes missing from failed.
"""
from __future__ import annotations

import argparse
from collections import defaultdict, Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENDPOINT = "https://query.wikidata.org/sparql"
UA = "CimaBecco/1.0 (open-source alpine atlas; https://github.com/MatteoCurro/cima-becco)"
POINT = re.compile(r"^Point\((-?[0-9.]+) (-?[0-9.]+)\)$")
QID = re.compile(r"^https?://www\.wikidata\.org/entity/(Q[1-9][0-9]*)$")


def chunks(data, length):
    for offset in range(0, len(data), length):
        yield data[offset:offset + length]


def query_text(ids):
    if not ids or any(re.fullmatch(r"[1-9][0-9]*", str(x)) is None for x in ids):
        raise ValueError("Invalid GeoNames ID list")
    vals = " ".join(f'"{x}"' for x in ids)
    return ("SELECT ?item ?gid ?coordinates WHERE {\n"
            " VALUES ?gid { " + vals + " }\n"
            " ?item <http://www.wikidata.org/prop/direct/P1566> ?gid .\n"
            " OPTIONAL { ?item <http://www.wikidata.org/prop/direct/P625> ?coordinates . }\n"
            "}")


def fetch_links(ids):
    params = urlencode({"query": query_text(ids), "format": "json"})
    request = Request(ENDPOINT + "?" + params, headers={
        "Accept": "application/sparql-results+json", "User-Agent": UA})
    with urlopen(request, timeout=55) as response:
        return json.load(response)


def coords_of(value):
    match = POINT.fullmatch(str(value or ""))
    if not match:
        return None
    try:
        lng, lat = float(match.group(1)), float(match.group(2))
    except ValueError:
        return None
    if math.isfinite(lng) and math.isfinite(lat) and -180 <= lng <= 180 and -90 <= lat <= 90:
        return lat, lng
    return None


def distance_km(a, b):
    lat1, lng1 = map(math.radians, a)
    lat2, lng2 = map(math.radians, b)
    dl = lat2 - lat1
    dr = lng2 - lng1
    return 12742 * math.asin(min(1, math.sqrt(math.sin(dl / 2)**2 +
        math.cos(lat1) * math.cos(lat2) * math.sin(dr / 2)**2)))


def verify(rows, wanted, *, max_distance_km=2.0):
    """Return deterministic, one-to-one audited links plus held reasons."""
    by_id = {str(e["sourceIds"]["geonames"]):e for e in wanted}
    candidates = defaultdict(set)
    reasons = Counter()
    for row in rows:
        try:
            bindings = {k: v.get("value") for k,v in row.items()}
            gid = str(bindings.get("gid", ""))
            match = QID.fullmatch(str(bindings.get("item", "")))
            coord = coords_of(bindings.get("coordinates"))
            if gid not in by_id or match is None:
                reasons["unrecognized_id_or_qid"] += 1
                continue
            if coord is None:
                reasons["wd_coordinates_missing"] += 1
                continue
            ent = by_id[gid]
            pt = ent["geo"]["point"]
            km = distance_km(coord, (pt["lat"],pt["lng"]))
            if km > (8 if ent["kind"] == "mountain_group" else max_distance_km):
                reasons["coordinate_disagreement"] += 1
                continue
            candidates[gid].add(match.group(1))
        except (ValueError, TypeError, KeyError):
            reasons["malformed_wd_result"] += 1
    reversed_links = defaultdict(set)
    for gid, qids in candidates.items():
        for qid in qids:
            reversed_links[qid].add(gid)
    links = []
    for gid, qids in sorted(candidates.items(), key=lambda kv: int(kv[0])):
        if len(qids) != 1:
            reasons["ambiguous_qid_for_geonames"] += 1
            continue
        qid = next(iter(qids))
        if len(reversed_links[qid]) != 1:
            reasons["ambiguous_geonames_for_qid"] += 1
            continue
        links.append({
            "geonameid": int(gid), "qid": qid, "wdtP1566": gid,
            "sourceUrl": "https://www.wikidata.org/wiki/" + qid,
            "verified": True,
            "identityMethod": "exact_P1566_and_P625_coordinate",
            "coordinateGateKm": 8 if by_id[gid]["kind"] == "mountain_group" else max_distance_km
        })
    return links, reasons


def run(stage_file, out, *, max_items=80, batch_size=20, pause=1.2, getter=fetch_links):
    if not (1 <= batch_size <= 30 and 1 <= max_items <= 500):
        raise ValueError("Batch size or max items out of allowed bounds")
    stage=json.loads(Path(stage_file).read_text(encoding="utf-8"))
    if stage.get("isPublished") is not False or stage.get("releaseChannel") != "GEONAMES_SUMMITS_STAGING_V1":
        raise ValueError("Expected unmodified GeoNames staging input")
    entities=stage.get("entities", [])[:max_items]
    rows_all=[]
    group_ok_ids=set()
    reasons=Counter()
    failures=[]
    for i, group in enumerate(chunks(entities,batch_size)):
        ids=[e["sourceIds"]["geonames"] for e in group]
        try:
            response=getter(ids)
            rows=response.get("results",{}).get("bindings",[])
            if not isinstance(rows,list):
                raise ValueError("SPARQL bindings not a list")
            # Collect the raw bindings; do NOT resolve independently per batch.
            # Two different GeoNames IDs in different requests can reference
            # the same Wikidata QID. The one-to-one gate has global scope.
            rows_all.extend(rows)
            group_ok_ids.update(str(x) for x in ids)
        except Exception as error:
            failures.append({"batch":i,"count":len(group),"error":str(error)[:200]})
            reasons["source_unavailable"] += len(group)
        if pause and (i+1)*batch_size < len(entities):
            time.sleep(pause)
    verified_entities=[e for e in entities
                       if str(e["sourceIds"]["geonames"]) in group_ok_ids]
    links,held=verify(rows_all,verified_entities)
    reasons.update(held)
    at=datetime.now(timezone.utc).isoformat()
    out=Path(out)
    out.parent.mkdir(parents=True,exist_ok=True)
    result={"schemaVersion":"1.0","checkedAt":at,
            "source":"https://www.wikidata.org/wiki/Property:P1566",
            "license":"CC0","links":links}
    report={"attempted":len(entities),"matched":len(links),
            "unmatched":len(entities)-len(links),
            "heldReasons":dict(reasons),"networkFailures":failures[:12],
            "isPublished":False}
    out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    out.with_name("summit-wikidata-report.json").write_text(
        json.dumps(report,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",type=Path,default=ROOT/"build/import-summits-v1/summits.json")
    p.add_argument("--out",type=Path,default=ROOT/"build/import-summits-v1/wikidata-map.json")
    p.add_argument("--max-items",type=int,default=80)
    p.add_argument("--batch-size",type=int,default=20)
    p.add_argument("--pause",type=float,default=1.2)
    args=p.parse_args()
    print(json.dumps(run(args.stage,args.out,max_items=args.max_items,
        batch_size=args.batch_size,pause=args.pause),ensure_ascii=False))


if __name__=="__main__":
    main()
