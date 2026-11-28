#!/usr/bin/env python3
"""Resolve Alpine natural features via exact GeoNames P1566 + Wikidata P625.

The GeoNames/OSM adapters produce *separate* G0/G1 records. Only an exact
P1566+P625 QID may bridge them, and an OSM wikidata tag is a *candidate*
until that same QID + subtype + coordinate are independently checked.
Nearest-neighbor and same-name matching are diagnostic, NEVER identity.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from resolve_summit_wikidata_v1 import chunks, fetch_links, verify, distance_km

GN_STAGE="GEONAMES_NATURAL_FEATURES_STAGING_V1"
OSM_STAGE="OSM_NATURAL_FEATURES_STAGING_V1"
OUT_STAGE="NATURAL_FEATURES_IDENTITY_STAGING_V1"
# Gate for point-to-point place identity; a lake centroid can be offset and
# must not be silently accepted as an exact location in that case.
MAX_COORD_KM={"mountain_pass":1.5,"saddle":1.0,"waterfall":0.6,
              "lake":1.5,"reservoir":1.5,"valley":2.0}


def doc_check(doc, channel):
    if not isinstance(doc,dict) or doc.get("releaseChannel")!=channel or doc.get("isPublished") is not False:
        raise ValueError("Unexpected or published source instead of raw staging: "+channel)
    records=doc.get("entities")
    if not isinstance(records,list):
        raise ValueError("Natural stage missing entities")
    keys=set()
    for e in records:
        if e.get("kind")!="natural_feature":
            raise ValueError("Source mixes natural features and unrelated entities")
        ids=e.get("sourceIds") or {}
        if channel==GN_STAGE and (not ids.get("geonames") or ids.get("osm")):
            raise ValueError("GeoNames source must have only its own provider identity")
        if channel==OSM_STAGE and (not ids.get("osm") or ids.get("geonames")):
            raise ValueError("OSM source must have only its own provider identity")
        key=e.get("id")
        if not key or key in keys:
            raise ValueError("Duplicate source entity ID")
        keys.add(key)
    return records


def reconcile(geonames, wdrows, osm=None):
    gn=doc_check(geonames, GN_STAGE)
    osm_rows=doc_check(osm,OSM_STAGE) if osm is not None else []
    # The same source's G0 homonym is allowed to appear in the input and is
    # audited, but must not be promoted under a guessed public identity.
    active=[e for e in gn if e.get("quality",{}).get("gate")=="G1"
            and not e.get("quality",{}).get("slugRequiresReview")]
    verified, held=verify(wdrows,active,max_distance_km=2.0)
    reasons=Counter(held)
    by_gid={e["sourceIds"]["geonames"]:e for e in active}
    links=[]
    by_qid=defaultdict(list)
    for e in osm_rows:
        q=e.get("sourceIds",{}).get("wikidataCandidate")
        if q and e.get("quality",{}).get("gate")=="G1":
            by_qid[q].append(e)
    for row in verified:
        gid=str(row["geonameid"])
        e=by_gid[gid]
        qid=row["qid"]
        # Recheck the subtype-specific max, not only generic 2 km.
        # verify() already established the exact QID↔GeoNames one-to-one.
        # Wikidata coordinates are retained in the verified entry below.
        best=[x for x in wdrows
              if x.get("gid",{}).get("value")==gid
              and str(x.get("item",{}).get("value","")).endswith("/"+qid)]
        if len(best)!=1:
            reasons["multiple_wikidata_coordinate_statements"]+=1
            continue
        from resolve_summit_wikidata_v1 import coords_of
        coords=coords_of(best[0].get("coordinates",{}).get("value"))
        if not coords:
            reasons["wikidata_coordinates_missing"]+=1
            continue
        pt=e["geo"]["point"]
        dist=distance_km(coords,(pt["lat"],pt["lng"]))
        maximum=MAX_COORD_KM[e["subtype"]]
        if dist>maximum:
            reasons["subtype_coordinate_conflict"]+=1
            continue
        verified_osm=None
        matches=by_qid.get(qid,[])
        if matches:
            compatible=[
                x for x in matches
                if x["subtype"]==e["subtype"]
                and x["geo"]["point"] and distance_km(
                    (coords[0],coords[1]),
                    (x["geo"]["point"]["lat"],x["geo"]["point"]["lng"]))<=maximum
            ]
            if len(matches)!=1 or len(compatible)!=1:
                reasons["osm_wikidata_candidate_ambiguous_or_incompatible"]+=1
            else:
                verified_osm=compatible[0]["sourceIds"]["osm"]
        links.append({
            "geonameid":int(gid),"qid":qid,
            "wikidataUrl":"https://www.wikidata.org/wiki/"+qid,
            "wikidataIdentityVerified":True,
            "identityMethod":"exact_P1566_P625_one_to_one",
            "coordinateDistanceKm":round(dist,3),
            "coordinateGateKm":maximum,
            "subtype":e["subtype"],
            "osmVerified":verified_osm, # only explicit WD tag + subtype + P625
            "osmMergeMethod":"exact_OSM_QID_tag_plus_P1566_P625" if verified_osm else None,
        })
    return sorted(links,key=lambda x:x["geonameid"]),dict(sorted(reasons.items()))


def run(gn_stage, out, *, osm_stage=None, max_items=220,
        batch_size=20, pause=1.5, getter=fetch_links):
    import time
    if not (1<=max_items<=1000 and 1<=batch_size<=30 and 0<=pause<=15):
        raise ValueError("Bounded source settings required")
    geonames=json.loads(Path(gn_stage).read_text(encoding="utf-8"))
    all_entities=doc_check(geonames, GN_STAGE)
    group=[e for e in all_entities if
           e.get("quality",{}).get("gate")=="G1" and
           not e.get("quality",{}).get("slugRequiresReview")][:max_items]
    osm=None
    if osm_stage:
        osm=json.loads(Path(osm_stage).read_text(encoding="utf-8"))
        doc_check(osm,OSM_STAGE)
    wdrows=[]
    failures=[]
    for n, batch in enumerate(chunks(group,batch_size)):
        try:
            response=getter([e["sourceIds"]["geonames"] for e in batch])
            bindings=response.get("results",{}).get("bindings")
            if not isinstance(bindings,list):
                raise ValueError("Malformed SPARQL result")
            wdrows.extend(bindings)
        except Exception as error:
            failures.append({"batch":n,"count":len(batch),"error":str(error)[:180]})
        if pause and (n+1)*batch_size<len(group):
            time.sleep(pause)
    if failures:
        # Fail closed: partial Wikidata coverage does not advance a cursor or
        # get reported as verified no-match.
        raise RuntimeError("Wikidata batch failures: "+json.dumps(failures))
    links,reasons=reconcile({**geonames,"entities":group},wdrows,osm)
    checked_at=datetime.now(timezone.utc).isoformat()
    result={"schemaVersion":"1.0","releaseChannel":OUT_STAGE,"isPublished":False,
            "checkedAt":checked_at,"source":"https://www.wikidata.org/wiki/Property:P1566",
            "licence":"CC0","links":links}
    report={"attempted":len(group),"matched":len(links),
            "unmatched":len(group)-len(links),
            "confirmedOsmBridges":sum(bool(x["osmVerified"]) for x in links),
            "reasons":reasons,"networkFailures":failures,
            "indexable":0,"published":0}
    path=Path(out);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    path.with_name("natural-identity-report.json").write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--geonames-stage",type=Path,required=True)
    p.add_argument("--osm-stage",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--max-items",type=int,default=220)
    p.add_argument("--batch-size",type=int,default=20)
    p.add_argument("--pause",type=float,default=1.5)
    args=p.parse_args()
    print(json.dumps(run(args.geonames_stage,args.out,osm_stage=args.osm_stage,
        max_items=args.max_items,batch_size=args.batch_size,pause=args.pause),ensure_ascii=False))


if __name__=="__main__":
    main()
