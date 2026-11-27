#!/usr/bin/env python3
"""CAI official Unico Rifugi API metadata/access probe.

Reads the public OpenAPI schema and attempts ONE paginated GET without
credentials. Does not bypass authentication; never harvests unrestricted data.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
BASE="https://rifugi.cai.it"
DOC=BASE+"/docs/api-docs.json"
UA="CimaBecco-API-Discovery/0.1 (https://www.cimabecco.it)"
def read(url,limit=1_000_000):
    req=Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    try:
        with urlopen(req,timeout=35) as resp:return resp.status,resp.read(limit).decode("utf-8","replace")
    except HTTPError as e:return e.code,e.read(1000).decode("utf-8","replace")
def main():
    result={"at":datetime.now(timezone.utc).isoformat(),"schemaUrl":DOC}
    try:
        status,body=read(DOC)
        if status!=200:raise RuntimeError("OpenAPI status "+str(status))
        doc=json.loads(body)
        paths=doc.get("paths") or {}
        result["openapiVersion"]=doc.get("openapi")
        result["endpointCount"]=len(paths)
        result["shelterOperationsRequireApiKey"]=any(
           any("api_key" in x for x in (v.get("security") or []))
           for p,methods in paths.items() if p.startswith("/api/v1/shelters")
           for v in methods.values() if isinstance(v,dict))
        op=paths.get("/api/v1/shelters",{}).get("get",{})
        result["availableShelterFieldsSchema"]=list((doc.get("components") or {}).get("schemas",{}).keys())[:30]
        result["sheltersQueryParameters"]=[x.get("name") for x in op.get("parameters") or []]
        endpoint=BASE+"/api/v1/shelters?"+urlencode({"per_page":1,"page":1})
        status,data=read(endpoint,100_000)
        result["probe"]={"url":endpoint,"httpStatus":status,
            "accessibleWithoutCredential":status==200}
        if status==200:
            payload=json.loads(data)
            result["probe"]["responseTopLevelKeys"]=list(payload)[:15] if isinstance(payload,dict) else []
            if isinstance(payload,dict):
                rows=payload.get("data") or []
                if isinstance(rows,list) and rows:result["probe"]["firstShelterAvailableFields"]=list(rows[0])[:45]
        elif status in (401,403):
            result["probe"]["note"]="Access denied without API key: do not scrape or bypass."
    except Exception as e:result["error"]=str(e)[:300]
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"cai-api-access-report.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
