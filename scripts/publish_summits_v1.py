#!/usr/bin/env python3
"""Publish only confirmed G2 summits, with semantic merge and safe batch history.

The GeoNames 5-degree tiles remain the canonical raw mapping catalog. This
release adds independently enriched dossiers without changing the legacy
gn<id>-<tile> identifiers used by existing UI, favorites and shared links.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import uuid

RELEASE="GEONAMES_SUMMITS_G2"
STAGING="GEONAMES_SUMMITS_G2_STAGING_V1"
QID=re.compile(r"Q[1-9][0-9]*$")
GN=re.compile(r"[1-9][0-9]*$")
LEGACY=re.compile(r"gn[1-9][0-9]*-m?[0-9]+xm?[0-9]+$")
SLUG=re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*$")
HISTORY="cime"


def verified_photos(entity):
    for media in entity.get("media", []):
        if (media.get("kind")=="photo"
            and media.get("subjectVerified") is True
            and media.get("reuseAllowed") is True
            and media.get("author") and media.get("licence")
            and str(media.get("url") or "").startswith("https://")
            and str(media.get("sourceUrl") or "").startswith("https://commons.wikimedia.org/")
            and media.get("subjectMethod") == "verified_P1566_P625_QID_P18"
            and str(media.get("sourceId") or "").startswith("wikidata:")):
            yield media


def validate_entity(entity, *, staging):
    ids=entity.get("sourceIds") or {}
    quality=entity.get("quality") or {}
    gn, qid=ids.get("geonames"), ids.get("wikidata")
    if (entity.get("kind")!="summit" or quality.get("gate")!="G2"
        or quality.get("slugRequiresReview") or quality.get("reviewRequired")
        or quality.get("elevationConflictReview")
        or ids.get("wikidataVerifiedBy")!="P1566+P625"
        or not GN.fullmatch(str(gn or "")) or not QID.fullmatch(str(qid or ""))
        or not entity.get("id") or not isinstance(entity.get("id"),str)
        or not SLUG.fullmatch(str(entity.get("slug") or ""))
        or not entity.get("geo",{}).get("point")
        or not any(LEGACY.fullmatch(str(s)) for s in entity.get("slugAliases",[]))
        or not entity.get("description") or len(entity["description"])<120
        or not any(verified_photos(entity))
        or not any(s.get("text") and len(s["text"])>=120
                   and str(s.get("sourceId") or "").startswith("wikipedia:it:")
                   and str(s.get("sourceUrl") or "").startswith("https://it.wikipedia.org/")
                   and s.get("licence")=="CC BY-SA 4.0"
                   for s in entity.get("textSources",[]))):
        raise ValueError("Summit below G2 publication gate: "+str(entity.get("slug")))
    try:
        uuid.UUID(entity["id"])
    except (ValueError, TypeError, AttributeError):
        raise ValueError("Summit has invalid canonical UUID: "+str(gn))
    for k in ("lat","lng"):
        coord=entity["geo"]["point"].get(k)
        if type(coord) not in (int,float):
            raise ValueError("Invalid summit coordinate: "+str(gn))
        if not (-90<=coord<=90 if k=="lat" else -180<=coord<=180):
            raise ValueError("Out-of-range summit coordinate: "+str(gn))
    alt=entity.get("facts") or {}
    if not any(isinstance(alt.get(k,{}).get("value"),(int,float))
               for k in ("elevationM","wikidataElevationReportedM")):
        raise ValueError("G2 summit with no documented elevation")
    for relation in entity.get("relations",[]):
        if relation.get("type")=="near" and (relation.get("verified") or relation.get("accessVerified")):
            raise ValueError("Near relationship cannot certify access")
    if staging and (quality.get("seoIndexable") is not False
                    or quality.get("candidateIndexable") is not True):
        raise ValueError("Input must be independently gated staging G2")
    if not staging and quality.get("seoIndexable") is not True:
        raise ValueError("Published summit must be SEO validated")


def validate_doc(document, *, staging):
    expect=STAGING if staging else RELEASE
    if not isinstance(document,dict) or document.get("releaseChannel")!=expect:
        raise ValueError("Summit releaseChannel mismatch")
    if document.get("isPublished") is (not staging):
        pass
    else:
        raise ValueError("Summit publication state mismatch")
    rows=document.get("entities")
    if not isinstance(rows,list):
        raise ValueError("Missing summit entity collection")
    identities=[]
    for row in rows:
        validate_entity(row,staging=staging)
        ids=row["sourceIds"]
        identities.append((row["id"],row["slug"],ids["geonames"],ids["wikidata"]))
    for i in range(4):
        values=[x[i] for x in identities]
        if len(values)!=len(set(values)):
            raise ValueError("Summit duplicate canonical ID / slug / GeoNames / QID")
    return rows


def empty_release():
    return {"schemaVersion":"1.0","releaseChannel":RELEASE,
            "isPublished":True,"entities":[]}


def merge(current, incoming):
    prior=validate_doc(current,staging=False)
    candidate=validate_doc(incoming,staging=True)
    by_gn={e["sourceIds"]["geonames"]:deepcopy(e) for e in prior}
    source_time=str(incoming.get("generatedAt") or "")
    previous_time=str(current.get("generatedAt") or "")
    added=updated=0
    for item in candidate:
        gn=item["sourceIds"]["geonames"]
        last=by_gn.get(gn)
        new=deepcopy(item)
        new["quality"].update({"seoIndexable":True,"needsReleaseGate":False})
        if last:
            keys=["id","slug","kind"]
            if (any(last[k]!=new[k] for k in keys)
                or last["sourceIds"]["wikidata"]!=new["sourceIds"]["wikidata"]):
                raise ValueError("Summit identity or canonical slug conflict: "+gn)
            if source_time>=previous_time:
                chosen,older=new,last
            else:
                chosen,older=deepcopy(last),new
            # Both variants were released only after media identity validation.
            gathered={}
            for media in [*verified_photos(older),*verified_photos(chosen)]:
                gathered[media["sourceUrl"]]=media
            chosen["media"]=list(gathered.values())
            chosen["slugAliases"]=list(dict.fromkeys(
                [*older.get("slugAliases",[]),*chosen.get("slugAliases",[])]))
            by_gn[gn]=chosen
            updated+=1
        else:
            by_gn[gn]=new
            added+=1
    result={"schemaVersion":"1.0","releaseChannel":RELEASE,
            "isPublished":True,"generatedAt":max(source_time,previous_time),
            "entities":sorted(by_gn.values(),key=lambda e:e["id"])}
    validate_doc(result,staging=False)
    return result, {"added":added,"refreshed":updated,
                    "total":len(result["entities"])}


def append_history(current, report, run_id, *, at=None):
    result=deepcopy(current or {"schemaVersion":"1.0","events":[]})
    if not isinstance(result.get("events"),list):
        raise ValueError("Invalid import history")
    if not report or not all(type(report.get(k)) is int for k in
                             ("offset","selectedCandidates","eligible")):
        raise ValueError("Missing successful source batch report")
    if report["selectedCandidates"]<=0:
        raise ValueError("Empty source batch never advances cursor")
    if not run_id or not str(run_id).strip():
        raise ValueError("Missing release run ID")
    if any(e.get("pipeline")==HISTORY and str(e.get("runId"))==str(run_id)
           for e in result["events"] if isinstance(e,dict)):
        return result
    result["events"].append({
        "pipeline":HISTORY,"status":"success","runId":str(run_id),
        "recordedAt":at or datetime.now(timezone.utc).isoformat(),
        "report":{"offset":report["offset"],
                  "selectedCandidates":report["selectedCandidates"],
                  "eligible":report["eligible"]}
    })
    result["events"]=result["events"][-500:]
    return result


def read(path,default=None):
    return json.loads(Path(path).read_text(encoding="utf-8")) if Path(path).exists() else default


def write(path, doc):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,
                              separators=(",",":"))+"\n",encoding="utf-8")
    tmp.replace(path)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--current",type=Path,required=True)
    p.add_argument("--incoming",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--history",type=Path,required=True)
    p.add_argument("--source-report",type=Path,required=True)
    p.add_argument("--run-id",required=True)
    args=p.parse_args()
    merged,stats=merge(read(args.current,empty_release()),read(args.incoming))
    history=append_history(read(args.history),read(args.source_report),args.run_id)
    write(args.out,merged)
    write(args.history,history)
    print(json.dumps(stats,ensure_ascii=False))


if __name__=="__main__":
    main()
