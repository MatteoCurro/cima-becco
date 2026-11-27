#!/usr/bin/env python3
"""Metadata availability: SAT hut descriptions, Commons rights, Wikipedia section
headings, CAI OpenAPI documentation. No copyrighted full prose/photos copied.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
SAMPLE=OUT/"localities-huts-wikidata.json"
UA="CimaBecco-SourceAudit/0.1 (https://www.cimabecco.it; research)"
COMMONS="https://commons.wikimedia.org/w/api.php"
WIKI="https://it.wikipedia.org/w/api.php"
HUTS=["https://www.sat.tn.it/rifugio-antermoia/","https://www.sat.tn.it/vajolet/"]
CAI_DOC="https://rifugi.cai.it/docs/api-docs.json"
class Headings(HTMLParser):
    def __init__(self):
        super().__init__();self.headings=[];self.active=None
    def handle_starttag(self,tag,attrs):
        if tag in ("h1","h2","h3","h4"):self.active=[tag,""]
    def handle_data(self,text):
        if self.active:self.active[1]+=text
    def handle_endtag(self,tag):
        if self.active and self.active[0]==tag:
            self.headings.append((tag,re.sub(r"\s+"," ",self.active[1]).strip()))
            self.active=None
def urlget(url,timeout=35,byteslimit=4_000_000):
    req=Request(url,headers={"User-Agent":UA,"Accept":"application/json,text/html"})
    with urlopen(req,timeout=timeout) as r:return r.read(byteslimit).decode("utf-8","replace")
def main():
    results={"at":datetime.now(timezone.utc).isoformat(),"satHuts":[],
     "commonsImages":[],"wikipediaSections":[],"caiApi":{},"errors":[]}
    for url in HUTS:
        try:
            doc=urlget(url)
            parser=Headings();parser.feed(doc)
            h=[t for lvl,t in parser.headings if lvl in ("h3","h4")]
            results["satHuts"].append({"url":url,"pageTitle":next((t for lvl,t in parser.headings if lvl=="h1"),None),
             "sections":list(dict.fromkeys(h))[:30],
             "providesHistorySection":any(re.search(r"storia|ambiente",x,re.I) for x in h),
             "providesAccessSection":any(re.search(r"accessi",x,re.I) for x in h),
             "providesCrossingSection":any(re.search(r"traversate",x,re.I) for x in h),
             "providesAscentsSection":any(re.search(r"ascensioni",x,re.I) for x in h),
             "publicationReuseStatus":"NOT verified; only metadata/reference to publisher."})
        except Exception as e:results["errors"].append({"url":url,"error":str(e)[:200]})
    try:
        doc=json.loads(urlget(CAI_DOC,45,3_000_000))
        paths=doc.get("paths") or {}
        results["caiApi"]={"url":CAI_DOC,"openapi":doc.get("openapi") or doc.get("swagger"),
          "pathCount":len(paths),
          "paths":[{"path":k,"methods":list(v)} for k,v in list(paths.items())[:30]],
          "authSchemas":list(((doc.get("components") or {}).get("securitySchemes") or {}).keys()),
          "note":"Schema discovery only. No automatic permission to republish content."}
    except Exception as e:results["caiApi"]={"url":CAI_DOC,"error":str(e)[:200]}
    if SAMPLE.exists():
        rows=json.loads(SAMPLE.read_text(encoding="utf-8"))["records"]
        media=[]
        for row in rows:
            wd=row.get("wikidataMetadata") or {}
            image=(wd.get("facts") or {}).get("imageFile") or {}
            if image.get("value") and image["value"] not in media:media.append(image["value"])
        for filename in media[:6]:
            title="File:"+str(filename).replace("_"," ")
            try:
                query=urlencode({"action":"query","format":"json","prop":"imageinfo",
                  "iiprop":"url|extmetadata","titles":title,"iiurlwidth":400})
                payload=json.loads(urlget(COMMONS+"?"+query))
                page=next(iter((payload.get("query") or {}).get("pages",{}).values()))
                info=(page.get("imageinfo") or [{}])[0]; ext=info.get("extmetadata") or {}
                val=lambda k: (ext.get(k) or {}).get("value")
                results["commonsImages"].append({"file":filename,"filePage":page.get("title"),
                 "sourceUrl":"https://commons.wikimedia.org/wiki/"+title.replace(" ","_"),
                 "thumbnailUrl":info.get("thumburl"),"licenceName":val("LicenseShortName"),
                 "licenceUrl":val("LicenseUrl"),"artistHtml":val("Artist"),"creditHtml":val("Credit"),
                 "reuseNeedsReview":True})
            except Exception as e:results["errors"].append({"source":"Commons","file":filename,"error":str(e)[:180]})
        names=[]
        for row in rows:
            title=(row.get("wikidataMetadata") or {}).get("wikipediaItTitle")
            if title and title not in names:names.append(title)
        for title in names[:4]:
            try:
                query=urlencode({"action":"parse","format":"json","prop":"sections","page":title})
                payload=json.loads(urlget(WIKI+"?"+query))
                if payload.get("error"):raise RuntimeError(str(payload["error"])[:150])
                sections=(payload.get("parse") or {}).get("sections") or []
                headings=[x.get("line") for x in sections if x.get("line")]
                results["wikipediaSections"].append({"title":title,
                  "sourceUrl":"https://it.wikipedia.org/wiki/"+title.replace(" ","_"),
                  "sectionTitles":headings,"historyRelatedHeadings":[x for x in headings if re.search(
                    r"storia|toponim|etimolog|alpinis|ascension|rifugi",x,re.I)],
                  "licence":"CC BY-SA, prose NOT copied"})
            except Exception as e:results["errors"].append({"source":"Wikipedia","title":title,"error":str(e)[:180]})
    results["summary"]={
      "satHutsFetched":len(results["satHuts"]),
      "satHutsWithHistorySection":sum(x["providesHistorySection"] for x in results["satHuts"]),
      "commonsFilesWithLicence":sum(bool(x["licenceUrl"]) for x in results["commonsImages"]),
      "commonsFilesInspected":len(results["commonsImages"]),
      "wikipediaPagesInspected":len(results["wikipediaSections"]),
      "caiApiPathsExposed":results["caiApi"].get("pathCount")}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"media-hut-history-report.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"summary":results["summary"],"errors":results["errors"]},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
