#!/usr/bin/env python3
"""Foto per itinerari da Wikimedia Commons, soltanto con corrispondenza forte.

Requisiti: titolo coerente col nome, coordinate del file prossime al GPX,
licenza esplicita compatibile, URL Commons e dimensioni adeguate.
Niente foto generiche "nelle vicinanze"; nessuna foto è meglio di una foto falsa.
"""
from __future__ import annotations
from datetime import datetime, timezone
import argparse
import html
import json
import math
from pathlib import Path
import re
import sys
import time
import unicodedata
from urllib.parse import urlencode
from urllib.request import Request, urlopen

DATA = Path(__file__).resolve().parent.parent / 'public' / 'data'
STATUS = DATA / 'route-photo-status.json'
API = 'https://commons.wikimedia.org/w/api.php'
STOP = {'via','ferrata','sentiero','delle','della','degli','del','dei','alla','alle',
        'percorso','anello','sulla','sulle','italia','dolomiti','monte','passo','alta',
        'sentieri','trail','cai','hiking','route','red','green','blue','nord','sud'}


def normalize(text):
    value = unicodedata.normalize('NFD', text.lower())
    value = ''.join(c for c in value if unicodedata.category(c) != 'Mn')
    return re.findall(r'[a-z0-9]{3,}', value)


def distinctive(name):
    return [s for s in normalize(name) if s not in STOP and not s.isdigit() and len(s) >= 5]


def matches_name(route_name, filename):
    keys = distinctive(route_name)
    if not keys:
        return False
    title = set(normalize(filename.replace('File:', '').replace('_', ' ')))
    needed = 2 if len(keys) >= 3 else 1
    return sum(1 for key in keys if key in title) >= needed


def distance_m(a, b):
    lng1, lat1 = map(math.radians, a[:2])
    lng2, lat2 = map(math.radians, b[:2])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lng2-lng1)/2)**2
    return 12742000*math.asin(min(1,math.sqrt(h)))


def route_near(route, lng, lat):
    pts = route['coordinates']
    if not pts:
        return False
    stride = max(1, len(pts)//180)
    return min(distance_m([lng, lat], point) for point in pts[::stride]) <= 1000


def get(query):
    request = Request(API+'?'+urlencode({'format':'json','formatversion':2,**query}),
        headers={'User-Agent':'CimaBecco/0.2 (academic hiking map; github.com/MatteoCurro/cima-becco)'})
    with urlopen(request, timeout=18) as res:
        return json.load(res)


def clean(text):
    return html.unescape(re.sub(r'<[^>]+>', ' ', text or '')).strip()


def photo_from_page(route, page):
    if not matches_name(route['name'], page.get('title', '')):
        return None
    info = (page.get('imageinfo') or [None])[0]
    coords = (page.get('coordinates') or [None])[0]
    if not info or not coords or 'lat' not in coords or 'lon' not in coords:
        return None
    if not route_near(route, coords['lon'], coords['lat']):
        return None
    meta = info.get('extmetadata') or {}
    license_name = clean(meta.get('LicenseShortName', {}).get('value', ''))
    if not re.search(r'^(?:CC[- ]?BY|CC0|Public domain|PD[- ])',license_name, re.I):
        return None
    source = info.get('descriptionurl', '')
    url = info.get('thumburl') or info.get('url', '')
    if not source.startswith('https://commons.wikimedia.org/') or not url.startswith('https://'):
        return None
    if info.get('width',0) < 900:
        return None
    return {
        'url': url,
        'sourceUrl': source,
        'author': clean(meta.get('Artist', {}).get('value', ''))[:140] or 'Wikimedia Commons',
        'license': license_name,
        'caption': 'Fotografia geolocalizzata nelle vicinanze del tracciato',
    }


def find_photo(route):
    keys = distinctive(route['name'])
    if not keys:
        return None
    query = ' '.join(keys[:4])
    data = get({'action':'query','list':'search','srsearch':query,
                'srnamespace':6,'srlimit':8})
    names = [x['title'] for x in data.get('query',{}).get('search',[])
             if matches_name(route['name'], x.get('title',''))]
    if not names:
        return None
    # Verifica metadati e coordinate degli stessi file prima di usarli.
    pages = get({'action':'query','prop':'imageinfo|coordinates','titles':'|'.join(names[:8]),
                 'iiprop':'url|extmetadata|size','iiurlwidth':1000,'colimit':1}).get('query',{}).get('pages',[])
    for page in pages:
        photo = photo_from_page(route,page)
        if photo:
            return photo
    return None


def save_json(path, data):
    tmp = path.with_name(path.name+'.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False,separators=(',',':'))+'\n', encoding='utf-8')
    tmp.replace(path)


def run(limit, write):
    manifest = json.loads((DATA/'routes-manifest.json').read_text())
    status = json.loads(STATUS.read_text()) if STATUS.exists() else {'checked':{},'version':1}
    checked=status.setdefault('checked',{})
    today = datetime.now(timezone.utc).date().isoformat()
    attempted, found, errors = 0, 0, 0
    for tile in manifest.get('tiles', []):
        for rel in tile.get('files', []):
            path=DATA/rel
            data=json.loads(path.read_text(encoding='utf-8'))
            changed=False
            for route in data.get('routes',[]):
                if attempted>=limit: break
                slug=route.get('slug','')
                if route.get('photos') or not distinctive(route.get('name','')):
                    continue
                last=checked.get(slug,'')
                if last and (datetime.now(timezone.utc).date()-datetime.fromisoformat(last).date()).days < 90:
                    continue
                attempted+=1
                try:
                    photo=find_photo(route)
                    checked[slug]=today
                    if photo:
                        route['photos']=[photo]
                        changed=True
                        found+=1
                except Exception as exc:
                    errors+=1
                    print(f'Commons {slug}: {exc}',file=sys.stderr)
                time.sleep(1)
            if changed and write:
                save_json(path,data)
            if attempted>=limit:break
        if attempted>=limit:break
    status.update({'version':1,'updatedAt':datetime.now(timezone.utc).isoformat(timespec='seconds'),
                   'attemptedLastRun':attempted,'matchedLastRun':found,'errorsLastRun':errors})
    if write:
        save_json(STATUS,status)
    print(json.dumps({'attempted':attempted,'matched':found,'errors':errors,
                      'totalChecked':len(checked)},ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write',action='store_true')
    parser.add_argument('--max-routes',type=int,default=30)
    args=parser.parse_args()
    if not 1<=args.max_routes<=120:parser.error('max-routes deve essere 1..120')
    run(args.max_routes,args.write)
