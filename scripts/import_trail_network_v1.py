#!/usr/bin/env python3
"""Cima Becco | network G0: OSM physical ways, true node IDs and route memberships.

FIRST PILOT, NEVER A REPLACEMENT FOR public/data/routes-tiles/*.json.
A route relation describes a network itinerary, NOT a physical traversable edge.
The topology is built ONLY from identical OSM node IDs in source ways;
coordinates and proximity do NOT create graph joins.

Reference: docs/MODELLO_METADATI_E_LAYOUT.md §8.
© OpenStreetMap contributors, ODbL 1.0.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from import_osm_routes import haversine  # reuse current distance utility

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"build/trail-network-g0-pilot"
CHANNEL="OSM_TRAIL_PHYSICAL_GRAPH_G0_STAGING_V1"
BBOX=(46.59,12.16,46.68,12.29)  # small, bounded Dolomites pilot
ENDPOINTS=("https://overpass.private.coffee/api/interpreter",
           "https://ovp.dresel.systems/api/interpreter")
HIGHWAYS={"path","footway","track","steps","via_ferrata"}
ROUTES={"foot","hiking","via_ferrata","ferrata"}
TECHNICAL={"yes","designated","official","1","true"}
NO_ACCESS={"no","private"}
ID=re.compile(r"^[1-9][0-9]*$")
MAX_WAY_NODES=2500

def validate_bbox(bbox):
    s,w,n,e=bbox
    if not(35<=s<n<=48 and 6<=w<e<=20):
        raise ValueError("BBOX outside bounded Italian alpine analysis region")
    if n-s>0.25 or e-w>0.25:
        raise ValueError("BBOX too wide for a source-only physical-network pilot")

def query_for_bbox(bbox):
    validate_bbox(bbox)
    s,w,n,e=bbox
    area=f"({s},{w},{n},{e})"
    # Geometry is requested only for the physical ways in the bounded box.
    # Route relations can extend far beyond the box: fetch metadata/member IDs
    # WITHOUT requesting every distant member geometry. Missing source members
    # are then explicitly reported as partial; never filled in by proximity.
    return ("[out:json][timeout:65];("
       f'way["highway"~"^(path|footway|track|steps|via_ferrata)$"]{area};'
       f'way["via_ferrata"]{area};'
       f'way["via_ferrata_scale"]{area};'
       ");out meta geom;"
       f'relation["type"="route"]["route"~"^(foot|hiking|via_ferrata|ferrata)$"]{area};'
       "out meta;")

def fetch_osm(bbox,*,endpoints=ENDPOINTS,retries=1):
    query=query_for_bbox(bbox)
    failures=[]
    for endpoint in endpoints:
        for attempt in range(retries):
            try:
                req=Request(endpoint,data=urlencode({"data":query}).encode(),
                    headers={"User-Agent":"CimaBecco-trail-network-pilot/1.0 (https://www.cimabecco.it)",
                             "Content-Type":"application/x-www-form-urlencoded",
                             "Accept":"application/json"})
                with urlopen(req,timeout=125) as response:
                    data=json.load(response)
                if not isinstance(data,dict) or not isinstance(data.get("elements"),list) or data.get("remark"):
                    raise ValueError("Overpass response invalid, truncated or rate limited")
                return data
            except (HTTPError,URLError,TimeoutError,ValueError,OSError) as exc:
                failures.append(f"{endpoint} attempt {attempt+1}: {str(exc)[:100]}")
                if attempt+1<retries: time.sleep(4*(attempt+1))
    raise RuntimeError("No source-verified pilot data returned by Overpass: "+"; ".join(failures))

def _way_points(row):
    ids=row.get("nodes")
    geometry=row.get("geometry")
    if (not isinstance(ids,list) or not isinstance(geometry,list) or
        not 2<=len(ids)==len(geometry)<=MAX_WAY_NODES):
        return None
    points=[]
    for node,p in zip(ids,geometry):
        if (type(node) is not int or node<=0 or not isinstance(p,dict) or
            type(p.get("lat")) not in (int,float) or type(p.get("lon")) not in (int,float)):
            return None
        lng,lat=p["lon"],p["lat"]
        if not math.isfinite(lng) or not math.isfinite(lat) or not 6<=lng<=20 or not 35<=lat<=48:
            return None
        points.append([round(lng,7),round(lat,7)])
    # Reject zero-length source sections, not change node IDs or join endpoints.
    if not any(a!=b for a,b in zip(points,points[1:])):
        return None
    return ids,points

def _is_ferrata(tags):
    return (tags.get("highway")=="via_ferrata" or
            str(tags.get("via_ferrata","")).strip().lower() in TECHNICAL or
            bool(str(tags.get("via_ferrata_scale","")).strip()))

def _report_access(tags):
    return {k:tags[k] for k in ("access","foot","oneway","seasonal","opening_hours",
       "trail_visibility","surface","smoothness","sac_scale","via_ferrata_scale",
       "via_ferrata","highway","ref","name","operator","osmc:symbol","bridge","tunnel")
            if isinstance(tags.get(k),str) and tags[k].strip()}

def parse_way(row):
    ident=row.get("id")
    tags=row.get("tags") or {}
    if row.get("type")!="way" or type(ident) is not int or ident<=0 or not isinstance(tags,dict):
        return None
    highway=tags.get("highway")
    # An explicit non-walking road class must not be converted into a
    # mountain trail even when it carries a stray ferrata-related tag.
    if highway is not None and highway not in HIGHWAYS:
        return None
    if highway not in HIGHWAYS and not _is_ferrata(tags):
        return None
    geometry=_way_points(row)
    if geometry is None:return None
    ids,points=geometry
    # Retain the complete publicly mapped OSM tag set in isolated G0 staging.
    # A selected subset alone would discard source-specific evidence needed for
    # future CAI/SAT reconciliation and could not support a full source audit.
    raw_tags={k:v for k,v in tags.items() if isinstance(k,str) and isinstance(v,str)}
    return {"osmWayId":ident,"nodeIds":ids,"coordinates":points,
            "tags":raw_tags,"operationalTags":_report_access(tags),
            "sourceUpdatedAt":row.get("timestamp") if isinstance(row.get("timestamp"),str) else None}

def parse_relation(row):
    tags=row.get("tags") or {}
    ident=row.get("id")
    if (row.get("type")!="relation" or type(ident) is not int or ident<=0 or
        not isinstance(tags,dict) or tags.get("type")!="route" or
        tags.get("route") not in ROUTES):
        return None
    members=row.get("members")
    if not isinstance(members,list):return None
    # OSM member order and role are evidence; never stitch missing sections.
    ways=[]
    for m in members:
        if not isinstance(m,dict):continue
        if m.get("type")=="way" and type(m.get("ref")) is int and m["ref"]>0:
            ways.append({"osmWayId":m["ref"],"role":m.get("role","") if isinstance(m.get("role"),str) else ""})
    if not ways:return None
    return {"osmRelationId":ident,"routeType":tags["route"],
            "ref":tags.get("ref") or None,
            "name":tags.get("name:it") or tags.get("name") or None,
            "network":tags.get("network") or None,
            "operator":tags.get("operator") or None,
            "osmcSymbol":tags.get("osmc:symbol") or None,
            "members":ways,
            "sourceUpdatedAt":row.get("timestamp") if isinstance(row.get("timestamp"),str) else None}

def _components(edges):
    # Components are based on shared OSM nodes ONLY; not map coordinates.
    parent={}
    def find(x):
        parent.setdefault(x,x)
        if parent[x]!=x:parent[x]=find(parent[x])
        return parent[x]
    for edge in edges:
        nodes=edge["osmNodeIds"]
        for node in nodes[1:]:
            parent[find(node)]=find(nodes[0])
    return len({find(n) for n in parent})

def build_graph(source,bbox=BBOX,*,at="2026-11-28T00:00:00+00:00",max_ways=1400):
    validate_bbox(bbox)
    if not isinstance(source,dict) or not isinstance(source.get("elements"),list) or source.get("remark"):
        raise ValueError("Full Overpass elements array required; fail closed")
    if not 1<=max_ways<=10000:raise ValueError("Unsafe max_ways bound")
    rows=source["elements"];ways={};relations={};held=Counter()
    for raw in rows:
        if raw.get("type")=="way":
            w=parse_way(raw)
            if not w:
                held["way_not_usable_or_missing_nodes"]+=1
                continue
            ident=w["osmWayId"]
            if ident in ways and ways[ident]!=w:
                raise ValueError("Conflicting OSM way versions in one input")
            ways[ident]=w
        elif raw.get("type")=="relation":
            r=parse_relation(raw)
            if not r:
                held["relation_not_a_supported_route"]+=1
                continue
            ident=r["osmRelationId"]
            if ident in relations and relations[ident]!=r:
                raise ValueError("Conflicting OSM route relation versions")
            relations[ident]=r
    if not ways:raise ValueError("No source way with exact nodes and complete geometry")
    if len(ways)>max_ways:raise ValueError("Pilot limit exceeded: never truncate source ways")
    # Same OSM node ID must never carry conflicting coordinates.
    coords_by_id={}
    node_to_ways=defaultdict(set)
    for w in ways.values():
        for node,p in zip(w["nodeIds"],w["coordinates"]):
            prev=coords_by_id.setdefault(node,p)
            if prev!=p:raise ValueError("A single OSM node has conflicting geometry")
            node_to_ways[node].add(w["osmWayId"])
    relation_of_way=defaultdict(list)
    for r in relations.values():
        for m in r["members"]:
            if m["osmWayId"] in ways:
                relation_of_way[m["osmWayId"]].append(r["osmRelationId"])

    # Split at true shared OSM node IDs, NEVER if two lines merely cross or
    # endpoints happen to be 12m apart. Original interior vertices are retained.
    segments=[]
    for ident,w in sorted(ways.items()):
        ids,geo=w["nodeIds"],w["coordinates"]
        repeats=Counter(ids)
        breakpoints=[i for i,node in enumerate(ids) if
           i in (0,len(ids)-1) or len(node_to_ways[node])>1 or repeats[node]>1]
        for start,end in zip(breakpoints,breakpoints[1:]):
            if start==end:continue
            pts=geo[start:end+1];nd=ids[start:end+1]
            length=sum(haversine(a,b) for a,b in zip(pts,pts[1:]))
            if length<=0:
                held["zero_length_subspan"]+=1
                continue
            tags=w["tags"]
            explicit=_is_ferrata(tags)
            candidates=[r for r in relation_of_way[ident] if relations[r]["routeType"] in ("via_ferrata","ferrata")]
            segments.append({
                "id":f"osm:way/{ident}:span/{start}-{end}",
                "kind":"physical_trail_segment",
                "subtype":"ferrata" if explicit else "trail",
                "classificationEvidence":"explicit_way_tag" if explicit else
                    ("route_member_candidate_only" if candidates else "unclassified_footpath"),
                "ferrataRelationCandidateOnly":not explicit and bool(candidates),
                "sourceIds":{"osmWay":f"way/{ident}",
                    "osmNodeStart":nd[0],"osmNodeEnd":nd[-1]},
                "osmNodeIds":nd,
                "geometry":{"type":"LineString","coordinates":pts},
                "lengthM":{"value":round(length,1),"unit":"m","method":"derived",
                    "sourceId":f"osm:way/{ident}:geometry",
                    "sourceUrl":f"https://www.openstreetmap.org/way/{ident}",
                    "licence":"ODbL 1.0"},
                "routeRelationIds":sorted(set(relation_of_way[ident])),
                "sourceTags":tags,
                "operationalTags":w["operationalTags"],
                "accessStatus":"restriction_reported" if any(
                    tags.get(x) in NO_ACCESS for x in ("access","foot")) else "not_verified",
                "sourceUpdatedAt":w["sourceUpdatedAt"],
                "quality":{"gate":"G0","seoIndexable":False,
                    "topologyMethod":"exact_OSM_node_id",
                    "safetyVerified":False,"traversableVerified":False},
            })
    if not segments:raise ValueError("No physically meaningful source segments")

    rel_out=[]
    for r in sorted(relations.values(),key=lambda x:x["osmRelationId"]):
        members=[x["osmWayId"] for x in r["members"]]
        missing=sorted(set(members)-set(ways))
        member_way_ids=set(members)&set(ways)
        edges=[s for s in segments if
               int(s["sourceIds"]["osmWay"].split("/")[1]) in member_way_ids]
        # "Connected" only describes mapped topology; it does not certify
        # safety, completeness of the route on the ground or official status.
        connected=_components(edges)
        rel_out.append({
            **r,"sourceUrl":f"https://www.openstreetmap.org/relation/{r['osmRelationId']}",
            "mappedMemberWays":len(set(members)&set(ways)),
            "missingMemberWayIds":missing,
            "sourceCoverage":"partial" if missing else "all_members_with_way_geometries",
            "topologyComponentCount":connected,
            "topologyContinuousInMappedWays":not missing and connected==1,
            "canonicalItinerary":False,
            "quality":{"gate":"G0","seoIndexable":False,
                       "routeOperationallyVerified":False},
        })
    output={
        "schemaVersion":"1.0","releaseChannel":CHANNEL,"isPublished":False,
        "seoIndexable":False,"routeCatalogueModified":False,"source":"OpenStreetMap",
        "licence":"ODbL 1.0","retrievedAt":at,
        "sourceSnapshotSha256":sha256(json.dumps(source,ensure_ascii=False,sort_keys=True,
            separators=(",",":")).encode()).hexdigest(),
        "bbox":[*bbox],
        "counts":{"sourceElements":len(rows),"waysAccepted":len(ways),
            "graphNodes":len(coords_by_id),"graphSegments":len(segments),
            "junctionNodes":sum(1 for x in node_to_ways.values() if len(x)>1),
            "ferrataSegmentsExplicit":sum(x["subtype"]=="ferrata" for x in segments),
            "ferrataSegmentsCandidateOnly":sum(x["ferrataRelationCandidateOnly"] for x in segments),
            "routeRelations":len(rel_out),
            "relationsPartial":sum(bool(r["missingMemberWayIds"]) for r in rel_out),
            "relationsDisconnected":sum(r["topologyComponentCount"]>1 for r in rel_out),
            "dropped":dict(sorted(held.items()))},
        "segments":segments,"routeRelations":rel_out,
    }
    # G0: this dataset is NOT complete national coverage, a routing service,
    # a claim of an official CAI trail or a G2 route.
    return output

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--input",type=Path,help="Original Overpass out body geom JSON; offline")
    p.add_argument("--bbox",nargs=4,type=float,default=BBOX)
    p.add_argument("--out",type=Path,default=OUT)
    p.add_argument("--max-ways",type=int,default=1400)
    args=p.parse_args()
    src=json.loads(args.input.read_text(encoding="utf-8")) if args.input else fetch_osm(args.bbox)
    now=datetime.now(timezone.utc).isoformat()
    output=build_graph(src,tuple(args.bbox),at=now,max_ways=args.max_ways)
    args.out.mkdir(parents=True,exist_ok=True)
    for name,doc in (("physical-graph-g0.json",output),
                     ("audit.json",{"releaseChannel":CHANNEL,"counts":output["counts"],
                                    "bbox":output["bbox"],"isPublished":False})):
        (args.out/name).write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,
              indent=2)+"\n",encoding="utf-8")
    print(json.dumps(output["counts"],ensure_ascii=False))

if __name__=="__main__":
    try:main()
    except (ValueError,OSError,RuntimeError) as exc:sys.exit(str(exc))
