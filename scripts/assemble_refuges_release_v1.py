#!/usr/bin/env python3
"""Publish unified Cima Becco refuge catalog using OSM + reused CAI API.

OSM geography and prior permalinks remain stable. A CAI detail can enrich
a unique strong OSM match; an unambiguous CAI-only hut gets a stable CAI
permalink; bivouacs are kept for block 2 and never presented as refuges.
No unsafe merge by proximity alone, no invented "open now"/route access.
"""
from __future__ import annotations
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from publish_refuges_v1 import build_public
from import_refuges_v1 import canonical_json, load, write
from reconcile_cai_osm_refuges_v1 import distance_m, name_score

ROOT=Path(__file__).resolve().parents[1]
MATCH_RADIUS_M=35
MATCH_NAME_SIMILARITY=0.95
MAX_ALTITUDE_DIFF_M=120
REVIEW_RADIUS_M=170
REVIEW_NAME_SIMILARITY=0.5


def eligible(ref):
    return ref.get("kind") == "rifugio" and isinstance(ref.get("facts"),dict)


def location(e):
    p=e["geo"]["point"]
    return p["lat"], p["lng"]


def altitude(e):
    v=e.get("facts",{}).get("elevationM")
    return v.get("value") if isinstance(v,dict) and isinstance(v.get("value"),(float,int)) else None


def candidate_matches(cai, osm):
    result=[]
    for o in osm:
        d=distance_m((cai["lat"],cai["lng"]),location(o))
        if d>REVIEW_RADIUS_M:
            continue
        score=name_score(cai["name"],o["name"])
        if score<REVIEW_NAME_SIMILARITY:
            continue
        a,b=altitude(cai),altitude(o)
        diff=abs(a-b) if a is not None and b is not None else None
        result.append({"targetId":o["id"],"sourceIds":o["sourceIds"],
                       "nameSimilarity":score,"distanceM":d,
                       "elevationDifferenceM":diff,
                       "highConfidence":score>=MATCH_NAME_SIMILARITY
                                        and d<=MATCH_RADIUS_M
                                        and (diff is None or diff<=MAX_ALTITUDE_DIFF_M)})
    return sorted(result,key=lambda x:(-x["nameSimilarity"],x["distanceM"],x["targetId"]))


def mapped_record(osm, cai):
    row=deepcopy(osm)
    code=cai["caiId"]
    row["sourceIds"]["cai"]=code
    row["sources"].append({
        "id":"cai:shelter:"+code,
        "url":"https://rifugi.cai.it/shelters/"+code,
        "licence":"CAI · riuso confermato dal titolare del progetto",
    })
    row.setdefault("factsAlternatives",[])
    for key,fact in cai["facts"].items():
        old=row["facts"].get(key)
        if old and old.get("value")!=fact.get("value"):
            row["factsAlternatives"].append({
                "key":key,"fact":old,"reason":"Valore precedente OSM: CAI preferito per informazioni gestionali dichiarate"
            })
        row["facts"][key]=fact
    row["factsAlternatives"].extend(cai.get("factsAlternatives",[]))
    row["media"].extend(cai.get("media",[]))
    row["webcams"].extend(cai.get("webcams",[]))
    if cai.get("description"):
        row["description"]=cai["description"]
        row["shortSummary"]=cai["description"][:200]
    row["officialUrl"]=cai["sourceUrl"]
    row["caiStructureType"]=cai["originalType"]
    row["quality"]={"gate":"G1","seoIndexable":False,
                    "notes":["Identità CAI-OSM riconciliata per nome, coordinate, tipo e quota",
                             "Stato di apertura e percorribilità non confermati in tempo reale"]}
    row["editorialStatus"]="linked"
    return row


def new_record(cai):
    code=cai["caiId"]
    record={
        "id":"cai:"+code,"kind":"refuge","subtype":cai["subtype"],
        "name":cai["name"],"displayName":cai["name"],
        "slug":cai["slug"],"slugAliases":[],
        "legacyUrl":"/rifugi/"+cai["slug"]+"/",
        "geo":{"point":{"lat":cai["lat"],"lng":cai["lng"]},
               "method":"cai_api_point","sourceUrl":cai["sourceUrl"]},
        "sourceIds":{"cai":code},
        "sources":[{"id":"cai:shelter:"+code,"url":cai["sourceUrl"],
                    "licence":"CAI · riuso confermato dal titolare del progetto"}],
        "facts":cai["facts"],"factsAlternatives":cai.get("factsAlternatives",[]),
        "relations":[],"media":cai.get("media",[]),
        "webcams":cai.get("webcams",[]),
        "description":cai.get("description") or None,
        "shortSummary":(cai.get("description") or "")[:200] or None,
        "officialUrl":cai["sourceUrl"],
        "caiStructureType":cai["originalType"],
        "quality":{"gate":"G1","seoIndexable":False,
                   "notes":["Fonte CAI con tipologia documentata",
                            "Stato di apertura e accessibilità non verificati in tempo reale"]},
        "editorialStatus":"enriched",
    }
    return record


def compile_release(osm_catalogue, cai_catalogue, *, complete=True):
    if not isinstance(osm_catalogue,dict) or not isinstance(osm_catalogue.get("entities"),list):
        raise ValueError("Catalogo OSM non valido")
    if not isinstance(cai_catalogue,dict) or not isinstance(cai_catalogue.get("records"),list):
        raise ValueError("Catalogo CAI non valido")
    if complete and not cai_catalogue.get("isCompleteSnapshot"):
        raise ValueError("Impossibile pubblicare un campione CAI incompleto")
    osms=deepcopy(osm_catalogue["entities"])
    caires=[r for r in cai_catalogue["records"] if eligible(r)]
    bivouacs=[r for r in cai_catalogue["records"] if r.get("kind")=="bivacco"]
    if complete and len(caires)<150:
        raise ValueError("Copertura rifugi CAI sotto la soglia di sicurezza")
    contenders={}
    all_suggestions={}
    for r in caires:
        matches=candidate_matches(r,osms)
        all_suggestions[r["caiId"]]=matches
        strong=[m for m in matches if m["highConfidence"]]
        if len(strong)==1:
            contenders.setdefault(strong[0]["targetId"],[]).append(r["caiId"])
    osm_by_id={o["id"]:o for o in osms}
    added, merged, conflicts, suppressed = [],[],[],[]
    for cai in caires:
        matches=all_suggestions[cai["caiId"]]
        strong=[m for m in matches if m["highConfidence"]]
        if len(strong)==1 and len(contenders[strong[0]["targetId"]])==1 and len(matches)==1:
            orig=osm_by_id[strong[0]["targetId"]]
            osm_by_id[strong[0]["targetId"]]=mapped_record(orig,cai)
            merged.append({"caiId":cai["caiId"],"osmId":orig["id"],
                           "distanceM":strong[0]["distanceM"],
                           "nameSimilarity":strong[0]["nameSimilarity"],
                           "method":"unique_exact_name_nearby_with_verified_type",
                           "permalinkPreserved":orig["legacyUrl"]})
        elif matches:
            conflicts.append({"caiId":cai["caiId"],"reason":"unresolved_nearby_osm_entity",
                              "candidates":matches,"publishedAsSeparate":False})
            suppressed.append(cai["caiId"])
        else:
            added.append(new_record(cai))
    # A bivouac CAI record might expose a legacy OSM entity typed as refuge:
    # no reclassification, only a documented category conflict.
    kind_conflicts=[]
    for r in bivouacs:
        for suggestion in candidate_matches(r,osms):
            if suggestion["nameSimilarity"]>=MATCH_NAME_SIMILARITY and suggestion["distanceM"]<=35:
                kind_conflicts.append({"caiId":r["caiId"],
                    "osmId":suggestion["targetId"],"sourceType":"Bivacco",
                    "action":"review_osm_classification_not_auto_change"})
    entities=sorted(list(osm_by_id.values())+added,key=lambda e:e["id"])
    ids=[e["id"] for e in entities]
    slugs=[e["slug"] for e in entities]
    if len(ids)!=len(set(ids)) or len(slugs)!=len(set(slugs)):
        raise ValueError("Collisione ID o permalink dopo merge CAI")
    attribution=list(osm_catalogue.get("attribution",[]))+[
        {"source":"Club Alpino Italiano · Unico Rifugi",
         "url":"https://rifugi.cai.it/","rights":"Riuso confermato dal titolare del progetto"}]
    output={
        "schemaVersion":"1.1","releaseChannel":"OSM_CAI_REFUGES",
        "sourceSnapshotSha256":osm_catalogue.get("sourceSnapshotSha256"),
        "sourceRevisionCAI":cai_catalogue.get("contentSha256"),
        "kind":"refuge","seoIndexable":False,
        "attribution":attribution,
        "limitations":[
            "Tipi e servizi CAI sono dichiarazioni della fonte e possono cambiare",
            "In attività sul catalogo non significa aperto in questo momento",
            "Relazioni di vicinanza OSM/GeoNames non attestano accessibilità",
            "Schede da fonti non riconciliate non sono fuse per nome soltanto",
        ],
        "entities":entities,
        "routeProximityEdges":osm_catalogue.get("routeProximityEdges",[]),
    }
    report={
        "schemaVersion":"1.1","status":"release_ready",
        "osmRecords":len(osms),"caiRecords":len(cai_catalogue["records"]),
        "caiRefugeRecords":len(caires),"caiBivouacsHeldForBlock2":len(bivouacs),
        "mergedOSMAndCAI":len(merged),"newCAIRefugePages":len(added),
        "suppressedForReview":len(suppressed),"typeConflicts":len(kind_conflicts),
        "totalRefuges":len(entities),
        "photos":sum(len(e.get("media",[])) for e in entities),
        "withCAIFacts":sum("cai" in e["sourceIds"] for e in entities),
        "sourceDataHash":hashlib.sha256(canonical_json(output)).hexdigest(),
    }
    review={"strongMatches":merged,"unresolvedMatches":conflicts,
            "typeConflicts":kind_conflicts,"suppressedCaiIds":sorted(suppressed)}
    return output,report,review


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--stage",type=Path,default=ROOT/"build"/"import-refuges-v1")
    p.add_argument("--cai",type=Path,default=ROOT/"public"/"data"/"atlas"/"cai-refuges-v1.json")
    p.add_argument("--quarantine",type=Path,default=ROOT/"scripts"/"refuges_release_quarantine_v1.json")
    p.add_argument("--out",type=Path,default=ROOT/"public"/"data"/"atlas"/"refuges-v1.json")
    p.add_argument("--report",type=Path,default=ROOT/"build"/"release-refuges-v1")
    args=p.parse_args()
    osm,osm_report=build_public(args.stage,load(args.quarantine))
    release,report,review=compile_release(osm,load(args.cai))
    release["quarantinedOsmIds"] = sorted({
        x["sourceKey"].removeprefix("osm:").replace(":", "/", 1)
        for x in osm_report["quarantine"]
    })
    write(args.out,release)
    final_report = {
        **osm_report, **report,
        "publicRecords": report["totalRefuges"],
        "publicPhotoCount": report["photos"],
        "publicCAIFields": sum(
            1 for entity in release["entities"] for fact in entity.get("facts", {}).values()
            if isinstance(fact, dict) and str(fact.get("sourceId", "")).startswith("cai:shelter:")
        ),
        "publicWebcamCount": sum(len(entity.get("webcams", [])) for entity in release["entities"]),
        "qualityGate": "G0_OSM_G1_CAI_with_reviewed_joins",
        "qualityNotes": [
            "CAI e OSM hanno provenance individuale; rifugi CAI-only non hanno ID OSM inventato",
            "Lo stato CAI non è una conferma di apertura in tempo reale",
            "I dati dei bivacchi sono conservati nel catalogo CAI ma non pubblicati come rifugi",
        ],
    }
    write(args.report/"report.json",final_report)
    write(args.report/"match-review.json",review)
    print(json.dumps(report,sort_keys=True,ensure_ascii=False))


if __name__=="__main__":
    main()
