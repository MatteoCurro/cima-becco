#!/usr/bin/env python3
"""Quota DEM per rifugi e borghi senza ele OSM, lotti riprendibili.

Usa esattamente il sampler Terrarium degli itinerari. Non sostituisce ele OSM,
né afferma che una quota DEM equivalga alla quota ufficiale del rifugio.
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import json
from pathlib import Path
import sys

DATA=Path(__file__).resolve().parents[1]/'public'/'data'
PLACES=DATA/'alpine-places.json'


def patch_elevation(places,sample,limit=160):
    attempted=updated=errors=0
    for item in places:
        if attempted>=limit:break
        if isinstance(item.get('elevationM'),(int,float)):
            continue
        if item.get('elevationDemLastError'):
            # Evita di riprovare continuamente un tile DEM che fallisce.
            continue
        attempted+=1
        try:
            value=sample(item['lng'],item['lat'])
            if value is None or not (0<float(value)<4800):
                errors+=1
                item['elevationDemLastError']='out_of_range'
                continue
            item['elevationM']=round(float(value))
            item['elevationSource']='dem'
            updated+=1
        except Exception as error:
            errors+=1
            # Non scrivere un errore definitivo: un tile S3 può fallire
            # temporaneamente e la prossima esecuzione potrà riuscire.
            print(f"DEM indisponibile per {item.get('slug')}: {error}",file=sys.stderr)
    return {'attempted':attempted,'filled':updated,'errors':errors}


def main(limit=160,write=False):
    # Import lazy: il modulo GPX esistente richiede Pillow, disponibile
    # nel workflow di enrichment ma non necessario ai test degli importer.
    from enrich_elevation import elevation
    dataset=json.loads(PLACES.read_text(encoding='utf-8'))
    places=dataset.get('places') or []
    outcome=patch_elevation(places,elevation,limit=limit)
    if write and outcome['filled']:
        dataset['elevationEnrichedAt']=datetime.now(timezone.utc).date().isoformat()
        tmp=PLACES.with_suffix('.json.tmp')
        tmp.write_text(json.dumps(dataset,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf-8')
        tmp.replace(PLACES)
    print(json.dumps(outcome,ensure_ascii=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--limit',type=int,default=160)
    parser.add_argument('--write',action='store_true')
    a=parser.parse_args()
    main(a.limit,a.write)
