#!/usr/bin/env python3
"""Cima Becco: acquisizione a lotti, riprendibile e incrementale dei sentieri OSM.

Eseguire da GitHub Actions con --write. Non richiede database o token:
gli shard geografici e il checkpoint sono file versionati. Non fare scraping.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sys
import time

from import_osm_routes import fetch_relations, to_route

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'public' / 'data'
TILES_DIR = DATA / 'routes-tiles'
STATUS = DATA / 'import-status.json'
MANIFEST = DATA / 'routes-manifest.json'
SHARD_SIZE = 200
SHARD_BYTES = 650_000  # geometrie compresse via HTTP, ma limitiamo anche i singoli JSON
REFRESH_DAYS = 45
# Aree sovrapposte soltanto per priorita: ogni cella ha un ID geografico unico.
# Le celle sono di un grado; le Dolomiti e le Alpi vengono lavorate per prime.
AREAS = [
    ('dolomiti', (46, 11, 48, 14)),
    ('alpi-occidentali', (44, 6, 48, 11)),
    ('alpi-orientali', (45, 13, 48, 17)),
    ('appennino-settentrionale', (43, 8, 46, 14)),
    ('appennino-centrale', (40, 10, 45, 16)),
    ('appennino-meridionale', (37, 13, 42, 19)),
    ('sardegna', (38, 8, 42, 10)),
    ('sicilia', (36, 12, 39, 16)),
]


def grid():
    """Tutte le celle nazionali, ordinate per priorita, senza doppioni."""
    cells = {}
    for area, (south, west, north, east) in AREAS:
        for lat in range(south, north):
            for lon in range(west, east):
                key = f'it_{lat}_{lon}'
                cells.setdefault(key, {'id': key, 'area': area,
                                       'bbox': [lat, lon, lat + 1, lon + 1]})
    return list(cells.values())


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')


def read_json(path, default):
    if not path.exists():
        return default
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + '.tmp')
    tmp.write_text(json.dumps(value, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    tmp.replace(path)


def due_cells(cells, status, now, force=False):
    records = status.get('tiles', {})
    unseen = [cell for cell in cells if cell['id'] not in records]
    if unseen:
        return unseen
    old = []
    for cell in cells:
        last = records.get(cell['id'], {}).get('lastSuccess')
        try:
            age = now - datetime.fromisoformat(last.replace('Z', '+00:00'))
        except (ValueError, TypeError, AttributeError):
            age = timedelta(days=999)
        if force or age >= timedelta(days=REFRESH_DAYS):
            old.append((age, cell))
    return [cell for _, cell in sorted(old, key=lambda value: -value[0].total_seconds())]


def in_own_cell(route, bbox):
    """L'assegnazione canonica per centro del bounding box evita doppie pubblicazioni."""
    pts = route.get('coordinates') or []
    if not pts:
        return False
    lng = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    lat = (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2
    south, west, north, east = bbox
    return south <= lat < north and west <= lng < east


def shard_files(tile_id, routes):
    """Separazione sia per numero tracce sia per bytes: il browser mobile non scarica file giganti."""
    chunks = []
    current = []
    size = 0
    for route in routes:
        weight = len(json.dumps(route, separators=(',', ':'), ensure_ascii=False).encode('utf-8'))
        if current and (len(current) >= SHARD_SIZE or size + weight > SHARD_BYTES):
            chunks.append(current)
            current = []
            size = 0
        current.append(route)
        size += weight
    if current:
        chunks.append(current)
    return [
        {'path': f'routes-tiles/{tile_id}_{n:03d}.json', 'routes': chunk}
        for n, chunk in enumerate(chunks)
    ]


def save_tile(cell, elements, status, now):
    tile_id, bbox = cell['id'], cell['bbox']
    routes = {}
    for element in elements:
        route = to_route(element)
        if route and in_own_cell(route, bbox):
            routes[route['slug']] = route

    # Stable order, no arbitrary 80/200-route cap: shard the result instead.
    listed = sorted(routes.values(), key=lambda row: row['slug'])
    previous = status.get('tiles', {}).get(tile_id, {})
    old_count = previous.get('count', 0)
    # Guard against an incomplete but technically valid upstream answer.
    if old_count and (not listed or (old_count >= 10 and len(listed) < old_count * 0.4)):
        raise RuntimeError(f'{tile_id}: upstream count collapsed from {old_count} to {len(listed)}; keep existing data')

    old_files = previous.get('files', [])
    old_enrichment = {}
    for path in old_files:
        doc = read_json(DATA / path, {'routes': []})
        for route in doc.get('routes', []):
            old_enrichment[route['slug']] = route

    for route in listed:
        former = old_enrichment.get(route['slug'], {})
        for key in ('photos',):
            if former.get(key) and not route.get(key):
                route[key] = former[key]
    pieces = shard_files(tile_id, listed)
    for piece in pieces:
        target = DATA / piece['path']
        current = read_json(target, {})
        # La data dell'aggiornamento non deve far riscrivere 200 geometrie immutate.
        if current.get('routes') != piece['routes']:
            write_json(target, {
                'generatedAt': now, 'source': 'OpenStreetMap', 'licence': 'ODbL-1.0',
                'routes': piece['routes'],
            })
    new_files = [p['path'] for p in pieces]
    for path in old_files:
        if path not in new_files:
            (DATA / path).unlink(missing_ok=True)

    status.setdefault('tiles', {})[tile_id] = {
        'area': cell['area'], 'bbox': bbox, 'lastSuccess': now,
        'count': len(listed), 'files': new_files,
        'slugs': [row['slug'] for row in listed],
        'sourceRelations': len(elements),
    }
    return len(listed)


def build_manifest(status, now):
    index = {cell['id']: cell for cell in grid()}
    tiles = []
    by_slug = {}
    for key in sorted(status.get('tiles', {})):
        if key not in index:
            continue
        state = status['tiles'][key]
        paths = state.get('files', [])
        if not paths:
            continue
        tiles.append({
            'id': key,
            'bbox': state['bbox'],
            'files': paths,
            'count': state['count'],
            'updatedAt': state['lastSuccess'],
        })
        slugs = state.get('slugs')
        if slugs is None:  # Retrocompatibilità con checkpoint precedenti.
            slugs = [
                route['slug']
                for path in paths
                for route in read_json(DATA / path, {'routes': []}).get('routes', [])
            ]
        for slug in slugs:
            by_slug[slug] = key
    return {
        'version': 1, 'generatedAt': now, 'tiles': tiles,
        'routeCount': len(by_slug), 'completedTiles': len(status.get('tiles', {})),
        'plannedTiles': len(index),
        'lookup': by_slug,
    }


def process(args):
    all_cells = grid()
    status = read_json(STATUS, {'version': 1, 'tiles': {}})
    now = datetime.now(timezone.utc)
    if args.tile:
        chosen = [cell for cell in all_cells if cell['id'] == args.tile]
        if not chosen:
            raise ValueError('Cella non presente nel piano: ' + args.tile)
    else:
        chosen = due_cells(all_cells, status, now, args.force)[:args.batch_size]
    if not chosen:
        print('Tutte le celle sono aggiornate: nessuna interrogazione Overpass necessaria.')
        return

    for cell in chosen:
        print(f"Acquisisco {cell['id']} ({cell['area']}) bbox={cell['bbox']}", flush=True)
        data = fetch_relations(cell['bbox'], retries=2)
        if args.write:
            count = save_tile(cell, data['elements'], status, timestamp())
            status['lastSuccess'] = timestamp()
            status['lastArea'] = cell['area']
            status['version'] = 1
            write_json(STATUS, status)
            write_json(MANIFEST, build_manifest(status, timestamp()))
        else:
            count = sum(1 for row in data['elements']
                        if (route := to_route(row)) and in_own_cell(route, cell['bbox']))
        print(f"{cell['id']}: {count} itinerari validi e assegnati alla cella", flush=True)
        if len(chosen) > 1 and cell != chosen[-1]:
            time.sleep(args.pause_seconds)

    manifest = build_manifest(status, timestamp())
    print(json.dumps({
        'plannedTiles': manifest['plannedTiles'], 'completedTiles': manifest['completedTiles'],
        'routeCount': manifest['routeCount'], 'lastArea': status.get('lastArea'),
    }, ensure_ascii=False), flush=True)
    summary_path = __import__('os').environ.get('GITHUB_STEP_SUMMARY')
    if summary_path and args.write:
        with open(summary_path, 'a', encoding='utf-8') as stream:
            stream.write(f"\n### Import Cima Becco\n"
                         f"- Celle: {manifest['completedTiles']} / {manifest['plannedTiles']}\n"
                         f"- Itinerari negli shard: {manifest['routeCount']}\n"
                         f"- Ultima area: {status.get('lastArea')}\n")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write', action='store_true', help='Salva checkpoint, manifest e shard')
    parser.add_argument('--tile', help='Riesegue una cella per ID (es. it_46_11)')
    parser.add_argument('--batch-size', type=int, default=2, help='Numero massimo di chiamate per esecuzione (1..3)')
    parser.add_argument('--pause-seconds', type=int, default=10, help='Intervallo fra chiamate Overpass')
    parser.add_argument('--force', action='store_true', help='Aggiorna le celle prima della scadenza')
    options = parser.parse_args()
    if not 1 <= options.batch_size <= 3 or not 0 <= options.pause_seconds <= 120:
        parser.error('batch-size 1..3, pause-seconds 0..120')
    try:
        process(options)
    except Exception as exc:
        sys.exit(f'Import non completato, dati precedenti conservati: {exc}')
