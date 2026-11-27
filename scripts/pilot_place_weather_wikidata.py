#!/usr/bin/env python3
"""Cima Becco: one-shot sample of locality, hut and bivouac metadata + weather.

Uses existing OSM record identities, Wikidata official API and Open-Meteo.
No geometry/GPX, no Wikipedia prose scraping, no frontend modifications.
Stdlib only; errors are recorded and NEVER presented as successful imports.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
PLACES=ROOT/"public"/"data"/"alpine-places.json"
UA="CimaBecco-Data-Pilot/0.1 (https://www.cimabecco.it; research)"
WD="https://www.wikidata.org/w/api.php"
FORECAST="https://api.open-meteo.com/v1/forecast"
ARCHIVE="https://archive-api.open-meteo.com/v1/archive"
CANDIDATE_NAMES=["Canazei","Arabba","Moena","Cortina d'Ampezzo","San Martino di Castrozza",
  "Rifugio Antermoia","Rifugio Vajolet","Rifugio Roda di Vael",
  "Rifugio Taramelli","Rifugio Ciampedie","Rifugio Oltradige"]
PROPS={"P1082":"population","P2044":"elevationM","P94":"coatOfArmsFile",
 "P18":"imageFile","P6":"mayorQid","P131":"locatedInQid","P31":"instanceOfQid",
 "P856":"officialWebsite","P1566":"geonamesId","P17":"countryQid",
 "P571":"inception"}
WEATHER=["temperature_2m","relative_humidity_2m","precipitation","snowfall",
 "weather_code","wind_speed_10m"]
def httpjson(url,params,timeout=30):
    req=Request(url+"?"+urlencode(params),headers={"User-Agent":UA,"Accept":"application/json"})
    with urlopen(req,timeout=timeout) as resp:
        return json.loads(resp.read(8_000_000).decode("utf-8"))
def qid(x): return isinstance(x,str) and x.startswith("Q") and x[1:].isdigit()
def pick(places):
    """Deterministic purposive pilot, not statistically representative."""
    picked=[]; seen=set()
    def take(p):
        if p["slug"] not in seen and qid(p.get("wikidata")):
            picked.append(p);seen.add(p["slug"])
    for name in CANDIDATE_NAMES:
        for p in places:
            if p["name"].casefold()==name.casefold():take(p)
    quotas={"borgo":18,"rifugio":14,"bivacco":5}
    for kind, quota in quotas.items():
        current=sum(p["kind"]==kind for p in picked)
        for p in places:
            if current>=quota: break
            if p["kind"]==kind and p["slug"] not in seen and qid(p.get("wikidata")):
                take(p);current+=1
    return picked

def snak_value(sn):
    if sn.get("snaktype")!="value": return None
    x=(sn.get("datavalue") or {}).get("value")
    if isinstance(x,dict):
        if "amount" in x:
            try: return float(x["amount"])
            except (ValueError,TypeError): return None
        if "id" in x:return x["id"]
        if "text" in x:return x["text"]
        if "time" in x:return x["time"]
        return None
    return x if isinstance(x,(str,int,float)) else None

def extract_claims(entity):
    out={}
    claims=entity.get("claims") or {}
    for prop,field in PROPS.items():
        raw=[x for x in claims.get(prop,[]) if x.get("rank")!="deprecated"]
        raw.sort(key=lambda x: 0 if x.get("rank")=="preferred" else 1)
        for statement in raw:
            val=snak_value(statement.get("mainsnak") or {})
            if val is None:continue
            item={"value":val,"source":"wikidata","property":prop,
              "statementId":statement.get("id"),"rank":statement.get("rank")}
            qs=statement.get("qualifiers") or {}
            if qs.get("P585"):item["pointInTime"]=snak_value(qs["P585"][0])
            if qs.get("P580"):item["validFrom"]=snak_value(qs["P580"][0])
            if qs.get("P582"):item["validUntil"]=snak_value(qs["P582"][0])
            out[field]=item
            break
    return out

def selected_entity(entity):
    labels=entity.get("labels") or {}; desc=entity.get("descriptions") or {}
    txt=lambda arr:next((arr[k]["value"] for k in ("it","de","en") if k in arr),None)
    wiki=entity.get("sitelinks") or {}
    return {"label":txt(labels),"shortDescription":txt(desc),
      "wikipediaItTitle":(wiki.get("itwiki") or {}).get("title"),
      "facts":extract_claims(entity)}

def weather_sample(p):
    coord={"latitude":p["lat"],"longitude":p["lng"],"timezone":"Europe/Rome"}
    res={"entity":p["name"],"source":"Open-Meteo","lat":p["lat"],"lon":p["lng"]}
    try:
        fc=httpjson(FORECAST,{**coord,
            "current":",".join(WEATHER),"daily":"temperature_2m_max,temperature_2m_min,precipitation_sum,snowfall_sum,weather_code",
            "forecast_days":5},timeout=45)
        daily=fc.get("daily") or {}
        res["forecast"]={"modelGridElevationM":fc.get("elevation"),
          "units":fc.get("daily_units"),"current":fc.get("current"),
          "currentUnits":fc.get("current_units"),
          "daily":{k:v[:5] if isinstance(v,list) else v for k,v in daily.items()}}
    except Exception as ex:
        res["forecastError"]=str(ex)[:300]
    try:
        ar=httpjson(ARCHIVE,{**coord,"start_date":"2025-01-01","end_date":"2025-12-31",
           "daily":"temperature_2m_mean,precipitation_sum,snowfall_sum","models":"era5_land"},timeout=90)
        days=(ar.get("daily") or {})
        months={}
        for i,date in enumerate(days.get("time",[])):
            month=date[:7]; m=months.setdefault(month,{"nTemperature":0,"sumTemp":0.0,
             "precipMm":0.0,"snowCm":0.0,"daysSnow":0,"nPrecip":0})
            t=(days.get("temperature_2m_mean") or [])[i]
            rain=(days.get("precipitation_sum") or [])[i]
            snow=(days.get("snowfall_sum") or [])[i]
            if isinstance(t,(int,float)):m["sumTemp"]+=t;m["nTemperature"]+=1
            if isinstance(rain,(int,float)):m["precipMm"]+=rain;m["nPrecip"]+=1
            if isinstance(snow,(int,float)):m["snowCm"]+=snow;m["daysSnow"]+=int(snow>0)
        res["historic2025"]={
          "method":"ERA5-Land reanalysis, single year 2025; NOT 30-year climate normals",
          "modelGridElevationM":ar.get("elevation"),
          "units":ar.get("daily_units"),
          "months":[{"month":month,"meanTempC":round(m["sumTemp"]/m["nTemperature"],1) if m["nTemperature"] else None,
             "precipTotalMm":round(m["precipMm"],1),
             "snowfallTotalCm":round(m["snowCm"],1),"daysSnow":m["daysSnow"]} for month,m in sorted(months.items())]
        }
    except Exception as ex:
        res["historyError"]=str(ex)[:300]
    return res

def build_local(p,wd=None):
    return {"id":p["slug"],"type":p["kind"],"name":p["name"],
      "sourceIds":{"osm":p["osmUrl"],"wikidata":p.get("wikidata")},
      "geo":{"lat":p["lat"],"lon":p["lng"]},
      "osmKnown":{k:p[k] for k in ["elevationM","elevationSource","operator","website",
        "capacity","openingHours","phone","email","wikipedia","description"] if p.get(k) is not None},
      "wikidataMetadata":wd,"editorialStatus":"raw_staging_only"}

def main():
    data=json.loads(PLACES.read_text(encoding="utf-8"))["places"]
    sel=pick(data)
    ids=sorted(set(p["wikidata"] for p in sel))
    errs=[]
    entities={}
    try:
        for start in range(0,len(ids),30):
            batch=ids[start:start+30]
            payload=httpjson(WD,{"action":"wbgetentities","ids":"|".join(batch),
              "props":"labels|descriptions|claims|sitelinks","languages":"it|de|en",
              "languagefallback":"1","format":"json"},timeout=65)
            if payload.get("error"):raise RuntimeError(str(payload["error"]))
            entities.update(payload.get("entities",{}))
            time.sleep(.5)
    except Exception as ex:errs.append({"source":"wikidata","error":str(ex)[:300]})
    records=[build_local(p, selected_entity(entities[p["wikidata"]])
        if p["wikidata"] in entities and not entities[p["wikidata"]].get("missing") else None)
        for p in sel]
    fields=Counter(k for r in records for k in ((r["wikidataMetadata"] or {}).get("facts") or {}))
    grouped=Counter(r["type"] for r in records)
    weather=[]
    for name in ["Canazei","Rifugio Antermoia"]:
        found=next((p for p in sel if p["name"]==name and (name!="Canazei" or p.get("wikidata")=="Q258031")),None)
        if found:weather.append(weather_sample(found))
    report={"at":datetime.now(timezone.utc).isoformat(),"sourcePlaces":len(data),
      "pilotPlaces":len(sel),"pilotByType":dict(grouped),
      "wikidataIdsRequested":len(ids),"wikidataRecordsReturned":sum(bool(r["wikidataMetadata"]) for r in records),
      "wikidataFieldsFound":dict(fields),"weather":{"sampled":len(weather),
        "forecastSuccess":sum("forecast" in x for x in weather),
        "historic2025Success":sum("historic2025" in x for x in weather)},
      "errors":errs,"examples":records[:8],
      "note":"Small purposive sample, not national coverage. Population/sindaco may be stale; Wikidata is NOT official ISTAT/DAIT."}
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"localities-huts-wikidata.json").write_text(json.dumps({"records":records},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"weather-sample.json").write_text(json.dumps({"records":weather},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"localities-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="examples"},ensure_ascii=False,indent=2))

if __name__=="__main__":main()
