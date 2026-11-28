#!/usr/bin/env python3
"""Publish a *thin source-only map catalogue* from official WFS G0 snapshots.

Bibbia §5/§30: G0 is eligible for map/catalogue visibility, NEVER as a
canonical place, public individual dossier, verified lake subtype, crosswalk
or indexable SEO page. The original G0 source snapshots stay out of public.
This is a derived, restricted, read-only projection, NOT an identity merge.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re

from import_official_lake_wfs_v1 import CHANNEL, PROVIDERS, validate_geometry

ROOT = Path(__file__).resolve().parents[1]
STAGE = ROOT / "data/snapshots"
DEFAULT_OUT = ROOT / "public/data/atlas/natural-lake-census-map-v1.json"
PUBLIC_CHANNEL = "NATURAL_LAKE_SOURCE_CENSUS_MAP_G0_V1"
FID = {
    "bolzano_lakes": re.compile(r"^Lakes\.[1-9]\d*$"),
    "arpav_water_surfaces": re.compile(
        r"^idrografia_specchio_acqua\.[1-9]\d*$"),
}
COUNTS = {
    "bolzano_lakes":("official-lakes-bolzano_lakes-geometry-g0.json",
                     "official-lakes-bolzano_lakes-topology-review-g0.json"),
    "arpav_water_surfaces":("official-lakes-arpav_water_surfaces-geometry-g0.json",
                            "official-lakes-arpav_water_surfaces-topology-review-g0.json"),
}
MAX_RECORDS = 10000
MAX_NAME_LENGTH = 180


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _number(fact, expected_unit):
    if not isinstance(fact,dict):
        return None
    value = fact.get("value")
    if (type(value) not in (int,float) or not math.isfinite(value) or value < 0 or
            fact.get("unit") != expected_unit or
            not isinstance(fact.get("sourceId"),str) or
            not isinstance(fact.get("sourceUrl"),str) or
            not fact.get("sourceUrl","").startswith("https://")):
        return None
    return value


def _names(entity, provider):
    names=[]
    langs=set()
    for item in entity.get("providerNames",[]):
        if not isinstance(item,dict):
            continue
        lang=item.get("language")
        value=item.get("value")
        if lang not in ("it","de") or not isinstance(value,str):
            continue
        value=" ".join(value.strip().split())
        if not (1 <= len(value) <= MAX_NAME_LENGTH) or (lang,value.casefold()) in langs:
            continue
        names.append({"lang":lang,"name":value})
        langs.add((lang,value.casefold()))
    return names[:4]


def source_to_map_record(entity, provider):
    if (entity.get("quality",{}).get("gate")!="G0" or
            entity.get("quality",{}).get("seoIndexable") is not False or
            entity.get("kind")!="natural_feature" or
            entity.get("subtype") is not None or
            entity.get("relations") or entity.get("media") or
            entity.get("quality",{}).get("subtypeConfirmed") is not False):
        raise ValueError("Unverified source attempted to become canonical lake")
    fid=entity.get("sourceFeatureId")
    if not isinstance(fid,str) or not FID[provider].fullmatch(fid):
        raise ValueError("Source FID has unexpected namespace")
    if entity.get("sourceIds",{}).get(provider)!=fid:
        raise ValueError("Inconsistent source FID")
    area=entity.get("geo",{}).get("area")
    if not isinstance(area,dict) or area.get("type")!="MultiPolygon":
        raise ValueError("No validated WFS polygon on source record")
    geom, measured=validate_geometry(area)
    fact=entity.get("facts",{}).get("providerMappedWaterSurfaceKm2")
    if (not isinstance(fact,dict) or fact.get("method")!="derived" or
            fact.get("unit")!="km2" or
            fact.get("licence")!=PROVIDERS[provider]["licence"] or
            type(fact.get("value")) not in (int,float) or
            abs(fact["value"]-measured)>0.00002):
        raise ValueError("Agency polygon geometry and mapped area conflict")
    names=_names(entity,provider)
    props=entity.get("sourcePropertiesRaw",{})
    raw_class=props.get("tipo") if provider=="arpav_water_surfaces" else None
    if raw_class is not None and (not isinstance(raw_class,str) or len(raw_class)>80):
        raise ValueError("Invalid provider class")
    facts=entity.get("facts",{})
    return {
        "sourceKey":provider+":"+fid,
        "sourceFeatureId":fid,
        "provider":provider,
        # The name is source-reported, not a confirmed multilingual atlas alias.
        "name":next((x["name"] for x in names if x["lang"]=="it"),None) or (
            names[0]["name"] if names else None),
        "names":names,
        "rawClass":raw_class,
        "canonicalSubtypeVerified":False,
        "qualityGate":"G0",
        "seoIndexable":False,
        "geom":geom,
        "derivedMappedKm2":measured,
        "agencyReportedAreaM2":_number(facts.get("officialAreaReportedM2"),"m2"),
        "agencyReportedElevationM":_number(facts.get("officialElevationReportedM"),"m"),
        "sourceUrl":PROVIDERS[provider]["sourceUrl"],
        "licence":PROVIDERS[provider]["licence"],
    }


def build(staged, held, registry):
    if (registry.get("releaseChannel")!="OFFICIAL_LAKE_CENSUS_SOURCE_REGISTRY_G0_V1"
            or registry.get("isPublished") is not False):
        raise ValueError("Missing immutable source-only census registry")
    features=[]
    summary={}
    allkeys=set()
    for provider in sorted(COUNTS):
        doc=staged[provider]
        review=held[provider]
        info=registry["providers"][provider]
        for obj in (doc,review):
            if (obj.get("releaseChannel")!=CHANNEL or
                    obj.get("isPublished") is not False or
                    obj.get("sourceProvider")!=provider or
                    obj.get("sampleOnly") is not True or
                    obj.get("completeDataset") is not False):
                raise ValueError("Official G0 source manifest failed")
        geometries=doc.get("entities",[])
        pending=review.get("entities",[])
        if len(geometries)>MAX_RECORDS or len(pending)>MAX_RECORDS:
            raise ValueError("Source manifest exceeds atlas map safety budget")
        if (len(geometries)!=info["validPolygons"] or
                len(pending)!=info["geometryReviewOnly"] or
                len(geometries)+len(pending)!=info["observedSourceIds"]):
            raise ValueError("Source counts or pending review do not match registry")
        accepted=[]
        for entry in geometries:
            record=source_to_map_record(entry,provider)
            if record["sourceKey"] in allkeys:
                raise ValueError("Duplicate provider source FID in census map")
            allkeys.add(record["sourceKey"])
            accepted.append(record)
        pending_keys=set()
        for entry in pending:
            fid=entry.get("sourceFeatureId")
            if not isinstance(fid,str) or not FID[provider].fullmatch(fid):
                raise ValueError("Invalid withheld geometry FID")
            if entry.get("quality",{}).get("gate")!="G0" or (
                    entry.get("quality",{}).get("seoIndexable") is not False):
                raise ValueError("Withheld geometry attempted SEO promotion")
            key=provider+":"+fid
            if key in allkeys or key in pending_keys:
                raise ValueError("Withheld geometry has duplicate identity")
            if entry.get("geo"):
                raise ValueError("Withheld geometry cannot carry a map polygon")
            pending_keys.add(key)
        # Preserve source-only records; no cross-provider dedup for place
        # identity, no inferred lake/reservoir subtaxonomy or fake centroids.
        features.extend(sorted(accepted,key=lambda x:x["sourceFeatureId"]))
        summary[provider]={
            "mappedSourceRecords":len(accepted),
            "namedSourceRecords":sum(x["name"] is not None for x in accepted),
            "geometryPendingReview":len(pending_keys),
            "sourceFeatureIdsObserved":info["observedSourceIds"],
            "sourceLicence":PROVIDERS[provider]["licence"],
            "providerLabel":("Provincia autonoma di Bolzano" if provider=="bolzano_lakes"
                             else "ARPAV Veneto"),
            "sourceDatasetUrl":PROVIDERS[provider]["sourceUrl"],
        }
    if not features:
        raise ValueError("No source polygons can be released to the map")
    return {
        "releaseChannel":PUBLIC_CHANNEL,
        "sourceOnlyCatalogue":True,
        "isPublishedG2":False,
        "individualPagesAllowed":False,
        "seoIndexable":False,
        "sourceRecordsAreNotDeduplicatedPhysicalLakes":True,
        "canonicalAtlasEntitiesAdded":0,
        "crossSourceIdentityLinksAdded":0,
        "sourceCounts":summary,
        "shownPolygons":len(features),
        "geometryPendingReview":sum(x["geometryPendingReview"] for x in summary.values()),
        "records":features,
    }


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source-root",type=Path,default=STAGE)
    parser.add_argument("--out",type=Path,default=DEFAULT_OUT)
    args=parser.parse_args()
    snapshots={provider:read_json(args.source_root/paths[0])
               for provider,paths in COUNTS.items()}
    pending={provider:read_json(args.source_root/paths[1])
             for provider,paths in COUNTS.items()}
    registry=read_json(args.source_root/"official-lakes-source-registry-g0.json")
    doc=build(snapshots,pending,registry)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(doc,ensure_ascii=False,separators=(",",":"))+"\n",
                        encoding="utf-8")
    print(json.dumps({
        "sourceOnlyCatalogue":True,
        "shownPolygons":doc["shownPolygons"],
        "pendingGeometry":doc["geometryPendingReview"],
        "named":{p:x["namedSourceRecords"] for p,x in doc["sourceCounts"].items()},
        "g2Released":0,
        "crossSourceIdentitiesCreated":0,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
