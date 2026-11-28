#!/usr/bin/env python3
"""Conservative publisher for source-verified Cima Becco mountain passes.

Only enrich_natural_wikimedia_v1 G2 with audited identity, media and source
narrative can be merged. Incomplete natural features never become SEO pages.
The already-published catalog is preserved when the provider is unavailable
or no candidate survives. No overwrite on identity/QID/slug conflicts.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import uuid

STAGING="NATURAL_FEATURES_G2_CANDIDATES_STAGING_V1"
RELEASE="NATURAL_FEATURES_PASSES_G2"
GN=re.compile(r"^[1-9]\d*$")
QID=re.compile(r"^Q[1-9]\d*$")
SLUG=re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
ALLOWED={"mountain_pass","saddle"}

def validate_item(e,staging=False):
    ids=e.get("sourceIds") or {}
    quality=e.get("quality") or {}
    gn=ids.get("geonames")
    qid=ids.get("wikidata")
    if (e.get("kind")!="natural_feature" or e.get("subtype") not in ALLOWED
        or quality.get("gate")!="G2" or quality.get("reviewRequired")
        or quality.get("slugRequiresReview")
        or quality.get("wikiAltitudeDisagreementReview")
        or quality.get("elevationConflictReview")
        or quality.get("needsAreaGeometryReview")
        or ids.get("wikidataVerifiedBy")!="P1566+P625"
        or not GN.fullmatch(str(gn or ""))
        or not QID.fullmatch(str(qid or ""))
        or not SLUG.fullmatch(str(e.get("slug") or ""))
        or not isinstance(e.get("name"),str) or len(e["name"])<3
        or not e.get("geo",{}).get("point")):
        raise ValueError("Natural pass fails identity or quality gate: "+str(e.get("slug")))
    try:
        uuid.UUID(e.get("id") or "")
    except (AttributeError,TypeError,ValueError) as ex:
        raise ValueError("Natural pass missing canonical UUID") from ex
    pos=e["geo"]["point"]
    if any(type(pos.get(k)) not in (int,float) or not math.isfinite(pos[k])
           for k in ("lat","lng")) or not (35<=pos["lat"]<=48 and 6<=pos["lng"]<=20):
        raise ValueError("Pass has invalid coordinates: "+str(gn))
    alt=e.get("facts",{}).get("elevationM",{})
    if (not isinstance(alt,dict) or type(alt.get("value")) not in (int,float)
        or not 100<=alt["value"]<=5000 or alt.get("unit")!="m"
        or alt.get("sourceId")!="geonames:"+gn
        or alt.get("licence")!="CC BY 4.0"):
        raise ValueError("Pass requires a typed source-backed altitude")
    checked=e.get("facts",{}).get("wikidataIdentityVerified",{})
    if (not checked or checked.get("value") is not True
        or checked.get("sourceId")!="wikidata:"+qid+":P1566+P625"):
        raise ValueError("Pass requires second-pass Wikidata proof")
    media=e.get("media") or []
    if not any(m.get("kind")=="photo"
               and m.get("subjectVerified") is True
               and m.get("reuseAllowed") is True
               and m.get("subjectMethod")=="verified_GeoNames_P1566_Wikidata_P625_P18"
               and m.get("sourceId")=="wikidata:"+qid+":P18"
               and str(m.get("sourceUrl") or "").startswith("https://commons.wikimedia.org/")
               and str(m.get("url") or "").startswith("https://")
               and m.get("author") and m.get("licence")
               for m in media):
        raise ValueError("Pass has no exact-entity licensed photograph")
    narrative=e.get("textSources") or []
    if not any(isinstance(t.get("text"),str) and len(t["text"])>=120
               and t.get("sourceId","").startswith("wikipedia:it:")
               and t.get("licence")=="CC BY-SA 4.0"
               and str(t.get("sourceUrl") or "").startswith("https://it.wikipedia.org/")
               for t in narrative):
        raise ValueError("Pass has no verified QID-matched Italian narrative")
    for rel in e.get("relations",[]):
        if rel.get("type")!="near" or rel.get("verified") is not False or rel.get("accessVerified") is not False:
            raise ValueError("Pass carries an unverified access or unsafe relation")
    if ids.get("osm") and ids.get("osmVerifiedBy")!="OSM_QID_tag+GeoNames_P1566+WD_P625":
        raise ValueError("Pass OSM ID has no verified crosswalk provenance")
    if staging:
        if (quality.get("candidateIndexable") is not True or
            quality.get("seoIndexable") is not False or
            quality.get("needsReleaseGate") is not True):
            raise ValueError("Input pass is not independently gated G2 staging")
    elif quality.get("seoIndexable") is not True:
        raise ValueError("Published pass needs final SEO gate")

def empty():
    return {"schemaVersion":"1.0","releaseChannel":RELEASE,"isPublished":True,
            "generatedAt":"","entities":[]}

def check_doc(data,*,staging=False):
    if not isinstance(data,dict):
        raise ValueError("Invalid natural release")
    if data.get("releaseChannel")!=(STAGING if staging else RELEASE):
        raise ValueError("Incorrect natural release channel")
    if data.get("isPublished") is not (False if staging else True):
        raise ValueError("Incorrect natural publication state")
    if not isinstance(data.get("entities"),list):
        raise ValueError("Missing natural entity list")
    entities=data["entities"]
    if not staging:
        for e in entities:
            validate_item(e)
    keys=lambda e:(e["id"],e["slug"],e["sourceIds"]["geonames"],e["sourceIds"]["wikidata"])
    active=[keys(e) for e in entities if (not staging or
       e.get("kind")=="natural_feature" and e.get("subtype") in ALLOWED and
       e.get("quality",{}).get("gate")=="G2")]
    for i in range(4):
        values=[x[i] for x in active]
        if len(values)!=len(set(values)):
            raise ValueError("Duplicate pass ID/slug/GeoNames/QID")
    return entities

def merge(current, incoming):
    prior=check_doc(current)
    rows=check_doc(incoming,staging=True)
    by_gn={e["sourceIds"]["geonames"]:deepcopy(e) for e in prior}
    added=updated=held=0
    new_time=str(incoming.get("generatedAt") or "")
    old_time=str(current.get("generatedAt") or "")
    for item in rows:
        if not (item.get("kind")=="natural_feature" and
                item.get("subtype") in ALLOWED and
                item.get("quality",{}).get("gate")=="G2"):
            held+=1
            continue
        validate_item(item,staging=True)
        ident=item["sourceIds"]["geonames"]
        doc=deepcopy(item)
        doc["quality"]["seoIndexable"]=True
        doc["quality"]["needsReleaseGate"]=False
        old=by_gn.get(ident)
        if old:
            if (any(old[k]!=doc[k] for k in ("id","slug","kind","subtype"))
                or old["sourceIds"]["wikidata"]!=doc["sourceIds"]["wikidata"]):
                raise ValueError("Existing pass source ID changed meaning: "+ident)
            # Refresh a pass from an older source must not delete attributes
            # verified and published by the previous run.
            if new_time and new_time>=old_time:
                if not doc["sourceIds"].get("osm") and old["sourceIds"].get("osm"):
                    doc["sourceIds"]["osm"]=old["sourceIds"]["osm"]
                    doc["sourceIds"]["osmVerifiedBy"]=old["sourceIds"]["osmVerifiedBy"]
                doc["slugAliases"]=list(dict.fromkeys(
                    [*old.get("slugAliases",[]),*doc.get("slugAliases",[])]))
                by_gn[ident]=doc
            updated+=1
        else:
            by_gn[ident]=doc
            added+=1
    result={"schemaVersion":"1.0","releaseChannel":RELEASE,"isPublished":True,
            "generatedAt":max(old_time,new_time),
            "entities":sorted(by_gn.values(),key=lambda e:e["id"])}
    check_doc(result)
    return result,{"added":added,"refreshed":updated,
                    "heldG0G1OrNonPass":held,"total":len(result["entities"])}

def read(path,default=None):
    path=Path(path)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default

def write(path,data):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(data,sort_keys=True,ensure_ascii=False,
                              separators=(",",":"))+"\n",encoding="utf-8")
    tmp.replace(path)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current",type=Path,required=True)
    p.add_argument("--incoming",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    args=p.parse_args()
    merged,report=merge(read(args.current,empty()),read(args.incoming))
    write(args.out,merged)
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
