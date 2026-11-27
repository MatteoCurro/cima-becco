import { describe, expect, it } from 'vitest';
import { mergeRefugeRelease, type RefugeRelease } from './refugeRelease';
import type { AlpinePlacesDataset } from './alpinePlaces';

const base: AlpinePlacesDataset = {
  generatedAt: '2026-11-27',
  source: 'OpenStreetMap · ODbL',
  coverage: 'Dolomiti',
  places: [
    { kind: 'rifugio', slug: 'osm-w-100', name: 'Rifugio Boé',
      lat: 46.5, lng: 11.5, osmUrl: 'https://www.openstreetmap.org/way/100', capacity: 60 },
    { kind: 'rifugio', slug: 'osm-n-200', name: 'Fiamme Gialle',
      lat: 46.6, lng: 11.6, osmUrl: 'https://www.openstreetmap.org/node/200' },
    { kind: 'borgo', slug: 'osm-n-999', name: 'Canazei',
      lat: 46.4, lng: 11.7, osmUrl: 'https://www.openstreetmap.org/node/999' },
  ],
};
const fixture: RefugeRelease = {
  schemaVersion: '1.1',
  releaseChannel: 'OSM_CAI_REFUGES',
  attribution: [{ source: 'CAI', url: 'https://rifugi.cai.it/' }],
  quarantinedOsmIds: ['node/200'],
  entities: [
    { id: 'cb-matched', kind: 'refuge', name: 'Rifugio Boé', slug: 'rifugio-boe',
      slugAliases: ['osm-w-100'], sourceIds: { osm: 'way/100', cai: '921800106' },
      sources: [{ id: 'osm:way:100', url: 'https://www.openstreetmap.org/way/100' }],
      geo: { point: { lat: 46.5, lng: 11.5 } },
      facts: { bedsTotal: { value: 75, sourceId: 'cai:921800106' } },
      description: 'Scheda CAI del Sella.',
      media: [{ id: 'cai:image:test', kind: 'photo', url: 'https://rifugi.cai.it/photo.jpg',
        sourceUrl: 'https://rifugi.cai.it/shelters/921800106',
        author: 'Archivio CAI', licence: 'Riuso verificato',
        reuseAllowed: true, subjectVerified: true }],
    },
    { id: 'cai:921800999', kind: 'refuge', name: 'Rifugio di prova', slug: 'cai-921800999',
      sourceIds: { cai: '921800999' }, sources: [
        { id: 'cai:shelter:921800999', url: 'https://rifugi.cai.it/shelters/921800999' },
      ],
      geo: { point: { lat: 46.9, lng: 12.5 } },
      facts: { wifi: { value: true, sourceUrl: 'https://rifugi.cai.it/shelters/921800999' } },
    },
  ],
};

describe('Canonical refuge release integration', () => {
  it('preserves the legacy OSM permalink and adds CAI facts/media', () => {
    const enriched = mergeRefugeRelease(base, fixture);
    const place = enriched.places.find(p => p.slug === 'osm-w-100');
    expect(place).toBeDefined();
    expect(place?.name).toBe('Rifugio Boé');
    expect(place?.sourceIds?.cai).toBe('921800106');
    expect(place?.capacity).toBe(75);
    expect(place?.description).toBe('Scheda CAI del Sella.');
    expect(place?.photo?.url).toBe('https://rifugi.cai.it/photo.jpg');
    expect(place?.media?.length).toBe(1);
  });

  it('has a navigable CAI-only refuge without falsely attributing to OSM', () => {
    const enriched = mergeRefugeRelease(base, fixture);
    const place = enriched.places.find(p => p.slug === 'cai-921800999');
    expect(place?.kind).toBe('rifugio');
    expect(place?.sourceIds?.cai).toBe('921800999');
    expect(place?.sourceIds?.osm).toBeUndefined();
    expect(place?.officialUrl).toBe('https://rifugi.cai.it/shelters/921800999');
    expect(place?.facts?.wifi.value).toBe(true);
    expect(place?.lat).toBe(46.9);
  });

  it('quarantines misclassified OSM items without changing nearby towns', () => {
    const enriched = mergeRefugeRelease(base, fixture);
    expect(enriched.places.some(p => p.slug === 'osm-n-200')).toBe(false);
    expect(enriched.places.some(p => p.slug === 'osm-n-999')).toBe(true);
    expect(enriched.places.length).toBe(3);
  });

  it('does not duplicate repeated OSM place or override it with new CAI slug', () => {
    const enriched = mergeRefugeRelease(base, fixture);
    expect(enriched.places.filter(p => p.sourceIds?.osm === 'way/100')).toHaveLength(1);
    expect(enriched.places.some(p => p.slug === 'rifugio-boe')).toBe(false);
  });

  it('falls back unchanged when the release is absent or not versioned', () => {
    expect(mergeRefugeRelease(base, null)).toBe(base);
    expect(mergeRefugeRelease(base, { schemaVersion: '0' })).toBe(base);
    expect(mergeRefugeRelease(base, { schemaVersion: '1.1',
      releaseChannel: 'OSM_CAI_REFUGES' })).toBe(base);
  });

  it('never renders a medium without subject and reuse verification', () => {
    const variant: RefugeRelease = JSON.parse(JSON.stringify(fixture)) as RefugeRelease;
    variant.entities[0].media![0].reuseAllowed = false;
    const place = mergeRefugeRelease(base, variant).places.find(p => p.slug === 'osm-w-100');
    expect(place?.photo).toBeUndefined();
    expect(place?.media).toHaveLength(0);
  });
});
