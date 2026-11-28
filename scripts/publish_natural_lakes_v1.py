#!/usr/bin/env python3
"""Safe G2 lake publisher; no G1 body, fake shore access or duplicate QIDs.

Source of truth: full GN P1566/P625 + exact OSM ring with island handling,
Wikimedia P18 Commons author/license and itwiki QID content. G1 source
snapshots remain private to the build/CI, not indexed.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
import json
import math
from pathlib import Path
import re
import uuid

from enrich_natural_water_geometry_v1 import (
    valid_ring,ring_area_km2,point_inside_polygon,
)

STAGE="NATURAL_WATER_G2_CANDIDATES_STAGING_V1"
RELEASE="NATURAL_FEATURES_LAKES_G2"
ALLOWED=("lake","reservoir")
GN_RE=re.compile(r"^[1-9][0-9]*$")
QID_RE=re.compile(r"^Q[1-9][0-9]*$")
OSM_RE=re.compile(r"^(way|relation)/[1-9][0-9]*$")
SLUG_RE=re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_geometry(e):
    geo=e.get("geo") or {}
    poly=geo.get("area") or {}
    pos=geo.get("point") or {}
    if poly.get("type")!="MultiPolygon" or not isinstance(poly.get("coordinates"),list):
        raise ValueError("No verified lake multipolygon")
    if type(pos.get("lat")) not in (int,float) or type(pos.get("lng")) not in (int,float):
        raise ValueError("No source lake representative point")
    if not 35<=pos["lat"]<=48 or not 6<=pos["lng"]<=20:
        raise ValueError("Water point outside bounded alpine source")
    area=0
    for group in poly["coordinates"]:
        if not isinstance(group,list) or not group:
            raise ValueError("Empty lake polygon group")
        outer=valid_ring(group[0])
        local=ring_area_km2(outer)
        for hole in group[1:]:
            valid_ring(hole)
            local-=ring_area_km2(hole)
        if local<=0:
            raise ValueError("Lake islands exceed exterior polygon area")
        area+=local
    if not area>0 or not point_inside_polygon([pos["lng"],pos["lat"]],poly):
        raise ValueError("Lake source point lies outside its polygon / in an island")
    return area


def validate(e,staging=False):
    quality=e.get("quality") or {}
    ids=e.get("sourceIds") or {}
    if (e.get("kind")!="natural_feature" or e.get("subtype") not in ALLOWED
        or quality.get("gate")!="G2" or quality.get("reviewRequired")
        or quality.get("slugRequiresReview")
        or quality.get("areaNotVerified")
        or quality.get("elevationConflictReview")
        or quality.get("wikiAltitudeDisagreementReview")
        or quality.get("needsTextAndMediaG2")
        or quality.get("geometryTopologyVerified") is not True
        or ids.get("wikidataVerifiedBy")!="P1566+P625"
        or ids.get("osmVerifiedBy")!="P1566_P625_and_exact_OSM_QID_or_GeoNames_ID"
        or not GN_RE.fullmatch(str(ids.get("geonames") or ""))
        or not QID_RE.fullmatch(str(ids.get("wikidata") or ""))
        or not OSM_RE.fullmatch(str(ids.get("osm") or ""))
        or not SLUG_RE.fullmatch(str(e.get("slug") or ""))
        or not isinstance(e.get("name"),str) or len(e["name"])<3
        or not isinstance(e.get("description"),str) or len(e["description"])<120):
        raise ValueError("Lake lacks G2 identity, editorial data or geometry proof: "+str(e.get("slug")))
    try:uuid.UUID(e.get("id") or "")
    except (ValueError,TypeError,AttributeError) as err:
        raise ValueError("Lake UUID unavailable") from err
    osm="https://www.openstreetmap.org/"+ids["osm"]
    if e["geo"].get("areaSourceUrl")!=osm or e["geo"].get("areaMethod")!="osm_out_geom_multipolygon":
        raise ValueError("Lake polygon source does not match its exact OSM ID")
    area=validate_geometry(e)
    fact=e.get("facts",{}).get("osmMappedWaterSurfaceKm2") or {}
    if (fact.get("sourceId")!="osm:"+ids["osm"]+":geometry" or
        fact.get("sourceUrl")!=osm or fact.get("licence")!="ODbL 1.0" or
        fact.get("method")!="derived" or fact.get("unit")!="km2" or
        type(fact.get("value")) not in (int,float) or
        not math.isfinite(fact["value"]) or
        abs(fact["value"]-area)>max(0.0001,area*0.025)):
        raise ValueError("Lake measured surface does not match actual OSM polygon")
    quota=e["facts"].get("elevationM",{})
    if (quota.get("sourceId")!="geonames:"+ids["geonames"]
        or quota.get("licence")!="CC BY 4.0"
        or quota.get("unit")!="m"
        or quota.get("method") not in ("reported","estimated")
        or type(quota.get("value")) not in (int,float)
        or not math.isfinite(quota["value"])
        or not 0<=quota["value"]<=5000):
        raise ValueError("Lake elevation must retain GeoNames source and method")
    identity=e["facts"].get("wikidataIdentityVerified",{})
    if (identity.get("value") is not True or identity.get("sourceId")!=
        "wikidata:"+ids["wikidata"]+":P1566+P625"):
        raise ValueError("Lake identity not independently rechecked against Wikidata")
    photos=e.get("media") or []
    if not any(
        m.get("kind")=="photo" and m.get("subjectVerified") is True
        and m.get("reuseAllowed") is True
        and m.get("sourceId")=="wikidata:"+ids["wikidata"]+":P18"
        and m.get("subjectMethod")=="verified_GeoNames_P1566_Wikidata_P625_P18"
        and m.get("author") and m.get("licence")
        and str(m.get("sourceUrl") or "").startswith("https://commons.wikimedia.org/")
        and str(m.get("url") or "").startswith("https://")
        for m in photos):
        raise ValueError("Lake has no licensed P18 photograph of exact QID")
    if not any(t.get("text") and len(t["text"])>=120 and
        t.get("sourceId","").startswith("wikipedia:it:") and
        t.get("licence")=="CC BY-SA 4.0" and
        str(t.get("sourceUrl") or "").startswith("https://it.wikipedia.org/")
        for t in e.get("textSources") or []):
        raise ValueError("Lake has no QID-checked licensed Italian narrative")
    for rel in e.get("relations") or []:
        if rel.get("type")!="near" or rel.get("verified") is not False or rel.get("accessVerified") is not False:
            raise ValueError("Lake includes an unverified water access relation")
    if e.get("facts",{}).get("potable") or e.get("facts",{}).get("bathingAllowed"):
        raise ValueError("Source water body cannot inherit arbitrary drinking/bathing claims")
    if staging:
        if (quality.get("candidateIndexable") is not True or
            quality.get("seoIndexable") is not False or
            quality.get("needsReleaseGate") is not True):
            raise ValueError("Natural lake input is not canonical reviewed G2 staging")
    else:
        if quality.get("seoIndexable") is not True or quality.get("needsReleaseGate") is True:
            raise ValueError("Published natural lake did not pass final release check")


def empty():
    return {"schemaVersion":"1.0","releaseChannel":RELEASE,
            "isPublished":True,"generatedAt":"","entities":[]}


def check(doc,*,stage=False):
    if not isinstance(doc,dict) or doc.get("releaseChannel")!=(STAGE if stage else RELEASE):
        raise ValueError("Wrong natural lake release channel")
    if doc.get("isPublished") is not (False if stage else True) or not isinstance(doc.get("entities"),list):
        raise ValueError("Natural lake document does not have expected source state")
    entities=doc["entities"]
    ids=[]
    for e in entities:
        if stage and e.get("quality",{}).get("gate")!="G2":
            continue
        validate(e,staging=stage)
        ids.append((e["id"],e["slug"],e["sourceIds"]["geonames"],
                    e["sourceIds"]["wikidata"],e["sourceIds"]["osm"]))
    for index in range(5):
        col=[x[index] for x in ids]
        if len(set(col))!=len(col):
            raise ValueError("Duplicate natural water source ID, QID or slug")
    return entities


def merge(current,incoming):
    before=check(current)
    proposed=check(incoming,stage=True)
    by_gn={e["sourceIds"]["geonames"]:deepcopy(e) for e in before}
    count={"added":0,"refreshed":0,"heldG1":0}
    prior_date=current.get("generatedAt") or ""
    new_date=incoming.get("generatedAt") or ""
    for e in proposed:
        if e.get("quality",{}).get("gate")!="G2":
            count["heldG1"]+=1
            continue
        candidate=deepcopy(e)
        candidate["quality"]["seoIndexable"]=True
        candidate["quality"]["needsReleaseGate"]=False
        old=by_gn.get(candidate["sourceIds"]["geonames"])
        if old:
            for key in ("id","slug","kind","subtype"):
                if old[key]!=candidate[key]:
                    raise ValueError("Published water identity changed: "+key)
            if (old["sourceIds"]["wikidata"]!=candidate["sourceIds"]["wikidata"]
                or old["sourceIds"]["osm"]!=candidate["sourceIds"]["osm"]):
                raise ValueError("Water source identity reassigned without explicit migration")
            if new_date>=prior_date:
                candidate["slugAliases"]=list(dict.fromkeys(
                    [*old.get("slugAliases",[]),*candidate.get("slugAliases",[])]))
                by_gn[candidate["sourceIds"]["geonames"]]=candidate
            count["refreshed"]+=1
        else:
            by_gn[candidate["sourceIds"]["geonames"]]=candidate
            count["added"]+=1
    after={"schemaVersion":"1.0","releaseChannel":RELEASE,
           "isPublished":True,"generatedAt":max(prior_date,new_date),
           "entities":sorted(by_gn.values(),key=lambda e:e["id"])}
    check(after)
    count["total"]=len(after["entities"])
    return after,count


def read(path,default=None):
    p=Path(path)
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else default


def write(path,data):
    p=Path(path);p.parent.mkdir(parents=True,exist_ok=True)
    tmp=p.with_suffix(p.suffix+".tmp")
    tmp.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,separators=(",",":"))+"\n",encoding="utf-8")
    tmp.replace(p)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current",type=Path,required=True)
    p.add_argument("--incoming",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    result,stats=merge(read(args.current,empty()),read(args.incoming))
    write(args.out,result)
    print(json.dumps(stats,ensure_ascii=False))


if __name__=="__main__":
    main()
