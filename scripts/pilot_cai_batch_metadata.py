#!/usr/bin/env python3
"""Bounded official CAI Unico Rifugi REST API pilot: one page (max 80) + one search.

Metadata STAGING ONLY; API accessibility != license/republication permission.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import json
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
BASE="https://rifugi.cai.it/api/v1"
UA="CimaBecco-CAI-Research/0.1 (https://www.cimabecco.it)"
def get(path,params):
    url=BASE+path+"?"+urlencode(params)
    req=Request(url,headers={"User-Agent":UA,"Accept":"application/json"})
    with urlopen(req,timeout=50) as res:
        data=json.loads(res.read(4_000_000))
    return data,url
def shape(d):
    if isinstance(d,dict):return {"type":"object","keys":list(d)[:50]}
    if isinstance(d,list):return {"type":"array","count":len(d),"firstType":type(d[0]).__name__ if d else None}
    return {"type":type(d).__name__}
def main():
    result={"at":datetime.now(timezone.utc).isoformat(),"source":BASE,
      "licenceStatus":"not confirmed for bulk republication","errors":[]}
    records=[]
    try:
        page,url=get("/shelters",{"per_page":80,"page":1})
        data=page.get("data") or []
        result["catalog"]={"url":url,"sampleCount":len(data),"paginationTotalReported":page.get("total"),
          "lastPage":page.get("last_page"),"perPage":page.get("per_page"),
          "knownAltitude":sum(isinstance(x.get("altitude_geo"),(int,float)) for x in data),
          "knownGeo":sum(bool(x.get("geo")) for x in data),
          "knownTitle":sum(bool(x.get("title")) for x in data),
          "dataFieldShape":shape(data[0].get("data")) if data else None}
        result["catalog"]["topLevelFields"]=dict(Counter(k for x in data for k in x))
        if data:
            nested=Counter()
            for x in data:
                d=x.get("data")
                if isinstance(d,dict):nested.update(d.keys())
            result["catalog"]["nestedDataKeys"]=dict(nested.most_common(40))
        records=[{"source":{"provider":"CAI Unico Rifugi","url":BASE+"/shelters/"+str(x.get("id_cai"))},
          "caiId":x.get("id_cai"),"name":x.get("title"),
          "providerSlug":x.get("slug"),"altitudeM":x.get("altitude_geo"),
          "geo":x.get("geo"),
          "details":x.get("data") if isinstance(x.get("data"),(dict,list)) else None,
          "updatedAt":x.get("updated_at"),"published":x.get("published"),
          "editorialStatus":"staging_unverified"} for x in data]
    except Exception as ex:result["errors"].append({"source":"CAI catalog","error":str(ex)[:220]})
    try:
        p,url=get("/shelters/search",{"formData[query]":"Antermoia"})
        # Search response structure documented by CAI may differ from paginated index.
        result["searchAntermoia"]={"url":url,"responseShape":shape(p),
          "resultShape":shape(p.get("results")) if isinstance(p,dict) else None,
          "resultCount":len(p.get("results") or []) if isinstance(p,dict) and isinstance(p.get("results"),list) else None}
    except Exception as ex:result["errors"].append({"source":"CAI named search","error":str(ex)[:220]})
    result["detailProbe"]=[]
    for entry in records[:4]:
        try:
            detail,detail_url=get("/shelters/"+str(entry["caiId"]),{})
            result["detailProbe"].append({"caiId":entry["caiId"],"url":detail_url,
                "responseShape":shape(detail),
                "topLevelKeys":list(detail)[:40] if isinstance(detail,dict) else [],
                "firstFieldShape":shape((detail.get("fields") or [None])[0])
                    if isinstance(detail,dict) and detail.get("fields") else None,
                "availableFieldNames":list(dict.fromkeys(
                    str(x.get("slug") or x.get("name") or x.get("field_name") or x.get("label") or x.get("title") or "")[:120]
                    for x in (detail.get("fields") or []) if isinstance(x,dict)))
                    if isinstance(detail,dict) else [],
                "fieldEntryCount":len(detail.get("fields") or []) if isinstance(detail,dict) else 0,
                "mediaEntryCount":len(detail.get("media") or []) if isinstance(detail,dict) else 0,
                "nestedTypes":{k:shape(v) for k,v in detail.items()
                    if k in ("data","fields","media","shelter","contacts","services")}
                    if isinstance(detail,dict) else {}})
        except Exception as ex:
            result["detailProbe"].append({"caiId":entry["caiId"],"error":str(ex)[:200]})
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"cai-shelter-records.json").write_text(json.dumps({"records":records,
      "notice":"Staging only; check licence and freshness before publication."},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"cai-shelter-coverage.json").write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=="__main__":main()
