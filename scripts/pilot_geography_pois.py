#!/usr/bin/env python3
"""Pilot of peaks, water, passes, mountain huts, transport, historical POIs.

Bounded OSM Overpass + local existing Cima Becco places; no shapes or GPX,
distance is geodesic straight line and NEVER claimed hiking distance.
"""
from __future__ import annotations
from collections import Counter
from datetime import datetime, timezone
import json, math, re
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"experiments"/"cross-domain-pilot"
PLACES=ROOT/"public"/"data"/"alpine-places.json"
PEAKS=ROOT/"public"/"data"/"peaks"/"index.json"
BBOX=(46.40,11.67,46.57,11.92) # Val di Fassa / gruppo Catinaccio
SERVERS=["https://overpass-api.de/api/interpreter","https://overpass.kumi.systems/api/interpreter"]
CATEGORIES={
 ("natural","peak"):"summit",("natural","saddle"):"mountain_pass",
 ("natural","spring"):"spring",("natural","water"):"water_body",
 ("tourism","alpine_hut"):"mountain_hut",("tourism","wilderness_hut"):"bivouac",
 ("amenity","shelter"):"shelter",("amenity","drinking_water"):"drinking_water",
 ("tourism","viewpoint"):"viewpoint",("tourism","information"):"information",
 ("historic","memorial"):"historic_memorial",("historic","ruins"):"historic_ruins",
 ("aerialway","station"):"cable_station",
}
def categorise(tags):
    for (key,val),kind in CATEGORIES.items():
        if tags.get(key)==val:return kind
    return "unclassified"
def request():
    bb=",".join(str(n) for n in BBOX)
    filters=['nwr["natural"~"^(peak|saddle|spring|water)$"]',
             'nwr["tourism"~"^(alpine_hut|wilderness_hut|viewpoint|information)$"]',
             'nwr["amenity"~"^(shelter|drinking_water)$"]',
             'nwr["historic"~"^(memorial|ruins)$"]',
             'nwr["aerialway"="station"]']
    q="[out:json][timeout:90];("+ "".join(f+"("+bb+");" for f in filters)+");out center tags;"
    errors=[]
    for server in SERVERS:
        try:
            req=Request(server+"?"+urlencode({"data":q}),headers={
               "User-Agent":"CimaBecco-GeographyResearch/0.1 (https://www.cimabecco.it)",
               "Accept":"application/json"})
            with urlopen(req,timeout=125) as resp:
                payload=json.loads(resp.read(30_000_000).decode("utf-8"))
            if isinstance(payload.get("elements"),list):return payload["elements"],server,errors
            raise ValueError("No OSM elements")
        except Exception as ex:errors.append({"url":server,"error":str(ex)[:200]})
    raise RuntimeError(json.dumps(errors))
def meters(a,b):
    try:return float(str(a).replace(",","."))
    except (ValueError,TypeError):return None
def normalize(e):
    t=e.get("tags") or {}
    center=e if e.get("type")=="node" else e.get("center") or {}
    lat=center.get("lat");lon=center.get("lon")
    if not isinstance(lat,(float,int)) or not isinstance(lon,(float,int)):return None
    kind=categorise(t)
    skip={"source","source:ref","note","fixme"}
    fields={k:v for k,v in t.items() if k in {"ele","name","name:it","name:de","alt_name",
      "wikidata","wikipedia","ref","operator","website","opening_hours","capacity",
      "shelter_type","drinking_water","wheelchair","information","historic","natural",
      "tourism","amenity","aerialway","start_date","inscription"} and k not in skip}
    return {"id":f"osm:{e['type']}:{e['id']}","type":kind,"name":t.get("name"),
      "geo":{"lat":lat,"lon":lon},"elevationM":meters(t.get("ele"),None),
      "facts":fields,"source":{"provider":"openstreetmap","url":f"https://www.openstreetmap.org/{e['type']}/{e['id']}","licence":"ODbL-1.0"},
      "review":{"identityVerified":False,"traversable":None}}
def haversine(a,b):
    p1,p2=math.radians(a[0]),math.radians(b[0])
    dp=p2-p1;dl=math.radians(b[1]-a[1])
    t=math.sin(dp/2)**2+math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return round(2*6371.0088*math.asin(math.sqrt(t)),2)
def top_neighbors(points,places):
    kinds={"summit","mountain_hut","mountain_pass","water_body","spring"}
    targets=[p for p in points if p["type"] in kinds and p.get("name")]
    preview=[]
    for place in places:
        if not (BBOX[0]<=place["lat"]<=BBOX[2] and BBOX[1]<=place["lng"]<=BBOX[3]):continue
        distances=[]
        for t in targets:
            d=haversine((place["lat"],place["lng"]),(t["geo"]["lat"],t["geo"]["lon"]))
            if d<=12:distances.append((d,t))
        distances.sort(key=lambda x:x[0])
        preview.append({"place":place["name"],"placeId":place["slug"],
          "nearby":[{"name":t["name"],"type":t["type"],"sourceId":t["id"],"straightLineKm":d}
            for d,t in distances[:5]]})
    return preview
def main():
    data=json.loads(PLACES.read_text(encoding="utf-8"))["places"]
    peak_index=json.loads(PEAKS.read_text(encoding="utf-8"))
    errors=[];osm_source=None;osms=[]
    try:osms,osm_source,errors=request()
    except Exception as ex:errors.append({"source":"Overpass","error":str(ex)[:300]})
    records=[row for e in osms if (row:=normalize(e)) is not None]
    dedup=list({row["id"]:row for row in records}.values())
    rel=top_neighbors(dedup,data)
    counts=Counter(x["type"] for x in dedup)
    attr=Counter(k for x in dedup for k,v in x["facts"].items() if v)
    report={"generatedAt":datetime.now(timezone.utc).isoformat(),
      "bbox":list(BBOX),"existingAtlasPlaces":len(data),"peakIndexTotalDeclared":peak_index.get("total"),
      "peakIndexCountries":peak_index.get("countries"),"osmProvider":osm_source,
      "osmRecords":len(dedup),"types":dict(counts),"fieldsPresent":dict(attr),
      "existingPlacesInsideBBox":len(rel),
      "placesWithNearbyFeatures":sum(bool(x["nearby"]) for x in rel),
      "note":"Nearest distances are *straight-line* km, not access trails or hiking distance. OSM unverified.",
      "errors":errors,"examples":dedup[:12],"nearestExamples":rel[:5]}
    OUT.mkdir(parents=True,exist_ok=True)
    for name,payload in {
      "mountain-pois.json":{"records":dedup},
      "geographical-relations-preview.json":{"relations":rel},
      "geography-report.json":report}.items():
      (OUT/name).write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k not in ("examples","nearestExamples")},ensure_ascii=False,indent=2))
if __name__=="__main__":main()
