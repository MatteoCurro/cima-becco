#!/usr/bin/env python3
"""Join official ISTAT 2021 DEM altimetry against stable 6-digit municipality IDs.

A territorial minimum/mean/maximum is NOT the altitude of the town hall.
Unknown and historically changed municipality codes remain missing, never
reconciled by name. Each fact retains its original dated source.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import hashlib
import json
import math
import re

from import_municipalities_v1 import xlsx_matrices,csv_matrix,header,code6,number,load,save,fact,require

SOURCE_URL="https://www.istat.it/wp-content/uploads/2026/02/Altimetria_Comuni-al-31_12_2021.xlsx"
SOURCE_PAGE="https://www.istat.it/classificazione/principali-statistiche-geografiche-sui-comuni/"
SOURCE_DATE="2021-12-31"

CODE_HEADERS=(
  "codice comune al 31 12 2021","codice istat comune","codice istat del comune",
  "codice comune formato alfanumerico","codice comune","codice del comune",
  "cod comune","pro com t","pro com","cod com","codice numerico comune",
)
# Only unambiguous column headings are used. Never confuse minimum altitude,
# mean territorial elevation, and a centre/town-hall altitude.
ALT_HEADERS={
 "altitudineTerritorioMinM":(
   "altitudine minima","altitudine min","quota minima","quota min",
   "alt min","alt min m","min dem","dem min","altitudine minima dem",
   "altitudine minima sul livello del mare"),
 "altitudineTerritorioMaxM":(
   "altitudine massima","altitudine max","quota massima","quota max",
   "alt max","alt max m","max dem","dem max","altitudine massima dem",
   "altitudine massima sul livello del mare"),
 "altitudineTerritorioMediaM":(
   "altitudine media","quota media","media dem","dem media","alt med",
   "alt media","altitudine media dem","altitudine media comunale"),
 "quotaCentroM":(
   "altitudine del centro","altitudine centro capoluogo",
   "altitudine del centro capoluogo","quota del centro",
   "altitudine del centro metri"),
}
def matching_column(names,options):
    normal=[header(n) for n in names]
    for candidate in options:
        key=header(candidate)
        matches=[i for i,n in enumerate(normal) if n==key]
        if len(matches)==1:return matches[0]
    for candidate in options:
        key=header(candidate)
        matches=[i for i,n in enumerate(normal) if n.startswith(key+" ") or n.endswith(" "+key)]
        if len(matches)==1:return matches[0]
    return None

def numeric_alt(value):
    v=number(value)
    return v if v is not None and -10<=v<=4800 else None

def rows_from_source(raw):
    matrices=xlsx_matrices(raw) if raw[:2]==b"PK" else csv_matrix(raw)
    for matrix in matrices:
        for pos,headings in enumerate(matrix[:75]):
            id_col=matching_column(headings,CODE_HEADERS)
            indices={key:matching_column(headings,aliases) for key,aliases in ALT_HEADERS.items()}
            active={key:i for key,i in indices.items() if i is not None}
            if id_col is None or not active:continue
            observations=[]
            for row in matrix[pos+1:]:
                if id_col>=len(row):continue
                code=code6(row[id_col])
                if code is None:continue
                metrics={}
                for key,i in active.items():
                    if i>=len(row):continue
                    val=numeric_alt(row[i])
                    if val is not None:metrics[key]=round(val,2)
                if metrics:observations.append((code,metrics))
            if observations:
                return observations,{"codeColumn":str(headings[id_col]),"metricColumns":{
                    k:str(headings[i]) for k,i in active.items()},"sourceRecords":len(observations)}
    raise ValueError("ISTAT altimetry: codice ISTAT + colonne altimetriche non riconosciute; bloccare il join")

def attach_altimetry(release,raw,*,retrieved_at=None):
    require(release.get("releaseChannel")=="ISTAT_DAIT_MUNICIPALITIES",
        "Wrong municipality release input")
    entries,metadata=rows_from_source(raw)
    source_id="istat:altimetry:2021:DEM"
    timestamp=retrieved_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    by_code={}
    conflicts=set()
    for code,values in entries:
        if code in by_code and by_code[code]!=values:
            conflicts.add(code)
        else:by_code[code]=values
    for code in conflicts:by_code.pop(code,None)
    added=0
    unknown=[]
    totals={key:0 for key in ALT_HEADERS}
    for entity in release.get("entities",[]):
        code=entity.get("sourceIds",{}).get("istat")
        values=by_code.get(code)
        if not values:
            unknown.append(code);continue
        minimum=values.get("altitudineTerritorioMinM")
        maximum=values.get("altitudineTerritorioMaxM")
        mean=values.get("altitudineTerritorioMediaM")
        if minimum is not None and maximum is not None and minimum>maximum:
            conflicts.add(code);continue
        if mean is not None and minimum is not None and mean<minimum:
            conflicts.add(code);continue
        if mean is not None and maximum is not None and mean>maximum:
            conflicts.add(code);continue
        for key,value in values.items():
            if key in entity["facts"] and entity["facts"][key].get("sourceId","").startswith("istat:"):
                continue
            entity["facts"][key]=fact(value,source_id,SOURCE_URL,unit="m",
                    as_of=timestamp,method="derived" if key!="quotaCentroM" else "reported")
            entity["facts"][key]["sourceUpdatedAt"]=SOURCE_DATE
            entity["facts"][key]["notes"]=(
                "Altimetria del territorio comunale derivata da DEM NASADEM (riferimento 2021)"
                if key!="quotaCentroM" else
                "Quota del centro soltanto perché presente come colonna esplicita ISTAT")
            totals[key]+=1
            added+=1
    return release,{"source":SOURCE_URL,"sourcePage":SOURCE_PAGE,"referenceDate":SOURCE_DATE,
        "rawSha256":hashlib.sha256(raw).hexdigest(),
        "joinMethod":"exact_istat_6_char_code",
        "metricsAdded":added,"matched":len(release.get("entities",[]))-len(unknown),
        "notMatchedCodes":unknown[:50],"conflicts":sorted(conflicts)[:50],
        "coverage":totals,**metadata}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--municipalities",type=Path,required=True)
    ap.add_argument("--source",type=Path,required=True)
    ap.add_argument("--report",type=Path,required=True)
    args=ap.parse_args()
    rel=load(args.municipalities)
    rel,report=attach_altimetry(rel,args.source.read_bytes(),retrieved_at=rel.get("retrievedAt"))
    # Idempotent daily refresh: zero changes is SUCCESS when the rows match
    # and an official 2021 ISTAT altimetric fact is already retained. Missing
    # joins still fail closed instead of using guessed altitudes.
    retained=sum(any(f.get("sourceId")=="istat:altimetry:2021:DEM"
      and f.get("value") is not None
      for f in entity.get("facts",{}).values()) for entity in rel.get("entities",[]))
    report["alreadyPublishedOfficialAltimetry"]=retained
    require(report["matched"]>0 and (report["metricsAdded"]>0 or retained>0),
      "Nessuna altimetria ISTAT riconciliata o gia verificata")
    save(args.municipalities,rel)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False))

if __name__=="__main__":main()
