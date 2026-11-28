#!/usr/bin/env python3
"""G2 editorial probe for source-exact lake polygons, not a second importer.

Consumes the SAME natural feature OSM → GN QID bridge and revalidates
Wikidata P1566/P625, Commons P18/licence and Italian Wikipedia pageprops.
G1 water bodies stay noindex. No lake is published by this stage.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from enrich_natural_water_geometry_v1 import (
    CHANNEL as GEOMETRY_CHANNEL,point_inside_polygon,
)
from enrich_natural_wikimedia_v1 import (
    enrich,GN_STAGE,CROSSWALK_STAGE,
)

OUT="NATURAL_WATER_G2_CANDIDATES_STAGING_V1"
WATER=("lake","reservoir")
SHA=re.compile(r"^[a-f0-9]{64}$")


def lake_candidates(geometry,crosswalk):
    if (geometry.get("releaseChannel")!=GEOMETRY_CHANNEL or
        geometry.get("isPublished") is not False or
        not SHA.fullmatch(str(geometry.get("sourceSha256","")))):
        raise ValueError("Water G2 requires immutable source-audited OSM geometry staging")
    if crosswalk.get("releaseChannel")!=CROSSWALK_STAGE or crosswalk.get("isPublished") is not False:
        raise ValueError("Water G2 requires audited WD source crosswalk")
    links={str(x.get("geonameid")):x for x in crosswalk.get("links") or []}
    if len(links)!=len(crosswalk.get("links") or []):
        raise ValueError("Duplicate crosswalk GeoNames IDs")
    seen=set();qids=set();slugs=set()
    selected=[]
    for entity in geometry.get("geonamesLinkedEntities") or []:
        ids=entity.get("sourceIds") or {}
        gn=ids.get("geonames")
        qid=ids.get("wikidata")
        osm=ids.get("osm")
        quality=entity.get("quality") or {}
        geo=entity.get("geo") or {}
        area=geo.get("area")
        source="https://www.openstreetmap.org/"+str(osm or "")
        size=entity.get("facts",{}).get("osmMappedWaterSurfaceKm2",{})
        link=links.get(gn)
        if (entity.get("kind")!="natural_feature" or entity.get("subtype") not in WATER
            or quality.get("gate")!="G1" or quality.get("reviewRequired")
            or quality.get("slugRequiresReview")
            or quality.get("geometryTopologyVerified") is not True
            or ids.get("wikidataVerifiedBy")!="P1566+P625"
            or ids.get("osmVerifiedBy")!="P1566_P625_and_exact_OSM_QID_or_GeoNames_ID"
            or not re.fullmatch(r"(?:way|relation)/[1-9][0-9]*",str(osm))
            or not re.fullmatch(r"Q[1-9][0-9]*",str(qid))
            or not area or area.get("type")!="MultiPolygon"
            or geo.get("areaSourceUrl")!=source
            or size.get("sourceId")!="osm:"+osm+":geometry"
            or size.get("licence")!="ODbL 1.0" or size.get("method")!="derived"
            or type(size.get("value")) not in (float,int) or not 0<size["value"]<350
            or not link or link.get("qid")!=qid
            or link.get("subtype")!=entity["subtype"]
            or link.get("wikidataIdentityVerified") is not True
            or link.get("identityMethod")!="exact_P1566_P625_one_to_one"
            or not geo.get("point")
            or not point_inside_polygon(
                [geo["point"].get("lng"),geo["point"].get("lat")],area)):
            raise ValueError("Water geometry lacks independently checked exact QID, subtype or polygon")
        if gn in seen or qid in qids or entity.get("slug") in slugs:
            raise ValueError("Duplicate water source identity or canonical URL")
        seen.add(gn);qids.add(qid);slugs.add(entity["slug"])
        selected.append(deepcopy(entity))
    return {"schemaVersion":"1.0","releaseChannel":GN_STAGE,
            "isPublished":False,"generatedAt":geometry.get("generatedAt"),
            "entities":selected}


def run(geometry,crosswalk,*,wd_getter=None,commons_getter=None,wiki_getter=None,at=None):
    stage=lake_candidates(geometry,crosswalk)
    new_date=at or datetime.now(timezone.utc).isoformat()
    enriched,report=enrich(stage,crosswalk,limit=100,at=new_date,
        wd_getter=wd_getter,commons_getter=commons_getter,wiki_getter=wiki_getter)
    for item in enriched["entities"]:
        if item["subtype"] not in WATER:
            raise ValueError("Water enrichment admitted a non-lake entity")
        if item["quality"]["gate"]=="G2":
            assert item["geo"]["area"]["type"]=="MultiPolygon"
            assert item["quality"]["geometryTopologyVerified"] is True
            assert item["quality"]["seoIndexable"] is False
            assert item["facts"]["osmMappedWaterSurfaceKm2"]["licence"]=="ODbL 1.0"
    enriched["releaseChannel"]=OUT
    enriched["sourceGeometrySha256"]=geometry["sourceSha256"]
    report["sourceGeometrySha256"]=geometry["sourceSha256"]
    report["geometryVerified"]=len(stage["entities"])
    report["waterSubtypes"]=dict(sorted(Counter(x["subtype"] for x in enriched["entities"]).items()))
    report["published"]=0
    return enriched,report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--geometry",type=Path,required=True)
    p.add_argument("--crosswalk",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    geo=json.loads(args.geometry.read_text(encoding="utf-8"))
    cross=json.loads(args.crosswalk.read_text(encoding="utf-8"))
    result,report=run(geo,cross)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    args.report.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
