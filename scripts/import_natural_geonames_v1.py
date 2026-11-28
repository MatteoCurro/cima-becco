#!/usr/bin/env python3
"""GeoNames source adapter for Cima Becco natural features (§5), G0/G1 only.

Reuses source typed facts and near semantics of the natural feature staging.
Consumes the *country dump* with stable GeoNames IDs; no OSM+GeoNames merges
by name, distance, or assumed shared areas. Springs remain in alpine-water.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO, TextIOWrapper
import json
from pathlib import Path
import re
import uuid
from zipfile import ZipFile

from import_alpine_places import BBOX
from import_natural_features_v1 import RELEASE, STAGE, reconcile_slugs
from import_summits_v1 import slugify, nearby

ROOT=Path(__file__).resolve().parents[1]
GEONAMES="https://www.geonames.org/"
LICENSE="CC BY 4.0"
# Exact feature classes from the official GeoNames code table.
CODES={
    "PASS":("mountain_pass","T"),
    "SAD":("saddle","T"),
    "VAL":("valley","T"),
    "LK":("lake","H"),
    "RES":("reservoir","H"),
    "FLLS":("waterfall","H"),
}
TYPES=set(CODES)

def valid_bbox(bounds):
    a,b,c,d=bounds
    return 35<=a<c<=48 and 6<=b<d<=20

def numeric(value, minimum, maximum):
    if not re.fullmatch(r"-?\d+",str(value or "")):
        return None
    n=int(value)
    return n if minimum<=n<=maximum else None

def field(value, ident, url, timestamp, unit=None, method="reported", source_updated_at=None):
    return {"value":value,"unit":unit,"sourceId":"geonames:"+str(ident),
            "sourceUrl":url,"licence":LICENSE,"retrievedAt":timestamp,
            "sourceUpdatedAt":source_updated_at,"validFrom":None,"validUntil":None,
            "method":method,"confidence":0.85 if method=="reported" else 0.6}

def entity_from_line(line, at, bounds):
    cols=line.rstrip("\r\n").split("\t")
    if len(cols)<19:return None
    ident=numeric(cols[0],1,10**12)
    name=cols[1].strip()
    feature=cols[7]
    if not ident or feature not in TYPES or cols[6]!=CODES[feature][1]:
        return None
    if not (2<=len(name)<=140 and slugify(name) and cols[8]=="IT"):
        return None
    try:
        lat=float(cols[4]);lon=float(cols[5])
    except (ValueError,TypeError):
        return None
    if not (bounds[0]<=lat<=bounds[2] and bounds[1]<=lon<=bounds[3]):
        return None
    subtype=CODES[feature][0]
    url=f"{GEONAMES}{ident}/"
    facts={"geoNamesFeatureCode":field(feature,ident,url,at,None,
              source_updated_at=cols[18] or None)}
    elev=numeric(cols[15],0,5000)
    dem=numeric(cols[16],0,5000)
    if elev is not None:
        facts["elevationM"]=field(elev,ident,url,at,"m","reported",cols[18] or None)
    elif dem is not None:
        facts["elevationM"]=field(dem,ident,url,at,"m","estimated",cols[18] or None)
    aliases=[]
    for name_alt in cols[3].split(",")[:50]:
        name_alt=name_alt.strip()
        if (name_alt and name_alt!=name and len(name_alt)<=100
            and name_alt.casefold() not in [a["value"].casefold() for a in aliases]):
            aliases.append({"value":name_alt,"language":None,"sourceUrl":url})
        if len(aliases)>=12:break
    return {
        "id":str(uuid.uuid5(uuid.NAMESPACE_URL,url)),
        "kind":"natural_feature","subtype":subtype,
        "name":name,"displayName":name,
        "slug":slugify(name),"slugAliases":[],
        "aliases":aliases,"localNames":[],
        "sourceIds":{"geonames":str(ident)},
        "geo":{"point":{"lat":round(lat,6),"lng":round(lon,6)},
               "area":None,"method":"geonames_point","sourceUrl":url,
               "precision":"provider_not_declared"},
        "administrativeHierarchy":{"country":"IT","geonamesAdmin1":cols[10] or None},
        "facts":facts,"factsAlternatives":[],
        "media":[],"textSources":[],"relations":[],
        "history":None,"shortSummary":None,"description":None,
        "restrictions":[],"alerts":[],
        "quality":{"gate":"G1","seoIndexable":False,"reviewRequired":False,
                   "areaNotVerified":subtype in ("lake","reservoir","valley"),
                   "wikidataIdentityVerified":False},
        "editorialStatus":"linked","checkedAt":at,"updatedAt":at,
    }

def load_dump(path, *, country="IT"):
    blob=Path(path).read_bytes()
    snapshots={"sourceFile":Path(path).name,"sha256":sha256(blob).hexdigest()}
    if path.suffix.lower()==".zip":
        with ZipFile(BytesIO(blob)) as archive:
            name=country+".txt"
            if name not in archive.namelist():
                raise ValueError(f"Country dump {name} missing in ZIP")
            with archive.open(name) as data:
                lines=TextIOWrapper(data,encoding="utf-8")
                rows=list(lines)
    else:
        rows=blob.decode("utf-8").splitlines()
    return rows,snapshots

def run(source,bounds,out,max_records=250,catalogs=()):
    if not valid_bbox(bounds):
        raise ValueError("Invalid bounded Italian alpine pilot coordinates")
    rows,snapshots=load_dump(Path(source))
    at=datetime.now(timezone.utc).isoformat()
    unique={}
    reasons=Counter()
    for line in rows:
        entity=entity_from_line(line,at,bounds)
        if entity is None:continue
        ident=entity["sourceIds"]["geonames"]
        if ident in unique and unique[ident]!=entity:
            raise ValueError("Conflicting GeoNames duplicate identity "+ident)
        unique[ident]=entity
    entities=sorted(unique.values(),key=lambda e:(e["subtype"],e["name"],e["id"]))
    total=len(entities)
    groups=reconcile_slugs(entities)
    entities=entities[:max_records] if max_records else entities
    for e in entities:
        nearby(e,catalogs,max_each=2)
    path=Path(out);(path/"raw").mkdir(parents=True,exist_ok=True)
    def dump(name,doc):
        (path/name).write_text(json.dumps(doc,ensure_ascii=False,sort_keys=True,
                                          indent=2)+"\n",encoding="utf-8")
    dump("raw/geonames-features.json",{"source":"GeoNames IT country dump",
         "capturedAt":at,"snapshot":snapshots,"bbox":bounds,
         "rowsSelected":total,
         "entitiesSource":[{"id":e["sourceIds"]["geonames"],"name":e["name"],
            "kind":e["subtype"],"point":e["geo"]["point"]} for e in entities]})
    dump("features-geonames.json",{
        "schemaVersion":"1.0","releaseChannel":"GEONAMES_NATURAL_FEATURES_STAGING_V1",
        "isPublished":False,"generatedAt":at,"entities":entities})
    report={"source":"GeoNames","license":LICENSE,"country":"IT",
            "sourceSnapshot":snapshots,"bbox":bounds,"candidates":total,
            "staged":len(entities),
            "bySubtype":dict(Counter(e["subtype"] for e in entities)),
            "collisionGroups":groups,"reviewRequired":sum(bool(e["quality"]["reviewRequired"]) for e in entities),
            "nearNotAccess":sum(len(e["relations"]) for e in entities),
            "published":0,"indexable":0,"reusedWaterCatalog":True,
            "crossSourceMerges":0}
    dump("geonames-report.json",report)
    return report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source",type=Path,required=True)
    p.add_argument("--bbox",type=float,nargs=4,default=BBOX)
    p.add_argument("--out",type=Path,default=STAGE)
    p.add_argument("--max-records",type=int,default=250)
    p.add_argument("--min-records",type=int,default=20)
    p.add_argument("--with-near",action="store_true")
    args=p.parse_args()
    catalogs=[]
    if args.with_near:
        catalogs=[
            ("refuges",ROOT/"public/data/atlas/refuges-v1.json"),
            ("shelters",ROOT/"public/data/atlas/shelters-v1.json"),
            ("settlements",ROOT/"public/data/atlas/settlements-v1.json"),
            ("summits",ROOT/"public/data/atlas/summits-v1.json"),
        ]
    result=run(args.source,args.bbox,args.out,args.max_records,catalogs)
    if result["staged"]<args.min_records:
        raise RuntimeError(f"GeoNames natural-feature coverage {result['staged']} below {args.min_records}")
    print(json.dumps(result,ensure_ascii=False))


if __name__=="__main__":
    main()
