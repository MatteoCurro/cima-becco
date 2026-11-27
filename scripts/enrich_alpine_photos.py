#!/usr/bin/env python3
"""Fotografie per rifugi, bivacchi e paesi: OSM File, Wikidata P18/P373 e Commons geolocalizzato.

La corrispondenza non si basa su nomi vaghi: P18/P373 identificano l'oggetto
tramite QID, le immagini geografiche richiedono anche una forte corrispondenza
del nome del luogo nel titolo. Solo licenze riutilizzabili e attribuzione.
Nessuna immagine stock, ricerca indiscriminata o associazione per sola distanza.
"""
from __future__ import annotations
import argparse
import html
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'public/data/alpine-places.json'
UA = 'CimaBecco atlas enrichment/0.3 (https://github.com/MatteoCurro/cima-becco)'
WIKIDATA = 'https://www.wikidata.org/w/api.php'
COMMONS = 'https://commons.wikimedia.org/w/api.php'
VALID_LICENSE = re.compile(r'^(?:CC\s?BY|CC0|PD-|Public Domain|Copyrighted-free|CC\s?0)', re.I)
STOP_WORDS = {'rifugio', 'bivacco', 'casera', 'malga', 'capanna', 'hut', 'biwak', 'alpino',
              'casa', 'monte', 'del', 'della', 'delle', 'degli', 'dei', 'allo', 'alla',
              'san', 'santa', 'saint', 'sankt', 'sul', 'per', 'bei', 'von', 'der', 'the'}


def request(url, params):
    req = Request(url + '?' + urlencode(params),
                  headers={'User-Agent': UA, 'Accept': 'application/json'})
    with urlopen(req, timeout=30) as response:
        return json.load(response)


def chunks(items, n=20):
    for i in range(0, len(items), n):
        yield items[i:i + n]


def plain(value):
    return html.unescape(re.sub(r'<[^>]*>', ' ', str(value or ''))).strip()[:180]


def clean_tokens(text):
    normalized = unicodedata.normalize('NFKD', str(text or '').lower())
    normalized = ''.join(ch for ch in normalized if not unicodedata.combining(ch))
    return [x for x in re.findall(r'[a-z0-9]+', normalized) if len(x) >= 4 and x not in STOP_WORDS]


def title_matches_place(name, filename):
    """Conservative name cross-check, never accept generic 'mountains near X'."""
    tokens = clean_tokens(name)
    file_tokens = set(clean_tokens(filename.rsplit('.', 1)[0]))
    if not tokens or not file_tokens:
        return False
    distinct = [word for word in tokens if len(word) >= 5]
    if len(distinct) >= 2:
        return len(set(distinct) & file_tokens) >= 2
    if len(distinct) == 1 and len(distinct[0]) >= 7:
        return distinct[0] in file_tokens
    return False


def fetch_claims(qids):
    """Wikidata P18: exact photo. P373: exact Commons category of the entity."""
    out = {}
    for batch in chunks(qids):
        doc = request(WIKIDATA, {'action': 'wbgetentities', 'format': 'json',
                                'ids': '|'.join(batch), 'props': 'claims'})
        for qid, entity in doc.get('entities', {}).items():
            claims = entity.get('claims', {})
            item = {}
            for prop, label in [('P18', 'photo'), ('P373', 'category')]:
                for claim in claims.get(prop, []):
                    value = claim.get('mainsnak', {}).get('datavalue', {}).get('value')
                    if isinstance(value, str) and value.strip():
                        item[label] = value.strip()
                        break
            if item:
                out[qid] = item
        time.sleep(1.2)
    return out


def commons_category_file(category):
    """Only files in the Wikidata-linked exact category, not categories nearby."""
    if not category or len(category) > 150:
        return []
    doc = request(COMMONS, {'action': 'query', 'format': 'json', 'list': 'categorymembers',
                            'cmtitle': 'Category:' + category.removeprefix('Category:'),
                            'cmtype': 'file', 'cmlimit': '16'})
    return [row['title'].removeprefix('File:') for row in doc.get('query', {}).get('categorymembers', [])
            if row.get('title', '').startswith('File:')]


def nearby_commons_files(place):
    """Geo-tagged images plus title match: never pair images on proximity alone."""
    radius = 250 if place['kind'] in ('rifugio', 'bivacco') else 450
    doc = request(COMMONS, {
        'action': 'query', 'format': 'json', 'generator': 'geosearch',
        'ggsprimary': 'all', 'ggsnamespace': '6',
        'ggscoord': f"{place['lat']}|{place['lng']}",
        'ggsradius': str(radius), 'ggslimit': '25',
    })
    candidates = sorted(doc.get('query', {}).get('pages', {}).values(),
                        key=lambda row: row.get('index', 999))
    return [row['title'].removeprefix('File:') for row in candidates
            if row.get('title', '').startswith('File:')
            and title_matches_place(place['name'], row['title'])][:5]


def commons_photos(filenames):
    result = {}
    for batch in chunks(sorted(set(filenames)), 15):
        doc = request(COMMONS, {'action': 'query', 'format': 'json',
                                'titles': '|'.join('File:' + fn.replace('_', ' ') for fn in batch),
                                'prop': 'imageinfo', 'iiprop': 'url|extmetadata',
                                'iiurlwidth': '960', 'redirects': '1'})
        for page in doc.get('query', {}).get('pages', {}).values():
            info = (page.get('imageinfo') or [None])[0]
            if not info:
                continue
            meta = info.get('extmetadata') or {}
            license_name = plain(meta.get('LicenseShortName', {}).get('value'))
            if not VALID_LICENSE.match(license_name):
                continue
            filename = page.get('title', '').removeprefix('File:')
            image = info.get('thumburl') or info.get('url', '')
            if not image.startswith('https://upload.wikimedia.org/'):
                continue
            result[filename.replace('_', ' ').casefold()] = {
                'url': image,
                'sourceUrl': 'https://commons.wikimedia.org/wiki/File:' + filename.replace(' ', '_'),
                'license': license_name,
                'author': plain(meta.get('Artist', {}).get('value') or info.get('user', ''))
                          or 'Autore nella pagina Commons',
                'licenseUrl': plain(meta.get('LicenseUrl', {}).get('value')),
            }
        time.sleep(1.2)
    return result


def run(limit=75, geo_limit=60, write=False):
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    places = data.get('places', [])
    today = datetime.now(timezone.utc).date().isoformat()

    # Preserve direct matches from old pipeline; score P18 > linked category > geo title.
    direct = [p for p in places if not p.get('photo') and not p.get('photoCheckedAt')
              and (p.get('commonsFile') or re.fullmatch(r'Q\d+', p.get('wikidata', '')))]
    direct.sort(key=lambda p: (not bool(p.get('commonsFile')), p.get('kind') == 'borgo',
                               p.get('name', '').casefold()))
    direct = direct[:max(0, min(250, limit))]
    qids = sorted({p['wikidata'] for p in direct if not p.get('commonsFile') and p.get('wikidata')})
    claims = fetch_claims(qids) if qids else {}
    direct_files = {}
    for place in direct:
        q = claims.get(place.get('wikidata'), {})
        filename = place.get('commonsFile') or q.get('photo')
        if not filename and q.get('category'):
            try:
                names = commons_category_file(q['category'])
                filename = next((name for name in names if title_matches_place(place['name'], name)), None)
                if not filename and place['kind'] == 'borgo':
                    filename = next(iter(names), None)
            except Exception as error:
                print(f"Categoria Commons non disponibile per {place['slug']}: {error}")
        if filename:
            direct_files[place['slug']] = filename
        time.sleep(.15)

    candidates = [p for p in places if not p.get('photo') and not p.get('photoGeoCheckedAt')
                  and len(clean_tokens(p.get('name', ''))) >= 1 and len(p.get('name', '')) >= 7]
    # Prefer refuges and bivouacs; then towns. Retry failures on another run, not on every page.
    candidates.sort(key=lambda p: (p.get('kind') == 'borgo', -int(bool(p.get('wikidata'))),
                                   p.get('name', '').casefold()))
    candidates = candidates[:max(0, min(150, geo_limit))]
    geo_files = {}
    for place in candidates:
        try:
            names = nearby_commons_files(place)
            if names:
                geo_files[place['slug']] = names[0]
            place['photoGeoCheckedAt'] = today
        except Exception as error:
            print(f"Geo Commons temporaneamente non disponibile ({place['slug']}): {error}")
        time.sleep(1.2)

    filenames = list(direct_files.values()) + list(geo_files.values())
    verified = commons_photos(filenames) if filenames else {}
    saved = 0
    for place in direct:
        filename = direct_files.get(place['slug'], '')
        photo = verified.get(filename.replace('_', ' ').casefold())
        if photo:
            place['photo'] = photo
            saved += 1
        place['photoCheckedAt'] = today
    for place in candidates:
        if place.get('photo'):
            continue
        filename = geo_files.get(place['slug'], '')
        photo = verified.get(filename.replace('_', ' ').casefold())
        if photo:
            place['photo'] = photo
            saved += 1
    if write and (direct or candidates):
        SOURCE.write_text(json.dumps(data, ensure_ascii=False, separators=(',', ':')) + '\n',
                          encoding='utf-8')
    print(json.dumps({
        'directChecked': len(direct), 'geoChecked': len(candidates),
        'newPhotos': saved, 'totalPhotos': sum(bool(p.get('photo')) for p in places),
    }))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--limit', type=int, default=75)
    parser.add_argument('--geo-limit', type=int, default=60)
    parser.add_argument('--write', action='store_true')
    options = parser.parse_args()
    run(options.limit, options.geo_limit, options.write)
