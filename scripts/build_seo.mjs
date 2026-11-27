#!/usr/bin/env node
/* global process, console */
/**
 * Pages search engines and AI assistants can read.
 *
 * The app keeps places and routes behind `#venue/…` addresses, which search
 * engines treat as one page (the home page). After `vite build`, this writes
 * a small static page for every hill, every summit in the world-peaks index,
 * every country and every committed route into `dist/`, each with a real
 * title, description, link-preview tags and schema.org data, and a button
 * into the live map. It also writes `sitemap.xml`, `robots.txt` and
 * `llms.txt`.
 *
 * Site address: SITE_URL (the deploy workflow sets it from public/CNAME, or the
 * GitHub Pages address), defaulting to the Pages address.
 *
 * Usage: node scripts/build_seo.mjs   (run by `npm run build`)
 */
import { mkdirSync, readFileSync, readdirSync, rmSync, writeFileSync, existsSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(ROOT, 'dist');
const DATA = join(ROOT, 'public', 'data');
const SITE = (process.env.SITE_URL || process.env.VITE_SITE_URL || 'https://www.cimabecco.it').replace(/\/+$/, '');
const TODAY = new Date().toISOString().slice(0, 10);
const TILE = 5;
// Cloudflare Pages' free plan takes at most 20,000 files per deployment.
// Place pages fill whatever room the app leaves, most useful first.
const MAX_FILES = Number(process.env.MAX_SITE_FILES || 19500);

if (!existsSync(DIST)) {
  console.error('dist/ is missing: run vite build first.');
  process.exit(1);
}
// Start from the app alone, so a second run does not count its own pages.
for (const dir of ['place', 'country', 'route']) rmSync(join(DIST, dir), { recursive: true, force: true });

const readJson = (path) => JSON.parse(readFileSync(path, 'utf8'));
const venues = readJson(join(DATA, 'venues.json')).venues;
const routesFile = readJson(join(DATA, 'routes.json'));
const featured = Array.isArray(routesFile) ? routesFile : routesFile.routes;
// Il generatore SEO legge gli shard solo in build: nessun download aggiuntivo sul telefono.
const routeIndex = new Map(featured.map((route) => [route.slug, route]));
const manifestPath = join(DATA, 'routes-manifest.json');
if (existsSync(manifestPath)) {
  const manifest = readJson(manifestPath);
  for (const tile of manifest.tiles ?? []) {
    for (const file of tile.files ?? []) {
      if (!/^routes-tiles\/it_\d+_\d+_\d+\.json$/.test(file)) continue;
      const shardPath = join(DATA, file);
      if (!existsSync(shardPath)) continue;
      for (const route of readJson(shardPath).routes ?? []) routeIndex.set(route.slug, route);
    }
  }
}
const routes = [...routeIndex.values()].filter((route) => !['cycle', 'run'].includes(route.activity));

// Selezione home già pronta nel pacchetto: niente 4.000 GPX scaricati all'apertura.
// Preferire sentieri con rifugi realmente identificati, quote e segnavia.
const picks = routes.filter((r) => r.coordinates?.length >= 2 && r.distanceM >= 1200 && r.distanceM <= 32000)
  .sort((a,b) => {
    const score = r => (r.stops?.filter(s=>s.kind==='rifugio').length || 0)*18
      + (r.stops?.filter(s=>s.kind==='borgo').length || 0)*5
      + (r.elevationAvailable!==false ? 5 : 0)
      + (r.caiDifficulty ? 6 : 0)
      + (r.trailRef ? 3 : 0)
      + (r.photos?.length ? 3 : 0);
    return score(b)-score(a) || a.slug.localeCompare(b.slug);
  });
const featuredRoutes = [];
const gridCells = new Set();
for (const r of picks) {
  if (featuredRoutes.length >= 20) break;
  const mid = r.coordinates[Math.floor(r.coordinates.length/2)];
  const cell = Math.floor(mid[0]*5) + ':' + Math.floor(mid[1]*5);
  if (gridCells.has(cell) && featuredRoutes.length < 10) continue;
  gridCells.add(cell);
  featuredRoutes.push(r);
}
mkdirSync(join(DIST,'data'),{recursive:true});
writeFileSync(join(DIST,'data','featured-routes.json'),JSON.stringify({generatedAt:TODAY,routes:featuredRoutes}));

const descriptions = existsSync(join(DATA, 'descriptions.json')) ? readJson(join(DATA, 'descriptions.json')).descriptions ?? {} : {};
const index = readJson(join(DATA, 'peaks', 'index.json'));
const peakPhotos = existsSync(join(DATA, 'peaks', 'photos.json')) ? readJson(join(DATA, 'peaks', 'photos.json')).photos ?? {} : {};
const alpinePlaces = existsSync(join(DATA, 'alpine-places.json')) ? readJson(join(DATA, 'alpine-places.json')).places ?? [] : [];
const trekProjects = existsSync(join(DATA, 'trekking-projects.json')) ? readJson(join(DATA, 'trekking-projects.json')).projects ?? [] : [];
const alpineWater=existsSync(join(DATA,'alpine-water.json')) ? readJson(join(DATA,'alpine-water.json')).sources ?? [] : [];
const byStop = new Map();
for (const route of routes) {
  for (const stop of route.stops || []) {
    const list = byStop.get(stop.slug) || [];
    list.push(route);
    byStop.set(stop.slug, list);
  }
}

const regionName = new Intl.DisplayNames(['it'], { type: 'region' });
const countryName = (code) => {
  try {
    return regionName.of(code) ?? code;
  } catch {
    return code;
  }
};

const escape = (text) =>
  String(text ?? '').replace(/[&<>"']/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[ch]);
const metres = (m) => `${Math.round(m).toLocaleString('en')} m`;
const km = (m) => `${(m / 1000).toFixed(m < 10000 ? 1 : 0)} km`;
const token = (n) => (n < 0 ? `m${-n}` : String(n));
const peakSlug = (id, lat, lng) => `gn${id}-${token(Math.floor(lat / TILE) * TILE)}x${token(Math.floor(lng / TILE) * TILE)}`;
const appLink = (hash) => `${SITE}/${hash}`;

function photoUrl(file) {
  if (!file) return null;
  return /^https?:/.test(file) ? file : `${SITE}/${file.replace(/^\/+/, '')}`;
}

const STYLE = `
:root{--ink:#143d2f;--muted:#637766;--accent:#ff2677;--line:#e1e8de;--sage:#eaf1e8;--paper:#fbfcf8}
*{box-sizing:border-box}body{margin:0;font:16px/1.65 'Space Grotesk',-apple-system,BlinkMacSystemFont,"Segoe UI",system-ui,sans-serif;color:var(--ink);background:var(--paper)}
header{display:flex;align-items:center;justify-content:space-between;gap:16px;max-width:880px;margin:0 auto;padding:18px 20px;border-bottom:1px solid var(--line)}
.brand{display:inline-flex;align-items:center;gap:8px;color:var(--accent);font-weight:700;font-size:21px;text-decoration:none;letter-spacing:-.03em}
.brand svg{width:28px;height:28px}
main{max-width:880px;margin:0 auto;padding:28px 20px 56px}
nav.crumbs{font-size:14px;color:var(--muted);margin-bottom:12px}nav.crumbs a{color:var(--muted)}
h1{margin:0 0 12px;font:900 clamp(34px,5vw,53px)/1.03 'Bricolage Grotesque',sans-serif;letter-spacing:-.028em}h2{font-family:'Bricolage Grotesque',sans-serif;letter-spacing:-.035em}
.sub{margin:0 0 20px;color:var(--muted)}
.facts{display:flex;flex-wrap:wrap;gap:10px;margin:0 0 22px;padding:0;list-style:none}
 .facts li{padding:13px 16px;border:1px solid var(--line);background:#f5f8f2;border-radius:12px;font-size:13px}.facts strong{display:block;font-size:18px}
figure{margin:0 0 22px}figure img{width:100%;max-height:440px;object-fit:cover;border-radius:16px;background:#f2f2f2}
figcaption{margin-top:6px;color:var(--muted);font-size:12px}
.cta{display:inline-flex;align-items:center;gap:8px;height:48px;padding:0 22px;border-radius:10px;background:var(--ink);color:#fff;font-weight:600;text-decoration:none}
.cta:hover{background:#50765f}
ul.list{padding-left:20px}ul.list li{margin:4px 0}ul.list a{color:var(--ink)}
footer{max-width:880px;margin:0 auto;padding:20px;border-top:1px solid var(--line);color:var(--muted);font-size:13px}footer a{color:var(--muted)}
.cima-seo-trail{max-width:900px;margin:auto}
.cima-seo-eyebrow{color:#658272;font-size:12px;font-weight:800;letter-spacing:.17em;margin-bottom:14px}
.cima-seo-lead{font-size:16px;max-width:750px;color:#506558;line-height:1.8;margin:0 0 20px}
.cima-seo-tags{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0 24px}
.cima-seo-tags span{border-radius:99px;background:#e7eee2;color:#48684d;padding:6px 12px;font-weight:800;font-size:12px}
.cima-seo-tags span.fun{background:#ff2677;color:#fff;font:900 30px/.93 'Barlow Condensed',Impact,sans-serif;letter-spacing:.01em;border-radius:5px;transform:rotate(-2deg);box-shadow:4px 4px 0 #143d2f}
.route-sketch{border-radius:18px;background:linear-gradient(145deg,#e2eade,#c9d9c7);padding:18px 25px;overflow:hidden;margin:0 0 23px;position:relative;color:#3b5947}
.route-sketch::before{content:'';position:absolute;inset:0;opacity:.23;background:repeating-radial-gradient(ellipse at 80% 20%,transparent 0px,transparent 17px,#7f9d88 19px,#7f9d88 20px,transparent 22px,transparent 38px);pointer-events:none}
.route-sketch svg{display:block;position:relative;width:100%;height:auto;max-height:260px;filter:drop-shadow(0 1px 1px #fafff7)}
.route-sketch-caption{font-weight:800;font-size:12px;letter-spacing:.12em}
.route-sketch small{position:relative;display:block;color:#557462;font-size:11px}
.cima-seo-photo img{max-height:400px;object-fit:cover;display:block;width:100%;border-radius:18px}
.cima-seo-facts{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));margin:18px 0 24px}
.cima-seo-facts strong{color:#2f573e;white-space:normal;line-height:1.3}
.cima-seo-actions{display:flex;align-items:center;gap:12px;flex-wrap:wrap;margin:24px 0 34px}
.cima-seo-actions .cta{background:#ff2677;border-radius:6px;font-weight:900;box-shadow:3px 3px 0 #143d2f}
.cima-seo-secondary{font-weight:800;color:#436e53;text-decoration:none;border:1px solid #d8e4d8;border-radius:12px;padding:11px 16px}
.cima-seo-secondary:hover{background:#e5eee4}
.cima-seo-body{border-top:1px solid #dfe6db;padding-top:12px;max-width:760px}
.cima-seo-body h2{font-size:23px;margin:25px 0 10px}
.cima-seo-details{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}
.cima-seo-details div{background:#f0f5ed;border-radius:10px;padding:12px}
.cima-seo-details dt{font-size:11px;color:#687869}
.cima-seo-details dd{margin:2px 0 0;font-weight:800}
.cima-seo-warning{font-size:13px;color:#6b6249;background:#f6f0e3;padding:12px 16px;border-radius:10px;margin-top:24px}
@media(max-width:660px){.cima-seo-facts,.cima-seo-details{grid-template-columns:repeat(2,minmax(0,1fr))}header{flex-wrap:wrap}main{padding-top:18px}}

`;
// Le pagine SEO contengono HTML leggibile senza JS; con JS montano la stessa
// SPA interattiva della home, senza un layout duplicato su permalink.
const APP_SHELL=readFileSync(join(DIST,'index.html'),'utf8');
const APP_ASSETS=[
  ...(APP_SHELL.match(/<script\b[^>]*\btype=["']module["'][^>]*><\/script>/gi)||[]),
  ...(APP_SHELL.match(/<link\b[^>]*\brel=["']stylesheet["'][^>]*>/gi)||[])
].filter(tag=>/\b(?:src|href)=["']\/(?:[^"']*\/)?assets\//.test(tag)).join('\n');
const MARK = '<svg viewBox="0 0 120 120" aria-hidden="true"><rect width="120" height="120" rx="25" fill="#143d2f"/><path d="M18 18 Q18 54 42 57 L51 31 L68 55 Q96 50 99 19" fill="none" stroke="#ff2677" stroke-width="13" stroke-linecap="square"/><path d="M30 66 L54 42 L78 62 L69 90 L39 90Z" fill="#e4ffbe"/><path d="M77 63 L108 73 L74 79Z" fill="#ff2677"/><circle cx="57" cy="65" r="3.7" fill="#143d2f"/></svg>';const pages = [];

function page({ path, title, description, image, jsonLd, body, noindex = false }) {
  const url = `${SITE}/${path}`;
  const html = `<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://fonts.googleapis.com/css2?family=Barlow+Condensed:wght@700;800;900&family=Bricolage+Grotesque:opsz,wght@12..96,200..800&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet">
<title>${escape(title)}</title>
<meta name="description" content="${escape(description)}">
${noindex ? '<meta name="robots" content="noindex,follow">' : ''}
<link rel="canonical" href="${url}">
<link rel="icon" href="${SITE}/favicon.svg" type="image/svg+xml">
<meta property="og:site_name" content="Cima Becco">
<meta property="og:type" content="website">
<meta property="og:title" content="${escape(title)}">
<meta property="og:description" content="${escape(description)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${escape(image || `${SITE}/og-image.png`)}">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">${JSON.stringify(jsonLd).replace(/</g, '\\u003c')}</script>
<style>${STYLE}</style>
${APP_ASSETS}
</head>
<body>
<div id="root">
<header><a class="brand" href="${SITE}/">${MARK}Cima Becco</a><a href="${SITE}/#map">Esplora la mappa</a></header>
<main>
${body}
</main>
<footer>Cima Becco · Ogni cima, un nuovo percorso. <a href="${SITE}/#data">Fonti e crediti</a> · <a href="${SITE}/#privacy">Privacy</a></footer>
</div>
</body>
</html>
`;
  const file = join(DIST, path, 'index.html');
  mkdirSync(dirname(file), { recursive: true });
  writeFileSync(file, html);
  pages.push(url);
}

const crumbs = (items) =>
  `<nav class="crumbs"><a href="${SITE}/">Cima Becco</a>${items.map(([label, href]) => ` › ${href ? `<a href="${href}">${escape(label)}</a>` : escape(label)}`).join('')}</nav>`;
const breadcrumbLd = (items) => ({
  '@type': 'BreadcrumbList',
  itemListElement: [['Cima Becco', `${SITE}/`], ...items].map(([name, item], i) => ({ '@type': 'ListItem', position: i + 1, name, ...(item ? { item } : {}) })),
});

function placePage({ slug, name, lat, lng, heightM, kind, country, countryCode, text, photo, routesHere }) {
  const where = country ? ` in ${country}` : '';
  const heightText = heightM ? `${metres(heightM)} ${kind === 'hill' ? 'summit' : 'climb'}` : 'climb';
  const description = text || `${name} is a ${heightText}${where}. See it on the Cima Becco map with routes, photos, weather and directions.`;
  const image = photo ? photoUrl(photo.file) : null;
  const countryHref = countryCode ? `${SITE}/country/${countryCode.toLowerCase()}/` : null;
  placeUrlBySlug.set(slug, `${SITE}/place/${slug}/`);
  page({
    path: `place/${slug}/`,
    title: `${name}${heightM ? ` (${metres(heightM)})` : ''}${where} · Cima Becco`,
    description: description.slice(0, 300),
    image,
    jsonLd: {
      '@context': 'https://schema.org',
      '@graph': [
        {
          '@type': ['Place', 'TouristAttraction'],
          name,
          description,
          url: `${SITE}/place/${slug}/`,
          geo: { '@type': 'GeoCoordinates', latitude: lat, longitude: lng, ...(heightM ? { elevation: heightM } : {}) },
          ...(country ? { containedInPlace: { '@type': 'Country', name: country } } : {}),
          ...(image ? { image } : {}),
          isAccessibleForFree: true,
        },
        breadcrumbLd([...(country ? [[country, countryHref]] : []), [name, null]]),
      ],
    },
    body: `${crumbs([...(country ? [[country, countryHref]] : []), [name]])}
<h1>${escape(name)}</h1>
<p class="sub">${escape(kind === 'hill' ? 'Hill or mountain' : 'Climb')}${escape(where)}</p>
<ul class="facts">${heightM ? `<li><strong>${metres(heightM)}</strong>elevation</li>` : ''}<li><strong>${lat.toFixed(4)}, ${lng.toFixed(4)}</strong>coordinates</li>${routesHere.length ? `<li><strong>${routesHere.length}</strong>GPX route${routesHere.length === 1 ? '' : 's'}</li>` : ''}</ul>
${image ? `<figure><img src="${escape(image)}" alt="${escape(name)}" loading="lazy"><figcaption>${escape([photo.credit && `Photo by ${photo.credit}`, photo.license || photo.licence, photo.source].filter(Boolean).join(' · '))}</figcaption></figure>` : ''}
<p>${escape(description)}</p>
${routesHere.length ? `<h2>GPX routes here</h2><ul class="list">${routesHere.map((route) => `<li><a href="${SITE}/route/${route.slug}/">${escape(route.name)}</a> · ${km(route.distanceM)}</li>`).join('')}</ul>` : ''}
<p><a class="cta" href="${appLink(`#venue/${slug}`)}">Open ${escape(name)} on the map</a></p>`,
  });
}

const placeUrlBySlug = new Map();
const placeSpecs = [];
// Coarse country boxes for the local hills (the same ones src/lib/regions.ts
// uses to label cards), checked in order.
const REGIONS = [
  ['Singapore', 103.6, 1.16, 104.1, 1.48], ['Hong Kong', 113.82, 22.15, 114.44, 22.57], ['Taiwan', 119.3, 21.8, 122.1, 25.4],
  ['Malaysia', 99.6, 0.85, 119.3, 7.4], ['Thailand', 97.3, 5.6, 105.7, 20.5], ['Vietnam', 102.1, 8.4, 109.5, 23.4],
  ['Philippines', 116.9, 4.6, 126.6, 21.1], ['Indonesia', 95, -11, 141, 6], ['Japan', 129.4, 30.9, 145.9, 45.6],
  ['South Korea', 125.8, 33.1, 129.6, 38.7], ['Australia', 112.9, -43.7, 153.7, -10.6], ['New Zealand', 166.4, -47.3, 178.6, -34.4],
];
const regionOf = (lng, lat) => REGIONS.find(([, w, s, e, n]) => lng >= w && lng <= e && lat >= s && lat <= n)?.[0] ?? null;
const routesByVenue = new Map();
for (const route of routes) for (const slug of route.venueSlugs ?? []) routesByVenue.set(slug, [...(routesByVenue.get(slug) ?? []), route]);

// Hills and mountains in the local data (blocks and stairwells are thousands of
// near-identical pages, so they stay in the app).
for (const venue of venues) {
  if (venue.type !== 'hill' || /^[\d\s.,m]+$/i.test(venue.name)) continue;
  const text = descriptions[venue.slug]?.text || (venue.notes && !venue.notes.startsWith('Summit elevation from') ? venue.notes : '');
  placeSpecs.push({
    slug: venue.slug,
    name: venue.name,
    lat: venue.lat,
    lng: venue.lng,
    heightM: venue.summitM ?? venue.gainM,
    kind: 'hill',
    country: regionOf(venue.lng, venue.lat),
    countryCode: null,
    text,
    photo: venue.photo,
    routesHere: routesByVenue.get(venue.slug) ?? [],
  });
}

// The world's tallest summits from the peaks index.
const peaksByCountry = new Map();
for (const [id, name, lat, lng, ele, , code, feature] of index.top) {
  // Ranges (MTS, HLLS) are areas, not summits you can stand on.
  if (feature === 'MTS' || feature === 'HLLS') continue;
  const slug = peakSlug(id, lat, lng);
  const stored = peakPhotos[slug];
  const photo = stored ? { file: stored[0], credit: stored[2], licence: stored[3], source: 'Wikimedia Commons' } : null;
  const country = code ? countryName(code) : null;
  placeSpecs.push({ slug, name, lat, lng, heightM: ele, kind: 'hill', country, countryCode: code || null, text: descriptions[slug]?.text || '', photo, routesHere: [] });
  if (code) peaksByCountry.set(code, [...(peaksByCountry.get(code) ?? []), { slug, name, ele, lat, lng }]);
}

// The local data's hills (Mount Fuji among them) are not in the world index,
// so add them to their country's list too.
const codeByName = new Map(Object.keys(index.byCountry).map((code) => [countryName(code), code]));
for (const venue of venues) {
  if (venue.type !== 'hill' || !venue.summitM) continue;
  const code = codeByName.get(regionOf(venue.lng, venue.lat));
  if (code) peaksByCountry.set(code, [...(peaksByCountry.get(code) ?? []), { slug: venue.slug, name: venue.name, ele: venue.summitM, lat: venue.lat, lng: venue.lng }]);
}

// Write the place pages that fit: places with routes, a photo or a written
// description first, then the tallest.
const countFiles = (dir) => readdirSync(dir, { withFileTypes: true }).reduce((n, entry) => n + (entry.isDirectory() ? countFiles(join(dir, entry.name)) : 1), 0);
const reserved = countFiles(DIST) + Object.keys(index.byCountry).length + routes.length + alpinePlaces.length + trekProjects.length + 12;
const room = Math.max(0, MAX_FILES - reserved);
const score = (spec) => (spec.routesHere.length ? 4 : 0) + (spec.photo ? 2 : 0) + (spec.text ? 1 : 0);
placeSpecs.sort((a, b) => score(b) - score(a) || (b.heightM ?? 0) - (a.heightM ?? 0));
for (const spec of placeSpecs.slice(0, room)) placePage(spec);
if (placeSpecs.length > room) console.warn(`SEO: ${(placeSpecs.length - room).toLocaleString('en')} place pages left out to stay under ${MAX_FILES.toLocaleString('en')} files.`);

// One page per country: its tallest summits.
for (const [code, [count]] of Object.entries(index.byCountry)) {
  const name = countryName(code);
  // Tallest first, skipping points within 3 km of a taller one (a summit's own sub-peaks).
  const peaks = [];
  for (const peak of (peaksByCountry.get(code) ?? []).sort((a, b) => b.ele - a.ele)) {
    const near = peaks.some((other) => 6371000 * Math.hypot(((peak.lat - other.lat) * Math.PI) / 180, (((peak.lng - other.lng) * Math.PI) / 180) * Math.cos((peak.lat * Math.PI) / 180)) < 3000);
    if (!near) peaks.push(peak);
    if (peaks.length === 40) break;
  }
  if (peaks.length === 0) continue;
  const description = `The highest peaks in ${name}, from ${peaks[0].name} (${metres(peaks[0].ele)}) down. ${count.toLocaleString('en')} summits in ${name} are on the Cima Becco map, with GPX routes, photos and weather.`;
  const [, west, south, east, north] = index.byCountry[code];
  page({
    path: `country/${code.toLowerCase()}/`,
    title: `Highest peaks in ${name} · Cima Becco`,
    description,
    image: photoUrl(peakPhotos[peaks[0].slug]?.[0]),
    jsonLd: {
      '@context': 'https://schema.org',
      '@graph': [
        {
          '@type': 'ItemList',
          name: `Highest peaks in ${name}`,
          itemListElement: peaks.map((peak, i) => ({ '@type': 'ListItem', position: i + 1, name: peak.name, url: placeUrlBySlug.get(peak.slug) ?? appLink(`#venue/${peak.slug}`) })),
        },
        breadcrumbLd([[name, null]]),
      ],
    },
    body: `${crumbs([[name]])}
<h1>Highest peaks in ${escape(name)}</h1>
<p class="sub">${count.toLocaleString('en')} summits mapped</p>
<p>${escape(description)}</p>
<ul class="list">${peaks.map((peak) => `<li><a href="${placeUrlBySlug.get(peak.slug) ?? appLink(`#venue/${peak.slug}`)}">${escape(peak.name)}</a> · ${metres(peak.ele)}</li>`).join('')}</ul>
<p><a class="cta" href="${appLink(`#map/${[west, south, east, north].map((n) => n.toFixed(4)).join(',')}`)}">See ${escape(name)} on the map</a></p>`,
  });
}

// Presentazione editoriale dei GPX: tenere sincronizzata la logica con src/lib/routeEditorial.ts.
function trailArea(route) {
  const p = route.coordinates?.[Math.floor((route.coordinates?.length ?? 1)/2)] ?? [0,0];
  const [lng,lat] = p;
  if (lat>46.1 && lat<47.2 && lng>=10.8 && lng<12) return 'Dolomiti occidentali';
  if (lat>46.1 && lat<47.2 && lng>=12 && lng<13.5) return 'Dolomiti orientali';
  if (lat>45 && lat<47.8 && lng>=6 && lng<11) return 'Alpi occidentali e centrali';
  if (lat>45 && lat<47.8 && lng>=11 && lng<17) return 'Alpi orientali';
  if (lat>43.3 && lat<=45.5) return 'Appennino settentrionale';
  if (lat>40.5 && lat<=43.5) return 'Appennino centrale';
  return 'Italia';
}
function routeDestinationNames(route) {
  const stays = (route.stops || []).filter(s=>(s.kind==='rifugio'||s.kind==='bivacco') && s.distanceM<=180);
  const preferred = [...stays.filter(s=>s.relation==='arrivo'),...stays];
  const chosen=[];
  for(const stop of preferred) if(!chosen.includes(stop.name) && chosen.length<2) chosen.push(stop.name);
  if(!chosen.length) for(const stop of (route.stops||[]).filter(s=>s.kind==='borgo'&&s.distanceM<=350)) {
    if(!chosen.includes(stop.name) && chosen.length<2)chosen.push(stop.name);
  }
  return chosen;
}
function trailName(route) {
  const s=(route.name||'').trim();
  const area=trailArea(route);
  const stops=routeDestinationNames(route);
  const destination=stops.length?stops.join(' · '):area;
  if(/^sentiero si$/i.test(s))return 'Sentiero Italia · '+destination;
  if(/^sentiero\s+\d+[a-z]?$/i.test(s))return s+' · '+destination;
  if(!s||/^route\s*\d+$/i.test(s))return (route.activity==='ferrata'?'Via ferrata':'Escursione')+' · '+destination;
  if(stops.length && s.length<54 && !s.toLowerCase().includes(stops[0].toLowerCase()))return s+' · '+stops[0];
  return s;
}
function trailMood(route) {
  if(route.activity==='ferrata') {
    const n=parseInt(route.viaFerrataScale||'',10);
    if(!n)return ['Scala ferrata non disponibile','GRADO IN LATITANZA'];
    if(n<=2)return ['Ferrata poco difficile','BRACCIA IN GITA'];
    if(n===3)return ['Ferrata impegnativa','AVAMBRACCI IN LEASING'];
    return ['Ferrata molto impegnativa',n>=5?'IL VUOTO TI FA CIAO':'LA ROCCIA TI SGAMA'];
  }
  return ({
    T:['Turistico · CAI T','MERENDEROS'],
    E:['Escursionistico · CAI E',route.gainM>=850&&route.elevationAvailable!==false?'GAMBE IN SCIOPERO':'MUOVI QUELLE GAMBE'],
    EE:['Escursionisti esperti · CAI EE',route.gainM>=900&&route.elevationAvailable!==false?'DO VETO MORE?':'OGGI SI BESTEMMIA'],
    EEA:['Esperti con attrezzatura · CAI EEA','NON FARE IL FENOMENO'],
  })[route.caiDifficulty] || ['Difficoltà da verificare','GRADO IN LATITANZA'];
}
function trailText(route) {
  const raw=(route.description||'').trim();
  const stops=(route.stops||[]).filter(s=>(s.kind==='rifugio'||s.kind==='bivacco')).slice(0,4);
  const villages=(route.stops||[]).filter(s=>s.kind==='borgo').slice(0,3);
  const places=[stops.length?'Nei pressi del tracciato: '+stops.map(s=>s.name).join(', ')+'.':'',
    villages.length?'Località attraversate o nelle vicinanze: '+villages.map(s=>s.name).join(', ')+'.':''].filter(Boolean).join(' ');
  if(raw && !/Tracciato OSM da verificare|non certifica percorribilità|^GPX route/i.test(raw))
    return [raw,places].filter(Boolean).join(' ');
  const area=trailArea(route),len=km(route.distanceM);
  const start=route.activity==='ferrata'?'Questo tratto attrezzato':'Questo percorso a piedi';
  const ref=route.trailRef?' Segnavia o riferimento: '+route.trailRef+'.':'';
  const gain=route.elevationAvailable!==false?' Dislivello positivo stimato: '+metres(route.gainM)+'.':'';
  const tech=route.activity==='ferrata'?' Ferrata: verifica una relazione tecnica aggiornata.':route.caiDifficulty?' Classificazione riportata CAI '+route.caiDifficulty+'.':'';
  return [start+' attraversa '+area+' per circa '+len+(route.loop?', ad anello':'')+'.'+ref+gain+tech,places].filter(Boolean).join(' ');
}
function routeSketch(route) {
  const pts=route.coordinates || [];
  if (pts.length<2) return '';
  const minx=Math.min(...pts.map(p=>p[0])), maxx=Math.max(...pts.map(p=>p[0]));
  const miny=Math.min(...pts.map(p=>p[1])), maxy=Math.max(...pts.map(p=>p[1]));
  const dx=Math.max(.0001,maxx-minx),dy=Math.max(.0001,maxy-miny);
  const scale=Math.min(500/dx,170/dy);
  const ox=(560-dx*scale)/2,oy=(230-dy*scale)/2;
  const path=pts.filter((_,i)=>i%Math.max(1,Math.ceil(pts.length/240))===0||i===pts.length-1).map((p,i)=>(i?'L':'M')+(ox+(p[0]-minx)*scale).toFixed(1)+' '+(230-oy-(p[1]-miny)*scale).toFixed(1)).join(' ');
  return '<div class="route-sketch"><div class="route-sketch-caption">IL TRACCIATO · '+escape(trailArea(route))+'</div><svg viewBox="0 0 560 230" role="img" aria-label="Anteprima schematica del tracciato"><path d="'+path+'" fill="none" stroke="#355d47" stroke-width="4.5" stroke-linecap="round" stroke-linejoin="round" /></svg><small>Rappresentazione schematica. Apri la mappa per il dettaglio.</small></div>';
}
// Pagine statiche dei sentieri: testo comprensibile, grafico originale della traccia, dati tecnici.
for (const route of routes) {
  const title = trailName(route);
  const [level, quip] = trailMood(route);
  const area = trailArea(route);
  const description = trailText(route);
  const passes = (route.venueSlugs ?? []).map((slug) => venues.find((venue) => venue.slug === slug)).filter(Boolean);
  const image = route.photos?.[0] || null;
  const original = route.sourceUrl?.startsWith('https://') ? route.sourceUrl : null;
  const official = route.officialDescriptionUrl?.startsWith('https://') && (new URL(route.officialDescriptionUrl)).pathname.split('/').filter(Boolean).length >= 2 ? route.officialDescriptionUrl : null;
  const stats = [
    ['Distanza', km(route.distanceM)],
    ['Dislivello positivo', route.elevationAvailable !== false ? metres(route.gainM) + ' (stima)' : 'In elaborazione'],
    ['Andamento', route.loop ? 'Anello' : 'Percorso lineare'],
    ['Difficoltà', level],
  ];
  page({
    path: `route/${route.slug}/`,
    title: `${title} · GPX e informazioni | Cima Becco`,
    description: description.slice(0, 280),
    image: image?.url || null,
    jsonLd: {
      '@context': 'https://schema.org',
      '@graph': [
        { '@type': 'CreativeWork', name: title, description, url: `${SITE}/route/${route.slug}/`, isAccessibleForFree: true, ...(image ? { image: image.url } : {}), ...(route.licence ? { license: 'https://opendatacommons.org/licenses/odbl/' } : {}) },
        breadcrumbLd([[title, null]]),
      ],
    },
    body: `${crumbs([['Percorsi', `${SITE}/#routes`], [title]])}
<article class="cima-seo-trail">
  <div class="cima-seo-eyebrow">${route.activity === 'ferrata' ? 'VIA FERRATA' : 'ESCURSIONE'} · ${escape(area)}</div>
  <h1>${escape(title)}</h1>
  <p class="cima-seo-lead">${escape(description)}</p>
  <div class="cima-seo-tags"><span class="fun" title="Soprannome editoriale, non scala tecnica">${escape(quip)}</span><span>${escape(level)}</span>${route.trailRef ? `<span>Segnavia ${escape(route.trailRef)}</span>` : ''}</div>
  ${image ? `<figure class="cima-seo-photo"><img src="${escape(image.url)}" alt="${escape(image.caption || title)}" loading="lazy"><figcaption>Foto: ${escape(image.author || 'Wikimedia Commons')} · ${escape(image.license || 'Licenza nella fonte')} · <a href="${escape(image.sourceUrl)}">Originale</a></figcaption></figure>` : routeSketch(route)}
  <ul class="facts cima-seo-facts">${stats.map(([label,value]) => `<li><strong>${escape(value)}</strong>${escape(label)}</li>`).join('')}</ul>
  <div class="cima-seo-actions"><a class="cta" href="${appLink(`#route/${route.slug}`)}">Apri sulla mappa · Scarica GPX</a>${original ? `<a class="cima-seo-secondary" href="${escape(original)}" target="_blank" rel="noopener noreferrer">Vedi tracciato OSM ↗</a>` : ''}</div>
  <section class="cima-seo-body"><h2>Il percorso</h2><p>${escape(description)}</p>
    <h2>Segnaletica e informazioni</h2><dl class="cima-seo-details">
      ${route.caiDifficulty ? `<div><dt>Classificazione CAI</dt><dd>${escape(route.caiDifficulty)}</dd></div>` : ''}
      ${route.viaFerrataScale ? `<div><dt>Scala ferrata</dt><dd>${escape(route.viaFerrataScale)}</dd></div>` : ''}
      ${route.sacScale ? `<div><dt>Scala escursionistica SAC</dt><dd>${escape(route.sacScale)}</dd></div>` : ''}
      ${route.trailRef ? `<div><dt>Numero sentiero</dt><dd>${escape(route.trailRef)}</dd></div>` : ''}
      ${route.operator ? `<div><dt>Gestore indicato</dt><dd>${escape(route.operator)}</dd></div>` : ''}
      ${route.network ? `<div><dt>Rete</dt><dd>${escape(route.network)}</dd></div>` : ''}
    </dl>
    ${official ? `<p><a href="${escape(official)}" rel="noopener noreferrer" target="_blank">Consulta la scheda del gestore ↗</a></p>` : ''}
    ${passes.length ? `<h2>Cime e luoghi vicini</h2><ul class="list">${passes.map((v) => `<li><a href="${SITE}/place/${v.slug}/">${escape(v.name)}</a></li>`).join('')}</ul>` : ''}
    ${route.stops?.length ? `<h2>Rifugi, bivacchi e paesi lungo il percorso</h2><p>Luoghi geograficamente vicini al GPX, non accessi garantiti.</p><ul class="list">${route.stops.slice(0,12).map(s=>`<li><a href="${SITE}/${s.kind==='rifugio'?'rifugi':s.kind==='bivacco'?'bivacchi':'borghi'}/${s.slug}/">${escape(s.name)}</a> · ${s.kind==='rifugio'?'Rifugio':s.kind==='bivacco'?'Bivacco':'Paese'}</li>`).join('')}</ul>` : ''}
    ${route.activity === 'ferrata' ? '<p class="cima-seo-warning">Una ferrata richiede attrezzatura e competenze specifiche. Il GPX non rappresenta esposizione e difficoltà tecnica.</p>' : '<p class="cima-seo-warning">Traccia e dislivelli sono indicativi: verifica percorribilità e condizioni prima di partire.</p>'}
  </section>
</article>`,
  });
}

// Pagine SEO locali per rifugi, bivacchi e borghi OSM con coordinate e percorsi verificati vicini.
// Evita pagine seriali prive di contenuto: i borghi senza sentieri o fonte propria
// restano consultabili nell'app ma non vengono generati come pagine indicizzabili.
for (const place of alpinePlaces) {
  if (!/^osm-[nwr]-\d+$/.test(place.slug)) continue;
  const related=(byStop.get(place.slug)||[]).slice(0,24);
  // Tutti i luoghi mostrati nel catalogo devono avere una pagina reale: niente link rotti.
  // I borghi poveri di metadati sono consultabili ma non indicizzabili finché non vengono arricchiti.
  const category=place.kind==='rifugio'?'rifugi':place.kind==='bivacco'?'bivacchi':'borghi';
  const kind=place.kind==='rifugio'?'rifugio alpino':place.kind==='bivacco'?'bivacco alpino':'località di montagna';
  const altitude=Number.isFinite(place.elevationM)?` a ${metres(place.elevationM)} di quota`:'';
  const nearbyWater=alpineWater.filter(w=>Math.abs(w.lat-place.lat)<.017 && Math.abs(w.lng-place.lng)<.03 &&
    Math.hypot((w.lat-place.lat)*111195,(w.lng-place.lng)*111320*Math.cos(place.lat*Math.PI/180))<1400).slice(0,8);
  const description=(place.description?`${place.description} `:'')+
    `${place.name} è ${kind==='località di montagna'?'una':'un'} ${kind} mappat${place.kind==='borgo'?'a':'o'} nelle Dolomiti${altitude}.`+
    (related.length?` Esplora ${related.length} sentieri collegati geograficamente e GPX.`:' Consulta posizione e sentieri nei dintorni.');
  const photo=place.photo?.url?.startsWith('https://upload.wikimedia.org/') ? place.photo : null;
  page({
    path:`${category}/${place.slug}/`,
    noindex:place.kind==='borgo' && !related.length && !place.website && !place.description && !place.photo,
    title:`${place.name} · ${place.kind==='rifugio'?'Rifugio':place.kind==='bivacco'?'Bivacco':'Paese'}, altitudine, sentieri e meteo | Cima Becco`,
    description:description.slice(0,285),
    image:photo?.url||null,
    jsonLd:{'@context':'https://schema.org','@graph':[
      {'@type':'Place',name:place.name,description,
        url:`${SITE}/${category}/${place.slug}/`,
        geo:{'@type':'GeoCoordinates',latitude:place.lat,longitude:place.lng,
          ...(place.elevationM?{elevation:place.elevationM}:{})},
        ...(photo?{image:photo.url}:{}),
        hasMap:place.osmUrl,
        ...(place.phone?{telephone:place.phone}:{}),
      },breadcrumbLd([[category==='rifugi'?'Rifugi':category==='bivacchi'?'Bivacchi':'Paesi',appLink(`#${category==='borghi'?'paesi':category}`)],[place.name,null]])]},
    body:`${crumbs([['Atlante',appLink(`#atlante/${category}`)],[place.name]])}
      <div class="cima-seo-eyebrow">CIMA BECCO · ${place.kind==='rifugio'?'RIFUGIO':place.kind==='bivacco'?'BIVACCO':'PAESE'} · DOLOMITI</div>
      <h1>${escape(place.name)}</h1>
      <p class="cima-seo-lead">${escape(description)}</p>
      ${photo?`<figure class="cima-seo-photo"><img src="${escape(photo.url)}" alt="${escape(place.name)}" loading="lazy"></figure>`:''}
      <ul class="facts cima-seo-facts">
        ${place.elevationM!=null?`<li><strong>${metres(place.elevationM)}</strong>${place.elevationSource==='dem'?'quota DEM stimata':'quota indicata in OSM'}</li>`:''}
        <li><strong>${escape(place.lat.toFixed(4)+', '+place.lng.toFixed(4))}</strong>coordinate</li>
        <li><strong>${related.length}</strong>sentieri collegati</li>
        ${place.capacity?`<li><strong>${place.capacity}</strong>posti letto OSM</li>`:''}
        
      </ul>
      <div class="cima-seo-actions">
        <a class="cta" href="${SITE}/${category}/${place.slug}/#cb-place-map">MAPPA E SENTIERI ↗</a>
        ${place.phone?`<a class="cima-seo-secondary" href="tel:${escape(place.phone.replace(/[^+\d]/g,''))}">Chiama la struttura</a>`:''}
        ${place.email?`<a class="cima-seo-secondary" href="mailto:${escape(place.email)}">Scrivi alla struttura</a>`:''}
      </div>
      ${place.operator||place.phone||place.email||place.openingHours||place.address||place.access||place.capacity? `<h2>Informazioni sulla località</h2><dl class="cima-seo-details">
        ${place.operator?`<div><dt>Gestore</dt><dd>${escape(place.operator)}</dd></div>`:''}
        ${place.phone?`<div><dt>Telefono</dt><dd>${escape(place.phone)}</dd></div>`:''}
        ${place.email?`<div><dt>Email</dt><dd>${escape(place.email)}</dd></div>`:''}
        ${place.capacity?`<div><dt>Capienza indicata</dt><dd>${escape(place.capacity)}</dd></div>`:''}
        ${place.access?`<div><dt>Accesso OSM</dt><dd>${escape(place.access)}</dd></div>`:''}
        ${place.openingHours?`<div><dt>Orari segnalati</dt><dd>${escape(place.openingHours)}</dd></div>`:''}
        ${place.address?`<div><dt>Indirizzo</dt><dd>${escape(place.address)}</dd></div>`:''}
        ${place.website?`<div><dt>Sito</dt><dd><a href="${escape(place.website)}" rel="noopener noreferrer">Sito della struttura</a></dd></div>`:''}
      </dl>`:''}
      ${related.length?`<h2>Sentieri e itinerari collegati</h2><ul class="list">${related.map(route=>`<li><a href="${SITE}/route/${route.slug}/">${escape(trailName(route))}</a> · ${km(route.distanceM)}</li>`).join('')}</ul>`:''}
      ${nearbyWater.length?`<h2>Acqua sulla cartografia del luogo</h2><p>${nearbyWater.length} fonti censite: posizione e indicazioni di potabilità sono visibili sulla mappa interattiva, non costituiscono una garanzia di sicurezza.</p><p><a class="cta" href="${SITE}/${category}/${place.slug}/#cb-place-map">Apri la mappa con i punti acqua</a></p>`:''}
      <h2>Meteo attuale e temperature stagionali</h2><p>Apri la scheda interattiva per consultare le condizioni attuali, le previsioni neve e pioggia e le medie stagionali 2021–2025 da Open-Meteo.</p>
      <p class="cima-seo-warning">Il dato geografico non prova accessibilità, stato della struttura, potabilità o percorribilità del sentiero. Verifica prima di partire.</p>
      <p class="sub">Fonte geografica: <a href="${escape(place.osmUrl)}" target="_blank" rel="noopener noreferrer">OpenStreetMap · ODbL</a>.
      ${photo?` Foto: ${escape(photo.author||'Wikimedia Commons')} · ${escape(photo.license||'Licenza nella fonte')} · <a href="${escape(photo.sourceUrl)}" target="_blank" rel="noopener noreferrer">Commons</a>`:''}</p>`,
  });
}

// Categoria SEO vera: un ingresso indicizzabile agli itinerari locali,
// senza 2.000 link a pagine vuote. La mappa dinamica mostra l'archivio intero.
for (const [kind,segment,label,title,blurb] of [
  ['rifugio','rifugi','Rifugi delle Dolomiti','RIFUGI. POI SI VEDE.',
    'Consulta rifugi con posizione, informazioni disponibili, meteo, sentieri e itinerari di avvicinamento nelle Dolomiti.'],
  ['bivacco','bivacchi','Bivacchi delle Dolomiti','BIVACCHI. POCHE SCUSE.',
    'Bivacchi alpini, ripari essenziali, quote, coordinate e sentieri nelle Dolomiti. Verifica sempre accesso e condizioni.'],
  ['borgo','borghi','Paesi e località montane','PAESI PICCOLI. GITE GROSSE.',
    'Esplora paesi alpini e punti di partenza con sentieri mappati, meteo e informazioni topografiche.'],
]) {
  const list=alpinePlaces
    .filter(p=>p.kind===kind && (kind==='rifugio'||kind==='bivacco'||(byStop.get(p.slug)||[]).length||p.website||p.photo||p.description))
    .sort((a,b)=>{
      const n=(byStop.get(b.slug)||[]).length-(byStop.get(a.slug)||[]).length;
      return n || a.name.localeCompare(b.name,'it');
    });
  page({
    path:`${segment}/`,
    title:`${label} · Meteo, dislivello, sentieri | Cima Becco`,
    description:blurb,
    jsonLd:{'@context':'https://schema.org','@graph':[
      {'@type':'CollectionPage',name:label,url:`${SITE}/${segment}/`,description:blurb,
        mainEntity:{'@type':'ItemList',itemListElement:list.slice(0,120).map((item,i)=>({
          '@type':'ListItem',position:i+1,name:item.name,url:`${SITE}/${segment}/${item.slug}/`
        }))}},
      breadcrumbLd([[label,null]])]},
    body:`${crumbs([[label]])}
      <div class="cima-seo-eyebrow">CIMA BECCO · ATLANTE DOLOMITI</div>
      <h1>${title}</h1>
      <p class="cima-seo-lead">${escape(blurb)}</p>
      <div class="cima-seo-actions"><a class="cta" href="${appLink(`#${segment==='borghi'?'paesi':segment}`)}">ESPLORA LA MAPPA COMPLETA ↗</a></div>
      <p class="sub">${list.length} luoghi con scheda · luoghi realmente censiti in OpenStreetMap.</p>
      <ul class="list">${list.slice(0,120).map(place=>`<li><a href="${SITE}/${segment}/${place.slug}/">${escape(place.name)}</a>${place.elevationM ? ' · '+metres(place.elevationM) : ''}${(byStop.get(place.slug)||[]).length?' · '+(byStop.get(place.slug)||[]).length+' sentieri':''}</li>`).join('')}</ul>
      <p class="sub">Per trovare anche i luoghi non ancora arricchiti usa la mappa interattiva. I dati OSM e le tracce non certificano condizioni, accessibilità o servizi.</p>`,
  });
}

// Le Alte Vie sono progetti contenitore; la lista delle tappe deriva soltanto
// da riferimenti espliciti OSM, non da distanze arbitrarie.
for (const trek of trekProjects) {
  const members=trek.routeSlugs.map(slug=>routeIndex.get(slug)).filter(Boolean);
  page({
    path:`trekking/${trek.slug}/`,
    title:`${trek.title} · Tappe e percorsi GPX | Cima Becco`,
    description:`${trek.description} Esplora segmenti, tappe confermate e collegamenti alle tracce cartografiche.`,
    jsonLd:{'@context':'https://schema.org','@graph':[
      {'@type':'CollectionPage',name:trek.title,description:trek.description,
       url:`${SITE}/trekking/${trek.slug}/`,
       mainEntity:{'@type':'ItemList',itemListElement:members.map((r,i)=>({
         '@type':'ListItem',position:i+1,url:`${SITE}/route/${r.slug}/`,name:trailName(r)}))}},
      breadcrumbLd([['Trekking',appLink('#atlante/trekking')],[trek.title,null]])]},
    body:`${crumbs([['Trekking',appLink('#atlante/trekking')],[trek.title]])}
      <div class="cima-seo-eyebrow">CAMMINI XXL · PROGETTO A TAPPE</div>
      <h1>${escape(trek.title)}</h1>
      <p class="cima-seo-lead">${escape(trek.description)}</p>
      <div class="cima-seo-tags"><span class="fun">${escape(trek.slogan)}</span><span>${members.length} segmenti mappati · ${trek.stages.length} tappe esplicite</span></div>
      <p><a class="cta" href="${appLink(`#atlante/trekking/${trek.slug}`)}">ESPLORA IL PROGETTO ↗</a></p>
      ${trek.stages.length?`<h2>TAPPE CON NUMERO ESPLICITO</h2><ul class="list">${trek.stages.map(stage=>`<li>Tappa ${stage.number}: ${stage.routeSlugs.map(slug=>`<a href="${SITE}/route/${slug}/">${escape(routeIndex.get(slug)?.name||slug)}</a>`).join(' · ')}</li>`).join('')}</ul>`:''}
      ${members.length?`<h2>TRACCE IDENTIFICATE</h2><ul class="list">${members.slice(0,80).map(route=>`<li><a href="${SITE}/route/${route.slug}/">${escape(trailName(route))}</a> · ${km(route.distanceM)}</li>`).join('')}</ul>`:''}
      <p class="cima-seo-warning">Il progetto non implica una traccia continua: le tappe devono essere connesse e verificate prima di pianificare un trekking end-to-end.</p>`,
  });
}

// The address list for search engines, the rules for crawlers, and a plain
// summary for AI assistants.
const urls = [`${SITE}/`, ...pages];
writeFileSync(
  join(DIST, 'sitemap.xml'),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map((url) => `<url><loc>${url}</loc><lastmod>${TODAY}</lastmod></url>`).join('\n')}\n</urlset>\n`,
);
// Everyone may read everything; the AI search crawlers are named so it is
// unmistakable that they are welcome.
const AI_CRAWLERS = ['GPTBot', 'OAI-SearchBot', 'ChatGPT-User', 'ClaudeBot', 'Claude-SearchBot', 'PerplexityBot', 'Google-Extended', 'Applebot-Extended', 'Bingbot'];
writeFileSync(
  join(DIST, 'robots.txt'),
  `User-agent: *\nAllow: /\n\n${AI_CRAWLERS.map((bot) => `User-agent: ${bot}\nAllow: /`).join('\n\n')}\n\nSitemap: ${SITE}/sitemap.xml\n`,
);
const topCountries = Object.entries(index.byCountry).sort((a, b) => b[1][0] - a[1][0]).slice(0, 12);
writeFileSync(
  join(DIST, 'llms.txt'),
  `# Cima Becco

> Atlante delle montagne italiane, con cime GeoNames, percorsi GPX e strumenti di pianificazione. Le tracce devono essere verificate sul terreno.

- Home and map: ${SITE}/
- Routes: ${SITE}/#routes
- Every place has a page at ${SITE}/place/<slug>/ and every country at ${SITE}/country/<iso-code>/
- Sitemap: ${SITE}/sitemap.xml
- Licences (MIT code, CC BY 4.0 routes and reviews, CC BY-SA photos): ${SITE}/#data

## Countries with the most mapped summits
${topCountries.map(([code, [count]]) => `- [${countryName(code)}](${SITE}/country/${code.toLowerCase()}/): ${count.toLocaleString('en')} summits`).join('\n')}

## GPX routes
${routes.map((route) => `- [${route.name}](${SITE}/route/${route.slug}/): ${km(route.distanceM)}, ${metres(route.gainM)} EG`).join('\n')}
`,
);

// A real "not found" page: without one, Cloudflare Pages answers every
// unknown address with the app and a 200, which search engines count as
// duplicate pages.
writeFileSync(
  join(DIST, '404.html'),
  `<!doctype html><html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Not found · Cima Becco</title><meta name="robots" content="noindex"><style>${STYLE}</style></head><body><header><a class="brand" href="${SITE}/">${MARK}Cima Becco</a></header><main><h1>That page is not here</h1><p class="sub">It may have moved, or the address has a typo.</p><p><a class="cta" href="${SITE}/">Go to Cima Becco</a></p></main></body></html>\n`,
);

console.log(`SEO: ${pages.length.toLocaleString('en')} pages, sitemap with ${urls.length.toLocaleString('en')} URLs, robots.txt, llms.txt for ${SITE}`);
