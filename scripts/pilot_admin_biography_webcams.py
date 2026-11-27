#!/usr/bin/env python3
"""Proof-of-access: official ISTAT/DAIT datasets, Wikidata alpine biographies,
regional webcam pages. No unsupported municipal claims, no image embedding.
"""
from __future__ import annotations
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError, URLError
import csv,io,json,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
UA="CimaBecco-OpenDataAudit/0.1 (https://www.cimabecco.it)"
SOURCES={
  "mayors_dait":"https://dait.interno.gov.it/documenti/sindaciincarica.csv",
  "municipal_population_datasets":"https://dati-coll.dfp.gov.it/api/3/action/package_show?id=comuni_eta_sesso",
  "municipality_dataset":"https://dati-coll.dfp.gov.it/api/3/action/package_show?id=comuni_italiani",
}
CAMERAS={
 "meteo_trentino":"https://www.meteotrentino.it/dati/meteo/webcam/",
 "veneto_arpav":"https://meteo.arpa.veneto.it/?page=webcam",
 "alto_adige":"https://meteo.provincia.bz.it/it/webcams"
}
SPARQL="https://query.wikidata.org/sparql"
Q="""SELECT DISTINCT ?person ?personLabel ?place ?placeLabel ?occupation ?occupationLabel WHERE {
 VALUES ?place { wd:Q258031 wd:Q30027591 wd:Q623690 }
 VALUES ?occupation { wd:Q9149093 wd:Q819677 wd:Q3951423 wd:Q86135347 }
 ?person wdt:P19 ?place; wdt:P106 ?occupation.
 SERVICE wikibase:label { bd:serviceParam wikibase:language "it,de,en". }
} LIMIT 25"""
def get(url,maxbytes=2_900_000,timeout=25):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/csv,application/json,text/html"})
    try:
        with urlopen(req,timeout=timeout) as x:return x.status,x.read(maxbytes),x.headers.get("Content-Type","")
    except HTTPError as ex:return ex.code,ex.read(1024),ex.headers.get("Content-Type","")
def probe(name,url):
    result={"source":name,"url":url}
    try:
        status,raw,ctype=get(url)
        result["httpStatus"]=status
        result["contentType"]=ctype
        result["bytesRead"]=len(raw)
        if status==200 and name=="mayors_dait":
            for enc in ("utf-8-sig","latin-1"):
                try:txt=raw.decode(enc);break
                except UnicodeDecodeError:continue
            lines=txt.splitlines()
            dialect=csv.Sniffer().sniff("\n".join(lines[:4]),delimiters=";,")
            reader=csv.DictReader(io.StringIO(txt),dialect=dialect)
            rows=list(reader)
            result["rowsParsed"]=len(rows)
            result["columns"]=reader.fieldnames
            picked=[r for r in rows if any(re.search(r"\b"+x+r"\b",str(r),re.I) for x in
                       ["Canazei","Moena","Arabba"])][:6]
            result["sampleRows"]=picked
            result["licenceToVerify"]=True
        elif status==200 and "dataset" in name:
            data=json.loads(raw)
            resources=(data.get("result") or {}).get("resources") or []
            result["resourceCount"]=len(resources)
            result["resources"]=[{"name":x.get("name"),"format":x.get("format"),"url":x.get("url"),"lastModified":x.get("last_modified")} for x in resources[:12]]
            result["datasetLicence"]=(data.get("result") or {}).get("license_id")
    except Exception as ex:result["error"]=str(ex)[:200]
    return result
def main():
    results={"generatedAt":datetime.now(timezone.utc).isoformat(),
      "officialDatasets":[probe(n,u) for n,u in SOURCES.items()]}
    try:
        query=urlencode({"query":Q,"format":"json"})
        status,body,ctype=get(SPARQL+"?"+query,300_000,timeout=40)
        result={"httpStatus":status,"queryType":"birthplace AND specialist mountain occupation",
          "placeQids":["Q258031","Q30027591","Q623690"],"occupations":["Q9149093","Q819677","Q3951423","Q86135347"]}
        if status==200:
            values=(json.loads(body).get("results") or {}).get("bindings") or []
            result["matches"]=len(values)
            result["people"]=[{"person":(v.get("person") or {}).get("value"),
              "name":(v.get("personLabel") or {}).get("value"),
              "birthplace":(v.get("placeLabel") or {}).get("value"),
              "occupation":(v.get("occupationLabel") or {}).get("value")} for v in values]
        else:result["error"]="No data: HTTP "+str(status)
        results["mountainPeople"]=result
    except Exception as ex:results["mountainPeople"]={"error":str(ex)[:240]}
    cameras=[]
    for name,url in CAMERAS.items():
        try:
            status,content,ct=get(url,120_000,timeout=20)
            cameras.append({"source":name,"url":url,"httpStatus":status,
              "htmlAccessible":status==200 and "html" in ct.lower(),
              "webcamMetadataExtracted":False,
              "note":"Portal URL is not a verified live frame stream; no embed created."})
        except Exception as ex:cameras.append({"source":name,"url":url,"error":str(ex)[:200]})
    results["webcamPortals"]=cameras
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"public-admin-biographies-webcams.json").write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({"datasets":{x["source"]:{"status":x.get("httpStatus"),"rowsParsed":x.get("rowsParsed"),"resources":x.get("resourceCount")} for x in results["officialDatasets"]},
      "people":results["mountainPeople"].get("matches"),"webcams":[{"name":x["source"],"status":x.get("httpStatus")} for x in cameras]},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
