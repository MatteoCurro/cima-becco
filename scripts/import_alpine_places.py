#!/usr/bin/env python3
"""Atlante dei borghi alpini e dei rifugi. Import Overpass incrementale (ODbL).

Fonte OSM puntuale: solo località e strutture effettivamente presenti.
Una geolocalizzazione vicina a un sentiero non implica che sia raggiungibile.
Le associazioni ai sentieri usano una distanza geodetica dal polilinea GPX.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATA = Path(__file__).resolve().parent.parent / "public" / "data"
OUT = DATA / "alpine-places.json"
MANIFEST = DATA / "routes-manifest.json"
ENDPOINTS = ("https://overpass.kumi.systems/api/interpreter", "https://overpass.nchc.org.tw/api/interpreter", "https://overpass-api.de/api/interpreter")
# Pilota Dolomiti: allargare a celle, non caricare l'intero arco alpino in un'unica richiesta.
BBOX = (46.28, 11.15, 46.95, 12.95)
BANNED = re.compile(r"^(?:unnamed|senza nome|rifugio|hut|bivacco|unknown)$", re.I)


def fetch_places():
    south, west, north, east = BBOX
    rect = f"({south},{west},{north},{east})"
    query = (
        "[out:json][timeout:65];("
        f'nwr["tourism"~"^(alpine_hut|wilderness_hut)$"]{rect};'
        f'nwr["place"~"^(town|village|hamlet)$"]{rect};'
        ");out center tags;"
    )
    last = None
    for endpoint in ENDPOINTS:
        try:
            request = Request(endpoint, data=urlencode({"data": query}).encode(),
                headers={"User-Agent": "CimaBecco/0.2 (open-source mountaineering atlas; https://github.com/MatteoCurro/cima-becco)",
                         "Content-Type": "application/x-www-form-urlencoded"})
            with urlopen(request, timeout=82) as response:
                data = json.load(response)
            if not isinstance(data.get("elements"), list):
                raise ValueError("Overpass senza elementi")
            return data["elements"]
        except Exception as error:
            last = error
            print(f"Overpass non disponibile da {endpoint}: {error}", file=sys.stderr)
    raise RuntimeError(f"Tutti i servizi Overpass hanno fallito: {last}")


def clean_name(text):
    return re.sub(r"\s+", " ", str(text or "").strip())[:110]


def sanitize_url(text):
    url = (text or "").strip()
    return url[:350] if url.startswith("https://") and " " not in url else None


def parse_item(row):
    tags = row.get("tags") or {}
    name = clean_name(tags.get("name:it") or tags.get("name"))
    if len(name) < 3 or BANNED.fullmatch(name):
        return None
    pt = row.get("center") or row
    lat, lng = pt.get("lat"), pt.get("lon")
    if not isinstance(lat, (int,float)) or not isinstance(lng, (int,float)):
        return None
    kind = "rifugio" if tags.get("tourism") in ("alpine_hut", "wilderness_hut") else (
        "borgo" if tags.get("place") in ("town", "village", "hamlet") else None)
    if not kind:
        return None
    ident = f"osm-{row.get('type','node')[0]}-{row['id']}"
    elevation = tags.get("ele", "")
    try:
        ele = float(re.search(r"-?\d+(?:\.\d+)?", elevation).group(0)) if elevation else None
    except (ValueError,AttributeError):
        ele = None
    return {
        "slug": ident, "name": name, "kind": kind, "lat": round(lat,6), "lng": round(lng,6),
        "osmUrl": f"https://www.openstreetmap.org/{row.get('type','node')}/{row['id']}",
        **({"elevationM": round(ele)} if ele is not None and 0 < ele < 4800 else {}),
        **({"wikidata": tags["wikidata"]} if re.fullmatch(r"Q\d+", tags.get("wikidata","")) else {}),
        **({"website": sanitize_url(tags.get("website"))} if sanitize_url(tags.get("website")) else {}),
        **({"operator": clean_name(tags["operator"])} if tags.get("operator") else {}),
        **({"description": clean_name(tags.get("description:it") or tags["description"])[:320]}
            if (tags.get("description:it") or tags.get("description")) else {}),
        **({"openingHours": clean_name(tags["opening_hours"])} if tags.get("opening_hours") else {}),
        **({"phone": clean_name(tags.get("contact:phone") or tags.get("phone"))[:48]}
            if (tags.get("contact:phone") or tags.get("phone")) else {}),
        **({"email": clean_name(tags.get("contact:email") or tags.get("email"))[:120]}
            if (tags.get("contact:email") or tags.get("email")) else {}),
        **({"address": ", ".join(str(tags[key]).strip() for key in
            ("addr:street", "addr:housenumber", "addr:city") if tags.get(key))[:200]}
            if any(tags.get(k) for k in ("addr:street","addr:housenumber","addr:city")) else {}),
        **({"commonsFile": clean_name(tags["wikimedia_commons"])[5:]}
            if tags.get("wikimedia_commons","").startswith("File:") else {}),
        **({"wikipedia": clean_name(tags["wikipedia"])}
            if re.fullmatch(r"[a-z]{2,3}:.+", tags.get("wikipedia","")) else {}),
        **({"capacity": int(tags["beds"])}
            if tags.get("beds","").isdigit() and 0<int(tags["beds"])<2000 else {}),

    }


def projection_distance_m(pt, a, b):
    # Proiezione equirettangolare locale alla latitudine del punto, in metri.
    latrad=math.radians(pt[1])
    kx=111320*math.cos(latrad)
    ky=111195
    ax, ay=(a[0]-pt[0])*kx, (a[1]-pt[1])*ky
    bx, by=(b[0]-pt[0])*kx, (b[1]-pt[1])*ky
    dx,dy=bx-ax,by-ay
    t=max(0.,min(1.,-(ax*dx+ay*dy)/max(1.,dx*dx+dy*dy)))
    return math.hypot(ax+t*dx,ay+t*dy)


def route_stops(route, places):
    points=route.get("coordinates") or []
    if len(points)<2:
        return []
    west=min(pt[0] for pt in points);east=max(pt[0] for pt in points)
    south=min(pt[1] for pt in points);north=max(pt[1] for pt in points)
    res=[]
    loop=route.get("loop") is True
    for item in places:
        lng,lat=item["lng"],item["lat"]
        if not (west-.01<=lng<=east+.01 and south-.01<=lat<=north+.01):
            continue
        threshold=180 if item["kind"]=="rifugio" else 350
        best=1e9;index=0
        for i in range(0,len(points)-1):
            # punto contro segmento, include tratti lunghi semplificati
            d=projection_distance_m((lng,lat),points[i],points[i+1])
            if d<best:
                best,index=d,i
            if best<12:break
        if best>threshold:
            continue
        progress=index/max(1,len(points)-1)
        if not loop and progress < .1: relation="partenza"
        elif not loop and progress > .9: relation="arrivo"
        else:relation="passaggio"
        res.append({"slug":item["slug"],"name":item["name"],"kind":item["kind"],
                    "relation":relation,"distanceM":round(best),"at":round(progress,3)})
    # In caso di molte località selezionare quelle più pertinenti, evitando risultati casuali.
    res.sort(key=lambda row: (row["at"],row["distanceM"]))
    return res[:15]


def read_json(path,default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def write_json(path,data):
    text=json.dumps(data,ensure_ascii=False,separators=(",",":"))+"\n"
    if path.exists() and path.read_text(encoding="utf-8")==text:
        return False
    tmp=path.with_suffix(path.suffix+".tmp")
    tmp.write_text(text,encoding="utf-8")
    tmp.replace(path)
    return True


def save_stops(places):
    manifest=read_json(MANIFEST, {"tiles":[]})
    checked=linked=changed=0
    for tile in manifest.get("tiles",[]):
        for rel in tile.get("files",[]):
            path=DATA / rel
            doc=read_json(path,{"routes":[]})
            dirty=False
            for route in doc.get("routes",[]):
                stops=route_stops(route,places)
                checked+=1
                if stops:linked+=1
                if route.get("stops",[])!=stops:
                    if stops:route["stops"]=stops
                    else:route.pop("stops",None)
                    dirty=True
            if dirty and write_json(path,doc):
                changed+=1
    return {"routesChecked":checked,"routesWithStops":linked,"shardsUpdated":changed}


def run(write,link_only):
    if link_only:
        places=read_json(OUT,{"places":[]}).get("places",[])
        if not places:
            print("Nessun POI disponibile. Importa prima l'atlante.")
            return
    else:
        elements=fetch_places()
        unique={}
        for row in elements:
            item=parse_item(row)
            if item:unique[item["slug"]]=item
        places=sorted(unique.values(),key=lambda p:(p["kind"],p["name"].casefold(),p["slug"]))
        old_places={p["slug"]:p for p in read_json(OUT,{"places":[]}).get("places",[])}
        # L'aggiornamento settimanale OSM non deve cancellare foto già verificate,
        # né informazioni editoriali approvate da un eventuale gestore.
        for place in places:
            former=old_places.get(place["slug"],{})
            for field in ("photo","photoCheckedAt"):
                if field in former and field not in place:
                    place[field]=former[field]
        if write:write_json(OUT,{"generatedAt":datetime.now(timezone.utc).date().isoformat(),"source":"OpenStreetMap · ODbL 1.0",
                               "coverage":"Dolomiti (pilota)", "places":places})
    counts={"rifugi":sum(p["kind"]=="rifugio" for p in places),
            "borghi":sum(p["kind"]=="borgo" for p in places)}
    if write:
        counts.update(save_stops(places))
    print(json.dumps(counts,ensure_ascii=False))


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--write",action="store_true")
    parser.add_argument("--link-only",action="store_true")
    args=parser.parse_args()
    run(args.write,args.link_only)
