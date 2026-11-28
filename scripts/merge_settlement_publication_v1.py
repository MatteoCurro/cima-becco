#!/usr/bin/env python3
"""Union two independently verified G2 releases without overwriting concurrent work.

Only source-verified G2 settlement entities are allowed. A shared Wikidata
QID with different stable IDs or slugs is a conflict, not an automatic merge.
Preserves dated historical images from either valid dossier. No inference.
"""
from __future__ import annotations
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path

CHANNEL = "ISTAT21_OSM_SETTLEMENTS"

def validate(release):
    if not isinstance(release, dict) or release.get("releaseChannel") != CHANNEL or release.get("isPublished") is not True:
        raise ValueError("Expected published G2 localities release")
    entities=release.get("entities")
    if not isinstance(entities,list):
        raise ValueError("Missing entities")
    keys=[]
    for entity in entities:
        ids=entity.get("sourceIds") or {}
        quality=entity.get("quality") or {}
        if (entity.get("kind") != "settlement" or quality.get("gate")!="G2"
            or quality.get("seoIndexable") is not True
            or not ids.get("wikidata") or not entity.get("id") or not entity.get("slug")
            or not entity.get("geo",{}).get("point")
            or not entity.get("textSources") or not entity.get("media")):
            raise ValueError("Unsafe G2 settlement entity: "+str(entity.get("slug")))
        if not any(m.get("kind")=="photo" and m.get("reuseAllowed") and
                   m.get("subjectVerified") and m.get("author") and m.get("licence")
                   and str(m.get("sourceUrl") or "").startswith("https://")
                   for m in entity["media"]):
            raise ValueError("Settlement without verified Commons image: "+str(entity["slug"]))
        keys.append((ids["wikidata"],entity["id"],entity["slug"]))
    for index in range(3):
        vals=[row[index] for row in keys]
        if len(vals)!=len(set(vals)):
            raise ValueError("Duplicate release identity or permalink")
    return entities

def verified_media(items):
    for media in items:
        if (media.get("reuseAllowed") and media.get("subjectVerified")
            and media.get("sourceUrl") and media.get("author") and media.get("licence")
            and media.get("kind") in ("photo","historical_photo","logo")):
            if media.get("kind")=="historical_photo" and not (
                media.get("capturedAt") and media.get("historicalDateMethod")
                and media.get("subjectMethod")):
                continue
            yield media

def merge_releases(current,incoming):
    existing=validate(current)
    newly=validate(incoming)
    by_qid={x["sourceIds"]["wikidata"]:deepcopy(x) for x in existing}
    current_at=str(current.get("generatedAt") or "")
    incoming_at=str(incoming.get("generatedAt") or "")
    for fresh in newly:
        qid=fresh["sourceIds"]["wikidata"]
        previous=by_qid.get(qid)
        if not previous:
            by_qid[qid]=deepcopy(fresh)
            continue
        if (previous["id"]!=fresh["id"] or previous["slug"]!=fresh["slug"] or
            previous["kind"]!=fresh["kind"]):
            raise ValueError("Stable entity identity changed for "+qid)
        newer,older=(fresh,previous) if incoming_at>=current_at else (previous,fresh)
        merged=deepcopy(newer)
        media={}
        for item in [*verified_media(older["media"]),*verified_media(newer["media"])]:
            key=(item.get("kind"),item.get("sourceUrl"))
            media[key]=item
        merged["media"]=list(media.values())
        # Merge only previously documented aliases; old canonical URLs remain.
        merged["slugAliases"]=list(dict.fromkeys(
            [*older.get("slugAliases",[]),*newer.get("slugAliases",[])]))
        by_qid[qid]=merged
    out=deepcopy(incoming)
    out["entities"]=sorted(by_qid.values(),key=lambda e:e["id"])
    out["generatedAt"]=max(current_at,incoming_at) or datetime.now(timezone.utc).isoformat()
    validate(out)
    return out

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--current",required=True,type=Path)
    parser.add_argument("--incoming",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    a=parser.parse_args()
    incoming=json.loads(a.incoming.read_text(encoding="utf-8"))
    current=json.loads(a.current.read_text(encoding="utf-8")) if a.current.exists() else {
        "schemaVersion":"1.0","releaseChannel":CHANNEL,"isPublished":True,"entities":[]}
    merged=merge_releases(current,incoming)
    a.out.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(merged,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    print(json.dumps({"current":len(current["entities"]),"incoming":len(incoming["entities"]),
                      "published":len(merged["entities"])},ensure_ascii=False))

if __name__=="__main__":
    main()
