#!/usr/bin/env python3
"""Durable import cursor. Commit only after ALL source and SEO release gates.

A QID-less or incomplete commune is retried AFTER untouched Alpine communes.
The public G2 archive remains separate from the progress log and G0/G1 staging.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
from pathlib import Path
import re
from import_municipalities_v1 import load,save,require

def update_progress(previous,report,release,run_id,now=None):
    require(str(run_id).isdigit(),"GitHub Actions run ID required")
    require(release.get("releaseChannel")=="ISTAT_DAIT_MUNICIPALITIES" and
            release.get("isPublished") is True,"Expected published municipality release")
    codes=report.get("selectedCodes")
    require(isinstance(codes,list) and codes and len(codes)==len(set(codes)) and
            all(isinstance(c,str) and re.fullmatch(r"[0-9]{6}",c) for c in codes),
            "Selected official municipality codes missing")
    prev=previous or {"schemaVersion":"1.0","successfulRuns":0,"attempts":{}}
    require(prev.get("schemaVersion")=="1.0","Wrong import cursor version")
    if prev.get("lastRunId")==str(run_id):return prev
    published={e["sourceIds"]["istat"] for e in release["entities"] if
               e["quality"]["gate"]=="G2"}
    entries=prev.get("attempts",{}).copy()
    checked=now or datetime.now(timezone.utc).isoformat(timespec="seconds")
    for code in codes:
        row=entries.get(code,{})
        entries[code]={"attempts":int(row.get("attempts",0))+1,
          "lastAttemptAt":checked,
          "lastRunId":str(run_id),
          "result":"G2" if code in published else "needs_enrichment"}
    return {"schemaVersion":"1.0","successfulRuns":int(prev.get("successfulRuns",0))+1,
      "lastRunId":str(run_id),"lastSuccessAt":checked,
      "attempts":dict(sorted(entries.items())),
      "statistics":{
        "processedDistinct":len(entries),
        "publishedG2":len(published),
        "pendingRevisit":sum(x["result"]=="needs_enrichment" for x in entries.values()),
        "candidateAttempts":sum(x["attempts"] for x in entries.values()),
        "firstAttemptedThisRun":sum(entries[c]["attempts"]==1 for c in codes),
      }}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--previous",type=Path,required=True)
    p.add_argument("--enrichment-report",type=Path,required=True)
    p.add_argument("--municipalities",type=Path,required=True)
    p.add_argument("--run-id",required=True)
    args=p.parse_args()
    before=load(args.previous) if args.previous.exists() else None
    doc=update_progress(before,load(args.enrichment_report),load(args.municipalities),args.run_id)
    save(args.previous,doc)
    print(doc["statistics"])

if __name__=="__main__":main()
