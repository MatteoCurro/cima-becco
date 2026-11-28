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
from urllib.parse import unquote, urlparse
from enrich_municipalities_v1 import (
    COMMONS_API,WIKIPEDIA_API,PHOTO_EXT,NON_PHOTO,QID,commons_files,request_json,text_only,meta_value)
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

def article_history_candidates(commune, *,getter=None):
    """Second source: photos from that commune's *verified* Wikipedia article.

    Never accept foreign photos merely linked in the article: the file title
    must also contain the full town name and the image must have a verified
    pre-1975 capture/inception date.
    """
    sources=commune.get("textSources") or []
    wiki=next((t["sourceUrl"] for t in sources if t.get("sourceUrl","").startswith(
        "https://it.wikipedia.org/wiki/")),None)
    if not wiki:return []
    title=unquote(wiki.rsplit("/",1)[-1]).replace("_"," ")
    qid=commune["sourceIds"]["wikidata"]
    doc=request_json(WIKIPEDIA_API,{
      "action":"query","format":"json","prop":"pageprops|images",
      "ppprop":"wikibase_item","imlimit":"max","titles":title,
      "redirects":"1"},getter=getter)
    import unicodedata
    def norm(v):
        v=unicodedata.normalize("NFKD",str(v))
        v="".join(c for c in v if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+"," ",v.casefold()).strip()
    town=norm(commune["name"])
    names=[]
    for page in (doc.get("query") or {}).get("pages",{}).values():
        if (page.get("pageprops") or {}).get("wikibase_item")!=qid:continue
        for img in (page.get("images") or []):
            original=img.get("title","")
            filename=original.removeprefix("File:")
            if not (original.startswith("File:") and PHOTO_EXT.search(filename) and
                    not NON_PHOTO.search(filename)):continue
            normalized=norm(filename.rsplit(".",1)[0])
            if " "+town+" " not in " "+normalized+" ":continue
            names.append(filename)
    return list(dict.fromkeys(names))[:24]

def commons_pages_by_title(files,*,getter=None):
    """Resolve Commons MediaInfo IDs from a confirmed Wikipedia image list."""
    pages=[]
    for offset in range(0,len(files),25):
        part=files[offset:offset+25]
        doc=request_json(COMMONS_API,{
          "action":"query","format":"json",
          "titles":"|".join("File:"+f for f in part),
          "prop":"imageinfo","iiprop":"extmetadata"},getter=getter)
        for p in (doc.get("query") or {}).get("pages",{}).values():
            if not isinstance(p.get("pageid"),int):continue
            if not (p.get("imageinfo") or []):continue
            pages.append({"pageid":p["pageid"],
               "filename":p.get("title","").removeprefix("File:"),
               "extmetadata":p["imageinfo"][0].get("extmetadata") or {}})
    return pages

def enrich_historical(release,*,getter=None,max_municipalities=20,
                      max_photos_per_municipality=3,checked_at=None,cycle=0):
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
    # Rotate the archive scan independently from current photo coverage.
    # Otherwise the same first 20 Commons-less towns are retried each day.
    offset=(int(cycle)*max_municipalities)%max(1,len(eligible))
    selected=(eligible+eligible)[offset:offset+min(max_municipalities,len(eligible))]
    report={"municipalitiesEligible":len(eligible),"municipalitiesChecked":len(selected),
            "imagesConsidered":0,"imagesSaved":0,
            "historicalMunicipalities":0,"errors":[]}
    for commune in selected:
        qid=commune["sourceIds"]["wikidata"]
        try:
            pages=search_depicts(qid,getter=getter)
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
                qualified.append((filename,date,origin,
                    "commons_media_info_P180_exact_municipality_QID",p["pageid"]))
            # The second independent path: a *same-QID* Wikipedia page
            # + exact town in filename + dated Commons file metadata.
            # P180 remains the stronger verification whenever available.
            if len(qualified)<max_photos_per_municipality:
                try:
                    article_files=article_history_candidates(commune,getter=getter)
                    commons_pages=commons_pages_by_title(article_files,getter=getter)
                    ids=fetch_sdc(commons_pages,getter=getter)
                    report["imagesConsidered"]+=len(commons_pages)
                    for page in commons_pages:
                        if len(qualified)>=max_photos_per_municipality:break
                        filename=page["filename"]
                        item=ids.get("M"+str(page["pageid"])) or {}
                        date,origin=recorded_history_date(item,page["extmetadata"])
                        if not date:continue
                        if any(t[0].replace(" ","_")==filename.replace(" ","_") for t in qualified):
                            continue
                        if sdc_depicts_exact(item,qid):
                            method="commons_media_info_P180_exact_municipality_QID"
                        else:
                            method="same_QID_itwiki_article_and_full_town_filename"
                        qualified.append((filename,date,origin,method,page["pageid"]))
                except Exception as exc:
                    report["errors"].append({"istat":commune["sourceIds"]["istat"],
                      "source":"itwiki-history","error":str(exc)[:130]})
            qualified=qualified[:max_photos_per_municipality]
            if qualified:
                images=commons_files([x[0] for x in qualified],getter=getter)
                prior={(m.get("sourceUrl"),m.get("kind")) for m in commune.get("media",[])}
                for filename,date,origin,subject_method,media_page_id in qualified:
                    media=images.get(filename.replace(" ","_"))
                    if not media or (media["sourceUrl"],"historical_photo") in prior:continue
                    key=hashlib.sha1((qid+filename).encode()).hexdigest()[:16]
                    commune.setdefault("media",[]).append({
                        **media,"id":"commons-history:"+key,"kind":"historical_photo",
                        "subjectVerified":True,"reuseAllowed":True,
                        "capturedAt":date,
                        "historicalDateMethod":origin,
                        "subjectMethod":subject_method,
                        "municipalityQid":qid,
                        "sourceId":"commons:mediainfo:M"+str(media_page_id),
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
    ap.add_argument("--cycle",type=int,default=0)
    args=ap.parse_args()
    doc=load(args.municipalities)
    updated,report=enrich_historical(doc,max_municipalities=args.max_municipalities,cycle=args.cycle)
    save(args.municipalities,updated)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
