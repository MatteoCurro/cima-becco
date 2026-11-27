import { describe, expect, it } from 'vitest';
import type { Route, RouteActivity, RoutePoint } from '../types';
import {
  NO_ROUTE_FILTERS, filterRoutes, mixByDifficulty, nearestPointOnRoute,
  radiusBounds, routeEndpoints, routeFromPoints, routeLink,
  routeSlugFromHash, routesBounds, routesNear, routesWithin,
} from './routes';
import { routeEstimateS } from './routeTime';

// Test indipendenti dal vecchio catalogo Singapore/Malaysia.
const route = (name: string, slug: string, lng: number, lat: number, distanceM: number, gainM: number): Route => {
  // Distanza della geometria coerente con quella dichiarata nei metadati:
  // il modello temporale usa il profilo GPX, non il numero distanceM.
  const degrees = distanceM / (111_320 * Math.cos((lat * Math.PI) / 180));
  return {
    slug, name, venueSlugs: [], distanceM, gainM, lossM: Math.floor(gainM / 2),
    elevationAvailable: true, loop: false, activity: 'hike', source: 'curated',
    coordinates: [
      [lng, lat, 1000],
      [lng + degrees / 2, lat + 0.0005, 1000 + gainM / 2],
      [lng + degrees, lat + 0.001, 1000 + gainM],
    ],
  };
};
const cadore = route('Sentiero Cadore', 'sentiero-cadore', 12.28, 46.52, 5_000, 400);
const fassa = route('Sentiero Fassa', 'sentiero-fassa', 11.65, 46.45, 10_000, 800);
const routes = [cadore, fassa];

describe('ricerca geografica percorsi a piedi', () => {
  it('ritrova solo il sentiero vicino', () => {
    expect(routesNear(routes, 12.28, 46.52, 5_000, 8)).toEqual([cadore]);
    expect(routesNear(routes, 12.28, 46.52, 200_000, 1)).toEqual([cadore]);
  });
  it('rileva le coordinate estreme e gestisce lista vuota', () => {
    const box = routesBounds(routes)!;
    expect(box.west).toBeLessThanOrEqual(11.65);
    expect(box.east).toBeGreaterThanOrEqual(12.284);
    expect(box.north).toBeGreaterThanOrEqual(46.521);
    expect(routesBounds([])).toBeNull();
  });
  it('estende il raggio solo quando necessario', () => {
    expect(routesWithin(routes, 12.28, 46.52, [1_000, 30_000], 8)?.radiusM).toBe(1_000);
    expect(routesWithin(routes, 11.65, 46.45, [1_000, 30_000], 8)?.routes).toContain(fassa);
    expect(routesWithin(routes, 0, 0, [10_000, 50_000], 8)).toBeNull();
  });
  it('genera correttamente il bounding box alla latitudine alpina', () => {
    const box = radiusBounds(12.28, 46.52, 5_000);
    expect(box.south).toBeLessThan(46.52);
    expect(box.north).toBeGreaterThan(46.52);
    expect(box.east - 12.28).toBeGreaterThan(0.04);
  });
});

describe('filtri escursionistici', () => {
  it('filtra la distanza', () => {
    expect(filterRoutes(routes, { ...NO_ROUTE_FILTERS, maxDistanceM: 6_000 })).toEqual([cadore]);
    expect(filterRoutes(routes, { ...NO_ROUTE_FILTERS, minDistanceM: 7_000 })).toEqual([fassa]);
  });
  it('filtra dislivello solo se le quote sono note', () => {
    const unknown = { ...cadore, slug: 'senza-quote', elevationAvailable: false };
    expect(filterRoutes([cadore, fassa, unknown], { ...NO_ROUTE_FILTERS, maxGainM: 500 })).toEqual([cadore]);
    expect(filterRoutes([unknown], NO_ROUTE_FILTERS)).toHaveLength(1);
  });
  it('applica il limite sul tempo stimato dal modello escursionistico', () => {
    const threshold = Math.round((routeEstimateS(cadore) + routeEstimateS(fassa)) / 2);
    expect(routeEstimateS(fassa)).toBeGreaterThan(routeEstimateS(cadore));
    expect(filterRoutes(routes, { ...NO_ROUTE_FILTERS, maxDurationS: threshold })).toEqual([cadore]);
    expect(filterRoutes(routes, { ...NO_ROUTE_FILTERS, minDurationS: threshold })).toEqual([fassa]);
  });
  it('separa escursione, trail e ferrata', () => {
    const trail = { ...cadore, slug: 'trail', activity: 'trail' as const };
    const ferrata = { ...cadore, slug: 'ferrata', activity: 'ferrata' as const };
    expect(filterRoutes([cadore, trail, ferrata], { ...NO_ROUTE_FILTERS, category: 'hike' })).toEqual([cadore]);
    expect(filterRoutes([cadore, trail, ferrata], { ...NO_ROUTE_FILTERS, category: 'trail' })).toEqual([trail]);
    expect(filterRoutes([cadore, trail, ferrata], { ...NO_ROUTE_FILTERS, category: 'ferrata' })).toEqual([ferrata]);
  });
  it('rifiuta dati ciclistici ereditati anche con filtro tutti', () => {
    const bike = { ...cadore, slug: 'legacy-bike', activity: 'cycle' as RouteActivity };
    const roadRun = { ...cadore, slug: 'legacy-road-run', activity: 'run' as RouteActivity };
    expect(filterRoutes([cadore, bike, roadRun], NO_ROUTE_FILTERS)).toEqual([cadore]);
  });
  it('separa preferiti e percorsi salvati solo nel browser', () => {
    const local = { ...cadore, slug: 'solo-local', source: 'local' as const };
    expect(filterRoutes([cadore, local], { ...NO_ROUTE_FILTERS, category: 'saved' }, new Set(['sentiero-cadore']))).toEqual([cadore]);
    expect(filterRoutes([cadore, local], { ...NO_ROUTE_FILTERS, category: 'device' })).toEqual([local]);
  });
});

describe('struttura, geometria e link', () => {
  it('trova l indice della posizione più vicina lungo il percorso', () => {
    expect(nearestPointOnRoute(cadore, 12.28, 46.52)).toEqual({ index: 0, distanceM: 0, onRoute: true });
    expect(nearestPointOnRoute(cadore, 12.28, 46.55).onRoute).toBe(false);
  });
  it('riconosce gli estremi e un vero anello', () => {
    expect(routeEndpoints(cadore.coordinates)?.isLoop).toBe(false);
    const ring: RoutePoint[] = [[12.28, 46.52, 1000], [12.29, 46.53, 1300], [12.2802, 46.5201, 1002]];
    expect(routeEndpoints(ring)?.isLoop).toBe(true);
    expect(routeFromPoints('Anello', ring, []).loop).toBe(true);
  });
  it('non crea endpoint per tracce senza geometria valida', () => {
    expect(routeEndpoints([])).toBeNull();
    expect(routeEndpoints(undefined)).toBeNull();
    expect(routeEndpoints([[NaN, 46.52, 1000], [12.2, 46.5, 1100]])).toBeNull();
  });
  it('costruisce permalink sicuri dei sentieri', () => {
    const href = routeLink('osm-hiking-1067616');
    expect(new URL(href).pathname).toBe('/cima-becco/route/osm-hiking-1067616/');
    expect(new URL(href).hash).toBe('');
    expect(routeSlugFromHash('#route/osm-hiking-1067616')).toBe('osm-hiking-1067616');
    expect(routeSlugFromHash('#route/Has Spaces')).toBeNull();
    expect(routeSlugFromHash('#route/<script>')).toBeNull();
  });
  it('mescola i livelli di difficoltà senza scartare nessun elemento', () => {
    const examples = [
      { ...cadore, slug: 't1', difficulty: 'easy' as const, gainM: 120 },
      { ...cadore, slug: 't2', difficulty: 'moderate' as const, gainM: 400 },
      { ...cadore, slug: 't3', difficulty: 'hard' as const, gainM: 950 },
    ];
    const mixed = mixByDifficulty(examples);
    expect(mixed).toHaveLength(3);
    expect(new Set(mixed.map(x => x.slug))).toEqual(new Set(['t1', 't2', 't3']));
  });
});
