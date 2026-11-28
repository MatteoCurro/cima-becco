#!/usr/bin/env python3
"""Blocco 3: arricchimento verificato Comuni con Wikidata, Wikipedia, Commons.

Raw ISTAT/DAIT -> identità Wikidata P635 -> coordinate P625 e media P18/P94
-> Commons imageinfo/extmetadata -> Wikipedia pageprops QID/extract -> G2.
Input obbligatorio: archivio canonico generato da import_municipalities_v1.py.
Usa un solo catalogo e non tocca le schede OSM o le vecchie URL.
L'estratto di Wikipedia è contenuto con licenza/provenienza propria; non è un
testo originale e non si spaccia per un riassunto redazionale.
"""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import time
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from import_municipalities_v1 import load, save, fact, require, code6

ROOT = Path(__file__).resolve().parents[1]
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
WIKIDATA_QUERY = "https://query.wikidata.org/sparql"
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
WIKIPEDIA_API = "https://it.wikipedia.org/w/api.php"
UA = "CimaBecco/1.0 (https://www.cimabecco.it; public metadata import)"
QID = re.compile(r"Q[1-9]\d*")
PHOTO_EXT = re.compile(r"\.(jpe?g|png|webp|tiff?)$", re.I)
SYMBOL_EXT = re.compile(r"\.(jpe?g|png|webp|tiff?|svg)$", re.I)
# No file named "map"/"coat of arms" promoted as a landscape.
NON_PHOTO = re.compile(r"(^|[\s_-])(stemma|wappen|coat.of.arms|flag|bandiera|mappa|map|locator|logo|svg)([\s_.-]|$)",re.I)
ALLOWED_LICENSES = {"CC0", "Public domain", "Public Domain", "CC BY 2.0",
                    "CC BY 3.0", "CC BY 4.0", "CC BY-SA 3.0", "CC BY-SA 4.0"}
ALPINE_PROVINCES = {"BL","TN","BZ","SO","AO","UD","PN","VI","VR","CO","LC","BG","BS","VB","CN","TO","TV","BI"}
PRIORITY_NAMES = (
    "Canazei","Cortina d'Ampezzo","Moena","Selva di Val Gardena",
    "Ortisei","Badia","Corvara in Badia","Livinallongo del Col di Lana",
    "Auronzo di Cadore","San Vito di Cadore","Falcade","Arabba",
    "Rocca Pietore","Alleghe","Agordo","Predazzo","Campitello di Fassa",
    "Pozza di Fassa","Vigo di Fassa","San Giovanni di Fassa",
    "Dobbiaco","Sesto","San Candido","Bressanone","Brunico",
)
RETRYABLE = {429, 502, 503, 504}

def request_json(url, params, *, getter=None, attempts=3):
    if getter is not None:
        return getter(url, params)
    uri = url + "?" + urlencode(params)
    for attempt in range(attempts):
        try:
            with urlopen(Request(uri, headers={"User-Agent": UA,
                         "Accept": "application/json"}), timeout=45) as response:
                return json.load(response)
        except HTTPError as ex:
            if ex.code not in RETRYABLE or attempt + 1 == attempts:
                raise
            time.sleep((4, 10)[min(attempt,1)])
        except (URLError,TimeoutError):
            if attempt + 1 == attempts: raise
            time.sleep((4,10)[min(attempt,1)])

def query_national_istat_qids(*, getter=None):
    """Direct P635 crosswalk; unrelated QIDs, ambiguous codes held in review."""
    query = 'SELECT ?item ?code WHERE { ?item wdt:P635 ?code . } LIMIT 12000'
    data = request_json(WIKIDATA_QUERY, {"query":query,"format":"json"},getter=getter)
    rows = {}
    collisions = set()
    for item in (data.get("results") or {}).get("bindings") or []:
        qid = (item.get("item") or {}).get("value","").rsplit("/",1)[-1]
        code = (item.get("code") or {}).get("value","")
        if not (QID.fullmatch(qid) and re.fullmatch(r"[0-9]{6}",code)):
            continue
        if code in rows and rows[code]!=qid:
            collisions.add(code)
        else:
            rows[code]=qid
    for code in collisions:
        rows.pop(code,None)
    return rows,sorted(collisions)

def wd_entities(qids, *, getter=None):
    if not qids:return {}
    data = request_json(WIKIDATA_API,{"action":"wbgetentities","format":"json",
        "ids":"|".join(qids),"props":"claims|sitelinks|labels","languages":"it|en",
        "sitefilter":"itwiki"},getter=getter)
    return data.get("entities") or {}

def claim_string(item, prop):
    for claim in (item.get("claims") or {}).get(prop,[]):
        if claim.get("rank")=="deprecated":continue
        v=((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v,str) and v:return v
    return None

def claim_quantity(item, prop, expected_unit, minimum, maximum):
    """Wikidata quantity with explicit unit and controlled domain; no implicit conversion."""
    unit_uri="http://www.wikidata.org/entity/"+expected_unit
    for claim in (item.get("claims") or {}).get(prop,[]):
        if claim.get("rank")=="deprecated":continue
        value=((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if not isinstance(value,dict) or value.get("unit")!=unit_uri:continue
        try:amount=float(value.get("amount"))
        except (ValueError,TypeError):continue
        if math.isfinite(amount) and minimum<=amount<=maximum:
            return amount
    return None

def claim_coord(item):
    for claim in (item.get("claims") or {}).get("P625",[]):
        if claim.get("rank")=="deprecated":continue
        v=((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v,dict):
            lat,lng=v.get("latitude"),v.get("longitude")
            if (isinstance(lat,(int,float)) and isinstance(lng,(int,float))
                and math.isfinite(lat) and math.isfinite(lng)
                and 35<=lat<=48 and 6<=lng<=20):
                return {"lat":round(lat,6),"lng":round(lng,6)}
    return None

def text_only(value):
    # Author and license metadata can include HTML markup; render only text.
    value = re.sub(r"<[^>]*>", " ", str(value or ""))
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()

def meta_value(meta,key):
    return (meta.get(key) or {}).get("value")

def commons_files(filenames,*, getter=None, allow_svg=False):
    """One batched imageinfo call; no guessing photo from file name."""
    filenames = list(dict.fromkeys(name for name in filenames if name))
    if not filenames:return {}
    titles = "|".join("File:" + filename.replace("_"," ") for filename in filenames)
    data = request_json(COMMONS_API,{
        "action":"query","format":"json","titles":titles,
        "prop":"imageinfo","iiprop":"url|extmetadata|timestamp","iiurlwidth":"1100"
    },getter=getter)
    result={}
    for page in (data.get("query") or {}).get("pages",{}).values():
        info=(page.get("imageinfo") or [None])[0]
        if not info:continue
        meta=info.get("extmetadata") or {}
        license_name=text_only(meta_value(meta,"LicenseShortName"))
        artist=text_only(meta_value(meta,"Artist"))
        licence_url=meta_value(meta,"LicenseUrl")
        fileurl=info.get("thumburl") or info.get("url") or ""
        original=info.get("descriptionurl") or ""
        title=page.get("title","")
        is_svg=title.lower().endswith(".svg")
        # SVGs represent most municipal coats of arms. Use Commons'
        # rasterized thumb rather than embedding unreviewed SVG bytes.
        if is_svg and not (allow_svg and (info.get("thumburl") or "").startswith("https://")):
            continue
        if not (fileurl.startswith("https://") and original.startswith("https://")
                and license_name in ALLOWED_LICENSES and artist
                and len(artist)<=240 and (SYMBOL_EXT if allow_svg else PHOTO_EXT).search(title)
                and (license_name.startswith("Public") or license_name=="CC0" or
                     (isinstance(licence_url,str) and licence_url.startswith("https://")))):
            continue
        result[title.removeprefix("File:").replace(" ","_")]={
            "url":fileurl,"sourceUrl":original,"licence":license_name,
            "licenceUrl":licence_url if licence_url and str(licence_url).startswith("https://") else None,
            "author":artist,"retrievedAt":None,
            "sourceUpdatedAt":info.get("timestamp"),
            "subjectVerified":True,"reuseAllowed":True
        }
    return result

def municipality_heraldry_filename(filename, municipality):
    """Only exact municipality + heraldic term, never generic 'Italy' files."""
    if not isinstance(filename,str) or not isinstance(municipality,str):return False
    def normalize(s):
        import unicodedata
        s=unicodedata.normalize("NFKD",s)
        s="".join(c for c in s if not unicodedata.combining(c))
        return re.sub(r"[^a-z0-9]+"," ",s.casefold()).strip()
    name=normalize(municipality)
    basename=normalize(filename.removeprefix("File:").rsplit(".",1)[0])
    if len(name)<3 or not ((" "+name+" ") in (" "+basename+" ")):return False
    return bool(re.search(r"\b(stemma|wappen|coat of arms|blason|blasonnement|heraldic|armoiries)\b",basename)) and not bool(
        re.search(r"\b(blank|template|provisional|facsimile|sample|bozza|modello|fake)\b",basename))

def verified_article_heraldry_images(intro, municipality):
    if not isinstance(intro,dict):return []
    images=intro.get("linkedImages") or []
    return list(dict.fromkeys(
        s for s in images if municipality_heraldry_filename(s,municipality)))[:4]

def wikipedia_intro(title,qid,*,getter=None):
    """Exact itwiki sitelink, with pageprops wikibase_item identity proof."""
    if not title:return None
    data = request_json(WIKIPEDIA_API,{
        "action":"query","format":"json","titles":title,
        "prop":"extracts|pageprops|images","imlimit":"max","exintro":"1","explaintext":"1",
        "ppprop":"wikibase_item","redirects":"1","exchars":"1400"
    },getter=getter)
    pages=(data.get("query") or {}).get("pages",{})
    for page in pages.values():
        if (page.get("pageprops") or {}).get("wikibase_item")!=qid:return None
        extract=re.sub(r"\s+"," ",page.get("extract") or "").strip()
        # Wiki lead frequently includes unqualified population. Never publish
        # an undated figure as an official ISTAT datum; remove such sentences.
        sentences=re.split(r"(?<=[.!?])\s+",extract)
        selected=[sentence for sentence in sentences if not re.search(
            r"\b(abitanti|popolazione|residenti)\b",sentence,re.I)]
        content=" ".join(selected)[:1000].strip()
        if len(content)<120 or len(content.split())<20:
            return None
        pid=page.get("pageid")
        if not isinstance(pid,int):return None
        return {"text":content,"sourceId":"wikipedia:it:"+str(pid),
                "sourceUrl":"https://it.wikipedia.org/wiki/"+quote(title.replace(" ","_")),
                "licence":"CC BY-SA 4.0","method":"reported",
                "sourceUpdatedAt":None,"retrievedAt":None,
                "originalLanguage":"it","kind":"source_excerpt_not_original_editorial",
                "linkedImages":[img.get("title","") for img in page.get("images",[])
                                if isinstance(img,dict) and img.get("title","").startswith("File:")]}
    return None

def choose_candidates(entities, crosswalk, limit=48, previous=None, progress=None):
    done = {e["sourceIds"]["istat"] for e in (previous or {}).get("entities",[])
            if e.get("quality",{}).get("gate")=="G2"}
    attempts=(progress or {}).get("attempts",{})
    pool=[]
    for e in entities:
        code=e["sourceIds"]["istat"]
        if code not in crosswalk or code in done:continue
        region=e.get("administrativeHierarchy") or {}
        p=region.get("provinceAbbreviation")
        if p not in ALPINE_PROVINCES:continue
        name=e["name"]
        try:priority=PRIORITY_NAMES.index(name)
        except ValueError:priority=1000
        count=int((attempts.get(code) or {}).get("attempts",0))
        # Unprocessed candidates first: bad candidates must not monopolise
        # every daily batch. Existing G2s are refreshed independently.
        pool.append((count,priority,0 if p in ("BL","TN","BZ") else 1,p,name,code))
    pool.sort()
    # Periodically refresh previously published dossiers as well as new ones:
    # they must not lose facts when ISTAT/DAIT is reimported from scratch.
    existing=sorted([code for code in done if code in crosswalk])
    # Rotate refreshed G2 so a growing catalogue does not force re-fetching
    # the same first 30 towns forever. No more than eight refreshes per run.
    start=(int((progress or {}).get("successfulRuns",0))*8)%max(1,len(existing))
    refreshed=(existing+existing)[start:start+min(8,len(existing))]
    return refreshed+[x[-1] for x in pool[:limit]]

def enrich(archive, qid_map, *, getter=None, max_new=48, previous=None, progress=None, retrieved_at=None):
    """Deterministic after source fixtures; a failed source never fabricates data."""
    require(archive.get("releaseChannel")=="ISTAT_DAIT_MUNICIPALITIES_STAGING",
            "Input non è l'archivio ISTAT canonico")
    retrieved_at = retrieved_at or archive.get("retrievedAt")
    entities={e["sourceIds"]["istat"]:e for e in archive.get("entities",[])}
    old={e["sourceIds"]["istat"]:e for e in (previous or {}).get("entities",[])}
    chosen=choose_candidates(list(entities.values()),qid_map,max_new,previous,progress)
    media_count=text_count=g2_count=0
    failures=[]
    for offset in range(0,len(chosen),25):
        part=chosen[offset:offset+25]
        qids=[qid_map[code] for code in part]
        try: details=wd_entities(qids,getter=getter)
        except Exception as exc:
            failures.append("wikidata:"+str(exc)[:120]);continue
        relevant=[]
        for code,qid in zip(part,qids):
            item=details.get(qid,{})
            # Verify the current P635 claim on the entity, not just a SPARQL row.
            ids=[((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
                 for c in (item.get("claims") or {}).get("P635",[])
                 if c.get("rank")!="deprecated"]
            if code not in ids:
                failures.append("p635_mismatch:"+code);continue
            relevant.append((code,qid,item))
        imgs=list(dict.fromkeys(name for _,_,item in relevant
                               for name in (claim_string(item,"P18"),claim_string(item,"P94"),claim_string(item,"P154")) if name))
        try: images=commons_files(imgs,getter=getter,allow_svg=True)
        except Exception as exc:
            images={};failures.append("commons:"+str(exc)[:120])
        for code,qid,item in relevant:
            entity=entities[code]
            if code in old:
                entity["facts"]={**old[code].get("facts",{}), **entity["facts"]}
            entity["sourceIds"]["wikidata"]=qid
            entity["sourceIds"]["wikidataVerifiedBy"]="P635"
            wd_url="https://www.wikidata.org/wiki/"+qid
            point=claim_coord(item)
            if point and not entity["geo"].get("point"):
                entity["geo"]={"point":point,"area":None,"method":"reported",
                               "sourceUrl":wd_url,"sourceId":"wikidata:"+qid+":P625"}
            # P2044 describes the elevation of an entity, not necessarily
            # the municipality's administrative centre. Never call it quotaCentroM.
            elevation=claim_quantity(item,"P2044","Q11573",-5,4800)
            if elevation is not None and "elevationReportedM" not in entity["facts"]:
                entity["facts"]["elevationReportedM"]=fact(
                    elevation,"wikidata:"+qid+":P2044",wd_url,unit="m",
                    as_of=retrieved_at,licence="CC0",method="reported")
            # P2046: square kilometres only, never reinterpret hectares/m².
            area=claim_quantity(item,"P2046","Q712226",0.01,3000)
            if area is not None and "superficieKm2" not in entity["facts"]:
                entity["facts"]["superficieKm2"]=fact(
                    area,"wikidata:"+qid+":P2046",wd_url,unit="km2",
                    as_of=retrieved_at,licence="CC0",method="reported")
            website=claim_string(item,"P856")
            if website and website.startswith("https://"):
                entity["facts"]["sitoUfficiale"]=fact(website,"wikidata:"+qid+":P856",
                    wd_url,as_of=retrieved_at,licence="CC0")
            for prop,kind,symbol_type in (
                ("P18","photo",None),("P94","logo","coat_of_arms"),
                ("P154","logo","institutional_logo")):
                file=claim_string(item,prop)
                if not file or (kind=="photo" and (NON_PHOTO.search(file) or
                    not PHOTO_EXT.search(file))):
                    continue
                image=images.get(file.replace(" ","_"))
                if image:
                    entity["media"].append({**image,"id":"wikimedia:"+qid+":"+prop+":"+hashlib.sha1(file.encode()).hexdigest()[:12],
                        "kind":kind,"symbolType":symbol_type,
                        "caption":("Stemma del Comune di "+entity["name"] if prop=="P94" else
                            "Logo istituzionale di "+entity["name"] if prop=="P154" else
                            "Fotografia di "+entity["name"]),
                        "retrievedAt":retrieved_at,
                        "subjectMethod":"explicit_wikidata_"+prop+"_confirmed_P635"})
                    if not any(m.get("url")==image["url"] and m.get("kind")==kind
                               for m in old.get(code,{}).get("media",[])):
                        media_count+=1
            wiki=((item.get("sitelinks") or {}).get("itwiki") or {}).get("title")
            if wiki:
                try:
                    intro=wikipedia_intro(wiki,qid,getter=getter)
                    if intro:
                        intro["retrievedAt"]=retrieved_at
                        entity["textSources"]=[{k:v for k,v in intro.items() if k!="linkedImages"}]
                        entity["description"]=intro["text"]
                        if not any(t.get("sourceId")==intro["sourceId"]
                                   for t in old.get(code,{}).get("textSources",[])):
                            text_count+=1
                        # The municipality's confirmed itwiki infobox may
                        # list a crest even when P94 is absent in Wikidata.
                        if not any(m.get("kind")=="logo" for m in entity["media"]):
                            candidates=verified_article_heraldry_images(intro,entity["name"])
                            if candidates:
                                try:
                                    crest_assets=commons_files([p.removeprefix("File:")
                                        for p in candidates],getter=getter,allow_svg=True)
                                except Exception as exc:
                                    crest_assets={}
                                    failures.append("itwiki_crest:"+code+":"+str(exc)[:75])
                                for filename in candidates[:2]:
                                    file=filename.removeprefix("File:")
                                    image=crest_assets.get(file.replace(" ","_"))
                                    if not image:continue
                                    entity["media"].append({**image,
                                        "id":"wikimedia:"+qid+":article:crest:"+
                                           hashlib.sha1(file.encode()).hexdigest()[:12],
                                        "kind":"logo","symbolType":"coat_of_arms",
                                        "caption":"Stemma di "+entity["name"],
                                        "retrievedAt":retrieved_at,
                                        "sourceId":"wikipedia:it:"+str(intro["sourceId"]),
                                        "subjectMethod":"exact_named_heraldry_file_in_itwiki_article_verified_QID"})
                                    media_count+=1
                                    break
                except Exception as exc:failures.append("wiki:"+code+":"+str(exc)[:70])
            if code in old and not any(m["kind"]=="photo" for m in entity["media"]):
                entity["media"]=old[code].get("media",[])
            if code in old and not entity.get("textSources"):
                entity["textSources"]=old[code].get("textSources",[])
                entity["description"]=old[code].get("description","")
            photo=any(m["kind"]=="photo" for m in entity["media"])
            has_text=any(len(x.get("text",""))>=120 for x in entity.get("textSources",[]))
            has_point=bool(entity["geo"].get("point"))
            if has_text and photo and has_point:
                entity["quality"]={"gate":"G2","seoIndexable":True,"reviewRequired":False,
                    "photoSourceVerified":True,"textLicenseVerified":True}
                entity["editorialStatus"]="enriched"
                if old.get(code,{}).get("quality",{}).get("gate")!="G2":g2_count+=1
            elif has_point:
                entity["quality"]={"gate":"G1","seoIndexable":False,"reviewRequired":False}
                entity["editorialStatus"]="linked"
    # Refresh of present dossiers must not discard previously licensed
    # coats of arms, images or archival photographs on provider outages.
    for code,previous in old.items():
        current=entities.get(code)
        if not current:continue
        known={(m.get("kind"),m.get("sourceUrl")) for m in current.get("media",[])}
        for media in previous.get("media",[]):
            key=(media.get("kind"),media.get("sourceUrl"))
            if (key not in known and media.get("reuseAllowed") and
                media.get("subjectVerified") and media.get("licence") and
                media.get("author") and media.get("sourceUrl")):
                current.setdefault("media",[]).append(media)
                known.add(key)
    # Existing G2 records must keep their facts when a run only processes
    # *new* candidates; ISTAT/DAIT facts in the current snapshot win.
    # preserve existing enriched identities/media across incremental refresh
    for code,old_e in old.items():
        if code not in entities:continue
        e=entities[code]
        if old_e.get("connectedPeople") and not e.get("connectedPeople"):
            e["connectedPeople"]=old_e["connectedPeople"]
        for historic_link in old_e.get("relations",[]):
            if historic_link.get("type") not in (
                "birthplace_of","historical_residence_of","workplace_of"
            ) or not historic_link.get("verified"):
                continue
            if not any(r.get("type")==historic_link["type"] and
                       r.get("target",{}).get("id")==historic_link.get("target",{}).get("id")
                       for r in e.get("relations",[])):
                e["relations"].append(historic_link)
        if e.get("quality",{}).get("gate")!="G2" and old_e.get("quality",{}).get("gate") in ("G1","G2"):
            e["facts"]={**old_e.get("facts",{}), **e.get("facts",{})}
            for k in ("geo","media","textSources","description","editorialStatus","quality"):
                if k in old_e:e[k]=old_e[k]
            for source in ("wikidata","wikidataVerifiedBy"):
                if source in old_e.get("sourceIds",{}):
                    e["sourceIds"][source]=old_e["sourceIds"][source]
    enriched = list(entities.values())
    for e in enriched:
        if e.get("quality",{}).get("gate")=="G0":
            e["quality"]["seoIndexable"]=False
    public=[e for e in enriched if e.get("quality",{}).get("gate")=="G2"]
    public.sort(key=lambda e:e["sourceIds"]["istat"])
    report={"nationalEntities":len(enriched),"publishedG2":len(public),
            "newG2":g2_count,"newMedia":media_count,"newWikiText":text_count,
            "elevationReportedCoverage":sum(e.get("facts",{}).get("elevationReportedM",{}).get("value") is not None for e in public),
            "areaCoverage":sum(e.get("facts",{}).get("superficieKm2",{}).get("value") is not None for e in public),
            "municipalitiesWithSymbols":sum(any(m.get("kind")=="logo" for m in e.get("media",[])) for e in public),
            "municipalitiesWithHistoricPhotos":sum(any(m.get("kind")=="historical_photo" for m in e.get("media",[])) for e in public),
            "selectedCandidates":len(chosen),"selectedCodes":chosen,
            "firstAttempts":sum((progress or {}).get("attempts",{}).get(code) is None for code in chosen),
            "failures":failures,
            "qualityG1":sum(e.get("quality",{}).get("gate")=="G1" for e in enriched),
            "qualityG0":sum(e.get("quality",{}).get("gate")=="G0" for e in enriched)}
    return {"schemaVersion":"1.0","releaseChannel":"ISTAT_DAIT_MUNICIPALITIES",
            "isPublished":True,"retrievedAt":retrieved_at,"entities":public}, report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--archive",type=Path,required=True)
    p.add_argument("--qid-map",type=Path)
    p.add_argument("--previous",type=Path)
    p.add_argument("--out",type=Path,default=ROOT/"public/data/atlas/municipalities-v1.json")
    p.add_argument("--report",type=Path,default=ROOT/"build/import-municipalities-v1/enrichment-report.json")
    p.add_argument("--max-new",type=int,default=48)
    p.add_argument("--progress",type=Path)
    args=p.parse_args()
    archive=load(args.archive)
    wd_map,collisions={},[]
    if args.qid_map and args.qid_map.is_file():
        r=load(args.qid_map)
        if isinstance(r,dict) and "associations" in r:
            records=r["associations"]
            for x in records:
                code=code6(x.get("istatCode"))
                qid=x.get("wikidata")
                if code and QID.fullmatch(str(qid or "")):
                    wd_map[code]=qid
    try:
        national,collisions=query_national_istat_qids()
        wd_map.update(national)
    except Exception as exc:
        print("Wikidata national P635 lookup unavailable; using verified P635 pilot only:",str(exc)[:160])
    old=load(args.previous) if args.previous and args.previous.is_file() else None
    progress=load(args.progress) if args.progress and args.progress.is_file() else None
    result,report=enrich(archive,wd_map,max_new=args.max_new,previous=old,progress=progress)
    report["wikidataP635Available"]=len(wd_map)
    report["wikidataP635Collisions"]=collisions[:100]
    require(report["publishedG2"]>0,"Nessuna scheda G2 verificata; vietata pubblicazione")
    save(args.out,result)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":
    main()
