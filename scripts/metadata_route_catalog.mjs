#!/usr/bin/env node
/**
 * Cima Becco — estrazione massiva di metadati degli itinerari già censiti.
 * Legge gli shard OSM esistenti, non importa né pubblica nuove geometrie.
 * Tutte le coordinate/GPX vengono ESCLUSE dall'output editoriale.
 *
 * node scripts/metadata_route_catalog.mjs
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DATA = join(ROOT, 'public/data');
const OUT = join(ROOT, 'experiments/metadata');
const read = f => JSON.parse(readFileSync(f, 'utf8'));
const normalize = s => String(s || '').trim().toLocaleLowerCase('it').normalize('NFD')
  .replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ');
const GENERIC = /Tracciato OSM da verificare|non certifica percorribilità|^GPX route/i;
const ACTIVITY = { hike: 'escursione a piedi', trail: 'trail running', ferrata: 'via ferrata' };
const include = x => x !== undefined && x !== null && x !== '';
export function originalDescription(route) {
  return Boolean(route.description?.trim() && !GENERIC.test(route.description));
}
export function routeScore(r) {
  return (r.trailRef ? 2 : 0) + (r.stops?.length ? 2 : 0) +
    (r.caiDifficulty ? 1 : 0) + (r.operator ? 1 : 0) +
    (r.photos?.length ? 2 : 0) + (r.officialDescriptionUrl ? 1 : 0) +
    (originalDescription(r) ? 3 : 0) + (r.wikidataId ? 1 : 0);
}
function seo(r, title) {
  const type = ACTIVITY[r.activity] || 'percorso escursionistico';
  const parts = [r.description && originalDescription(r) ? r.description : type + ': ' + title + '.'];
  if (r.trailRef) parts.push('Segnavia ' + r.trailRef + '.');
  if (r.caiDifficulty) parts.push('Difficoltà dichiarata CAI ' + r.caiDifficulty + '.');
  if (r.stops?.length) parts.push('Nei pressi del percorso: ' + r.stops.slice(0, 3).map(s => s.name).join(', ') + '.');
  if (r.operator) parts.push('Gestore indicato: ' + r.operator + '.');
  return { title: title + ' — ' + type + ' | Cima Becco',
    description: parts.join(' ').replace(/\s+/g,' ').trim().slice(0, 290),
    isTemplate: !originalDescription(r) };
}
export function catalog(routes) {
  const unique = new Map(routes.map(r => [r.slug, r]));
  const data = [...unique.values()];
  const seen = new Map();
  for (const r of data) {
    const key = normalize(r.name);
    seen.set(key, (seen.get(key) || 0) + 1);
  }
  const byPlace = new Map();
  const records = data.map(r => {
    const ambiguous = (seen.get(normalize(r.name)) || 0) > 1;
    const nearbyNames = [...new Set((r.stops || []).filter(s => s.name).map(s => s.name))];
    const title = ambiguous && nearbyNames.length ? r.name + ' · ' + nearbyNames[0] : r.name;
    const facts = Object.fromEntries([
      'activity', 'trailRef', 'caiTrailNumber', 'operator', 'network',
      'caiDifficulty', 'sacScale', 'viaFerrataScale', 'osmcSymbol',
      'officialDescriptionUrl', 'sourceUpdatedAt', 'wikidataId',
    ].filter(k => include(r[k])).map(k => [k, r[k]]));
    const related = (r.stops || []).filter(s => s.slug && s.name).map(s =>
      ({ slug: s.slug, name: s.name, kind: s.kind,
        distanceM: s.distanceM, relation: s.relation,
        relationMeaning: 'vicinanza geometrica, non prova di accessibilità' }));
    for (const stop of related) {
      const links = byPlace.get(stop.slug) || new Set();
      links.add(r.slug);
      byPlace.set(stop.slug, links);
    }
    return {
      id: r.slug, entity: 'hiking_route_metadata',
      name: r.name, displayName: title, facts,
      ...(originalDescription(r) ? { originalDescription: r.description } : {}),
      source: { provider: 'openstreetmap', url: r.sourceUrl || null,
        licence: 'ODbL-1.0' },
      nearbyPlaces: related, seo: seo(r, title),
      review: { score: routeScore(r), nameCollision: ambiguous,
        candidateForEditorialReview: routeScore(r) >= 3 &&
          (!ambiguous || nearbyNames.length > 0),
        disambiguationByNearbyPlace: ambiguous && nearbyNames.length > 0 }
    };
  });
  const summary = {
    totalImportedRouteRecords: routes.length, distinctRouteIds: records.length,
    withTrailRef: records.filter(r => r.facts.trailRef).length,
    withCaiDifficulty: records.filter(r => r.facts.caiDifficulty).length,
    withOriginalDescription: records.filter(r => r.originalDescription).length,
    withNearbyPlaces: records.filter(r => r.nearbyPlaces.length).length,
    distinctNearbyPlaces: byPlace.size,
    nameCollisionRecords: records.filter(r => r.review.nameCollision).length,
    candidateForEditorialReview: records.filter(r => r.review.candidateForEditorialReview).length,
    noGeometryInOutput: true,
  };
  return { records, summary,
    relations: Object.fromEntries([...byPlace].map(([k,v]) => [k, [...v]])) };
}
export function collect() {
  const all = [];
  const featured = join(DATA, 'routes.json');
  if (existsSync(featured)) {
    const file = read(featured);
    all.push(...(Array.isArray(file) ? file : file.routes || []));
  }
  const manifest = read(join(DATA, 'routes-manifest.json'));
  let missingShards = 0;
  for (const tile of manifest.tiles || [])
    for (const filename of tile.files || []) {
      // Non permettere path traversal da dati esterni.
      if (!/^routes-tiles\/it_\d+_\d+_\d+\.json$/.test(filename)) continue;
      const path = join(DATA, filename);
      if (!existsSync(path)) { missingShards++; continue; }
      all.push(...(read(path).routes || []));
    }
  return { routes: all, missingShards, manifestRouteCount: manifest.routeCount };
}
export function main() {
  const { routes, missingShards, manifestRouteCount } = collect();
  if (missingShards) throw Error('Shard mancanti: ' + missingShards + '. Nessun report incompleto.');
  const output = catalog(routes);
  mkdirSync(OUT, { recursive: true });
  const save = (name, value) =>
    writeFileSync(join(OUT, name), JSON.stringify(value, null, 2) + '\n', 'utf8');
  save('route-metadata.json', { version: 1,
    generatedAt: new Date().toISOString(), records: output.records });
  save('route-place-relations.json', { version: 1, relations: output.relations });
  save('route-simulation-report.json', { ...output.summary, manifestRouteCount,
    sample: output.records.filter(r => r.review.candidateForEditorialReview)
      .sort((a,b) => b.review.score-a.review.score).slice(0, 20),
    note: 'Prototipo editoriale: nessuna nuova traccia e nessuna pubblicazione automatica' });
  console.log(JSON.stringify({ ...output.summary, manifestRouteCount }, null, 2));
}
if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) main();
