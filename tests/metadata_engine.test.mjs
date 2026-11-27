import test from 'node:test';
import assert from 'node:assert/strict';
import { buildAtlas, scorePlace, seoMetadata } from '../scripts/metadata_atlas_engine.mjs';
import { catalog, originalDescription, routeScore } from '../scripts/metadata_route_catalog.mjs';

test('schede luoghi: provenienza e nessun dato inventato', () => {
  const input = [
    { slug: 'osm-n-1', name: 'Rifugio di prova', kind: 'rifugio', lat: 46.1, lng: 11.4,
      osmUrl: 'https://www.openstreetmap.org/node/1', elevationM: 2000,
      elevationSource: 'dem', wikidata: 'Q123', website: 'https://example.org' },
    { slug: 'osm-n-2', name: 'Rifugio di prova', kind: 'rifugio', lat: 46.2, lng: 11.5,
      osmUrl: 'https://www.openstreetmap.org/node/2' }
  ];
  const { records, summary } = buildAtlas(input, {
    Q123: { label: 'Rifugio di prova', description: 'rifugio nelle Alpi', aliases: ['Testhütte'] }
  });
  assert.equal(records.length, 2);
  assert.equal(summary.ambiguousNameRecords, 2);
  assert.equal(records[0].review.candidateForEditorialReview, false);
  assert.equal(records[0].provenance.elevationM.confidence, 'estimated');
  assert.equal(records[0].wikidataMetadata.licence, 'CC0');
  assert.ok(records[0].aliases.includes('Testhütte'));
  assert.match(records[0].seo.description, /quota stimata 2000 m/);
  assert.equal(records[1].seo.isTemplate, true);
  assert.ok(!records[1].seo.description.includes('2000'));
});

test('rifiuta identificativi Wikidata non validi e mantiene null informativi', () => {
  assert.equal(scorePlace({ wikidata: 'invalid' }), 0);
  const s = seoMetadata({ name: 'Bivacco Prova', kind: 'bivacco' });
  assert.ok(!s.description.includes('m di quota'));
});

test('itinerari: nessuna traccia/coordinate in archivio metadata', () => {
  const input = [
    { slug: 'osm-hiking-1', name: 'Sentiero SI', activity: 'hike',
      coordinates: [[11, 46, 1000], [11.1, 46.1, 1200]],
      trailRef: 'SI', description: 'Tracciato OSM da verificare; non certifica percorribilità.',
      stops: [{ slug: 'osm-n-1', name: 'Rifugio Prova', kind: 'rifugio', distanceM: 50, relation: 'passaggio' }],
      sourceUrl: 'https://www.openstreetmap.org/relation/1' },
    { slug: 'osm-hiking-2', name: 'Sentiero SI', activity: 'hike',
      coordinates: [[11.3, 46.2, 1200]], sourceUrl: 'https://www.openstreetmap.org/relation/2' }
  ];
  const { records, relations, summary } = catalog(input);
  assert.equal(records.length, 2);
  assert.equal(summary.withOriginalDescription, 0);
  assert.equal(summary.nameCollisionRecords, 2);
  assert.equal(records[0].displayName, 'Sentiero SI · Rifugio Prova');
  assert.equal(records[1].review.candidateForEditorialReview, false);
  assert.deepEqual(relations['osm-n-1'], ['osm-hiking-1']);
  assert.ok(!JSON.stringify(records).includes('coordinates'));
  assert.equal(originalDescription(input[0]), false);
  assert.equal(routeScore(input[0]), 4);
});
