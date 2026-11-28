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
from urllib.parse import urlencode, quote, unquote
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import time
from enrich_municipalities_v1 import (WIKIDATA_API, WIKIDATA_QUERY, WIKIPEDIA_API,
    UA, commons_files, claim_string, NON_PHOTO)
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


# A profile stores externally verified facts without creating an account.
# The same stable 'person:QID' will link routes, ascents, opening events, and
# community profiles in a later, identity-verified claim workflow.
PUBLIC_ASSOCIATIONS={
  "P800":"notable_work",
  "P793":"significant_event",
  "P1344":"participant_in",
  "P463":"member_of",
  "P166":"award_received",
  "P101":"field_of_work",
}
# P18 links a file to a person but is not guaranteed to depict their face.
# Keep linked artwork in the archive; do not present documentary posters,
# monument details, signatures, or paintings of unrelated scenes as avatars.
NON_PORTRAIT_CONTEXT=re.compile(
  r"banner|filmretrospektive|allegori|monument|monumento|"
  r"firma(?:[_. -]|$)|signature|hagar|ismael|"
  r"споруда|храм|landscape|panorama|targa|plaque|"
  r"gravestone|tombstone|facade|facciata|architett|poster|locandina",
  re.I)
def portrait_candidate(filename):
    return not bool(NON_PORTRAIT_CONTEXT.search(unquote(filename).replace("_"," ")))

def safe_wikipedia_url(title):
    return "https://it.wikipedia.org/wiki/"+quote(title.replace(" ","_"),safe="")

def wiki_biographies(entries, *,getter=None):
    """Batch Wikipedia extracts, only if pageprops confirms exact person QID."""
    accepted={}
    indexed={title:qid for qid,title in entries if title and isinstance(title,str)}
    titles=list(indexed)
    for offset in range(0,len(titles),20):
        group=titles[offset:offset+20]
        data=api(WIKIPEDIA_API,{
          "action":"query","format":"json","prop":"pageprops|extracts",
          "ppprop":"wikibase_item","exintro":"1","explaintext":"1",
          "exchars":"1050","redirects":"1","titles":"|".join(group)},getter)
        for page in (data.get("query") or {}).get("pages",{}).values():
            title=page.get("title")
            qid=indexed.get(title)
            if not qid or (page.get("pageprops") or {}).get("wikibase_item")!=qid:
                continue
            contents=re.sub(r"\s+"," ",str(page.get("extract") or "")).strip()
            if len(contents)<110 or len(contents.split())<18:continue
            pid=page.get("pageid")
            if not isinstance(pid,int):continue
            accepted[qid]={
                "text":contents[:1050],"sourceId":"wikipedia:it:"+str(pid),
                "sourceUrl":safe_wikipedia_url(title),
                "licence":"CC BY-SA 4.0",
                "method":"reported","retrievedAt":None,"sourceUpdatedAt":None,
                "originalLanguage":"it","kind":"source_excerpt_not_original_editorial",
                "author":"Contributori di Wikipedia"
            }
    return accepted

def enrich_profiles(profiles, details, *,getter=None, checked_at=None):
    """Preserve existing biographies/media on temporary Wikimedia failures.

    All profile facts are public, sourced and non-sensitive. No inferred ascent
    and no personal accounts/contacts are imported or linked.
    """
    checked_at=checked_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    failed=[]
    missing=[qid for qid in profiles if qid not in details]
    for offset in range(0,len(missing),35):
        part=missing[offset:offset+35]
        try:details.update(detail_entities(part,getter))
        except Exception as exc:failed.append("wikidata:"+str(exc)[:120])
    portrait_requests={}
    for qid,profile in profiles.items():
        profile.setdefault("profileKind","biographical_person")
        profile.setdefault("claim",{"status":"not_enabled","requiresVerification":True,
                                    "verifiedUserId":None})
        profile.setdefault("sourceIds",{"wikidata":qid})
        item=details.get(qid)
        if not item or item.get("missing"):continue
        if "Q5" not in wd_claim_targets(item,"P31"):continue
        profile["profileKind"]="biographical_person"
        profile["sourceIds"]={"wikidata":qid}
        profile["claim"]={"status":"not_enabled","requiresVerification":True,
                          "verifiedUserId":None}
        profile["quality"]={"gate":"G1","seoIndexable":False}
        wd_source="https://www.wikidata.org/wiki/"+qid
        profile["checkedAt"]=checked_at
        profile["descriptionSourceUrl"]=wd_source
        profile["descriptionLicence"]="CC0"
        # Preserve provenance and precision: P569/P570 may be year only.
        for property_id,key in (("P569","birthDate"),("P570","deathDate")):
            value=wd_time(item,property_id)
            if value:
                profile[key]=value
                profile.setdefault("facts",{})[key]={
                  "value":value,"sourceId":"wikidata:"+qid+":"+property_id,
                  "sourceUrl":wd_source,"licence":"CC0","method":"reported",
                  "retrievedAt":checked_at}
        birthplace=sorted(wd_claim_targets(item,"P19"))
        deathplace=sorted(wd_claim_targets(item,"P20"))
        for key,values,prop in (("birthPlaceQids",birthplace,"P19"),
                                ("deathPlaceQids",deathplace,"P20")):
            if values:
                profile[key]=values
                profile.setdefault("facts",{})[key]={
                    "value":values[0],"sourceId":"wikidata:"+qid+":"+prop,
                    "sourceUrl":wd_source,"licence":"CC0","retrievedAt":checked_at,
                    "method":"reported"}
        aliases=[]
        for claim in (item.get("claims") or {}).get("P742",[]):
            value=((claim.get("mainsnak") or {}).get("datavalue") or {}).get("value")
            if claim.get("rank")!="deprecated" and isinstance(value,str) and 1<len(value)<=100:
                aliases.append(value)
        if aliases:
            profile["pseudonyms"]=sorted(set(aliases))[:12]
        associations=[]
        for prop,category in PUBLIC_ASSOCIATIONS.items():
            for target in sorted(wd_claim_targets(item,prop))[:18]:
                associations.append({
                  "type":category,"propertyId":prop,"targetQid":target,
                  "sourceId":"wikidata:"+qid+":"+prop,"sourceUrl":wd_source,
                  "licence":"CC0","method":"reported","retrievedAt":checked_at,
                  "resolution":"external_identity_only_not_atlas_entity"})
        if associations:profile["externalEntityLinks"]=associations[:80]
        image=claim_string(item,"P18")
        if image and not NON_PHOTO.search(image):
            portrait_requests[qid]=image
        labels=item.get("labels") or {}
        name=((labels.get("it") or labels.get("en") or {}).get("value") or "").strip()
        if name:profile["name"]=name[:180]
        description=((item.get("descriptions") or {}).get("it") or
           (item.get("descriptions") or {}).get("en") or {}).get("value")
        if isinstance(description,str) and description.strip():
            profile["description"]=description.strip()[:240]
        wiki=(item.get("sitelinks") or {}).get("itwiki",{}).get("title")
        if wiki:profile["wikipediaUrl"]=safe_wikipedia_url(wiki)
    images={}
    for start in range(0,len(portrait_requests),35):
        qids=list(portrait_requests)[start:start+35]
        try:images.update(commons_files([portrait_requests[q] for q in qids],getter=getter))
        except Exception as exc:failed.append("commons:"+str(exc)[:120])
    new_photos=0
    for qid,name in portrait_requests.items():
        media=images.get(name.replace(" ","_"))
        if not media:continue
        profile=profiles[qid]
        candidate=portrait_candidate(name)
        entry={**media,"id":"wikimedia-person:"+qid+":P18",
               "kind":"photo","retrievedAt":checked_at,
               "subjectMethod":"explicit_wikidata_P18_human_QID",
               "personQid":qid,"portraitCandidate":candidate,
               "needsPortraitReview":not candidate}
        existing=[m for m in profile.get("media",[])
                  if m.get("kind")=="photo" and m.get("sourceUrl")==entry["sourceUrl"]]
        profile["media"]=[entry]+[
            m for m in profile.get("media",[]) if m.get("id")!=entry["id"]
            and m.get("sourceUrl")!=entry["sourceUrl"]]
        if not existing:new_photos+=1
        if candidate:profile["avatarMediaId"]=entry["id"]
        else:profile.pop("avatarMediaId",None)
    biographies={}
    pending=[]
    for qid,profile in profiles.items():
        item=details.get(qid) or {}
        wiki=(item.get("sitelinks") or {}).get("itwiki",{}).get("title")
        if wiki and not profile.get("textSources"):pending.append((qid,wiki))
    for offset in range(0,len(pending),20):
        try:biographies.update(wiki_biographies(pending[offset:offset+20],getter=getter))
        except Exception as exc:failed.append("wikipedia:"+str(exc)[:120])
    for qid,source in biographies.items():
        source["retrievedAt"]=checked_at
        profiles[qid]["textSources"]=[source]
        profiles[qid]["biography"]=source["text"]
    return {
        "profilesProcessed":len(profiles),
        "portraitCandidates":len(portrait_requests),
        "portraitsAdded":new_photos,
        "profilesWithPortrait":sum(any(m.get("kind")=="photo" and m.get("portraitCandidate") and
            m.get("subjectVerified") for m in p.get("media",[])) for p in profiles.values()),
        "imagesHeldForReview":sum(any(m.get("needsPortraitReview") for m in p.get("media",[]))
            for p in profiles.values()),
        "biographiesAdded":len(biographies),
        "profilesWithBiography":sum(bool(p.get("textSources")) for p in profiles.values()),
        "associationsObserved":sum(len(p.get("externalEntityLinks",[])) for p in profiles.values()),
        "errors":failed
    }

def build(release,*,getter=None,previous_people=None,checked_at=None,batch=6,max_mountain=20,max_culture=4):
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
    detail_cache={}
    for offset in range(0,len(town_to_municipality),batch):
        part=list(town_to_municipality)[offset:offset+batch]
        try:
            candidates=sparql_candidates(part,getter=getter)
            details=detail_entities(sorted({c["person"] for c in candidates}),getter=getter)
            detail_cache.update(details)
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
            # A refreshed Wikidata identity never erases the earlier verified
            # picture, Wikipedia extract, or source links on transient errors.
            identity={**previous.get(c["person"],{}),**identity}
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
        def prominence(e):
            role=e["role"].casefold()
            if "guida alpina" in role or "alpinista" in role or "mountaineer" in role or "mountain guide" in role:
                return 0
            if "arrampic" in role or "climber" in role or "sci alpin" in role or "ski mountaineer" in role:
                return 1
            if "soccorso" in role or "mountain rescu" in role:
                return 2
            if "sciatore" in role or "fondista" in role or "ski" in role:
                return 3
            return 4
        ordered=sorted(unique.values(),key=lambda e:(0 if e["category"]=="montagna" else 1,
            prominence(e),priority[e["relationType"]],e["name"],e["personId"]))
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
    enrichment=enrich_profiles(profiles,detail_cache,getter=getter,checked_at=now)
    by_qid={p["qid"]:p for p in profiles.values()}
    # Cards of communes refer to canonical person profiles; only their photo
    # and a short bio are mirrored as a view-model, never a second identity.
    for commune in municipalities:
        for entry in commune.get("connectedPeople",[]):
            profile=by_qid.get(entry.get("qid"))
            if not profile:continue
            portrait=next((m for m in profile.get("media",[]) if m.get("kind")=="photo"
                        and m.get("subjectVerified") and m.get("reuseAllowed")),None)
            if portrait and portrait.get("portraitCandidate"):entry["portrait"]=portrait
            else:entry.pop("portrait",None)
            if profile.get("biography"):entry["biography"]=profile["biography"][:500]
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
      "mountainLinks":sum(sum(p.get("category")=="montagna" for p in m.get("connectedPeople",[])) for m in municipalities),
      "otherNotableLinks":sum(sum(p.get("category")=="cultura_e_ricerca" for p in m.get("connectedPeople",[])) for m in municipalities),
      "errors":errors+enrichment["errors"],
      "portraitsAdded":enrichment["portraitsAdded"],
      "profilesWithPortrait":enrichment["profilesWithPortrait"],
      "imagesHeldForReview":enrichment["imagesHeldForReview"],
      "biographiesAdded":enrichment["biographiesAdded"],
      "profilesWithBiography":enrichment["profilesWithBiography"],
      "associationsObserved":enrichment["associationsObserved"],
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
