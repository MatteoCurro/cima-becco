#!/usr/bin/env python3
"""Import di sorgenti idriche OSM e collegamento per prossimità ai tracciati.

ATTENZIONE: una sorgente naturale non è automaticamente potabile e la sua
presenza nel dataset non garantisce acqua disponibile sul terreno.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
import re
import sys
from urllib.parse import urlencode
from urllib.request import Request,urlopen
from import_alpine_places import DATA,MANIFEST,ENDPOINTS,BBOX,projection_distance_m,read_json,write_json,clean_name

OUT=DATA/'alpine-water.json'


def fetch_water():
    south,west,north,east=BBOX
    rect=f"({south},{west},{north},{east})"
    query=(
        "[out:json][timeout:65];("
        f'nwr["amenity"="drinking_water"]{rect};'
        f'nwr["natural"="spring"]{rect};'
        f'nwr["amenity"="fountain"]["drinking_water"="yes"]{rect};'
        f'nwr["man_made"="water_tap"]["drinking_water"="yes"]{rect};'
        ");out center tags;"
    )
    for endpoint in ENDPOINTS:
        try:
            req=Request(endpoint,data=urlencode({'data':query}).encode('utf-8'),
               headers={'User-Agent':'CimaBecco/0.2 (https://github.com/MatteoCurro/cima-becco)',
                        'Content-Type':'application/x-www-form-urlencoded'})
            with urlopen(req,timeout=82) as res:
                doc=json.load(res)
            if not isinstance(doc.get('elements'),list):
                raise ValueError('Risposta Overpass non valida')
            return doc['elements']
        except Exception as exc:
            print(f'Overpass water: {endpoint}: {exc}',file=sys.stderr)
    raise RuntimeError('Impossibile importare le fonti idriche. Mantieni i dati precedenti.')


def to_water(row):
    tags=row.get('tags') or {}
    point=row.get('center') or row
    lat,lng=point.get('lat'),point.get('lon')
    if not isinstance(lat,(float,int)) or not isinstance(lng,(float,int)):
        return None
    if tags.get('amenity')=='drinking_water':kind='fontanella'
    elif tags.get('natural')=='spring':kind='sorgente'
    elif tags.get('amenity')=='fountain':kind='fontanella'
    elif tags.get('man_made')=='water_tap':kind='rubinetto'
    else:return None
    if tags.get('drinking_water')=='no' or tags.get('potable')=='no':
        potable='no'
    elif tags.get('amenity')=='drinking_water' or tags.get('drinking_water')=='yes' or tags.get('potable')=='yes':
        potable='yes'
    else:potable='unknown'
    return {
        'slug':f"osm-{row.get('type','node')[0]}-{row['id']}",
        'name':clean_name(tags.get('name:it') or tags.get('name')) or ('Sorgente' if kind=='sorgente' else 'Punto acqua'),
        'kind':kind,'potable':potable,
        'lat':round(lat,6),'lng':round(lng,6),
        'osmUrl':f"https://www.openstreetmap.org/{row.get('type','node')}/{row['id']}",
        **({'seasonal':True} if tags.get('seasonal')=='yes' else {}),
    }


def route_water(route,waters):
    pts=route.get('coordinates') or []
    if len(pts)<2:return []
    west=min(p[0] for p in pts);east=max(p[0] for p in pts)
    south=min(p[1] for p in pts);north=max(p[1] for p in pts)
    matches=[]
    for item in waters:
        lng,lat=item['lng'],item['lat']
        if not(west-.002<=lng<=east+.002 and south-.002<=lat<=north+.002):
            continue
        best=1e9;at=0
        for i,(a,b) in enumerate(zip(pts,pts[1:])):
            d=projection_distance_m((lng,lat),a,b)
            if d<best:best,at=d,i
            if best<10:break
        if best>120:continue
        matches.append({
            'slug':item['slug'],'name':item['name'],'kind':item['kind'],
            'potable':item['potable'],'distanceM':round(best),
            'at':round(at/max(1,len(pts)-1),3),
        })
    matches.sort(key=lambda x:(x['at'],x['distanceM']))
    return matches[:20]


def connect(waters):
    manifest=read_json(MANIFEST,{'tiles':[]})
    checked=has_water=changed=0
    for tile in manifest.get('tiles',[]):
        for rel in tile.get('files',[]):
            path=DATA/rel
            doc=read_json(path,{'routes':[]})
            dirty=False
            for route in doc.get('routes',[]):
                new=route_water(route,waters)
                checked+=1;has_water+=bool(new)
                if route.get('waterSources',[])!=new:
                    if new:route['waterSources']=new
                    else:route.pop('waterSources',None)
                    dirty=True
            if dirty and write_json(path,doc):changed+=1
    return {'routesChecked':checked,'routesNearWater':has_water,'shardsChanged':changed}


def main(write=False,link_only=False):
    if link_only:
        waters=read_json(OUT,{'sources':[]}).get('sources',[])
    else:
        waters=sorted(
            {item['slug']:item for raw in fetch_water() if (item:=to_water(raw))}.values(),
            key=lambda x:x['slug'])
        if write:write_json(OUT,{'generatedAt':datetime.now(timezone.utc).date().isoformat(),
            'source':'OpenStreetMap · ODbL 1.0',
            'coverage':'Dolomiti (pilota)','sources':waters})
    outcome={'sources':len(waters),'potableConfirmed':sum(i['potable']=='yes' for i in waters),
             'potabilityUnknown':sum(i['potable']=='unknown' for i in waters)}
    if write:outcome.update(connect(waters))
    print(json.dumps(outcome,ensure_ascii=False))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--write',action='store_true');p.add_argument('--link-only',action='store_true')
    args=p.parse_args();main(args.write,args.link_only)
