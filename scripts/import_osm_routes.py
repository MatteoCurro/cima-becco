#!/usr/bin/env python3
"""Importa itinerari escursionistici OSM dal settore dolomitico pilota.

Richiede solo Python standard. Non inventa geometrie per colmare tratti mancanti.
Usa --input per prove offline e --write per aggiornare public/data/routes.json.
Dati OSM: © OpenStreetMap contributors (ODbL 1.0).
"""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
DEST = ROOT / 'public/data/routes.json'
API = 'https://overpass-api.de/api/interpreter'
# Area pilota Dolomiti: Fassa, Gardena, Badia, Cortina e Cadore occidentale.
BBOX = (46.37, 11.55, 46.79, 12.48)  # south, west, north, east


def haversine(a, b):
    lon1, lat1 = a[:2]; lon2, lat2 = b[:2]
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = p2 - p1; dl = math.radians(lon2 - lon1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742000 * math.asin(min(1, math.sqrt(h)))


def fetch_relations():
    s, w, n, e = BBOX
    # Relations only, with geometry on their member ways. No per-route API requests.
    query = (f'[out:json][timeout:80];relation["type"="route"]'
             f'["route"="hiking"]({s},{w},{n},{e});out body geom;')
    data = urlencode({'data': query}).encode()
    req = Request(API, data=data, headers={
        'User-Agent': 'CimaBecco/0.1 (+https://github.com/MatteoCurro/cima-becco)',
        'Accept': 'application/json',
    })
    with urlopen(req, timeout=110) as res:
        return json.load(res)


def segment_points(member):
    if member.get('type') != 'way':
        return []
    coords = []
    for p in member.get('geometry') or []:
        lng, lat = p.get('lon'), p.get('lat')
        if not isinstance(lng, (float, int)) or not isinstance(lat, (float, int)):
            return []
        if not 6 <= lng <= 19 or not 36 <= lat <= 48:
            return []
        point = [round(lng, 6), round(lat, 6), 0]
        if not coords or coords[-1][:2] != point[:2]:
            coords.append(point)
    return coords if len(coords) > 1 else []


def stitch(members):
    seen = set()
    remaining = []
    for member in members:
        if member.get('type') != 'way' or member.get('ref') in seen:
            continue
        seen.add(member.get('ref'))
        piece = segment_points(member)
        if piece:
            remaining.append(piece)
        else:
            return None  # incomplete relation: fail closed
    if not remaining or len(remaining) > 140:
        return None
    line = remaining.pop(0)
    while remaining:
        best = (float('inf'), None, None)
        for i, part in enumerate(remaining):
            options = [
                (haversine(line[-1], part[0]), 'tail'),
                (haversine(line[-1], part[-1]), 'tail_reverse'),
                (haversine(line[0], part[-1]), 'head'),
                (haversine(line[0], part[0]), 'head_reverse'),
            ]
            d, direction = min(options)
            if d < best[0]:
                best = (d, i, direction)
        d, i, direction = best
        if i is None or d > 12:
            return None  # no straight-line shortcuts across missing segments
        part = remaining.pop(i)
        if direction == 'tail':
            line.extend(part[1:])
        elif direction == 'tail_reverse':
            line.extend(list(reversed(part))[1:])
        elif direction == 'head':
            line = part[:-1] + line
        else:
            line = list(reversed(part))[:-1] + line
    return line


def simplify(points, tolerance_m=6):
    """Conservative Ramer-Douglas-Peucker (local equirectangular projection)."""
    if len(points) < 3:
        return points
    lat = sum(p[1] for p in points) / len(points)
    scale_x = 111320 * math.cos(math.radians(lat))
    xy = [(p[0] * scale_x, p[1] * 111320) for p in points]
    kept = {0, len(points) - 1}
    stack = [(0, len(points) - 1)]
    while stack:
        start, end = stack.pop()
        ax, ay = xy[start]; bx, by = xy[end]
        dx, dy = bx - ax, by - ay
        denom = dx * dx + dy * dy
        largest = 0.0; index = -1
        for i in range(start + 1, end):
            x, y = xy[i]
            t = max(0.0, min(1.0, ((x - ax) * dx + (y - ay) * dy) / denom)) if denom else 0
            sq = (x - ax - t * dx) ** 2 + (y - ay - t * dy) ** 2
            if sq > largest:
                largest = sq; index = i
        if index >= 0 and largest > tolerance_m ** 2:
            kept.add(index)
            stack.append((start, index)); stack.append((index, end))
    return [points[i] for i in sorted(kept)]


def to_route(relation):
    if relation.get('type') != 'relation':
        return None
    tags = relation.get('tags') or {}
    if tags.get('type') != 'route' or tags.get('route') != 'hiking':
        return None
    ref = (tags.get('ref') or '').strip()
    name = (tags.get('name:it') or tags.get('name') or '').strip()
    if not name and not ref:
        return None
    if not name:
        name = 'Sentiero ' + ref
    if len(name) > 120:
        return None
    points = stitch(relation.get('members') or [])
    if not points or len(points) < 8:
        return None
    length_m = sum(haversine(a, b) for a, b in zip(points, points[1:]))
    if not 800 <= length_m <= 45000:
        return None
    points = simplify(points)
    if not 2 <= len(points) <= 2500:
        return None
    rid = relation.get('id')
    if not isinstance(rid, int) or rid <= 0:
        return None
    is_loop = haversine(points[0], points[-1]) <= 60
    return {
        'slug': f'osm-hiking-{rid}',
        'name': name,
        'venueSlugs': [],
        'distanceM': round(length_m),
        'gainM': 0, 'lossM': 0, 'elevationAvailable': False,
        'loop': is_loop,
        'surface': 'trail',
        'coordinates': points,
        'source': 'curated',
        'description': 'Tracciato OSM da verificare sul terreno; non certifica percorribilità, condizioni o sicurezza.',
        'country': 'Italy',
        'sourceUrl': f'https://www.openstreetmap.org/relation/{rid}',
        'licence': 'ODbL 1.0 · © OpenStreetMap contributors',
        'activity': 'trail',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, help='JSON Overpass già salvato (test offline)')
    parser.add_argument('--write', action='store_true', help='Scrive routes.json; altrimenti è un dry-run')
    parser.add_argument('--max-routes', type=int, default=80)
    args = parser.parse_args()
    if not 1 <= args.max_routes <= 200:
        parser.error('--max-routes deve essere 1..200')
    document = json.loads(args.input.read_text(encoding='utf-8')) if args.input else fetch_relations()
    elements = document.get('elements')
    if not isinstance(elements, list):
        raise RuntimeError('Risposta Overpass incompleta: non modifico i dati pubblicati.')
    candidates = (to_route(row) for row in elements)
    accepted = sorted((r for r in candidates if r), key=lambda row: row['slug'])[:args.max_routes]
    if not accepted:
        raise RuntimeError('Nessun itinerario continuo valido: lascio invariato il catalogo.')
    existing = json.loads(DEST.read_text(encoding='utf-8')) if DEST.exists() else {'routes': []}
    routes = {route['slug']: route for route in existing.get('routes', [])}
    for route in accepted:
        routes[route['slug']] = route
    print(json.dumps({'relations': len(elements), 'accepted': len(accepted), 'totalRoutes': len(routes), 'dryRun': not args.write}, ensure_ascii=False))
    if args.write:
        DEST.parent.mkdir(parents=True, exist_ok=True)
        temp = DEST.with_suffix('.json.tmp')
        temp.write_text(json.dumps({'generatedAt': datetime.now(timezone.utc).date().isoformat(), 'routes': list(routes.values())}, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
        temp.replace(DEST)


if __name__ == '__main__':
    try:
        main()
    except (OSError, ValueError, RuntimeError) as exc:
        sys.exit(str(exc))
