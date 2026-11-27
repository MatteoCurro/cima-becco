import { describe, expect, it } from 'vitest';
import type { Route } from '../types';
import { DEFAULT_PACE_S_PER_KM, matchRoutes, type RunNeeds } from './routeMatch';
import { routeEstimateS } from './routeTime';

// Geometrie costruite per il test, senza dipendere da GPX esterni eliminati.
const make = (name: string, slug: string, km: number, gainM: number, longitude: number, latitude: number, loop = false): Route => ({
  slug, name, venueSlugs: [], distanceM: km * 1000, gainM, lossM: 0,
  elevationAvailable: true, loop,
  activity: 'hike', source: 'curated',
  coordinates: [
    [longitude, latitude, 950],
    [longitude + 0.005, latitude + 0.002, 950 + gainM],
    [longitude + 0.012, latitude + 0.003, 950 + gainM],
  ],
});
const lago = make('Sentiero del Lago', 'sentiero-lago', 5, 20, 12.20, 46.52);
const rifugio = make('Salita al Rifugio', 'salita-rifugio', 8, 600, 12.36, 46.62);
const lungo = make('Traversata Dolomitica', 'traversata-dolomitica', 24, 450, 11.79, 46.57);
const ferrata = make('Ferrata', 'ferrata', 3, 900, 12.46, 46.78);
const routes = [lago, rifugio, lungo, ferrata];
const needs = (over: Partial<RunNeeds> = {}): RunNeeds =>
  ({ where: null, length: null, terrain: 'any', paceSPerKm: DEFAULT_PACE_S_PER_KM, ...over });
const match = (n: RunNeeds, data = routes) => matchRoutes(data, n);

describe('suggerimenti escursionistici', () => {
  it('restituisce un elenco vuoto quando non ci sono percorsi', () => {
    expect(match(needs(), []).matches).toEqual([]);
  });
  it('ordina per distanza obiettivo, senza privilegiare vecchie categorie bike', () => {
    expect(match(needs({ length: { kind: 'distance', metres: 5_000 } })).matches[0].route.slug).toBe(lago.slug);
    expect(match(needs({ length: { kind: 'distance', metres: 8_000 } })).matches[0].route.slug).toBe(rifugio.slug);
    expect(match(needs({ length: { kind: 'distance', metres: 23_000 } })).matches[0].route.slug).toBe(lungo.slug);
  });
  it('usa lo stesso algoritmo temporale delle schede', () => {
    const result = match(needs()).matches.find((x) => x.route.slug === rifugio.slug);
    expect(result?.durationS).toBe(routeEstimateS(rifugio));
    expect(match(needs({ paceSPerKm: DEFAULT_PACE_S_PER_KM * 1.4 })).matches.find((x) => x.route.slug === rifugio.slug)?.durationS)
      .toBeGreaterThan(result!.durationS);
  });
  it('distingue il profilo pianeggiante dalla salita tecnica', () => {
    const flat = match(needs({ terrain: 'flat' })).matches;
    expect(flat[0].route.slug).toBe(lago.slug);
    const hilly = match(needs({ terrain: 'hilly' })).matches;
    expect([rifugio.slug, ferrata.slug]).toContain(hilly[0].route.slug);
  });
  it('non inventa dislivello per itinerari privi di quote', () => {
    const unknown = { ...lago, slug: 'senza-quote', elevationAvailable: false };
    const selected = match(needs({ terrain: 'hilly' }), [unknown]).matches[0];
    expect(selected.reasons).toContainEqual({ kind: 'terrain', band: null, climbRateMPerKm: null });
    expect(selected.route.slug).toBe('senza-quote');
  });
  it('trova itinerari vicini al punto scelto, non quelli oltre 5 km', () => {
    const center = { kind: 'point' as const, lng: 12.20, lat: 46.52 };
    const result = match(needs({ where: center }));
    expect(result.reachM).toBe(5_000);
    expect(result.matches.map((x) => x.route.slug)).toContain(lago.slug);
    expect(result.matches.map((x) => x.route.slug)).not.toContain(ferrata.slug);
    expect(result.matches.map((x) => x.route.slug)).not.toContain(rifugio.slug);
  });
  it('rispetta i confini di un area senza allargarla arbitrariamente', () => {
    const area = { kind: 'area' as const, bounds: { west: 12.19, east: 12.23, south: 46.50, north: 46.54 } };
    const result = match(needs({ where: area }));
    expect(result.matches.map((x) => x.route.slug)).toEqual([lago.slug]);
    expect(result.matches[0].reasons[0]).toEqual({ kind: 'away', metres: 0 });
  });
  it('segnala le ragioni del punteggio di un itinerario', () => {
    const result = match(needs({
      where: { kind: 'point', lng: 12.20, lat: 46.52 },
      length: { kind: 'distance', metres: 5_000 }, terrain: 'flat',
    }), [lago]).matches[0];
    expect(result.label).toBe('great');
    expect(result.reasons.map((x) => x.kind)).toEqual(['away', 'length', 'terrain']);
    expect(result.misses).toEqual([]);
  });
  it('esclude tutti gli itinerari quando il punto è lontano', () => {
    const empty = match(needs({ where: { kind: 'point', lng: 0, lat: 0 } }));
    expect(empty).toEqual({ matches: [], reachM: null });
  });
});
