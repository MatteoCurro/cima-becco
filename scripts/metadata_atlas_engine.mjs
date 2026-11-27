#!/usr/bin/env node
/**
 * Cima Becco — prototipo di motore metadata-first.
 *
 * Solo metadati; NON importa, copia o pubblica geometrie/GPX.
 * Run:
 *   node scripts/metadata_atlas_engine.mjs
 *   node scripts/metadata_atlas_engine.mjs --fetch --limit 100
 *
 * Gli output vanno in experiments/metadata/ e NON vengono pubblicati da Pages.
 * Le acquisizioni online sono esplicite, a piccoli batch, con cache e retry.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const INPUT = join(ROOT, 'public/data/alpine-places.json');
const DIR = join(ROOT, 'experiments/metadata');
const CACHE = join(DIR, 'wikidata-cache.json');
const SNAPSHOT = join(DIR, 'atlas-metadata.json');
const REPORT = join(DIR, 'simulation-report.json');
const WDQS_API = 'https://www.wikidata.org/w/api.php';
const UA = 'CimaBecco-MetadataResearch/0.1 (https://www.cimabecco.it; metadata research; no bulk scraping)';
const KIND = { rifugio: 'rifugio alpino', bivacco: 'bivacco', borgo: 'località' };
const SOURCE_KEYS = [
  'description', 'website', 'operator', 'capacity', 'openingHours',
  'phone', 'email', 'address', 'elevationM', 'wikipedia', 'wikidata', 'photo'
];

export const validQid = x => /^Q[1-9]\d*$/.test(String(x ?? ''));
export const nameKey = x => String(x || '').trim().toLocaleLowerCase('it')
  .normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/\s+/g, ' ');

const meaningful = x => x !== undefined && x !== null && x !== '';
const factsCount = p => SOURCE_KEYS.filter(k => meaningful(p[k])).length;

export function scorePlace(p, wd = null) {
  // Uno score editoriale, NON un giudizio di sicurezza/affidabilita della via.
  return (p.description ? 3 : 0) + (p.wikipedia ? 2 : 0) +
    (validQid(p.wikidata) ? 1 : 0) + (p.website ? 1 : 0) +
    (p.photo ? 2 : 0) + (Number.isFinite(p.elevationM) ? 1 : 0) +
    (p.operator ? 1 : 0) + (p.openingHours ? 1 : 0) +
    (p.capacity ? 1 : 0) + (wd?.description ? 2 : 0) +
    (wd?.aliases?.length ? 1 : 0);
}
export function seoMetadata(p, wd = null) {
  const category = KIND[p.kind] || 'luogo';
  const title = p.name + ' — ' + category + ' | Cima Becco';
  const facts = [];
  if (Number.isFinite(p.elevationM)) {
    const label = p.elevationSource === 'dem' ? 'quota stimata' : 'quota riportata';
    facts.push(label + ' ' + Math.round(p.elevationM) + ' m');
  }
  if (p.operator) facts.push('gestore: ' + p.operator);
  if (p.capacity) facts.push('posti indicati: ' + p.capacity);
  if (wd?.description) facts.push(wd.description);
  const head = p.description || p.name + ' è una ' + (p.kind === 'borgo' ? 'località' : p.kind === 'bivacco' ? 'struttura di tipo bivacco' : 'struttura di tipo rifugio') + ' censita nell’atlante Cima Becco.';
  return {
    title,
    description: (head + ' ' + facts.join('. ') + '. Consulta fonti e posizione.').replace(/\s+/g, ' ').trim().slice(0, 290),
    isOriginalDescription: Boolean(p.description),
    // La descrizione di servizio non deve essere scambiata per contenuto editoriale originale.
    isTemplate: !p.description,
  };
}
const safeFields = p => Object.fromEntries(SOURCE_KEYS
  .filter(k => meaningful(p[k]))
  .map(k => [k, p[k]]));

export function buildAtlas(places, wdCache = {}) {
  const counts = new Map();
  for (const p of places) {
    const key = p.kind + ':' + nameKey(p.name);
    counts.set(key, (counts.get(key) || 0) + 1);
  }
  const records = places.map(p => {
    const wd = validQid(p.wikidata) ? (wdCache[p.wikidata] || null) : null;
    const sameName = counts.get(p.kind + ':' + nameKey(p.name)) > 1;
    const quality = scorePlace(p, wd);
    const sourceFields = safeFields(p);
    const fieldProvenance = Object.fromEntries(Object.keys(sourceFields).map(k =>
      [k, { source: 'openstreetmap', url: p.osmUrl, licence: 'ODbL-1.0',
        ...(k === 'elevationM' && p.elevationSource === 'dem' ?
          { method: 'DEM', confidence: 'estimated' } : {}) }]));
    const aliases = [...new Set([...(wd?.aliases || []), ...(wd?.alternativeLabels || [])]
      .filter(x => x && nameKey(x) !== nameKey(p.name)))].slice(0, 25);
    return {
      id: p.slug, type: p.kind, name: p.name, aliases,
      location: { lat: p.lat, lon: p.lng },
      sourceIds: { osm: p.osmUrl, ...(validQid(p.wikidata) ? { wikidata: p.wikidata } : {}) },
      originalFacts: sourceFields, provenance: fieldProvenance,
      ...(wd ? { wikidataMetadata: { ...wd, licence: 'CC0', source: 'https://www.wikidata.org/wiki/' + p.wikidata } } : {}),
      seo: seoMetadata(p, wd),
      review: {
        score: quality, factsCount: factsCount(p), nameCollision: sameName,
        // Il semplice titolo/coordinate NON bastano per indicizzare una pagina.
        candidateForEditorialReview: quality >= 3 && !sameName,
        needsDisambiguation: sameName,
      }
    };
  });
  const byKind = {};
  for (const r of records) {
    const c = byKind[r.type] ??= { records: 0, withWikidataId: 0, withWikidataEnrichment: 0, candidateForReview: 0, ambiguousNames: 0, originalDescriptions: 0 };
    c.records++;
    c.withWikidataId += Number(Boolean(r.sourceIds.wikidata));
    c.withWikidataEnrichment += Number(Boolean(r.wikidataMetadata));
    c.candidateForReview += Number(r.review.candidateForEditorialReview);
    c.ambiguousNames += Number(r.review.needsDisambiguation);
    c.originalDescriptions += Number(!r.seo.isTemplate);
  }
  const summary = {
    generatedAt: new Date().toISOString(), mode: 'offline_metadata_simulation',
    totalPlaces: records.length, byKind,
    totalWikidataIds: records.filter(r => r.sourceIds.wikidata).length,
    totalEnrichedViaWikidata: records.filter(r => r.wikidataMetadata).length,
    totalOriginalDescriptions: records.filter(r => !r.seo.isTemplate).length,
    candidateForEditorialReview: records.filter(r => r.review.candidateForEditorialReview).length,
    ambiguousNameRecords: records.filter(r => r.review.needsDisambiguation).length,
    notice: 'I candidati NON sono automaticamente pubblicati o certificati. Punteggi e descrizioni sintetiche sono sperimentali.'
  };
  return { records, summary };
}
const load = path => existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : null;
const save = (path, value) => {
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, JSON.stringify(value, null, 2) + '\n', 'utf8');
};
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function getLang(entry) {
  for (const key of ['it', 'de', 'en']) if (entry?.[key]?.value) return entry[key].value;
  return null;
}
function parseWikidata(entity) {
  const label = getLang(entity.labels);
  const description = getLang(entity.descriptions);
  const aliasSet = new Set();
  for (const key of ['it', 'de', 'en'])
    for (const a of entity.aliases?.[key] || []) if (a?.value) aliasSet.add(a.value);
  const italianArticle = entity.sitelinks?.itwiki?.title || null;
  return { ...(label ? { label } : {}), ...(description ? { description } : {}),
    aliases: [...aliasSet].slice(0, 25),
    ...(italianArticle ? { wikipediaTitleIt: italianArticle } : {}),
    retrievedAt: new Date().toISOString() };
}
async function fetchBatch(ids, attempts = 4) {
  const query = new URLSearchParams({
    action: 'wbgetentities', ids: ids.join('|'), format: 'json',
    props: 'labels|descriptions|aliases|sitelinks', languages: 'it|de|en',
    languagefallback: '1'
  });
  for (let attempt = 0; attempt < attempts; attempt++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 25000);
      let response;
      try {
        response = await fetch(WDQS_API + '?' + query, {
          headers: { 'User-Agent': UA, Accept: 'application/json' },
          signal: controller.signal
        });
      } finally { clearTimeout(timer); }
      if (response.ok) {
        const payload = await response.json();
        if (payload.error) throw new Error(JSON.stringify(payload.error));
        return payload.entities || {};
      }
      if (response.status !== 429 && response.status < 500)
        throw new Error('Wikidata HTTP ' + response.status);
      const retry = Number(response.headers.get('retry-after') || 0);
      await sleep(Math.max(1200 * 2 ** attempt, Math.min(retry * 1000, 30000)));
    } catch (e) {
      if (attempt === attempts - 1) throw e;
      await sleep(1200 * 2 ** attempt);
    }
  }
  return {};
}
async function enrich(places, limit, delayMs) {
  const cache = load(CACHE) || { version: 1, entities: {} };
  const existing = cache.entities || {};
  const unique = [...new Set(places.map(p => p.wikidata).filter(validQid))].sort();
  const candidates = unique.filter(id => !existing[id]);
  const selected = candidates.slice(0, limit);
  let success = 0;
  for (let i = 0; i < selected.length; i += 20) {
    const ids = selected.slice(i, i + 20);
    try {
      const found = await fetchBatch(ids);
      for (const id of ids) {
        if (found[id] && !found[id].missing) {
          existing[id] = parseWikidata(found[id]);
          success++;
        }
      }
      cache.entities = existing;
      cache.generatedAt = new Date().toISOString();
      save(CACHE, cache);
      console.log('Wikidata', Math.min(i+20, selected.length), '/', selected.length, 'recuperati', success);
    } catch (error) {
      console.error('Batch fallito: ' + ids.join(',') + ': ' + error.message);
      // Nessun record inesistente o errore viene spacciato per successo.
    }
    if (i + 20 < selected.length) await sleep(delayMs);
  }
  return cache.entities;
}
export async function main(args = process.argv.slice(2)) {
  const fetchMode = args.includes('--fetch');
  const limitPos = args.indexOf('--limit');
  const delayPos = args.indexOf('--delay-ms');
  const limit = limitPos >= 0 ? Number(args[limitPos + 1]) : 100;
  const delayMs = delayPos >= 0 ? Number(args[delayPos + 1]) : 1250;
  if (!Number.isInteger(limit) || limit < 1 || limit > 100000) throw new Error('Invalid --limit');
  if (!Number.isInteger(delayMs) || delayMs < 1000) throw new Error('Invalid --delay-ms');
  const input = load(INPUT);
  if (!Array.isArray(input?.places)) throw new Error('Missing public/data/alpine-places.json');
  const cache = fetchMode ? await enrich(input.places, limit, delayMs) : (load(CACHE)?.entities || {});
  const { records, summary } = buildAtlas(input.places, cache);
  const sample = records.filter(r => r.review.candidateForEditorialReview)
    .sort((a,b) => b.review.score-a.review.score || a.name.localeCompare(b.name, 'it'))
    .slice(0, 20);
  save(SNAPSHOT, { version: 1, generatedAt: summary.generatedAt, records });
  save(REPORT, { ...summary, sample, source: 'public/data/alpine-places.json',
    sourceLicence: 'ODbL-1.0', outputsAreNotPublished: true,
    note: 'Il recupero Wikidata richiede --fetch; la sola simulazione offline non effettua richieste.' });
  console.log(JSON.stringify({ ...summary, sample: sample.slice(0, 3).map(r => ({ name:r.name, score:r.review.score })) }, null, 2));
}
if (process.argv[1] && fileURLToPath(import.meta.url) === fileURLToPath(new URL('file://' + process.argv[1]).href)) {
  main().catch(e => { console.error(e); process.exitCode = 1; });
}
