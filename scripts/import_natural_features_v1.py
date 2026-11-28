#!/usr/bin/env python3
"""Cima Becco natural-feature importer: single small Overpass cell, raw -> G0/G1.

Following metadata bible §5 and the same staging rules as earlier importers.
- Excludes springs/fountains, already in alpine-water.json.
- Does not infer lake outlines, waterfall access, potable water or pass opening.
- Separates point-of-interest centroids from documented geometry and height.
- Source-linked facts and spatial *near* edges only; no automated G2/SEO.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import uuid
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from import_alpine_places import ENDPOINTS, alpine_cells
from import_summits_v1 import nearby, slugify

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"build/import-natural-features-v1"
RELEASE="OSM_NATURAL_FEATURES_STAGING_V1"
ODBL="ODbL 1.0"
SOURCE="https://www.openstreetmap.org"
QID=re.compile(r"Q[1-9][0-9]*$")
OSM_TYPES=("node","way","relation")
FEATURES={
    "mountain_pass": "pass",
    "saddle": "saddle",
    "lake": "lake",
    "reservoir": "reservoir",
    "valley": "valley",
    "waterfall": "waterfall",
    "viewpoint": "viewpoint",
}

def query_for_bbox(bbox):
    south,west,north,east=bbox
    if not (35<=south<north<=48 and 6<=west<east<=20):
        raise ValueError("Pilot cells must lie inside the bounded Italian alpine region")
    rect=f"({south},{west},{north},{east})"
    # Query per tag; larger arbitrary natural=water and all springs are excluded.
    selectors=[
        f'nwr["mountain_pass"="yes"]{rect};',
        f'nwr["natural"="saddle"]{rect};',
        f'nwr["natural"="valley"]{rect};',
        f'nwr["natural"="water"]["water"~"^(lake|reservoir)$"]{rect};',
        f'nwr["waterway"="waterfall"]{rect};',
        f'nwr["tourism"="viewpoint"]["name"]{rect};',
    ]
    return "[out:json][timeout:65];("+''.join(selectors)+");out center tags;"

def fetch_osm(bbox, endpoints=ENDPOINTS, timeout=82):
    query=query_for_bbox(bbox)
    last=None
    for endpoint in endpoints:
        try:
            req=Request(endpoint,data=urlencode({"data":query}).encode(),headers={
                "User-Agent":"CimaBecco/1.0 (https://github.com/MatteoCurro/cima-becco)",
                "Content-Type":"application/x-www-form-urlencoded",
            })
            with urlopen(req,timeout=timeout) as response:
                doc=json.load(response)
            if not isinstance(doc.get("elements"),list):
                raise ValueError("Overpass response has no elements list")
            return doc
        except Exception as error:
            last=error
            print(f"Overpass natural features unavailable from {endpoint}: {error}")
    raise RuntimeError("All bounded Overpass providers failed: "+str(last))

def classify(tags):
    if tags.get("waterway")=="waterfall":
        return "waterfall"
    if tags.get("mountain_pass")=="yes":
        return "mountain_pass"
    if tags.get("natural")=="saddle":
        return "saddle"
    if tags.get("natural")=="valley":
        return "valley"
    if tags.get("natural")=="water" and tags.get("water") in ("lake","reservoir"):
        return tags["water"]
    if tags.get("tourism")=="viewpoint":
        return "viewpoint"
    return None

def osm_fact(value, unit, source_id, url, at):
    return {"value":value,"unit":unit,"sourceId":source_id,
            "sourceUrl":url,"licence":ODBL,"retrievedAt":at,
            "sourceUpdatedAt":None,"validFrom":None,"validUntil":None,
            "method":"reported","confidence":0.85}

def numeric_meters(value, *, maximum):
    if value is None or isinstance(value,bool):
        return None
    cleaned=str(value).strip()
    # Unitless OpenStreetMap ele is interpreted in metres; reject mixed
    # ranges/feet/approximation rather than silently mis-converting.
    matched=re.fullmatch(r"([0-9]{1,5}(?:[.,][0-9]{1,2})?)\s*(?:m|metri|meters)?",cleaned,re.I)
    if not matched:
        return None
    number=float(matched.group(1).replace(",","."))
    return round(number,2) if math.isfinite(number) and 0<=number<=maximum else None

def parse_osm(row, at):
    typ,ident=row.get("type"),row.get("id")
    if typ not in OSM_TYPES or type(ident) is not int or ident<=0:
        return None
    tags=row.get("tags") or {}
    if not isinstance(tags,dict):
        return None
    subtype=classify(tags)
    if not subtype:return None
    name=str(tags.get("name:it") or tags.get("name") or "").strip()
    if not (2<=len(name)<=140 and slugify(name)):
        return None
    pt=row.get("center") if isinstance(row.get("center"),dict) else row
    lat,lng=pt.get("lat"),pt.get("lon")
    if (type(lat) not in (int,float) or type(lng) not in (int,float)
        or not math.isfinite(lat) or not math.isfinite(lng)
        or not (35<=lat<=48 and 6<=lng<=20)):
        return None
    osm_id=f"{typ}/{ident}"
    source_url=f"{SOURCE}/{osm_id}"
    stable_id=str(uuid.uuid5(uuid.NAMESPACE_URL,source_url))
    facts={
        "osmFeatureTag":osm_fact(subtype,None,"osm:"+osm_id,source_url,at)
    }
    elev=numeric_meters(tags.get("ele"),maximum=5000)
    if elev is not None:
        facts["elevationM"]=osm_fact(elev,"m","osm:"+osm_id+":ele",source_url,at)
    if subtype=="waterfall":
        fall=numeric_meters(tags.get("height"),maximum=1000)
        if fall is not None:
            facts["waterfallDropM"]=osm_fact(fall,"m","osm:"+osm_id+":height",source_url,at)
    aliases=[]
    for lang in ("de","it","lld","en"):
        local=tags.get("name:"+lang)
        if isinstance(local,str) and local.strip() and local.strip()!=name:
            aliases.append({"value":local.strip()[:140],"language":lang,"sourceUrl":source_url})
    wd=tags.get("wikidata")
    ids={"osm":osm_id}
    if isinstance(wd,str) and QID.fullmatch(wd):
        ids["wikidataCandidate"]=wd  # candidate; never verified identity
    is_center=typ!="node"
    quality_gate="G1"
    return {
        "id":stable_id,"kind":"natural_feature","subtype":subtype,
        "name":name,"displayName":name,"slug":slugify(name),
        "slugAliases":[f"osm-{typ[0]}-{ident}"],
        "aliases":aliases,"localNames":aliases,
        "sourceIds":ids,"geo":{"point":{"lat":round(lat,6),"lng":round(lng,6)},
            "area":None,"method":"osm_element_center" if is_center else "osm_node_point",
            "sourceUrl":source_url,"precision":"area_not_retrieved" if is_center else "osm_reported_point"},
        "facts":facts,"factsAlternatives":[],
        "administrativeHierarchy":{"country":"IT"},
        "media":[],"textSources":[],"relations":[],
        "history":None,"shortSummary":None,"description":None,
        "restrictions":[],"alerts":[],
        "quality":{"gate":quality_gate,"seoIndexable":False,"reviewRequired":False,
            "wikidataIdentityVerified":False,"perimeterNotVerified":is_center},
        "editorialStatus":"linked","checkedAt":at,"updatedAt":at,
    }

def reconcile_slugs(entities):
    by_name=defaultdict(list)
    for e in entities:
        by_name[e["slug"]].append(e)
    reserved={k for k,group in by_name.items() if len(group)==1}
    collisions=0
    for slug,group in sorted(by_name.items()):
        if len(group)<2:continue
        collisions+=1
        for e in sorted(group,key=lambda e:e["id"]):
            candidate=slug+"-"+e["id"].replace("-","")[:10]
            if candidate in reserved:
                raise ValueError("Natural feature slug collision cannot be resolved")
            e["slug"]=candidate
            e["quality"].update({"gate":"G0","seoIndexable":False,
                                 "slugRequiresReview":True,"reviewRequired":True})
            reserved.add(candidate)
    if len(entities)!=len({e["slug"] for e in entities}):
        raise ValueError("Duplicate natural feature slugs")
    return collisions

def run(rows, *, cell, out, max_records=250, catalogs=()):
    if not isinstance(rows,list):
        raise ValueError("Malformed Overpass raw elements")
    at=datetime.now(timezone.utc).isoformat()
    fingerprint=sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False,
                       separators=(",",":")).encode()).hexdigest()
    found={}
    rejected=Counter()
    for row in rows:
        entity=parse_osm(row,at) if isinstance(row,dict) else None
        if not entity:
            rejected["invalid_or_unnamed_or_unsupported"]+=1
            continue
        old=found.get(entity["sourceIds"]["osm"])
        if old and old!=entity:
            # Duplicate provider identity with inconsistent fields: fail
            # closed instead of selecting one arbitrary variant.
            raise ValueError("Conflicting repeated OSM identity: "+entity["sourceIds"]["osm"])
        found[entity["sourceIds"]["osm"]]=entity
    entities=sorted(found.values(),key=lambda e:(e["subtype"],e["name"],e["id"]))
    collision_groups=reconcile_slugs(entities)  # inspect entire pilot before slicing
    all_count=len(entities)
    entities=entities[:max_records] if max_records else entities
    for e in entities:
        nearby(e,catalogs,max_each=2)
    out=Path(out);(out/"raw").mkdir(parents=True,exist_ok=True)
    def save(name,doc):
        target=out/name
        target.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n",
                          encoding="utf-8")
    save("raw/osm-features.json",{
        "capturedAt":at,"source":"OpenStreetMap / Overpass",
        "license":ODBL,"cell":cell,"sha256":fingerprint,
        "raw":rows
    })
    save("features.json",{
        "schemaVersion":"1.0","releaseChannel":RELEASE,"isPublished":False,
        "generatedAt":at,"entities":entities
    })
    save("report.json",{
        "cell":cell,"rawCount":len(rows),"eligible":all_count,
        "staged":len(entities),"bySubtype":dict(Counter(e["subtype"] for e in entities)),
        "slugCollisionGroups":collision_groups,
        "reviewRequired":sum(bool(e["quality"]["reviewRequired"]) for e in entities),
        "nearNotAccess":sum(len(e["relations"]) for e in entities),
        "rejected":dict(rejected),"published":0,"seoIndexable":0,
        "overpassSha256":fingerprint,
        "reusedWaterCatalog":True,
        "waterNotice":"Natural springs and drinking-water taps stay in existing alpine-water.json",
    })
    return len(entities)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--cell-index",type=int,default=2)
    p.add_argument("--raw-file",type=Path)
    p.add_argument("--max-records",type=int,default=250)
    p.add_argument("--min-records",type=int,default=20)
    p.add_argument("--out",type=Path,default=STAGE)
    p.add_argument("--with-near",action="store_true")
    args=p.parse_args()
    cells=alpine_cells()
    if not (0<=args.cell_index<len(cells)):
        p.error("Invalid import-alpine-places pilot cell index")
    if args.max_records<0 or args.min_records<0:
        p.error("Counts must not be negative")
    raw=json.loads(args.raw_file.read_text(encoding="utf-8")) if args.raw_file else fetch_osm(cells[args.cell_index])
    rows=raw["elements"] if isinstance(raw,dict) else raw
    catalogs=[]
    if args.with_near:
        catalogs=[
            ("refuges",ROOT/"public/data/atlas/refuges-v1.json"),
            ("shelters",ROOT/"public/data/atlas/shelters-v1.json"),
            ("settlements",ROOT/"public/data/atlas/settlements-v1.json"),
            ("summits",ROOT/"public/data/atlas/summits-v1.json"),
        ]
    num=run(rows,cell=args.cell_index,out=args.out,max_records=args.max_records,catalogs=catalogs)
    if num<args.min_records:
        raise RuntimeError(f"Overpass natural feature pilot coverage too small: {num} < {args.min_records}")
    print((args.out/"report.json").read_text(encoding="utf-8"))

if __name__=="__main__":
    main()
