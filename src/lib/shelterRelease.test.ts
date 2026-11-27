import { describe, expect, it } from 'vitest';
import { mergeShelterRelease, type ShelterRelease } from './shelterRelease';
import type { AlpinePlacesDataset } from './alpinePlaces';

const existing: AlpinePlacesDataset = {
  generatedAt: '2026-11-27', source: 'OSM', coverage: 'Dolomiti',
  places: [
    { kind: 'bivacco', name: 'Bivacco Cavinato', slug: 'osm-n-1',
      lat: 46.5, lng: 11.8, osmUrl: 'https://www.openstreetmap.org/node/1',
      capacity: 5 },
    { kind: 'rifugio', name: 'Fiamme Gialle', slug: 'osm-n-2',
      lat: 46.7, lng: 11.9, osmUrl: 'https://www.openstreetmap.org/node/2' },
    { kind: 'borgo', name: 'Canazei', slug: 'osm-n-3',
      lat: 46.48, lng: 11.77, osmUrl: 'https://www.openstreetmap.org/node/3' },
  ],
};
const release: ShelterRelease = {
  schemaVersion: '2.0', releaseChannel: 'CAI_OSM_BIVOUACS_SHELTERS',
  creditPolicy: 'centralized:/fonti-e-crediti/', reclassifiedOsmIds: ['node/2'],
  entities: [
    { id: 'osm:node:1', name: 'CAVINATO GIUSEPPE', kind: 'bivouac',
      subtype: 'fixed_bivouac', shelterTypeLabel: 'Bivacco', slug: 'osm-n-1',
      sourceIds: {osm: 'node/1', cai: '920000101'},
      geo: {point: {lat: 46.5, lng: 11.8}},
      facts: {bedsTotal: {value: 9, unit: 'posti', sourceId: 'cai:shelter:920000101'}},
      media: [{id: 'caimedia:1', kind: 'photo',
        url: 'https://rifugi.cai.it/m/1.jpg',
        sourceUrl: 'https://rifugi.cai.it/shelters/920000101',
        licence: 'CAI source', author: 'Foto CAI', reuseAllowed: true, subjectVerified: true}],
    },
    { id: 'osm:node:2', name: 'FIAMME GIALLE', kind: 'bivouac',
      subtype: 'fixed_bivouac', shelterTypeLabel: 'Bivacco', slug: 'osm-n-2',
      sourceIds: {osm: 'node/2', cai: '922005301'},
      geo: {point: {lat: 46.7, lng: 11.9}}, facts: {} },
    { id: 'cai:999', name: 'CAPANNA SOCIALE ESEMPIO', kind: 'shelter',
      subtype: 'social_cabin', shelterTypeLabel: 'Capanna sociale',
      slug: 'cai-999', sourceIds: {cai:'999'}, geo: {point: {lat: 46.9, lng: 12.0}},
      facts: {waterAvailableReported: {value: false, sourceId: 'cai:shelter:999'}} },
  ],
};

describe('Blocco 2 — integrazione bivacchi e ricoveri', () => {
  it('mantiene permalink OSM e arricchisce il bivacco con CAI', () => {
    const result = mergeShelterRelease(existing, release);
    const p = result.places.find(x => x.slug === 'osm-n-1');
    expect(p?.kind).toBe('bivacco');
    expect(p?.capacity).toBe(9);
    expect(p?.sourceIds?.cai).toBe('920000101');
    expect(p?.photo?.url).toContain('/m/1.jpg');
    expect(p?.shelterTypeLabel).toBe('Bivacco');
  });
  it('riclassifica Fiamme Gialle e non crea doppia scheda', () => {
    const result = mergeShelterRelease(existing, release);
    const p = result.places.filter(x => x.slug === 'osm-n-2');
    expect(p).toHaveLength(1);
    expect(p[0].kind).toBe('bivacco');
    expect(p[0].sourceIds?.cai).toBe('922005301');
  });
  it('conserva capanna sociale con tipologia esplicita e URL CAI', () => {
    const result = mergeShelterRelease(existing, release);
    const p = result.places.find(x => x.slug === 'cai-999');
    expect(p?.kind).toBe('bivacco');
    expect(p?.subtype).toBe('social_cabin');
    expect(p?.shelterTypeLabel).toBe('Capanna sociale');
    expect(p?.officialUrl).toBe('https://rifugi.cai.it/shelters/999');
    expect(p?.facts?.waterAvailableReported.value).toBe(false);
    expect(p?.sourceIds?.osm).toBeUndefined();
  });
  it('preserva i paesi e non espone foto senza metadati', () => {
    const copy: ShelterRelease = JSON.parse(JSON.stringify(release)) as ShelterRelease;
    copy.entities[0].media![0].reuseAllowed = false;
    const merged = mergeShelterRelease(existing, copy);
    expect(merged.places.some(p => p.slug === 'osm-n-3')).toBe(true);
    expect(merged.places.find(p => p.slug === 'osm-n-1')?.photo).toBeUndefined();
  });
  it('ignora i formati sconosciuti senza danneggiare il catalogo', () => {
    expect(mergeShelterRelease(existing, null)).toBe(existing);
    expect(mergeShelterRelease(existing, {schemaVersion:'999'})).toBe(existing);
  });
});
