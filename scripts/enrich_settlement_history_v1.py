#!/usr/bin/env python3
"""Fotografie storiche delle località G2: soggetto e data di scatto verificati.

Non sono ammesse foto comunali ereditate. Vengono usati solo:
1) P180 MediaInfo = QID esatto della località e P571/DateTimeOriginal ante 1975;
2) la stessa pagina itwiki con QID verificato e nome intero del borgo nel titolo.
Autore/licenza verificati tramite Commons e cronologia separata dagli upload.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path

from import_municipalities_v1 import load, save, require
from enrich_municipalities_v1 import QID, commons_files
from enrich_municipality_history_v1 import (
    search_depicts, fetch_sdc, fetch_file_dates, sdc_depicts_exact,
    recorded_history_date, article_history_candidates,
    commons_pages_by_title, safe_historical_scene,
)

def enrich_historical_settlements(release, *, getter=None, max_settlements=8,
                                   cycle=0, checked_at=None):
    require(release.get("releaseChannel")=="ISTAT21_OSM_SETTLEMENTS" and
            release.get("isPublished") is True,
            "Solo dossier località G2 verificati")
    checked_at=checked_at or datetime.now(timezone.utc).isoformat()
    eligible=[e for e in release.get("entities",[]) if
              e.get("quality",{}).get("gate")=="G2" and
              QID.fullmatch(str(e.get("sourceIds",{}).get("wikidata") or "")) and
              e.get("textSources") and e.get("media")]
    eligible.sort(key=lambda e:(sum(m.get("kind")=="historical_photo"
                     for m in e.get("media",[])),e["id"]))
    offset=(max(0,int(cycle))*max_settlements)%max(1,len(eligible))
    chosen=(eligible+eligible)[offset:offset+min(len(eligible),max_settlements)]
    report={"eligible":len(eligible),"checked":len(chosen),
            "saved":0,"candidatesChecked":0,"errors":[]}
    for place in chosen:
        qid=place["sourceIds"]["wikidata"]
        try:
            pages=search_depicts(qid,getter=getter,limit=20)
            sdc=fetch_sdc(pages,getter=getter)
            dates=fetch_file_dates(pages,getter=getter)
            report["candidatesChecked"]+=len(pages)
            qualifying=[]
            for page in pages:
                filename=page["filename"]
                entity=sdc.get("M"+str(page["pageid"])) or {}
                if not sdc_depicts_exact(entity,qid):continue
                date,method=recorded_history_date(entity,dates.get(filename.replace(" ","_"),{}))
                if date:qualifying.append((filename,date,method,
                    "commons_media_info_P180_exact_settlement_QID",page["pageid"]))
            if len(qualifying)<2:
                candidates=article_history_candidates(place,getter=getter)
                commons_pages=commons_pages_by_title(candidates,getter=getter)
                media_info=fetch_sdc(commons_pages,getter=getter)
                report["candidatesChecked"]+=len(commons_pages)
                for page in commons_pages:
                    if len(qualifying)>=2:break
                    filename=page["filename"]
                    if any(x[0].replace(" ","_")==filename.replace(" ","_") for x in qualifying):
                        continue
                    item=media_info.get("M"+str(page["pageid"])) or {}
                    date,method=recorded_history_date(item,page["extmetadata"])
                    if not date:continue
                    provenance=("commons_media_info_P180_exact_settlement_QID"
                                if sdc_depicts_exact(item,qid) else
                                "same_QID_itwiki_article_and_exact_settlement_filename")
                    qualifying.append((filename,date,method,provenance,page["pageid"]))
            if not qualifying:continue
            images=commons_files([c[0] for c in qualifying],getter=getter)
            seen={(m.get("kind"),m.get("sourceUrl")) for m in place.get("media",[])}
            for filename,date,method,subject_method,page_id in qualifying[:2]:
                asset=images.get(filename.replace(" ","_"))
                if (not asset or not safe_historical_scene(asset,date) or
                    ("historical_photo",asset["sourceUrl"]) in seen):
                    continue
                record={**asset,
                    "id":"commons-local-history:"+hashlib.sha1((qid+filename).encode()).hexdigest()[:14],
                    "kind":"historical_photo","capturedAt":date,
                    "historicalDateMethod":method,"subjectMethod":subject_method,
                    "subjectVerified":True,"reuseAllowed":True,
                    "sourceId":"commons:mediainfo:M"+str(page_id),
                    "caption":("Fotografia storica di "+place["name"]+" ("+date[:4]+")"),
                    "retrievedAt":checked_at}
                place.setdefault("media",[]).append(record)
                seen.add(("historical_photo",asset["sourceUrl"]))
                report["saved"]+=1
        except Exception as e:
            report["errors"].append({"qid":qid,"error":str(e)[:120]})
    return release,report

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--settlements",required=True)
    p.add_argument("--out",required=True)
    p.add_argument("--report",required=True)
    p.add_argument("--max",type=int,default=8)
    p.add_argument("--cycle",type=int,default=0)
    a=p.parse_args()
    release,report=enrich_historical_settlements(load(a.settlements),
        max_settlements=a.max,cycle=a.cycle)
    save(a.out,release)
    save(a.report,report)
    print(report)

if __name__=="__main__":main()
