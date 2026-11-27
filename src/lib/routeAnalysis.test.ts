import { describe, expect, it } from 'vitest';
import type { Route, RoutePoint } from '../types';
import { computeGain } from './elevation';
import { classifyActivity, findOverlaps, isSameRoute, routeFingerprint } from './routeAnalysis';
import { routeFromPoints } from './routes';

// Test indipendenti da vecchi GPX asiatici non più presenti nella repository.
const sentieroDolomiti: RoutePoint[] = Array.from({ length: 100 }, (_, i) =>
  [12.20 + i * 0.00012, 46.51 + i * 0.000025, 1100 + i * 2]);
const sentieroAlpi: RoutePoint[] = Array.from({ length: 100 }, (_, i) =>
  [10.20 + i * 0.00012, 46.20 + i * 0.000025, 1500 + i * 2]);

const toRoute = (name: string, coords: RoutePoint[]): Route => routeFromPoints(name, coords, []);

describe('classificazione attività a piedi', () => {
  it('una camminata resta escursione, non bici o ferrata', () => {
    const timestamps = sentieroDolomiti.map((_, i) => i * 40_000);
    expect(classifyActivity(sentieroDolomiti, computeGain(sentieroDolomiti).gainM, timestamps)).toBe('hike');
  });
  it('riconosce la corsa su sentiero da velocità umana compatibile', () => {
    const points: RoutePoint[] = Array.from({ length: 50 }, (_, i) => [12.20 + i * 0.0001, 46.51, 1000]);
    const timestamps = points.map((_, i) => i * 3_500);
    expect(classifyActivity(points, 0, timestamps)).toBe('trail');
  });
  it('non inventa ferrate dalla sola traccia GPS', () => {
    expect(classifyActivity(sentieroDolomiti, 900)).not.toBe('ferrata');
  });
});

describe('impronte e sovrapposizioni dei percorsi', () => {
  it('genera la stessa impronta per la stessa geometria', () => {
    expect(routeFingerprint(sentieroDolomiti)).toBe(routeFingerprint([...sentieroDolomiti]));
    expect(routeFingerprint(sentieroDolomiti)).not.toBe(routeFingerprint(sentieroAlpi));
  });
  it('riconosce un file ripubblicato con campionamento ridotto', () => {
    const thinned = sentieroDolomiti.filter((_, i) => i % 2 === 0);
    expect(isSameRoute(thinned, toRoute('Sentiero campione', sentieroDolomiti))).toBe(true);
    expect(isSameRoute(sentieroAlpi, toRoute('Sentiero campione', sentieroDolomiti))).toBe(false);
  });
  it('identifica un tratto realmente condiviso senza confondere zone distanti', () => {
    const partial = sentieroDolomiti.slice(0, 60);
    const hits = findOverlaps(partial, [
      toRoute('Sentiero Dolomiti', sentieroDolomiti),
      toRoute('Sentiero Alpi', sentieroAlpi),
    ]);
    expect(hits[0]?.route.name).toBe('Sentiero Dolomiti');
    expect(hits[0]?.share).toBeGreaterThan(0.75);
    expect(hits.some((hit) => hit.route.name === 'Sentiero Alpi')).toBe(false);
  });
  it('non cade su route danneggiate', () => {
    const broken = { ...toRoute('Danneggiato', []), coordinates: undefined as unknown as RoutePoint[] };
    expect(() => isSameRoute(sentieroDolomiti, broken)).not.toThrow();
    expect(isSameRoute(sentieroDolomiti, broken)).toBe(false);
  });
});
