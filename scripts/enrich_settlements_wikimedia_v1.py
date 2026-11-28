#!/usr/bin/env python3
"""Arricchimento località: OSM QID verificato -> Wikidata -> Wikipedia/Commons.

Pubblica soltanto G2: identità e coordinate coerenti, articolo itwiki con QID
verificato, immagine Commons P18 attribuita, testo sostanziale e relazioni.
Un paese vicino a una località ISTAT con stesso nome NON viene fuso se manca
anche la prova amministrativa diretta Wikidata P131 e unicità del riscontro.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from hashlib import sha1
import json
import math
from pathlib import Path
import re

from import_municipalities_v1 import load, save, header, fact
from enrich_municipalities_v1 import (
    wd_entities, claim_coord, claim_string, commons_files, wikipedia_intro,
    NON_PHOTO, PHOTO_EXT
)

QID = re.compile(r"^Q[1-9][0-9]*$")
OSM = re.compile(r"^(node|way|relation)/[1-9][0-9]*$")
STAGING = "STAGING_ISTAT21_OSM_SETTLEMENTS"
RELEASE = "ISTAT21_OSM_SETTLEMENTS"
WIKIDATA = "https://www.wikidata.org/wiki/"

def wd_item_ids(item, prop):
    out = []
    for claim in (item.get("claims") or {}).get(prop,[]):
        if claim.get("rank") == "deprecated":
            continue
        value = ((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(value,dict) and value.get("entity-type") == "item":
            qid = "Q" + str(value.get("numeric-id"))
            if QID.fullmatch(qid):
                out.append(qid)
    return out

def haversine(a,b):
    lat1,lon1=math.radians(a["lat"]),math.radians(a["lng"])
    lat2,lon2=math.radians(b["lat"]),math.radians(b["lng"])
    h=math.sin((lat2-lat1)/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088*2*math.asin(min(1.0, math.sqrt(max(0,h))))

def names_agree(name,item):
    """Italian Wikidata label must agree when present: article title cannot
    silently override a contradicting entity label (false positive gate).
    """
    norm=header(name)
    if not norm:return False
    labels=item.get("labels") or {}
    preferred=labels.get("it")
    if isinstance(preferred,dict) and preferred.get("value"):
        return header(preferred["value"])==norm
    # Without an Italian label, accept a single documented English/local
    # label or exact itwiki title, never broad fuzzy edit-distance matches.
    fallback=[v.get("value") for v in labels.values()
              if isinstance(v,dict) and v.get("value")]
    title=((item.get("sitelinks") or {}).get("itwiki") or {}).get("title")
    if title:fallback.append(str(title).split("(",1)[0].strip())
    return any(header(v)==norm for v in fallback)

def find_istat(legacy, official, municipality_by_qid, parent_claims, wd_point):
    """QID P131 + matching 2021 parent + exact name + unique near point."""
    parent_codes = {str(m["sourceIds"]["istat"]) for q in parent_claims
                    if (m:=municipality_by_qid.get(q))}
    if not parent_codes:
        return None, "no_verified_2021_parent"
    options = [e for e in official if
               e["sourceIds"]["istatMunicipality"] in parent_codes and
               header(e["name"])==header(legacy["name"]) and
               e["geo"].get("point") and
               haversine(legacy["geo"]["point"],e["geo"]["point"])<=1.2 and
               haversine(wd_point,e["geo"]["point"])<=2.0]
    if len(options)!=1:
        return None, "unresolved_istat_identity" if not options else "ambiguous_istat_identity"
    return options[0], None

def add_person_connections(entity,qid,people):
    candidates=[]
    for person in (people or {}).get("entities",[]):
        if qid not in person.get("birthPlaceQids",[]):
            continue
        roles=person.get("roles") or []
        role=roles[0] if roles else {}
        person_qid=person.get("qid")
        if not QID.fullmatch(str(person_qid or "")):
            continue
        candidates.append({
            "personId":person["id"],"qid":person_qid,"name":person["name"],
            "relationType":"birthplace_of","category":role.get("category","cultura_e_ricerca"),
            "role":role.get("label") or "biografia documentata",
            "birthDate":person.get("birthDate"),"deathDate":person.get("deathDate"),
            "description":person.get("description"),
            "wikipediaUrl":person.get("wikipediaUrl"),
            "sourceId":"wikidata:"+person_qid+":P19",
            "sourceUrl":WIKIDATA+person_qid,
            "verified":True,"quality":"G1",
        })
    entity["connectedPeople"]=candidates[:20]
    return len(candidates)

def enrich(archive,municipalities,people=None,*,limit=48,offset=0,
           previous=None,wd_getter=None,wiki_getter=None,commons_getter=None,
           retrieved_at=None):
    if archive.get("releaseChannel")!=STAGING or archive.get("isPublished"):
        raise ValueError("Richiesto il catalogo di staging del blocco 4")
    retrieved_at=retrieved_at or datetime.now(timezone.utc).isoformat()
    official = [e for e in archive["entities"] if e.get("sourceIds",{}).get("istatLocality")]
    osm = sorted((e for e in archive["entities"] if e.get("sourceIds",{}).get("osm") and
                  QID.fullmatch(str(e.get("sourceIds",{}).get("wikidata") or ""))),
                 key=lambda e:(e["sourceIds"]["wikidata"],e["id"]))
    muni = {e["sourceIds"]["wikidata"]:e for e in (municipalities or {}).get("entities",[])
            if QID.fullmatch(str(e.get("sourceIds",{}).get("wikidata") or "")) and
            e.get("sourceIds",{}).get("istat")}
    known_muni_qids=set(muni)
    unique_qid = defaultdict(list)
    for e in osm:
        unique_qid[e["sourceIds"]["wikidata"]].append(e)
    # A QID shared by multiple OSM points is ambiguous, not merged.
    selected=[e for e in osm if len(unique_qid[e["sourceIds"]["wikidata"]])==1 and
              e["sourceIds"]["wikidata"] not in known_muni_qids]
    selected=selected[offset:offset+limit]
    old = {e["sourceIds"].get("wikidata"):e for e in (previous or {}).get("entities",[])
           if e.get("sourceIds",{}).get("wikidata")}
    published=[]
    reasons=Counter()
    reviewed=[]
    photo_count=0
    text_count=0
    same_istat=0
    for chunk_offset in range(0,len(selected),20):
        chunk=selected[chunk_offset:chunk_offset+20]
        qids=[e["sourceIds"]["wikidata"] for e in chunk]
        try:
            items=wd_entities(qids,getter=wd_getter)
        except Exception as error:
            reasons["wikidata_unavailable"]+=len(chunk)
            reviewed.append({"source":"Wikidata","error":str(error)[:150]})
            continue
        images_needed = [claim_string(items.get(qid,{}) ,"P18") for qid in qids]
        images_needed=[name for name in images_needed if name and
                       PHOTO_EXT.search(name) and not NON_PHOTO.search(name)]
        try:
            images=commons_files(images_needed,getter=commons_getter)
        except Exception as error:
            images={}
            reviewed.append({"source":"Commons","error":str(error)[:150]})
        for legacy in chunk:
            qid=legacy["sourceIds"]["wikidata"]
            item=items.get(qid,{})
            # Claim QID identity is not enough: independent Wikidata
            # coordinate and label checks protect against false OSM tags.
            point=claim_coord(item)
            if not point or haversine(point,legacy["geo"]["point"])>2.0:
                reasons["coordinate_mismatch_or_missing"]+=1
                continue
            if not names_agree(legacy["name"],item):
                reasons["name_mismatch"]+=1
                continue
            if "Q5" in wd_item_ids(item,"P31"):
                reasons["person_not_settlement"]+=1
                continue
            parents=wd_item_ids(item,"P131")
            canonical,issue=find_istat(legacy,official,muni,parents,point)
            entity=dict(canonical if canonical else legacy)
            entity["facts"]=dict(entity.get("facts") or {})
            entity["relations"]=list(entity.get("relations") or [])
            entity["media"]=[]
            entity["textSources"]=[]
            if canonical:
                same_istat+=1
                entity["sourceIds"]=dict(entity["sourceIds"])
                entity["sourceIds"]["osm"]=legacy["sourceIds"]["osm"]
                entity["slugAliases"]=list(dict.fromkeys((entity.get("slugAliases") or [])+
                    (legacy.get("slugAliases") or [])+[legacy["slug"]]))
            else:
                entity["sourceIds"]=dict(entity["sourceIds"])
            entity["sourceIds"]["wikidata"]=qid
            entity["sourceIds"]["wikidataVerifiedBy"]="P625+label+OSM_ID"
            entity["geo"]=dict(entity["geo"])
            entity["geo"]["wikidataPointVerifiedAt"]=retrieved_at
            entity["facts"]["wikidataLocationValidated"]=fact(
                True,"wikidata:"+qid+":P625",WIKIDATA+qid,
                as_of=retrieved_at,licence="CC0",method="reported")
            for parent_qid in parents:
                parent=muni.get(parent_qid)
                if not parent:continue
                if any(rel["type"]=="part_of" and
                       rel["target"]["id"]==parent["id"] for rel in entity["relations"]):
                    break
                entity["relations"].append({
                    "type":"part_of",
                    "target":{"id":parent["id"],"kind":"municipality",
                              "name":parent["name"],"slug":parent["slug"]},
                    "verified":True,"method":"direct_wikidata_P131",
                    "sourceId":"wikidata:"+qid+":P131","sourceUrl":WIKIDATA+qid,
                    "notes":"Località nel Comune: non prova di status di frazione amministrativa",
                })
                entity["parentMunicipalityId"]=parent["id"]
                entity["parentMunicipalityName"]=parent["name"]
                break
            image_name=claim_string(item,"P18")
            if not image_name or NON_PHOTO.search(image_name) or not PHOTO_EXT.search(image_name):
                reasons["no_subject_photo_P18"]+=1
                continue
            image=images.get(image_name.replace(" ","_"))
            if not image:
                reasons["no_verified_commons_media"]+=1
                continue
            title=((item.get("sitelinks") or {}).get("itwiki") or {}).get("title")
            if not title:
                reasons["no_italian_article"]+=1
                continue
            try:
                article=wikipedia_intro(title,qid,getter=wiki_getter)
            except Exception:
                article=None
            if not article:
                reasons["no_verified_text"]+=1
                continue
            entity["media"]=[{**image,
               "id":"wikimedia:"+qid+":P18:"+sha1(image_name.encode()).hexdigest()[:12],
               "kind":"photo","sourceId":"wikidata:"+qid+":P18",
               "subjectMethod":"wikidata_P18_with_P625_name_and_OSM_identity_verified",
               "retrievedAt":retrieved_at,
               "caption":"Fotografia documentata di "+entity["name"]}]
            article["retrievedAt"]=retrieved_at
            entity["textSources"]=[{k:v for k,v in article.items() if k!="linkedImages"}]
            entity["description"]=article["text"]
            entity["shortSummary"]=None
            # A verified QID/photo/text does not authorize publishing an
            # unresolved homonymous slug. The importer explicitly marks these
            # candidates G0/noindex; keep them in editorial review.
            if (entity.get("quality") or {}).get("slugRequiresReview"):
                reasons["ambiguous_slug_pending_editorial_review"]+=1
                reviewed.append({"wikidata":qid,"slug":entity.get("slug"),
                                 "reason":"ambiguous_slug_pending_editorial_review"})
                continue
            entity["quality"]={
               **entity["quality"],"gate":"G2","seoIndexable":True,
               "reviewRequired":False,"photoSourceVerified":True,
               "textLicenseVerified":True,"identityMethod":"OSM_QID_P625_label_verified",
               "istatIdentityVerified":bool(canonical),
            }
            entity["editorialStatus"]="enriched"
            add_person_connections(entity,qid,people)
            published.append(entity)
            photo_count+=1;text_count+=1
            if issue:reasons[issue]+=1
    # Preserve previously verified dossier on upstream downtime; never
    # publish a new source-less placeholder. Existing IDs remain stable.
    seen={e["sourceIds"].get("wikidata") for e in published}
    for qid, entity in sorted(old.items()):
        if (qid not in seen and entity.get("quality",{}).get("gate")=="G2" and
            entity.get("media") and entity.get("textSources") and
            entity.get("geo",{}).get("point")):
            published.append(entity)
            seen.add(qid)
    ids=[x["id"] for x in published]
    slugs=[x["slug"] for x in published]
    if len(ids)!=len(set(ids)) or len(slugs)!=len(set(slugs)):
        raise ValueError("Collisioni G2 fra dataset precedenti e attuali: blocco")
    document={"schemaVersion":"1.0","releaseChannel":RELEASE,
              "isPublished":True,"generatedAt":retrieved_at,
              "entities":sorted(published,key=lambda e:e["id"])}
    report={"selectedCandidates":len(selected),"offset":offset,
            "publishedG2":len(published),"newG2":photo_count,
            "withIstatExactMatch":same_istat,
            "newPhotos":photo_count,"newTexts":text_count,
            "connectionsPeople":sum(len(e.get("connectedPeople") or []) for e in published),
            "heldReasons":dict(sorted(reasons.items())),
            "reviewExamples":reviewed[:20]}
    return document,report

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--settlements",required=True)
    p.add_argument("--municipalities",required=True)
    p.add_argument("--people")
    p.add_argument("--previous")
    p.add_argument("--max-new",type=int,default=48)
    p.add_argument("--offset",type=int,default=0)
    p.add_argument("--out",required=True)
    p.add_argument("--report",required=True)
    args=p.parse_args()
    previous=load(args.previous) if args.previous and Path(args.previous).exists() else None
    document,report=enrich(load(args.settlements),load(args.municipalities),
                           load(args.people) if args.people else None,
                           limit=args.max_new,offset=args.offset,previous=previous)
    save(args.out,document)
    save(args.report,report)
    print(json.dumps(report,ensure_ascii=False,sort_keys=True))

if __name__=="__main__":
    main()
