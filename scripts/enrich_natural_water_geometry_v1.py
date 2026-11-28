#!/usr/bin/env python3
"""Source-exact OSM lake/reservoir multipolygons, G1 pilot ONLY.

This is the same natural_feature importer. The original OSM and GeoNames
stages remain independent. An OSM shoreline may attach to a GeoNames lake
ONLY by a one-to-one audited P1566/P625 Wikidata QID + exact OSM wikidata tag
(or an explicit matching ref:geonames), matching water subtype, valid ring
topology and a GeoNames point INSIDE the water surface (not inside an island).

Never infer shore access, potable water, bathing permission, hydrological
depth or official cadastral surface from an OSM mapped outline. A derived
surface has its own ODbL fact, method and uncertainty.
"""
from __future__ import annotations

import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from import_alpine_places import ENDPOINTS
from import_natural_features_v1 import parse_osm

ROOT=Path(__file__).resolve().parents[1]
STAGE=ROOT/"build/import-natural-water-geometry-v1"
CHANNEL="OSM_NATURAL_WATER_GEOMETRIES_STAGING_V1"
GN_CHANNEL="GEONAMES_NATURAL_FEATURES_STAGING_V1"
OSM_CHANNEL="OSM_NATURAL_FEATURES_STAGING_V1"
CROSSWALK_CHANNEL="NATURAL_FEATURES_IDENTITY_STAGING_V1"
OSM_SOURCE="https://www.openstreetmap.org/"
ODBL="ODbL 1.0"
BBOX=(46.28,11.15,46.95,12.95) # same official GN first-batch Dolomites pilot
QID_RE=re.compile(r"^Q[1-9][0-9]*$")
MAX_MEMBERS=150
MAX_VERTICES=1800
MAX_BODY_BYTES=17_000_000
MAX_OSM_REQUESTED=90
MAX_QID_REQUESTED=35
MIN_AREA_KM2=0.00001
MAX_AREA_KM2=350.0


def query_for_water_ids(osm_ids, qids, bbox=BBOX):
    """Bounded targeted identifiers, NOT a generic water=* mass download."""
    south,west,north,east=bbox
    if not (35<=south<north<=48 and 6<=west<east<=20):
        raise ValueError("Out-of-bounds natural water source request")
    if len(osm_ids)>MAX_OSM_REQUESTED or len(qids)>MAX_QID_REQUESTED:
        raise ValueError("Water geometry pilot must be bounded")
    by_type={"way":set(),"relation":set()}
    for value in osm_ids:
        match=re.fullmatch(r"(way|relation)/([1-9][0-9]*)",str(value))
        if not match:
            raise ValueError("Only exact OSM way/relation IDs may be requested")
        by_type[match[1]].add(int(match[2]))
    for qid in qids:
        if not QID_RE.fullmatch(qid):
            raise ValueError("Unverified Wikidata item in water geometry query")
    selectors=[]
    for typ,ids in by_type.items():
        if ids:
            selectors.append(f'{typ}(id:{",".join(map(str,sorted(ids)))});')
    if qids:
        # Only WD IDs that have an already audited GeoNames P1566/P625 link.
        # Use explicit lake/reservoir typing AND strict bounding box.
        qexpr="^("+("|".join(re.escape(q) for q in sorted(set(qids))))+")$"
        bounds=f'({south},{west},{north},{east})'
        for typ in ("way","relation"):
            selectors.append(f'{typ}["natural"="water"]["water"~"^(lake|reservoir)$"]'
                             f'["wikidata"~"{qexpr}"]{bounds};')
    if not selectors:
        raise ValueError("No audited OSM identities or WD QIDs to request")
    return "[out:json][timeout:65];("+"".join(selectors)+");out body geom;"


def fetch_overpass(query, endpoints=ENDPOINTS, timeout=82):
    last=None
    for endpoint in endpoints:
        try:
            request=Request(endpoint,data=urlencode({"data":query}).encode("utf-8"),
                headers={"User-Agent":"CimaBecco/1.0 (https://github.com/MatteoCurro/cima-becco)",
                    "Content-Type":"application/x-www-form-urlencoded"})
            with urlopen(request,timeout=timeout) as response:
                raw=response.read(MAX_BODY_BYTES+1)
            if len(raw)>MAX_BODY_BYTES:
                raise ValueError("OSM water geometry response exceeds 17MB bound")
            doc=json.loads(raw)
            if doc.get("remark"):
                raise ValueError("Overpass incomplete/timeout: "+str(doc["remark"])[:150])
            if not isinstance(doc.get("elements"),list):
                raise ValueError("Overpass geometry response missing elements")
            return doc
        except Exception as err:
            print("OSM geometry endpoint unavailable:",endpoint,str(err)[:160],flush=True)
            last=err
    raise RuntimeError("No bounded OSM geometry endpoint succeeded: "+str(last))


def pt(raw):
    if not isinstance(raw,dict):
        raise ValueError("OSM geometry point is not an object")
    lat,lng=raw.get("lat"),raw.get("lon")
    if (type(lat) not in (int,float) or type(lng) not in (int,float)
        or not math.isfinite(lat) or not math.isfinite(lng)
        or not(35<=lat<=48 and 6<=lng<=20)):
        raise ValueError("Invalid coordinates on OSM water boundary")
    return [round(float(lng),7),round(float(lat),7)]


def ring_area_km2(points):
    """Equirectangular local projection at latitude mean; estimate, not survey."""
    lat0=sum(p[1] for p in points[:-1])/max(1,len(points)-1)
    sx=111.195*math.cos(math.radians(lat0))
    sy=111.195
    return abs(sum((a[0]*sx)*(b[1]*sy)-(b[0]*sx)*(a[1]*sy)
        for a,b in zip(points,points[1:])))/2


def crossing(a,b,c,d):
    """Exact segment topology on 7-decimal OSM WGS84 grid.

    The prior float epsilon treated close but disjoint shores as intersecting,
    wrongly holding valid Lago di Fedaia/Landro polygons. Python integers
    preserve the source's quantized coordinates without near-miss guesses.
    """
    a,b,c,d=[(int(round(p[0]*10_000_000)),
              int(round(p[1]*10_000_000))) for p in (a,b,c,d)]
    def orient(p,q,r):
        return ((q[0]-p[0])*(r[1]-p[1])
                -(q[1]-p[1])*(r[0]-p[0]))
    def on_segment(p,q,r):
        return (min(p[0],r[0])<=q[0]<=max(p[0],r[0])
            and min(p[1],r[1])<=q[1]<=max(p[1],r[1]))
    o1,o2,o3,o4=orient(a,b,c),orient(a,b,d),orient(c,d,a),orient(c,d,b)
    if o1==0 and on_segment(a,c,b):return True
    if o2==0 and on_segment(a,d,b):return True
    if o3==0 and on_segment(c,a,d):return True
    if o4==0 and on_segment(c,b,d):return True
    return (o1>0)!=(o2>0) and (o3>0)!=(o4>0)

def valid_ring(points):
    if not (4<=len(points)<=MAX_VERTICES+1) or points[0]!=points[-1]:
        raise ValueError("Unclosed or oversized shoreline ring")
    if len(set(map(tuple,points[:-1])))!=len(points)-1:
        raise ValueError("Shoreline ring repeats vertices")
    if ring_area_km2(points)<MIN_AREA_KM2:
        raise ValueError("Shoreline ring has degenerate mapped area")
    # A broken topology cannot be asserted to be an exact lake outline.
    n=len(points)-1
    for i in range(n):
        for j in range(i+2,n):
            if i==0 and j==n-1:continue
            if crossing(points[i],points[i+1],points[j],points[j+1]):
                raise ValueError("Self-intersecting shoreline ring")
    return points


def segments_to_rings(segments):
    remaining=[list(s) for s in segments]
    rings=[]
    while remaining:
        ring=remaining.pop(0)
        while ring[0]!=ring[-1]:
            matches=[]
            for i,part in enumerate(remaining):
                if part[0]==ring[-1]:
                    matches.append((i,part[1:]))
                if part[-1]==ring[-1]:
                    matches.append((i,list(reversed(part[:-1]))))
            if len(matches)!=1:
                raise ValueError("Gapped or branching OSM multipolygon ring")
            i,tail=matches[0]
            remaining.pop(i)
            ring.extend(tail)
            if len(ring)>MAX_VERTICES+1:
                raise ValueError("Multipolygon outer ring too large")
        rings.append(valid_ring(ring))
    return rings


def inside_ring(point,ring):
    """Strict interior (boundary does not establish a lake's centre)."""
    x,y=point
    inside=False
    for (ax,ay),(bx,by) in zip(ring,ring[1:]):
        if (min(ay,by)<=y<=max(ay,by) and min(ax,bx)<=x<=max(ax,bx)
            and abs((bx-ax)*(y-ay)-(by-ay)*(x-ax))<1e-11):
            return False
        if (ay>y)!=(by>y):
            xx=ax+(y-ay)*(bx-ax)/(by-ay)
            if xx>x:inside=not inside
    return inside


def extract_polygon(row):
    typ=row.get("type")
    tags=row.get("tags") or {}
    if tags.get("natural")!="water" or tags.get("water") not in ("lake","reservoir"):
        raise ValueError("Feature has no explicit lake/reservoir OSM type")
    if typ=="way":
        ring=valid_ring([pt(x) for x in row.get("geometry",[])])
        groups=[[ring]]
    elif typ=="relation":
        if tags.get("type")!="multipolygon":
            raise ValueError("Water relation is not a multipolygon")
        members=row.get("members") or []
        if len(members)>MAX_MEMBERS:
            raise ValueError("Oversized water relation requires GIS/manual inspection")
        outer=[];inner=[]
        for m in members:
            if m.get("type")!="way" or m.get("role") not in ("outer","inner"):
                raise ValueError("Unexpected nested member or role in water relation")
            geom=[pt(x) for x in m.get("geometry",[])]
            if len(geom)<2:
                raise ValueError("Missing full member way geometry")
            (outer if m["role"]=="outer" else inner).append(geom)
        if not outer:
            raise ValueError("Water multipolygon has no outer shoreline")
        groups=[[ring] for ring in segments_to_rings(outer)]
        for hole in segments_to_rings(inner):
            candidates=[group for group in groups if inside_ring(hole[0],group[0])]
            if len(candidates)!=1:
                raise ValueError("Island cannot be assigned unambiguously to water polygon")
            candidates[0].append(hole)
    else:
        raise ValueError("Water outline requires OSM way or relation")
    area=sum(ring_area_km2(g[0])-sum(ring_area_km2(x) for x in g[1:]) for g in groups)
    if not MIN_AREA_KM2<area<MAX_AREA_KM2:
        raise ValueError("Implausible water surface area from OSM shoreline")
    # Inner rings must lie in their outer and remove a smaller surface.
    for g in groups:
        outer=ring_area_km2(g[0])
        if outer<=sum(ring_area_km2(x) for x in g[1:]):
            raise ValueError("Islands exceed available water surface")
    return {"type":"MultiPolygon","coordinates":groups},round(area,6)


def point_inside_polygon(point,polygon):
    for rings in polygon["coordinates"]:
        if inside_ring(point,rings[0]) and not any(
            inside_ring(point,hole) for hole in rings[1:]):
            return True
    return False


def inspect_source(osm,gn,cross):
    for doc,channel in ((osm,OSM_CHANNEL),(gn,GN_CHANNEL),(cross,CROSSWALK_CHANNEL)):
        if doc.get("releaseChannel")!=channel or doc.get("isPublished") is not False:
            raise ValueError("Natural water requires G0/G1 source staging only: "+channel)
    if not isinstance(osm.get("entities"),list) or not isinstance(gn.get("entities"),list):
        raise ValueError("No typed OSM/GeoNames source records")
    if not isinstance(cross.get("links"),list):
        raise ValueError("No audited GeoNames-Wikidata crosswalk")
    osms=[e for e in osm["entities"] if e.get("kind")=="natural_feature"
          and e.get("subtype") in ("lake","reservoir")
          and not e.get("quality",{}).get("slugRequiresReview")]
    links=[x for x in cross["links"]
           if x.get("subtype") in ("lake","reservoir") and
           x.get("wikidataIdentityVerified") is True and
           x.get("identityMethod")=="exact_P1566_P625_one_to_one" and
           QID_RE.fullmatch(str(x.get("qid") or "")) and
           x.get("wikidataUrl")=="https://www.wikidata.org/wiki/"+x["qid"] and
           type(x.get("coordinateDistanceKm")) in (int,float) and
           type(x.get("coordinateGateKm")) in (int,float) and
           0<=x["coordinateDistanceKm"]<=x["coordinateGateKm"]<=2.0]
    if len(links)!=len([x for x in cross["links"] if x.get("subtype") in ("lake","reservoir")]):
        raise ValueError("Water source contains unaudited GeoNames/Wikidata identity")
    if len({str(x["geonameid"]) for x in links})!=len(links):
        raise ValueError("Duplicate water GeoNames ID in crosswalk")
    geom_ids=[e["sourceIds"]["osm"] for e in osms
              if re.fullmatch(r"(?:way|relation)/[1-9]\d*",e["sourceIds"].get("osm",""))]
    return osms,links,geom_ids


def run(osm,gn,cross,rows,*,query=None,at=None):
    osms,links,ids=inspect_source(osm,gn,cross)
    if not isinstance(rows,list) or len(rows)>400:
        raise ValueError("Unexpectedly large water geometry response")
    at=at or datetime.now(timezone.utc).isoformat()
    snap=sha256(json.dumps(rows,sort_keys=True,ensure_ascii=False,
                       separators=(",",":")).encode()).hexdigest()
    prior_osm={e["sourceIds"]["osm"]:e for e in osms}
    gn_by_id={e["sourceIds"]["geonames"]:e for e in gn["entities"]
              if e.get("kind")=="natural_feature" and
              e.get("subtype") in ("lake","reservoir")}
    audited={x["qid"]:x for x in links}
    if len(audited)!=len(links):
        raise ValueError("Duplicate crosswalk QID in a natural water pilot")
    processed={}
    held=Counter()
    diagnostics=[]
    for row in rows:
        typ,idx=row.get("type"),row.get("id")
        if typ not in ("way","relation") or type(idx)!=int or idx<=0:
            held["no_polygon_element"]+=1
            continue
        osm_id=f"{typ}/{idx}"
        if osm_id in processed:
            raise ValueError("Duplicate exact OSM geometry ID in Overpass response")
        tags=row.get("tags") or {}
        try:
            polygon,area=extract_polygon(row)
        except (KeyError,TypeError,ValueError) as err:
            held["invalid_water_geometry"]+=1
            diagnostics.append({"osm":osm_id,"reason":str(err)[:150]})
            continue
        if osm_id not in ids:
            qid=tags.get("wikidata")
            if qid not in audited:
                held["not_in_exact_source_request"]+=1
                continue
        if tags.get("intermittent")=="yes":
            # Exposed shoreline is still a mapped body, but no water
            # availability or swimming suitability is asserted.
            held["intermittent_water_requires_context"]+=1
        source=f"{OSM_SOURCE}{osm_id}"
        osm_e=deepcopy(prior_osm.get(osm_id))
        if osm_e is not None and osm_e["subtype"]!=tags["water"]:
            held["source_subtype_changed"]+=1
            diagnostics.append({"osm":osm_id,"reason":"OSM lake/reservoir type changed since original G1 snapshot"})
            continue
        if osm_e is None:
            # A requested P1566/P625 QID may have matching OSM geometry even
            # if outside the original bounded 250-entity OSM stage sample.
            outer=polygon["coordinates"][0][0]
            center={"lat":round(sum(p[1] for p in outer[:-1])/(len(outer)-1),6),
                    "lon":round(sum(p[0] for p in outer[:-1])/(len(outer)-1),6)}
            osm_e=parse_osm({**row,"center":center},at)
        if osm_e is not None:
            osm_e["geo"]["area"]=polygon
            osm_e["geo"]["areaSourceUrl"]=source
            osm_e["geo"]["areaMethod"]="osm_out_geom_multipolygon"
            osm_e["quality"]["perimeterNotVerified"]=False
            osm_e["quality"]["geometryTopologyVerified"]=True
            osm_e["quality"]["gate"]="G1"
            osm_e["quality"]["seoIndexable"]=False
            osm_e["facts"]["osmMappedWaterSurfaceKm2"]={
                "value":area,"unit":"km2","sourceId":"osm:"+osm_id+":geometry",
                "sourceUrl":source,"licence":ODBL,"retrievedAt":at,
                "sourceUpdatedAt":row.get("timestamp"),
                "validFrom":None,"validUntil":None,"method":"derived",
                "confidence":0.65,
                "notes":"Area calcolata dal perimetro OSM mappato, non superficie catastale o ufficiale"
            }
        processed[osm_id]={"osmId":osm_id,"name":tags.get("name"),
            "subtype":tags["water"],"wikidataCandidate":tags.get("wikidata"),
            "geonamesCandidate":tags.get("ref:geonames") or tags.get("geonames"),
            "sourceUrl":source,"sourceUpdatedAt":row.get("timestamp"),
            "polygon":polygon,"surfaceKm2":area,"osmEntity":osm_e}
    # A QID from an OSM tag is NOT an identity in itself. Cross-reference
    # with the independent P1566/P625 GeoNames audit AND verify the GN source
    # point belongs to the exact OSM water geometry, including island holes.
    by_qid=defaultdict(list)
    by_gn=defaultdict(list)
    for item in processed.values():
        qid=item.get("wikidataCandidate")
        if qid and QID_RE.fullmatch(str(qid)):
            by_qid[qid].append(item)
        rid=item.get("geonamesCandidate")
        if re.fullmatch(r"[1-9]\d*",str(rid or "")):
            by_gn[str(rid)].append(item)
    verified_gn=[]
    used_osm=set()
    for qid,link in sorted(audited.items()):
        gid=str(link["geonameid"])
        base=gn_by_id.get(gid)
        if not base or base.get("quality",{}).get("gate")!="G1" or base["quality"].get("slugRequiresReview"):
            held["geonames_source_not_G1"]+=1;continue
        candidates={x["osmId"]:x for x in by_qid.get(qid,[])}
        for x in by_gn.get(gid,[]):
            if x.get("wikidataCandidate") not in (None,qid):
                held["conflicting_osm_qid_and_geonames_id"]+=1
                continue
            candidates[x["osmId"]]=x
        if len(candidates)!=1:
            held["no_unique_exact_osm_identifier"]+=1;continue
        item=next(iter(candidates.values()))
        if item["subtype"]!=base["subtype"]:
            held["water_subtype_conflict"]+=1
            diagnostics.append({"geonames":gid,"osm":item["osmId"],
                                "reason":"OSM lake/reservoir subtype differs from GeoNames"})
            continue
        p=base["geo"]["point"]
        if not point_inside_polygon([p["lng"],p["lat"]],item["polygon"]):
            held["geonames_point_outside_water_polygon"]+=1
            diagnostics.append({"geonames":gid,"osm":item["osmId"],
                                "reason":"GN reported coordinate is not inside mapped OSM water surface"})
            continue
        source=item["sourceUrl"]
        e=deepcopy(base)
        e["geo"]["area"]=item["polygon"]
        e["geo"]["areaSourceUrl"]=source
        e["geo"]["areaMethod"]="osm_out_geom_multipolygon"
        e["sourceIds"]["wikidata"]=qid
        e["sourceIds"]["wikidataVerifiedBy"]="P1566+P625"
        e["sourceIds"]["osm"]=item["osmId"]
        e["sourceIds"]["osmVerifiedBy"]="P1566_P625_and_exact_OSM_QID_or_GeoNames_ID"
        e["facts"]["osmMappedWaterSurfaceKm2"]={
            "value":item["surfaceKm2"],"unit":"km2",
            "sourceId":"osm:"+item["osmId"]+":geometry","sourceUrl":source,
            "licence":ODBL,"retrievedAt":at,"sourceUpdatedAt":item["sourceUpdatedAt"],
            "validFrom":None,"validUntil":None,"method":"derived","confidence":0.65,
            "notes":"Superficie derivata dal contorno OSM, non misura ufficiale del lago"
        }
        e["quality"].update({"areaNotVerified":False,
             "geometryTopologyVerified":True,"identityMethod":"exact_GeoNames_P1566_P625_OSM_Tag",
             "seoIndexable":False,"gate":"G1",
             "needsTextAndMediaG2":True,"reviewRequired":False})
        verified_gn.append(e)
        used_osm.add(item["osmId"])
    osm_result=[x["osmEntity"] for x in processed.values() if x["osmEntity"] is not None]
    ids_seen=[x["sourceIds"]["osm"] for x in osm_result]
    if len(ids_seen)!=len(set(ids_seen)):
        raise ValueError("Duplicate OSM water entity in staging")
    if len(verified_gn)!=len({x["sourceIds"]["geonames"] for x in verified_gn}):
        raise ValueError("Duplicate identified GeoNames lake")
    result={
        "schemaVersion":"1.0","releaseChannel":CHANNEL,"isPublished":False,
        "generatedAt":at,"sourceSha256":snap,"query":query or "offline_fixture",
        "osmEntities":sorted(osm_result,key=lambda e:e["sourceIds"]["osm"]),
        "geonamesLinkedEntities":sorted(verified_gn,key=lambda e:e["sourceIds"]["geonames"]),
        "diagnosticReviews":diagnostics[:120],
    }
    report={"source":"OSM / Overpass out geom","licence":ODBL,
        "osmPilotCandidates":len(osms),"geonamesQidCandidates":len(links),
        "rawPolygonElements":len(rows),"polygonVerified":len(processed),
        "osmWaterProfiles":len(osm_result),"geonamesIdentityAndAreaVerified":len(verified_gn),
        "waterSubtypeCounts":dict(Counter(x["subtype"] for x in processed.values())),
        "rejectedOrReview":dict(sorted(held.items())),
        "staged":len(osm_result)+len(verified_gn),
        "sourceSha256":snap,"published":0,"seoIndexable":0,
        "uniquePerimeters":len(set(processed)),
        "noSpringOrPotabilityImports":True}
    return result,report


def write(path,obj):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(obj,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--osm-stage",type=Path,required=True)
    p.add_argument("--geonames-stage",type=Path,required=True)
    p.add_argument("--crosswalk",type=Path,required=True)
    p.add_argument("--out",type=Path,default=STAGE)
    p.add_argument("--raw-file",type=Path,
                   help="Replay immutable audited out geom snapshot, without Overpass")
    p.add_argument("--max-osm-ids",type=int,default=65)
    p.add_argument("--max-qids",type=int,default=20)
    args=p.parse_args()
    if not 1<=args.max_osm_ids<=MAX_OSM_REQUESTED or not 1<=args.max_qids<=MAX_QID_REQUESTED:
        p.error("The pilot must remain bounded")
    osm=json.loads(args.osm_stage.read_text(encoding="utf-8"))
    gn=json.loads(args.geonames_stage.read_text(encoding="utf-8"))
    cross=json.loads(args.crosswalk.read_text(encoding="utf-8"))
    osms,links,ids=inspect_source(osm,gn,cross)
    geom_ids=sorted(ids)[:args.max_osm_ids]
    qids=sorted({l["qid"] for l in links})[:args.max_qids]
    query=query_for_water_ids(geom_ids,qids)
    raw=json.loads(args.raw_file.read_text(encoding="utf-8")) if args.raw_file else fetch_overpass(query)
    if not isinstance(raw.get("elements"),list):
        raise ValueError("No complete, audited Overpass water geometry response")
    result,report=run(osm,gn,cross,raw["elements"],query=query)
    path=args.out
    write(path/"raw/water-geometry-response.json",{
        "capturedAt":result["generatedAt"],
        "source":"OpenStreetMap Overpass","licence":ODBL,
        "sha256":result["sourceSha256"],"query":query,
        "elements":raw["elements"]})
    write(path/"water-geometry-staging.json",result)
    write(path/"water-geometry-report.json",report)
    if report["polygonVerified"]<3:
        raise RuntimeError("Real OSM water geometry pilot has insufficient verified polygons")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
