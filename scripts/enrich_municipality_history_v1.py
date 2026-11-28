#!/usr/bin/env python3
"""Cima Becco: conservative Commons historical-photo enrichment for municipalities.

Publication requires three independent verifications:
  * municipality identity linked directly by Wikidata P635 => municipality QID;
  * Commons MediaInfo explicitly depicts (P180) that exact QID;
  * acquisition/capture or image inception date supplied in metadata < 1975,
    not guessed from filename, upload timestamp or appearance.
Every image additionally passes Commons' file-level author/license gate.
Unverified search hits are audited, never published as facts.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import json
import re
from pathlib import Path
from urllib.parse import unquote
from enrich_municipalities_v1 import (
    COMMONS_API,PHOTO_EXT,QID,commons_files,request_json,text_only,meta_value)
from import_municipalities_v1 import load,save,require

HISTORY_CUTOFF=1975

def sdc_claims(item,prop):
    return [c for c in (item.get("claims") or {}).get(prop,[])
            if c.get("rank")!="deprecated"]

def sdc_depicts_exact(item,qid):
    for c in sdc_claims(item,"P180"):
        value=((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(value,dict) and value.get("entity-type")=="item" and value.get("id")==qid:
            return True
    return False

def parse_history_date(value):
    """Reject vague words/ranges and EXIF upload dates. Return precision kept."""
    if isinstance(value,dict):value=value.get("time","")
    if not isinstance(value,str):return None
    raw=text_only(value).strip()
    match=re.match(r"^\+?(\d{4})(?:-(\d\d)(?:-(\d\d))?)?(?:T.*)?$",raw)
    if not match:return None
    y,month,day=match.groups()
    year=int(y)
    if not 1800<=year<HISTORY_CUTOFF:return None
    if month and month not in ("00",) and not 1<=int(month)<=12:return None
    if day and day not in ("00",) and not 1<=int(day)<=31:return None
    if month=="00":return y
    if day=="00":return y+"-"+month
    return "-".join([y,month,day]) if day and month else y+(("-"+month) if month else "")

def recorded_history_date(item,extmetadata):
    for c in sdc_claims(item,"P571"): # inception/creation of the work, not upload timestamp
        val=((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        date=parse_history_date(val)
        if date:return date,"commons-sdc:P571"
    # DateTimeOriginal is the original capture field when provided by Commons,
    # not the date the image was uploaded to the Wikimedia servers.
    original=text_only(meta_value(extmetadata,"DateTimeOriginal"))
    date=parse_history_date(original)
    if date:return date,"commons-imageinfo:DateTimeOriginal"
    return None,None

def search_depicts(qid,*,getter=None,limit=35):
    require(QID.fullmatch(qid),"Comune QID invalido")
    doc=request_json(COMMONS_API,{
       "action":"query","format":"json","list":"search",
       "srsearch":"haswbstatement:P180="+qid,
       "srnamespace":"6","srlimit":str(limit),"srprop":""},getter=getter)
    rows=(doc.get("query") or {}).get("search") or []
    pages=[]
    for r in rows:
        name=r.get("title","")
        pid=r.get("pageid")
        if isinstance(pid,int) and name.startswith("File:") and PHOTO_EXT.search(name):
            pages.append({"pageid":pid,"filename":name.removeprefix("File:")})
    return pages

def fetch_sdc(pages,*,getter=None):
    if not pages:return {}
    result={}
    for i in range(0,len(pages),25):
        batch=pages[i:i+25]
        d=request_json(COMMONS_API,{
           "action":"wbgetentities","format":"json",
           "ids":"|".join("M"+str(p["pageid"]) for p in batch),
           "props":"claims"},getter=getter)
        result.update(d.get("entities") or {})
    return result

def fetch_file_dates(pages,*,getter=None):
    if not pages:return {}
    result={}
    for i in range(0,len(pages),25):
        part=pages[i:i+25]
        d=request_json(COMMONS_API,{
          "action":"query","format":"json","titles":"|".join("File:"+p["filename"] for p in part),
          "prop":"imageinfo","iiprop":"extmetadata"},getter=getter)
        for p in ((d.get("query") or {}).get("pages") or {}).values():
            key=p.get("title","").removeprefix("File:").replace(" ","_")
            result[key]=((p.get("imageinfo") or [{}])[0].get("extmetadata") or {})
    return result

def enrich_historical(release,*,getter=None,max_municipalities=20,
                      max_photos_per_municipality=3,checked_at=None):
    require(release.get("releaseChannel")=="ISTAT_DAIT_MUNICIPALITIES",
            "Archivio pubblico Comuni richiesto")
    require(release.get("isPublished") is True,"Archivio comuni non pubblicato")
    checked_at=checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    all_m=release.get("entities") or []
    # prioritize communes not already covered; retain previous archive on
    # live-query failures. Batch is bounded to protect Commons and CI budgets.
    eligible=[e for e in all_m if e.get("sourceIds",{}).get("wikidataVerifiedBy")=="P635"
              and QID.fullmatch(e.get("sourceIds",{}).get("wikidata",""))]
    eligible.sort(key=lambda e:(sum(m.get("kind")=="historical_photo"
                       for m in e.get("media",[])),e["sourceIds"]["istat"]))
    selected=eligible[:max_municipalities]
    report={"municipalitiesEligible":len(eligible),"municipalitiesChecked":len(selected),
            "imagesConsidered":0,"imagesSaved":0,
            "historicalMunicipalities":0,"errors":[]}
    for commune in selected:
        qid=commune["sourceIds"]["wikidata"]
        try:
            pages=search_depicts(qid,getter=getter)
            if not pages:continue
            sdc=fetch_sdc(pages,getter=getter)
            dates=fetch_file_dates(pages,getter=getter)
            report["imagesConsidered"]+=len(pages)
            qualified=[]
            for p in pages:
                filename=p["filename"]
                item=sdc.get("M"+str(p["pageid"])) or {}
                if not sdc_depicts_exact(item,qid):continue
                date,origin=recorded_history_date(item,dates.get(filename.replace(" ","_"),{}))
                if not date:continue
                qualified.append((filename,date,origin))
            qualified=qualified[:max_photos_per_municipality]
            if qualified:
                images=commons_files([x[0] for x in qualified],getter=getter)
                prior={(m.get("sourceUrl"),m.get("kind")) for m in commune.get("media",[])}
                for filename,date,origin in qualified:
                    media=images.get(filename.replace(" ","_"))
                    if not media or (media["sourceUrl"],"historical_photo") in prior:continue
                    key=hashlib.sha1((qid+filename).encode()).hexdigest()[:16]
                    commune.setdefault("media",[]).append({
                        **media,"id":"commons-history:"+key,"kind":"historical_photo",
                        "subjectVerified":True,"reuseAllowed":True,
                        "capturedAt":date,
                        "historicalDateMethod":origin,
                        "subjectMethod":"commons_media_info_P180_exact_municipality_QID",
                        "municipalityQid":qid,
                        "sourceId":"commons:mediainfo:M"+str(pages[next(i for i,x in enumerate(pages) if x["filename"]==filename)]["pageid"]),
                        "caption":"Fotografia storica di "+commune["name"]+" ("+date[:4]+")",
                        "retrievedAt":checked_at
                    })
                    prior.add((media["sourceUrl"],"historical_photo"))
                    report["imagesSaved"]+=1
        except Exception as exc:
            report["errors"].append({"istat":commune["sourceIds"]["istat"],
                "qid":qid,"error":str(exc)[:180]})
    report["historicalMunicipalities"]=sum(any(m.get("kind")=="historical_photo"
        for m in e.get("media",[])) for e in all_m)
    return release,report

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--municipalities",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    ap.add_argument("--max-municipalities",type=int,default=20)
    args=ap.parse_args()
    doc=load(args.municipalities)
    updated,report=enrich_historical(doc,max_municipalities=args.max_municipalities)
    save(args.municipalities,updated)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
