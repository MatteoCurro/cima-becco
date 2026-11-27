#!/usr/bin/env python3
"""Compone hub delle Alte Vie solo con segmenti realmente nominati nei dati OSM.

Non presume la percorribilità o l'ordine delle tappe. Il numero di tappa si
deduce soltanto se scritto nel nome originale. Nessun merge di segmenti separati.
"""
import json
from pathlib import Path
import re
from datetime import datetime, timezone

DATA=Path(__file__).resolve().parent.parent/'public'/'data'
MANIFEST=DATA/'routes-manifest.json'
OUT=DATA/'trekking-projects.json'

PROJECTS=[
    ('alta-via-dolomiti-1','Alta Via delle Dolomiti n. 1','UN GIORNO NON BASTAVA?',
     'Tracce OSM collegate all\u2019Alta Via n. 1, senza inventare collegamenti o ordine di marcia.',
     re.compile(r'alta\s+via\s+(?:delle\s+dolomiti\s*)?(?:n\.?\s*)?(?:1|i)(?:\b|$)',re.I)),
    ('alta-via-dolomiti-2','Alta Via delle Dolomiti n. 2','PIÙ GIORNI, MENO SCUSE',
     'Segmenti OSM associati all\u2019Alta Via n. 2. Le tappe vengono nominate solo quando la fonte lo permette.',
     re.compile(r'alta\s+via\s+(?:delle\s+dolomiti\s*)?(?:n\.?\s*)?(?:2|ii)(?:\b|$)',re.I)),
    ('sentiero-italia','Sentiero Italia CAI','UNA PASSEGGIATINA. IN ITALIA.',
     'Catalogo delle sezioni del Sentiero Italia CAI identificate nel tracciato di origine.',
     re.compile(r'\bsentiero\s+italia\b|\bsi\s*-\s*cai\b',re.I)),
]


def stage_number(route):
    candidate=(route.get('name') or '')+' '+(route.get('trailRef') or '')
    m=re.search(r'\b(?:tappa|stage|etapa|giorno|day)\s*(?:n\.?\s*)?(\d{1,3})\b',candidate,re.I)
    return int(m.group(1)) if m and int(m.group(1))<=100 else None


def build(routes):
    projects=[]
    for slug,title,slogan,description,rx in PROJECTS:
        matched=[]
        for route in routes:
            # Non basta che un sentiero cada nelle Dolomiti: è necessario il nome OSM.
            evidence=' '.join(str(route.get(key) or '') for key in ('name','trailRef','network'))
            if rx.search(evidence):
                matched.append(route)
        stages={}
        for route in matched:
            no=stage_number(route)
            if no is not None:
                stages.setdefault(no,[]).append(route['slug'])
        projects.append({
            'slug':slug,'title':title,'slogan':slogan,'description':description,
            'routeSlugs':sorted({route['slug'] for route in matched}),
            'stages':[{'number':number,'routeSlugs':sorted(slugs)} for number,slugs in sorted(stages.items())],
        })
    return projects


def run():
    manifest=json.loads(MANIFEST.read_text(encoding='utf-8'))
    routes=[]
    for tile in manifest.get('tiles',[]):
        for rel in tile.get('files',[]):
            doc=json.loads((DATA/rel).read_text(encoding='utf-8'))
            routes.extend(doc.get('routes',[]))
    projects=build(routes)
    out={'generatedAt':datetime.now(timezone.utc).date().isoformat(),'projects':projects}
    text=json.dumps(out,ensure_ascii=False,separators=(',',':'))+'\n'
    existing=OUT.read_text(encoding='utf-8') if OUT.exists() else ''
    if existing!=text:
        OUT.write_text(text,encoding='utf-8')
    print(json.dumps({'groups':len(projects),'segments':{p['slug']:len(p['routeSlugs']) for p in projects}},ensure_ascii=False))


if __name__=='__main__':
    run()
