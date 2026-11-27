#!/usr/bin/env python3
"""Foto dell'atlante da OSM Commons File / Wikidata P18, mai da ricerca di nomi.

Provenienza univoca: OSM del luogo con File: oppure QID P18.
Licenza/attribuzione verificata sulle API Commons, nessuna foto per prossimità.
"""
from __future__ import annotations
import argparse,html,json,re,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request,urlopen

ROOT=Path(__file__).resolve().parent.parent
SOURCE=ROOT/'public/data/alpine-places.json'
UA='CimaBecco atlas enrichment/0.2 (https://github.com/MatteoCurro/cima-becco)'
WIKIDATA='https://www.wikidata.org/w/api.php'
COMMONS='https://commons.wikimedia.org/w/api.php'
VALID_LICENSE=re.compile(r'^(?:CC\s?BY|CC0|PD-|Public Domain|Copyrighted-free|CC\s?0)',re.I)


def request(url,params):
    full=url+'?'+urlencode(params)
    req=Request(full,headers={'User-Agent':UA,'Accept':'application/json'})
    with urlopen(req,timeout=30) as response:return json.load(response)


def chunks(items,n=20):
    for i in range(0,len(items),n):yield items[i:i+n]


def fetch_p18(qids):
    answers={}
    for batch in chunks(qids,20):
        data=request(WIKIDATA,{'action':'wbgetentities','format':'json','ids':'|'.join(batch),'props':'claims'})
        for qid,entity in data.get('entities',{}).items():
            for claim in entity.get('claims',{}).get('P18',[]):
                filename=claim.get('mainsnak',{}).get('datavalue',{}).get('value')
                if isinstance(filename,str) and filename.strip():
                    answers[qid]=filename.strip();break
        time.sleep(1.4)
    return answers


def plain(text):
    return html.unescape(re.sub(r'<[^>]*>',' ',str(text or ''))).strip()[:180]


def commons_photos(filenames):
    results={}
    for batch in chunks(sorted(set(filenames)),15):
        titles='|'.join('File:'+fn.replace('_',' ') for fn in batch)
        data=request(COMMONS,{
            'action':'query','format':'json','titles':titles,'prop':'imageinfo',
            'iiprop':'url|extmetadata','iiurlwidth':'960','redirects':'1',
        })
        for page in data.get('query',{}).get('pages',{}).values():
            info=(page.get('imageinfo') or [None])[0]
            if not info:continue
            meta=info.get('extmetadata') or {}
            short=plain(meta.get('LicenseShortName',{}).get('value'))
            if not VALID_LICENSE.match(short):continue
            author=plain(meta.get('Artist',{}).get('value') or info.get('user',''))
            filename=page.get('title','').removeprefix('File:')
            image=info.get('thumburl') or info.get('url','')
            if not image.startswith('https://upload.wikimedia.org/'):continue
            results[filename.replace('_',' ').casefold()]={
                'url':image,'sourceUrl':'https://commons.wikimedia.org/wiki/File:'+filename.replace(' ','_'),
                'license':short,'author':author or 'Autore nella pagina Commons',
                'licenseUrl':plain(meta.get('LicenseUrl',{}).get('value')),
            }
        time.sleep(1.4)
    return results


def run(limit=75,write=False):
    data=json.loads(SOURCE.read_text(encoding='utf-8'))
    places=data.get('places',[])
    targets=[p for p in places if not p.get('photo') and not p.get('photoCheckedAt')
             and (p.get('commonsFile') or re.fullmatch(r'Q\d+',p.get('wikidata','')))]
    # Prima OSM File: espliciti, poi rifugi, poi località con sito verificabile.
    # La scansione alfabetica dei villaggi senza foto ha finora prodotto 0 immagini.
    targets.sort(key=lambda p:(not bool(p.get('commonsFile')),p.get('kind')!='rifugio',
                               not bool(p.get('website')),p.get('name','').casefold()))
    targets=targets[:max(0,min(300,limit))]
    qids=sorted(set(p['wikidata'] for p in targets if not p.get('commonsFile') and p.get('wikidata')))
    p18=fetch_p18(qids) if qids else {}
    names={p['slug']:p.get('commonsFile') or p18.get(p.get('wikidata','')) for p in targets}
    found=commons_photos([name for name in names.values() if name]) if any(names.values()) else {}
    today=datetime.now(timezone.utc).date().isoformat()
    saved=0
    for p in targets:
        name=names.get(p['slug']) or ''
        photo=found.get(name.replace('_',' ').casefold())
        if photo:
            p['photo']=photo
            saved+=1
        p['photoCheckedAt']=today
    if write and targets:
        txt=json.dumps(data,ensure_ascii=False,separators=(',',':'))+'\n'
        SOURCE.write_text(txt,encoding='utf-8')
    print(json.dumps({'considered':len(targets),'withPhoto':saved,
                      'remainingCandidates':len([p for p in places if not p.get('photo') and not p.get('photoCheckedAt')
                      and (p.get('commonsFile') or p.get('wikidata'))])}))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=75)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    run(args.limit,args.write)
