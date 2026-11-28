#!/usr/bin/env python3
"""Personaggi dei comuni: identità Wikidata, relazione diretta, professione verificata.

Si elaborano SOLO Comuni già riconciliati tramite P635. P19 luogo di nascita,
P551 residenza storica (solo deceduti), P937 luogo di lavoro; la provincia non
crea mai il collegamento. Nessuna ascensione o intitolazione si inferisce.
L'output persone è un catalogo G1 non indicizzato: verrà riutilizzato
dall'importatore Persone del blocco 21 della Bibbia.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import time
from enrich_municipalities_v1 import WIKIDATA_API, WIKIDATA_QUERY, UA
from import_municipalities_v1 import load,save,require

QID = re.compile(r"Q[1-9][0-9]*$")
# These occupation QIDs are documented in Wikidata, not guessed from the
# person's family name or from proximity to mountains.
MOUNTAIN_ROLE_IDS={
  "Q9149093":"alpinismo",
  "Q819677":"guida alpina",
  "Q19801627":"sci alpinismo",
  "Q59917804":"soccorso alpino",
}
ROLE_RE=re.compile(
  r"\b(alpinista|mountaineer|mountain climber|guida alpina|mountain guide|"
  r"rock climber|arrampicatore|arrampicatrice|climber|sci alpinista|"
  r"ski mountaineer|sciatore alpino|sciatrice alpina|alpine skier|"
  r"fondista|cross country skier|sciatore di fondo|sciatrice di fondo|"
  r"mountain rescuer|soccorritore alpino)\b",re.I)
CULTURAL_ROLES_RE=re.compile(
  r"\b(storico|storica|historian|scrittore|scrittrice|writer|"
  r"poeta|poetessa|poet|geologo|geologa|geologist|"
  r"naturalista|naturalist|botanico|botanica|botanist|"
  r"compositore|compositrice|composer|pittore|pittrice|painter|"
  r"architetto|architetta|architect|scultore|scultrice|sculptor|"
  r"fotografo|fotografa|photographer)\b",re.I)
RELATION={
  "P19":("birthplace_of","born_in","nato/a qui"),
  "P551":("historical_residence_of","resided_in","residenza storica"),
  "P937":("workplace_of","worked_in","luogo di attività"),
}
def api(url, params, getter=None):
    if getter:return getter(url,params)
    query=url+"?"+urlencode(params)
    for attempt in range(3):
        try:
            with urlopen(Request(query,headers={"User-Agent":UA,
                "Accept":"application/json"}),timeout=50) as conn:
                return json.load(conn)
        except HTTPError as exc:
            if exc.code not in {429,502,503,504} or attempt==2:raise
        except (URLError,TimeoutError):
            if attempt==2:raise
        time.sleep((2,6)[min(attempt,1)])

def wd_claim_targets(item, property_id):
    result=set()
    for c in (item.get("claims") or {}).get(property_id,[]):
        if c.get("rank")=="deprecated":continue
        v=((c.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if isinstance(v,dict) and v.get("entity-type")=="item":
            qid=v.get("id")
            if isinstance(qid,str) and QID.fullmatch(qid):
                result.add(qid)
    return result

def wd_time(item,prop):
    for claim in (item.get("claims") or {}).get(prop,[]):
        if claim.get("rank")=="deprecated":continue
        value=((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
        if not isinstance(value,dict):continue
        t=str(value.get("time",""))
        m=re.match(r"^[+]([0-9]{4})-([0-9]{2})-([0-9]{2})T",t)
        if m:
            year,month,day=m.groups()
            if month=="00":return year
            if day=="00":return year+"-"+month
            return year+"-"+month+"-"+day
    return None

def sparql_candidates(qids,getter=None,limit=500):
    require(qids and all(QID.fullmatch(q) for q in qids),"QID comuni non validi")
    if len(qids)>8:raise ValueError("max 8 comuni per batch")
    values=" ".join("wd:"+q for q in qids)
    query="""SELECT DISTINCT ?person ?town ?relation ?occupation ?occupationLabel WHERE {
        VALUES ?town { """+values+""" }
        VALUES ?relation { wdt:P19 wdt:P551 wdt:P937 }
        ?person ?relation ?town ;
                wdt:P31 wd:Q5 ;
                wdt:P106 ?occupation.
        SERVICE wikibase:label { bd:serviceParam wikibase:language "it,en". }
    } LIMIT """+str(limit)
    doc=api(WIKIDATA_QUERY,{"query":query,"format":"json"},getter)
    rows=[]
    for x in (doc.get("results") or {}).get("bindings",[]):
        person=x.get("person",{}).get("value","").rsplit("/",1)[-1]
        town=x.get("town",{}).get("value","").rsplit("/",1)[-1]
        prop=x.get("relation",{}).get("value","").rsplit("/",1)[-1]
        occupation=x.get("occupation",{}).get("value","").rsplit("/",1)[-1]
        label=x.get("occupationLabel",{}).get("value","").strip()
        if not (QID.fullmatch(person) and town in qids and
                QID.fullmatch(occupation) and prop in RELATION):continue
        rows.append({"person":person,"town":town,"prop":prop,"occupation":occupation,"roleLabel":label})
    if len(rows)>=limit:
        raise ValueError("WDQS batch raggiunge LIMIT: rifiutata estrazione potenzialmente troncata")
    return rows

def detail_entities(qids,getter=None):
    result={}
    for start in range(0,len(qids),35):
        ids=qids[start:start+35]
        doc=api(WIKIDATA_API,{"action":"wbgetentities","format":"json",
          "ids":"|".join(ids),"props":"claims|sitelinks|labels|descriptions",
          "languages":"it|en","sitefilter":"itwiki|enwiki"},getter)
        result.update(doc.get("entities") or {})
    return result

def classify(role_qid,role_label):
    if role_qid in MOUNTAIN_ROLE_IDS or ROLE_RE.search(role_label):
        return "montagna"
    if CULTURAL_ROLES_RE.search(role_label):
        return "cultura_e_ricerca"
    return None

def build(release,*,getter=None,previous_people=None,checked_at=None,batch=6,max_mountain=12,max_culture=4):
    require(release.get("releaseChannel")=="ISTAT_DAIT_MUNICIPALITIES","Archivio comuni atteso")
    municipalities=release.get("entities") or []
    town_to_municipality={
        m["sourceIds"]["wikidata"]:m for m in municipalities
        if QID.fullmatch(str(m.get("sourceIds",{}).get("wikidata",""))) and
           m.get("sourceIds",{}).get("wikidataVerifiedBy")=="P635"}
    now=checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    errors=[]
    profiles={}
    previous={p["qid"]:p for p in (previous_people or {}).get("entities",[])
              if QID.fullmatch(str(p.get("qid","")))}
    selected=defaultdict(list)
    for offset in range(0,len(town_to_municipality),batch):
        part=list(town_to_municipality)[offset:offset+batch]
        try:
            candidates=sparql_candidates(part,getter=getter)
            details=detail_entities(sorted({c["person"] for c in candidates}),getter=getter)
        except Exception as exc:
            errors.append({"townQids":part,"error":str(exc)[:160]})
            continue
        for c in candidates:
            item=details.get(c["person"],{})
            if item.get("missing") or not item:continue
            if c["town"] not in wd_claim_targets(item,c["prop"]):continue
            if c["occupation"] not in wd_claim_targets(item,"P106"):continue
            if "Q5" not in wd_claim_targets(item,"P31"):continue
            typ=classify(c["occupation"],c["roleLabel"])
            if typ is None:continue
            birth=wd_time(item,"P569")
            death=wd_time(item,"P570")
            # A current residence should not be published for a living person.
            if c["prop"]=="P551" and not death:continue
            # Additional non-mountain figures must have an itwiki biography
            # and a *direct* P19 connection. A generic profession alone
            # does not establish alpinistic relevance.
            wiki=((item.get("sitelinks") or {}).get("itwiki") or {}).get("title")
            if typ=="cultura_e_ricerca" and (not wiki or c["prop"]!="P19"):continue
            label=(item.get("labels") or {}).get("it") or (item.get("labels") or {}).get("en") or {}
            name=str(label.get("value") or "").strip()
            if not name or name==c["person"]:continue
            description=((item.get("descriptions") or {}).get("it") or
                (item.get("descriptions") or {}).get("en") or {}).get("value") or ""
            identity={
                "id":"person:"+c["person"],"qid":c["person"],"name":name,
                "description":str(description).strip()[:240],
                "birthDate":birth,"deathDate":death,
                "wikidataUrl":"https://www.wikidata.org/wiki/"+c["person"],
                "wikipediaUrl":("https://it.wikipedia.org/wiki/"+urlencode({"":wiki})[1:].replace("+","_")
                                if wiki else None),
                "roles":[],"relations":[],"quality":{"gate":"G1","seoIndexable":False},
                "editorialStatus":"linked",
            }
            p=profiles.setdefault(c["person"],identity)
            if not any(r["occupationQid"]==c["occupation"] for r in p["roles"]):
                p["roles"].append({"occupationQid":c["occupation"],"label":c["roleLabel"],
                    "category":typ,"sourceId":"wikidata:"+c["person"]+":P106"})
            town=town_to_municipality[c["town"]]
            type_from,type_to,note=RELATION[c["prop"]]
            rel={"type":type_to,"target":{"id":town["id"],
                "kind":"municipality","name":town["name"],"slug":town["slug"]},
                "sourceId":"wikidata:"+c["person"]+":"+c["prop"],
                "sourceUrl":"https://www.wikidata.org/wiki/"+c["person"],
                "method":"reported","verified":True,"retrievedAt":now,
                "notes":note}
            if not any(x["type"]==type_to and x["target"]["id"]==town["id"] for x in p["relations"]):
                p["relations"].append(rel)
            entry={"personId":"person:"+c["person"],"qid":c["person"],
                "name":name,"relationType":type_from,
                "category":typ,"role":c["roleLabel"],
                "birthDate":birth,"deathDate":death,
                "description":p["description"],"wikipediaUrl":p["wikipediaUrl"],
                "sourceId":"wikidata:"+c["person"]+":"+c["prop"],
                "sourceUrl":"https://www.wikidata.org/wiki/"+c["person"],
                "verified":True,"method":"reported","retrievedAt":now,
                "quality":"G1"}
            selected[town["sourceIds"]["istat"]].append(entry)
    linked=0
    for m in municipalities:
        candidates=selected.get(m["sourceIds"]["istat"],[])
        priority={"birthplace_of":0,"historical_residence_of":1,"workplace_of":2}
        unique={}
        for entry in candidates:
            key=entry["personId"]+":"+entry["relationType"]
            existing=unique.get(key)
            if existing is None or (entry["category"]=="montagna" and existing["category"]!="montagna"):
                unique[key]=entry
        ordered=sorted(unique.values(),key=lambda e:(0 if e["category"]=="montagna" else 1,
            priority[e["relationType"]],e["name"],e["personId"]))
        mountain=[x for x in ordered if x["category"]=="montagna"][:max_mountain]
        culture=[x for x in ordered if x["category"]=="cultura_e_ricerca"][:max_culture]
        new=mountain+culture
        if new:
            m["connectedPeople"]=new
            linked+=len(new)
            # Links are first-class graph edges; the visible dossier is an
            # adapter of the same relationships, not an unrelated text list.
            for entry in new:
                relation={"type":entry["relationType"],
                  "target":{"id":entry["personId"],"kind":"person",
                            "name":entry["name"]},
                  "sourceId":entry["sourceId"],
                  "sourceUrl":entry["sourceUrl"],"method":"reported",
                  "verified":True,"retrievedAt":now}
                if not any(r.get("type")==relation["type"] and
                           r.get("target",{}).get("id")==entry["personId"]
                           for r in m.get("relations",[])):
                    m.setdefault("relations",[]).append(relation)
        elif m.get("connectedPeople"):
            # Preserve source-verified historical links if WDQS timed out.
            m["connectedPeople"]=[p for p in m["connectedPeople"] if p.get("verified")]
    for p in previous.values():
        if p["qid"] not in profiles:profiles[p["qid"]]=p
    results=sorted(profiles.values(),key=lambda p:p["qid"])
    return {
      "schemaVersion":"1.0","releaseChannel":"ALPINE_PEOPLE_LINKS","isPublished":True,
      "generatedAt":now,"entities":results,
      "status":"source_verified_not_full_biographical_dossiers"
    },{
      "municipalitiesConsidered":len(town_to_municipality),
      "peopleCatalogued":len(results),
      "municipalitiesWithPeople":sum(bool(m.get("connectedPeople")) for m in municipalities),
      "municipalityPeopleLinks":sum(len(m.get("connectedPeople",[])) for m in municipalities),
      "newLinksInRun":linked,
      "mountainLinks":sum(sum(p["category"]=="montagna" for p in m.get("connectedPeople",[])) for m in municipalities),
      "otherNotableLinks":sum(sum(p["category"]=="cultura_e_ricerca" for p in m.get("connectedPeople",[])) for m in municipalities),
      "errors":errors,
      "quality":"G1; no personal permalink or inferred ascent"
    }

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--municipalities",type=Path,required=True)
    p.add_argument("--people",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    release=load(args.municipalities)
    previous=load(args.people) if args.people.exists() else None
    people,report=build(release,previous_people=previous,checked_at=release.get("retrievedAt"))
    # Preserve earlier biographies; a provider failure must not zero out pages.
    save(args.municipalities,release)
    save(args.people,people)
    save(args.report,report)
    print(json.dumps({k:v for k,v in report.items() if k!="errors"},ensure_ascii=False))

if __name__=="__main__":main()
