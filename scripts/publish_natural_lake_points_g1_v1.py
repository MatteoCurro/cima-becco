#!/usr/bin/env python3
"""Sourced G1 lake profiles: GeoNames P1566/P625 identity, optional OSM shoreline.

Reuse the 28/11/2026 original GeoNames + verified Wikidata/Wikimedia stages.
Photo and text enrichment are *optional* for a point-only, noindex G1 page.
No inferred polygon/shore access, no source-WFS merge, no indexable G2 URL.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime,timezone
import json
from pathlib import Path
import re

from enrich_natural_water_geometry_v1 import point_inside_polygon

ROOT=Path(__file__).resolve().parents[1]
CHANNEL="NATURAL_LAKE_IDENTIFIED_PROFILES_G1_V1"
GN_CHANNEL="GEONAMES_NATURAL_FEATURES_STAGING_V1"
IDENTITY_CHANNEL="NATURAL_FEATURES_IDENTITY_STAGING_V1"
ENRICHED_CHANNEL="NATURAL_FEATURES_G2_CANDIDATES_STAGING_V1"
GEOMETRY_CHANNEL="OSM_NATURAL_WATER_GEOMETRIES_STAGING_V1"
G2_CHANNEL="NATURAL_FEATURES_LAKES_G2"
GN=re.compile(r"^[1-9][0-9]*$")
QID=re.compile(r"^Q[1-9][0-9]*$")
SLUG=re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
OSMID=re.compile(r"^(?:way|relation)/[1-9][0-9]*$")


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def source_gn_lakes(geonames,links):
    """Reduce the original source staging to *only* independently identified LK."""
    if geonames.get("releaseChannel")!=GN_CHANNEL or geonames.get("isPublished") is not False:
        raise ValueError("GeoNames source needs immutable non-published stage")
    wanted={str(x["geonameid"]) for x in links}
    matches={}
    for e in geonames.get("entities",[]):
        if e.get("kind")!="natural_feature" or e.get("subtype")!="lake":
            continue
        gn=e.get("sourceIds",{}).get("geonames")
        if gn not in wanted:continue
        if (not GN.fullmatch(gn) or e.get("quality",{}).get("gate")!="G1" or
                e.get("quality",{}).get("seoIndexable") is not False or
                not SLUG.fullmatch(str(e.get("slug",""))) or
                e.get("quality",{}).get("slugRequiresReview") or
                e.get("geo",{}).get("method")!="geonames_point" or
                e.get("geo",{}).get("area") is not None or
                e.get("geo",{}).get("sourceUrl")!="https://www.geonames.org/"+gn+"/"):
            raise ValueError("Unvalidated GeoNames lake source "+str(gn))
        p=e["geo"]["point"]
        if (not 35<=p.get("lat",0)<=48 or not 6<=p.get("lng",0)<=20 or
                not isinstance(e.get("name"),str) or len(e["name"].strip())<3):
            raise ValueError("Missing sourced name or WGS84 point")
        if gn in matches:raise ValueError("Duplicate GeoNames primary ID")
        matches[gn]=deepcopy(e)
    if set(matches)!=wanted:
        raise ValueError("Verified lake QIDs have no matching GeoNames source record: "+
                         str(sorted(wanted-set(matches))))
    return {"schemaVersion":"1.0","releaseChannel":GN_CHANNEL,"isPublished":False,
            "generatedAt":geonames.get("generatedAt"),"entities":
                sorted(matches.values(),key=lambda x:x["sourceIds"]["geonames"])}


def verified_links(identity):
    if identity.get("releaseChannel")!=IDENTITY_CHANNEL or identity.get("isPublished") is not False:
        raise ValueError("No independent GeoNames-to-QID audit")
    found={};seen_qids=set()
    for x in identity.get("links",[]):
        if x.get("subtype")!="lake":continue
        gn=str(x.get("geonameid",""));qid=x.get("qid")
        if (not GN.fullmatch(gn) or not QID.fullmatch(str(qid or "")) or
                x.get("wikidataIdentityVerified") is not True or
                x.get("identityMethod")!="exact_P1566_P625_one_to_one" or
                x.get("wikidataUrl")!="https://www.wikidata.org/wiki/"+qid or
                type(x.get("coordinateDistanceKm")) not in (float,int) or
                type(x.get("coordinateGateKm")) not in (float,int) or
                x["coordinateDistanceKm"]<0 or
                x["coordinateDistanceKm"]>x["coordinateGateKm"] or
                x["coordinateGateKm"]>2):
            raise ValueError("Invalid lake identity link "+gn)
        if gn in found or qid in seen_qids:raise ValueError("Ambiguous QID source identity")
        found[gn]=deepcopy(x);seen_qids.add(qid)
    if not found:raise ValueError("No identity-verified G1 lake candidates")
    return found


def choose_media(doc,qid):
    """Only the Wikidata exact-identity P18 + licensed Commons file."""
    result=[]
    for m in doc.get("media",[]) if doc else []:
        if (m.get("kind")=="photo" and
            m.get("sourceId")=="wikidata:"+qid+":P18" and
            m.get("subjectMethod")=="verified_GeoNames_P1566_Wikidata_P625_P18" and
            m.get("subjectVerified") is True and m.get("reuseAllowed") is True and
            all(isinstance(m.get(k),str) and m[k].strip() for k in
                ("author","licence","sourceUrl","url","id")) and
            m["sourceUrl"].startswith("https://commons.wikimedia.org/wiki/File:") and
            m["url"].startswith("https://") and
            not re.search(r"\.(?:svg|pdf)(?:\?|$)",m["url"],re.I)):
            result.append(deepcopy(m))
    return result[:1]


def choose_text(doc):
    """Existing Wikipedia adapter already verified pageprops QID."""
    for t in doc.get("textSources",[]) if doc else []:
        if (isinstance(t.get("text"),str) and 120<=len(t["text"])<=10000 and
                t.get("licence")=="CC BY-SA 4.0" and
                str(t.get("sourceId","")).startswith("wikipedia:it:") and
                str(t.get("sourceUrl","")).startswith("https://it.wikipedia.org/wiki/") and
                t.get("kind")=="source_excerpt_not_original_editorial"):
            return [deepcopy(t)]
    return []


def _geometry(by_gn,gn,src,link):
    shape=by_gn.get(gn)
    if shape is None:return None
    ids=shape.get("sourceIds",{})
    osm=ids.get("osm")
    geo=shape.get("geo",{})
    source="https://www.openstreetmap.org/"+str(osm)
    area=geo.get("area")
    fact=shape.get("facts",{}).get("osmMappedWaterSurfaceKm2",{})
    p=src["geo"]["point"]
    if (shape.get("quality",{}).get("geometryTopologyVerified") is not True or
            shape.get("quality",{}).get("gate")!="G1" or
            shape.get("quality",{}).get("reviewRequired") or
            ids.get("geonames")!=gn or ids.get("wikidata")!=link["qid"] or
            ids.get("osmVerifiedBy")!="P1566_P625_and_exact_OSM_QID_or_GeoNames_ID" or
            not OSMID.fullmatch(str(osm)) or
            geo.get("point")!=p or
            geo.get("areaSourceUrl")!=source or
            area is None or area.get("type")!="MultiPolygon" or
            not area.get("coordinates") or
            fact.get("unit")!="km2" or fact.get("licence")!="ODbL 1.0" or
            fact.get("method")!="derived" or
            fact.get("sourceId")!="osm:"+osm+":geometry" or
            type(fact.get("value")) not in (float,int) or
            not 0<fact["value"]<350 or
            not point_inside_polygon([p["lng"],p["lat"]],area)):
        raise ValueError("Conflicting cross-source lake polygon for GeoNames "+gn)
    return {"area":deepcopy(area),"areaSourceUrl":source,
            "areaMethod":geo.get("areaMethod"),
            "sourceIds":{"osm":osm,"osmVerifiedBy":ids["osmVerifiedBy"]},
            "areaFact":deepcopy(fact)}


def build(geonames,identity,geometry,enriched,g2,at=None):
    links=verified_links(identity)
    reduced=source_gn_lakes(geonames,links.values())
    if (geometry.get("releaseChannel")!=GEOMETRY_CHANNEL or
            geometry.get("isPublished") is not False or
            not isinstance(geometry.get("geonamesLinkedEntities"),list)):
        raise ValueError("Missing audit-backed optional OSM geometry")
    if (enriched.get("releaseChannel")!=ENRICHED_CHANNEL or
            enriched.get("isPublished") is not False or
            not isinstance(enriched.get("entities"),list)):
        raise ValueError("Missing existing Wikimedia attribution staging")
    if (g2.get("releaseChannel")!=G2_CHANNEL or
            g2.get("isPublished") is not True or
            not isinstance(g2.get("entities"),list)):
        raise ValueError("Current G2 dataset required for exclusion of canonical dossiers")
    published_gn={e["sourceIds"]["geonames"] for e in g2["entities"]}
    published_qid={e["sourceIds"]["wikidata"] for e in g2["entities"]}
    if len(published_gn)!=len(g2["entities"]) or len(published_qid)!=len(g2["entities"]):
        raise ValueError("Duplicate canonical G2 identities")
    geom={}
    for e in geometry["geonamesLinkedEntities"]:
        gn=e.get("sourceIds",{}).get("geonames")
        if gn in geom:raise ValueError("Duplicate source-exact OSM water polygons")
        geom[gn]=e
    wiki={}
    for e in enriched["entities"]:
        if e.get("subtype")!="lake":continue
        gn=e.get("sourceIds",{}).get("geonames")
        if gn in wiki:raise ValueError("Duplicate Wikimedia GeoNames identity")
        wiki[gn]=e
    rows=[];seen_slugs=set();seen_qids=set()
    at=at or datetime.now(timezone.utc).isoformat()
    for e in reduced["entities"]:
        gn=e["sourceIds"]["geonames"];link=links[gn];qid=link["qid"]
        # Canonical G2 takes precedence: NEVER publish a duplicate G1 profile.
        if gn in published_gn or qid in published_qid:continue
        doc=wiki.get(gn)
        if doc and (doc.get("sourceIds",{}).get("wikidata")!=qid or
                    doc.get("sourceIds",{}).get("wikidataVerifiedBy")!="P1566+P625" or
                    doc.get("geo",{}).get("point")!=e["geo"]["point"]):
            raise ValueError("Mismatched G1 Wikimedia source identity "+gn)
        slug=e["slug"]
        if slug in seen_slugs or qid in seen_qids:raise ValueError("Conflicting G1 lake permalink")
        seen_slugs.add(slug);seen_qids.add(qid)
        polygon=_geometry(geom,gn,e,link)
        media=choose_media(doc,qid)
        text=choose_text(doc)
        facts={key:deepcopy(value) for key,value in e["facts"].items()
               if key in ("elevationM","geoNamesFeatureCode")}
        if doc:
            other=doc.get("facts",{}).get("wikidataElevationReportedM")
            if (other and other.get("sourceId")=="wikidata:"+qid+":P2044" and
                    other.get("unit")=="m" and
                    type(other.get("value")) in (float,int)):
                facts["wikidataElevationReportedM"]=deepcopy(other)
        if polygon:
            facts["osmMappedWaterSurfaceKm2"]=polygon["areaFact"]
        local=doc.get("localNames",[]) if doc else []
        rows.append({
            "id":e["id"],"name":e["name"],"slug":slug,"subtype":"lake",
            "aliases":deepcopy(e.get("aliases",[]))[:12],
            "localNames":deepcopy(local)[:12],
            "sourceIds":{"geonames":gn,"wikidata":qid,
                         "wikidataVerifiedBy":"P1566+P625",
                         **(polygon["sourceIds"] if polygon else {})},
            "geo":{"point":deepcopy(e["geo"]["point"]),
                   "method":"geonames_point",
                   "pointSourceUrl":"https://www.geonames.org/"+gn+"/",
                   "area":polygon["area"] if polygon else None,
                   "areaSourceUrl":polygon["areaSourceUrl"] if polygon else None,
                   "areaMethod":polygon["areaMethod"] if polygon else None},
            "facts":facts,
            "media":media,"textSources":text,
            "description":text[0]["text"] if text else None,
            "quality":{"gate":"G1","seoIndexable":False,
                       "sourcePointVerified":True,
                       "wikidataIdentityVerified":True,
                       "hasVerifiedShoreline":bool(polygon),
                       "needsAreaGeometryReview":not bool(polygon),
                       "photoSourceVerified":bool(media),
                       "textLicenseVerified":bool(text)},
            "identitySource":"exact_P1566_P625_one_to_one",
            "checkedAt":at,
        })
    return {
        "schemaVersion":"1.0","releaseChannel":CHANNEL,
        "isCanonicalPublished":False,"seoIndexable":False,"noindexFollow":True,
        "crossSourceWfsMerges":0,"g2Duplicated":0,
        "sourceG1Candidates":len(links),
        "excludedCanonicalG2":len(set(links).intersection(published_gn)),
        "generatedAt":at,
        "counts":{"profiles":len(rows),
                  "pointOnly":sum(x["geo"]["area"] is None for x in rows),
                  "withOsmGeometry":sum(x["geo"]["area"] is not None for x in rows),
                  "withVerifiedP18":sum(bool(x["media"]) for x in rows),
                  "withVerifiedItwiki":sum(bool(x["textSources"]) for x in rows)},
        "entities":sorted(rows,key=lambda r:r["slug"]),
    },reduced


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--geonames",type=Path,required=True)
    p.add_argument("--identity",type=Path,required=True)
    p.add_argument("--geometry",type=Path,required=True)
    p.add_argument("--enriched",type=Path,required=True)
    p.add_argument("--g2",type=Path,default=ROOT/"public/data/atlas/natural-lakes-v1.json")
    p.add_argument("--out",type=Path,default=ROOT/"public/data/atlas/natural-lake-points-g1-v1.json")
    p.add_argument("--source-cache",type=Path)
    p.add_argument("--enriched-cache",type=Path)
    args=p.parse_args()
    enriched=load(args.enriched)
    result,source=build(load(args.geonames),load(args.identity),
                        load(args.geometry),enriched,load(args.g2))
    for path,doc in ((args.out,result),(args.source_cache,source),
                     (args.enriched_cache,enriched)):
        if path is None:continue
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,
                                   indent=2)+"\n",encoding="utf-8")
    print(json.dumps({
        "channel":CHANNEL,"sourceG1Candidates":result["sourceG1Candidates"],
        "excludedCanonicalG2":result["excludedCanonicalG2"],
        **result["counts"],"seoIndexable":False,"crossSourceWfsMerges":0,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
