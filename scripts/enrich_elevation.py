#!/usr/bin/env python3
"""Arricchisce progressivamente i GPX OSM con altimetria DEM Terrarium su AWS.

Dati stimati e non certificati: conserva la geometria originale XY, calcola
dislivello e quote da tile del terreno. Non modifica i percorsi se fallisce
l'acquisizione di un tile. Richiede Pillow, solo in GitHub Actions.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
from io import BytesIO
import json
import math
from pathlib import Path
import sys
import time
from urllib.request import Request, urlopen
from PIL import Image

DATA = Path(__file__).resolve().parent.parent / 'public' / 'data'
ZOOM = 12
SIZE = 256
TERRARIUM = 'https://elevation-tiles-prod.s3.amazonaws.com/terrarium'
CACHE = {}
MAX_CACHE = 180


def world_pixel(lon, lat):
    size = SIZE * 2 ** ZOOM
    lat = max(-85, min(85, lat))
    sin = math.sin(math.radians(lat))
    return ((lon + 180) / 360 * size,
            (0.5 - math.log((1 + sin) / (1 - sin)) / (4 * math.pi)) * size)


def load_tile(tx, ty):
    key = (tx, ty)
    if key not in CACHE:
        url = f'{TERRARIUM}/{ZOOM}/{tx}/{ty}.png'
        for attempt in range(2):
            try:
                req = Request(url, headers={'User-Agent': 'CimaBecco/0.2 (hiking DEM enrichment)'})
                with urlopen(req, timeout=20) as response:
                    raw = response.read()
                with Image.open(BytesIO(raw)) as pic:
                    CACHE[key] = pic.convert('RGB').copy()
                break
            except Exception:
                if attempt:
                    raise
                time.sleep(2)
        if len(CACHE) > MAX_CACHE:
            first = next(iter(CACHE))
            CACHE[first].close()
            del CACHE[first]
    return CACHE[key]


def pixel(x, y):
    ix, iy = math.floor(x), math.floor(y)
    tile = load_tile(ix // SIZE, iy // SIZE)
    r, g, b = tile.getpixel((ix % SIZE, iy % SIZE))
    return r * 256 + g + b / 256 - 32768


def elevation(lon, lat):
    x, y = world_pixel(lon, lat)
    x0, y0 = math.floor(x - 0.5), math.floor(y - 0.5)
    dx, dy = x - 0.5 - x0, y - 0.5 - y0
    a, b = pixel(x0, y0), pixel(x0 + 1, y0)
    c, d = pixel(x0, y0 + 1), pixel(x0 + 1, y0 + 1)
    return (a * (1 - dx) + b * dx) * (1 - dy) + (c * (1 - dx) + d * dx) * dy


def haversine(a, b):
    lon1, lat1 = map(math.radians, a[:2])
    lon2, lat2 = map(math.radians, b[:2])
    v = math.sin((lat2 - lat1) / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    return 12742000 * math.asin(min(1, math.sqrt(v)))


def samples(points, step=65, max_points=210):
    if len(points) < 2:
        return [0] if points else []
    indices = [0]
    distance = 0
    for i in range(1, len(points) - 1):
        distance += haversine(points[i - 1], points[i])
        if distance >= step:
            indices.append(i)
            distance = 0
    indices.append(len(points) - 1)
    if len(indices) > max_points:
        skip = math.ceil(len(indices) / max_points)
        indices = indices[::skip]
        if indices[-1] != len(points) - 1:
            indices.append(len(points) - 1)
    return indices


def gain_loss(heights, smooth=5, threshold=3):
    if len(heights) < 2:
        return 0, 0
    half = smooth // 2
    filtered = [sum(heights[max(0,i-half):min(len(heights),i+half+1)]) /
                len(heights[max(0,i-half):min(len(heights),i+half+1)]) for i in range(len(heights))]
    anchor, gain, loss = filtered[0], 0., 0.
    for height in filtered[1:]:
        delta = height - anchor
        if delta >= threshold:
            gain += delta
            anchor = height
        elif delta <= -threshold:
            loss -= delta
            anchor = height
    return round(gain), round(loss)


def enrich(route):
    points = route.get('coordinates') or []
    if len(points) < 2 or route.get('elevationAvailable') is not False:
        return False
    indices = samples(points)
    heights = [elevation(points[i][0], points[i][1]) for i in indices]
    if not all(math.isfinite(h) and -500 <= h <= 9000 for h in heights):
        return False
    gain, loss = gain_loss(heights)
    out = []
    segment = 0
    for i, point in enumerate(points):
        while segment + 1 < len(indices) - 1 and i > indices[segment + 1]:
            segment += 1
        ia, ib = indices[segment], indices[segment + 1]
        ratio = (i - ia) / max(1, ib - ia)
        h = heights[segment] * (1-ratio) + heights[segment+1] * ratio
        out.append([point[0], point[1], round(h, 1)])
    route['coordinates'] = out
    route['gainM'] = gain
    route['lossM'] = loss
    route['elevationAvailable'] = True
    route['elevationSource'] = 'terrain'
    route['elevationEstimatedAt'] = datetime.now(timezone.utc).date().isoformat()
    return True


def run(max_routes, write):
    manifest = json.loads((DATA/'routes-manifest.json').read_text())
    count, success, errors, total = 0, 0, 0, 0
    for tile in manifest.get('tiles', []):
        for file in tile['files']:
            path = DATA / file
            original = json.loads(path.read_text(encoding='utf-8'))
            routes = original.get('routes', [])
            total += len(routes)
            updated = False
            for route in routes:
                if count >= max_routes:
                    break
                if route.get('elevationAvailable') is not False:
                    continue
                count += 1
                try:
                    if enrich(route):
                        updated = True
                        success += 1
                    else:
                        errors += 1
                except Exception as exc:
                    errors += 1
                    print(f"DEM non disponibile per {route.get('slug')}: {exc}", file=sys.stderr)
                if count % 40 == 0:
                    print(f'Altimetria: {count} analizzati, {success} arricchiti, {errors} rinviati', flush=True)
            if updated and write:
                tmp = path.with_name(path.name + '.tmp')
                tmp.write_text(json.dumps(original, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf-8')
                tmp.replace(path)
            if count >= max_routes:
                break
        if count >= max_routes:
            break
    metrics = {'updatedAt': datetime.now(timezone.utc).isoformat(timespec='seconds'),
               'attempted': count, 'enriched': success, 'unavailable': errors,
               'catalogRoutes': manifest.get('routeCount', total)}
    print(json.dumps(metrics, ensure_ascii=False))
    if write:
        (DATA/'elevation-status.json').write_text(json.dumps(metrics, ensure_ascii=False)+'\n', encoding='utf-8')
    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--write', action='store_true')
    parser.add_argument('--max-routes', type=int, default=180)
    args = parser.parse_args()
    if not 1 <= args.max_routes <= 500:
        parser.error('--max-routes deve essere compreso tra 1 e 500')
    run(args.max_routes, args.write)
