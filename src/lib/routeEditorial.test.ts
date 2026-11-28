import { describe, expect, it } from 'vitest';
import type { Route } from '../types';
import { trailTitle, trailDescription, trailMood, trailSources, trailArea } from './routeEditorial';

const route = (over: Partial<Route> = {}): Route => ({
  slug: 'osm-hiking-123', name: 'Sentiero 479', venueSlugs: [], distanceM: 7800,
  gainM: 0, lossM: 0, elevationAvailable: false, loop: false,
  coordinates: [[12.27, 46.51, 0], [12.28, 46.52, 0]],
  source: 'curated', activity: 'hike', sourceUrl: 'https://www.openstreetmap.org/relation/123',
  description: 'Tracciato OSM da verificare sul terreno; non certifica percorribilità, condizioni o sicurezza.',
  ...over,
});

describe('editoriale Cima Becco', () => {
  it('rende un nome sentiero generico leggibile senza inventare luoghi', () => {
    const found = route();
    expect(trailArea(found)).toBe('Dolomiti orientali');
    expect(trailTitle(found)).toBe('Sentiero 479 · Dolomiti orientali');
    expect(trailTitle(route({ name: 'Sentiero Italia delle Alpi' }))).toBe('Sentiero Italia delle Alpi');
  });
  it('non inventa quota e panorami quando il DEM manca', () => {
    const description = trailDescription(route());
    expect(description).toMatch(/7,8 km/);
    expect(description).toMatch(/479/);
    expect(description).not.toMatch(/panoram|dislivello positivo stimato/);
  });
  it('separa difficoltà CAI e tag umoristici', () => {
    expect(trailMood(route({ caiDifficulty: 'T', elevationAvailable: true, gainM: 120 })).quip).toBe('MERENDEROS');
    expect(trailMood(route({ caiDifficulty: 'T' })).quip).toBeNull();
    expect(trailMood(route({ caiDifficulty: 'EE' })).quip).toBe('OGGI SI BESTEMMIA');
    expect(trailMood(route({ caiDifficulty: 'EEA' })).label).toBe('Esperti con attrezzatura · CAI EEA');
    // Quando manca il grado CAI ma è nota la distanza, la fatica è stimabile\n    // e resta distinta dalla difficoltà tecnica sconosciuta.\n    expect(trailMood(route({})).quip).toBeNull();\n    expect(trailMood(route({})).label).toMatch(/grado tecnico da verificare/);
  });
  it('non attribuisce a una ferrata una difficoltà se manca la scala', () => {
    expect(trailMood(route({ activity: 'ferrata' })).level).toBe('unknown');
    expect(trailMood(route({ activity: 'ferrata', viaFerrataScale: '3+' })).quip).toBe('AVAMBRACCI IN LEASING');
  });
  it('esclude le homepage CAI/SAT scambiate per schede singole', () => {
    const first = trailSources(route({ officialDescriptionUrl: 'https://www.sat.tn.it/' }));
    expect(first).toHaveLength(1);
    expect(first[0].label).toMatch(/OpenStreetMap/);
    const second = trailSources(route({ officialDescriptionUrl: 'https://www.sat.tn.it/sentieri/numero-479/' }));
    expect(second).toHaveLength(2);
    expect(second[0].label).toBe('Scheda SAT');
  });
  it('collega solo i rifugi geolocalizzati nei dati importati', () => {
    const associated=route({stops:[{
      slug:'osm-n-321',name:'Rifugio Test',kind:'rifugio',relation:'arrivo',distanceM:7,at:0.98,
    }]});
    expect(trailTitle(associated)).toContain('Rifugio Test');
    expect(trailDescription(associated)).toContain('Rifugio Test');
    expect(trailTitle(route())).not.toContain('Rifugio Test');
  });

});
