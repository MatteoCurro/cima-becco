#!/usr/bin/env python3
"""Wikimedia enrichment for GeoNames natural features (source-backed only).

Single canonical GeoNames entity with an optional explicitly verified OSM ID;
no coordinate/name-only merge and no synthetic access or lake shoreline.
A G2 dossier needs exact P1566/P625, P18 Commons photo author+license,
matching itwiki pageprops QID and a substantial sourced narrative.
Lakes/reservoirs/valleys stay G1 pending polygon or external boundary review.
All output is staging and explicitly noindex.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path
import re

from enrich_municipalities_v1 import (
    WIKIDATA_API, request_json, commons_files, wikipedia_intro,
    claim_coord, claim_string, claim_quantity, NON_PHOTO, PHOTO_EXT
)
from resolve_summit_wikidata_v1 import distance_km

GN_STAGE="GEONAMES_NATURAL_FEATURES_STAGING_V1"
CROSSWALK_STAGE="NATURAL_FEATURES_IDENTITY_STAGING_V1"
OUT_STAGE="NATURAL_FEATURES_G2_CANDIDATES_STAGING_V1"
WIKIDATA="https://www.wikidata.org/wiki/"
G2_ALLOWED={"mountain_pass","saddle","waterfall","viewpoint"}

def batches(rows,size=20):
    for start in range(0,len(rows),size):
        yield rows[start:start+size]


def wd_entities_multilingual(ids, *, getter=None):
    if not ids:return {}
    data=request_json(WIKIDATA_API,{
        "action":"wbgetentities","format":"json","ids":"|".join(ids),
        "props":"claims|labels|sitelinks",
        "languages":"it|de|lld|en|fr|rm",
        "sitefilter":"itwiki",
    },getter=getter)
    return data.get("entities") or {}


def exact_identity(base,item,link):
    gid=base["sourceIds"]["geonames"]
    if claim_string(item,"P1566")!=gid:
        return "wikidata_P1566_mismatch"
    loc=claim_coord(item)
    if not loc:
        return "wikidata_P625_absent"
    pt=base["geo"]["point"]
    dist=distance_km((loc["lat"],loc["lng"]),(pt["lat"],pt["lng"]))
    if dist>link["coordinateGateKm"] or abs(dist-link["coordinateDistanceKm"])>0.15:
        return "wikidata_coordinates_conflict"
    return None


def from_multilingual_labels(entity,item,qid):
    local=[]
    seen={entity["name"].casefold()}
    for language,entry in sorted((item.get("labels") or {}).items()):
        value=(entry or {}).get("value","").strip()
        if not value or len(value)>110 or value.casefold() in seen:
            continue
        seen.add(value.casefold())
        local.append({"value":value,"language":language,
                      "sourceUrl":WIKIDATA+qid})
    existing=entity.get("aliases") or []
    entity["localNames"]=local[:12]
    entity["aliases"]=existing


def wd_fact(value,qid,prop,at,unit=None):
    return {
        "value":value,"unit":unit,"sourceId":"wikidata:"+qid+":"+prop,
        "sourceUrl":WIKIDATA+qid,"licence":"CC0","retrievedAt":at,
        "sourceUpdatedAt":None,"validFrom":None,"validUntil":None,
        "method":"reported","confidence":0.9,
    }


def enrich(geonames, crosswalk, *, limit=240,
           wd_getter=None,commons_getter=None,wiki_getter=None,at=None):
    if geonames.get("releaseChannel")!=GN_STAGE or geonames.get("isPublished") is not False:
        raise ValueError("Expected natural GeoNames G1 staging catalog")
    if crosswalk.get("releaseChannel")!=CROSSWALK_STAGE or crosswalk.get("isPublished") is not False:
        raise ValueError("Expected verified natural identity crosswalk")
    links={}
    qids={}
    for link in crosswalk.get("links") or []:
        gid=str(link.get("geonameid") or "")
        qid=link.get("qid")
        if (link.get("wikidataIdentityVerified") is not True
            or link.get("identityMethod")!="exact_P1566_P625_one_to_one"
            or not re.fullmatch(r"[1-9][0-9]*",gid)
            or not re.fullmatch(r"Q[1-9][0-9]*",str(qid or ""))
            or type(link.get("coordinateDistanceKm")) not in (float,int)
            or type(link.get("coordinateGateKm")) not in (float,int)
            or link["coordinateDistanceKm"]>link["coordinateGateKm"]
            or link.get("wikidataUrl")!=WIKIDATA+qid):
            raise ValueError("Invalid or unchecked natural QID association")
        if gid in links or qid in qids:
            raise ValueError("Ambiguous crosswalk identity for natural features")
        links[gid]=link
        qids[qid]=gid
    at=at or datetime.now(timezone.utc).isoformat()
    records=[e for e in geonames.get("entities",[]) if
             e.get("kind")=="natural_feature" and
             e.get("quality",{}).get("gate")=="G1" and
             not e["quality"].get("slugRequiresReview") and
             e["sourceIds"].get("geonames") in links][:limit]
    held=Counter()
    output=[]
    examples=[]
    for batch in batches(records):
        ids=[links[e["sourceIds"]["geonames"]]["qid"] for e in batch]
        try:
            items=wd_entities_multilingual(ids,getter=wd_getter)
        except Exception as ex:
            held["wikidata_api_unavailable"]+=len(batch)
            examples.append({"step":"wikidata","error":str(ex)[:120]})
            continue
        candidates={}
        filenames=[]
        for e in batch:
            qid=links[e["sourceIds"]["geonames"]]["qid"]
            item=items.get(qid) or {}
            filename=claim_string(item,"P18")
            if filename and PHOTO_EXT.search(filename) and not NON_PHOTO.search(filename):
                filenames.append(filename)
                candidates[qid]=filename
        try:
            licensed=commons_files(filenames,getter=commons_getter)
        except Exception as ex:
            licensed={}
            examples.append({"step":"commons","error":str(ex)[:120]})
            held["commons_api_unavailable"]+=len(filenames)
        for e in batch:
            gn=e["sourceIds"]["geonames"]
            link=links[gn]
            qid=link["qid"]
            item=items.get(qid) or {}
            reason=exact_identity(e,item,link)
            if reason:
                held[reason]+=1
                continue
            doc=deepcopy(e)
            doc["sourceIds"]["wikidata"]=qid
            doc["sourceIds"]["wikidataVerifiedBy"]="P1566+P625"
            if link.get("osmVerified"):
                doc["sourceIds"]["osm"]=link["osmVerified"]
                doc["sourceIds"]["osmVerifiedBy"]="OSM_QID_tag+GeoNames_P1566+WD_P625"
            doc["facts"]["wikidataIdentityVerified"]=wd_fact(True,qid,"P1566+P625",at)
            doc["geo"]["wikidataPointVerifiedAt"]=at
            from_multilingual_labels(doc,item,qid)
            reported=claim_quantity(item,"P2044","Q11573",0,5000)
            if reported is not None:
                doc["facts"]["wikidataElevationReportedM"]=wd_fact(
                    round(reported,2),qid,"P2044",at,"m")
                main=doc["facts"].get("elevationM",{})
                if main.get("value") is not None and abs(main["value"]-reported)>100:
                    doc["quality"]["elevationConflictReview"]=True
                    held["elevation_difference_over_100m"]+=1
            filename=candidates.get(qid)
            photo=licensed.get(filename.replace(" ","_")) if filename else None
            if photo and all((photo.get("subjectVerified"),photo.get("reuseAllowed"),
                              photo.get("author"),photo.get("licence"),
                              photo.get("sourceUrl"),photo.get("url"))):
                media={**photo,"id":"wikimedia:"+qid+":P18:"+sha1(filename.encode()).hexdigest()[:12],
                       "kind":"photo","sourceId":"wikidata:"+qid+":P18",
                       "subjectMethod":"verified_GeoNames_P1566_Wikidata_P625_P18",
                       "caption":"Fotografia documentata di "+doc["name"],
                       "retrievedAt":at}
                doc["media"]=[media]
            else:
                held["no_verified_P18_commons_photo"]+=1
            title=((item.get("sitelinks") or {}).get("itwiki") or {}).get("title")
            article=None
            if title:
                try:
                    article=wikipedia_intro(title,qid,getter=wiki_getter)
                except Exception as ex:
                    examples.append({"step":"itwiki","qid":qid,"error":str(ex)[:120]})
            if article and article.get("text") and len(article["text"])>=120:
                source={k:v for k,v in article.items() if k!="linkedImages"}
                source["retrievedAt"]=at
                doc["textSources"]=[source]
                doc["description"]=article["text"]
                doc["shortSummary"]=article["text"][:190]
            else:
                held["no_verified_itwiki_narrative"]+=1
            # The coordinate of a water polygon/valley is not its physical
            # extent; an informative text alone does not certify the geometry.
            geo_review=doc["subtype"] in ("lake","reservoir","valley") and not doc["geo"].get("area")
            if geo_review:
                doc["quality"]["needsAreaGeometryReview"]=True
                held["lake_valley_polygon_not_verified"]+=1
            eligible=(bool(doc.get("media")) and bool(doc.get("textSources"))
                      and not doc["quality"].get("elevationConflictReview")
                      and not geo_review and doc["subtype"] in G2_ALLOWED
                      and bool(doc.get("facts"))
                      and not doc["quality"].get("slugRequiresReview"))
            doc["quality"].update({
                "gate":"G2" if eligible else "G1",
                "candidateIndexable":eligible,
                "seoIndexable":False,
                "needsReleaseGate":True,
                "photoSourceVerified":bool(doc.get("media")),
                "textLicenseVerified":bool(doc.get("textSources")),
                "identityMethod":"GeoNames_P1566_P625_checked",
                "reviewRequired":bool(doc["quality"].get("elevationConflictReview") or geo_review),
            })
            doc["editorialStatus"]="enriched" if doc.get("textSources") else "linked"
            output.append(doc)
    result={
        "schemaVersion":"1.0","releaseChannel":OUT_STAGE,
        "isPublished":False,"generatedAt":at,
        "entities":sorted(output,key=lambda d:d["id"]),
    }
    summary={
        "selected":len(records),"identityVerified":len(output),
        "candidateG2":sum(x["quality"]["gate"]=="G2" for x in output),
        "heldG1":sum(x["quality"]["gate"]=="G1" for x in output),
        "withPhoto":sum(bool(x.get("media")) for x in output),
        "withText":sum(bool(x.get("textSources")) for x in output),
        "verifiedOSM":sum(bool(x["sourceIds"].get("osm")) for x in output),
        "heldReasons":dict(sorted(held.items())),
        "reviewExamples":examples[:12],
        "isPublished":False,"seoIndexable":0,
    }
    return result,summary


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--geonames-stage",type=Path,required=True)
    p.add_argument("--crosswalk",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--max-items",type=int,default=240)
    args=p.parse_args()
    doc,report=enrich(
        json.loads(args.geonames_stage.read_text(encoding="utf-8")),
        json.loads(args.crosswalk.read_text(encoding="utf-8")),
        limit=args.max_items,
    )
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    args.report.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
