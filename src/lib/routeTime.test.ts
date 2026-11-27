import { describe, expect, it } from 'vitest';
import type { Route, RoutePoint } from '../types';
import {
  climbProfile,
  estimateProfile,
  estimateRouteTimeS,
  estimateTrackDuration,
  formatDuration,
  formatEstimate,
  roundDurationMinutes,
  routeEstimateS,
} from './routeTime';

const M_PER_DEG_LNG = 111_194.9; // at the equator, on the 6,371,008.8 m sphere haversineM uses

/**
 * A straight track heading east from the equator, a point every `stepM` (20 m, so no bucket edge falls on exactly 75 m), that
 * climbs evenly: `gainM` over `km` kilometres.
 */
function slope(km: number, gainM: number, stepM = 20): RoutePoint[] {
  const count = Math.round((km * 1000) / stepM);
  return Array.from({ length: count + 1 }, (_, i) => [(i * stepM) / M_PER_DEG_LNG, 0, (gainM * i) / count] as RoutePoint);
}

const minutes = (points: RoutePoint[], activity: Parameters<typeof estimateTrackDuration>[1] = 'hike') =>
  estimateTrackDuration(points, activity).minutes;

describe('climbProfile', () => {
  it('measures a straight track and splits its climb by steepness', () => {
    const gentle = climbProfile(slope(3, 150)); // 5%
    const steep = climbProfile(slope(1, 150)); // 15%
    expect(gentle.distanceKm).toBeCloseTo(3, 2);
    expect(gentle.steepM).toBe(0);
    expect(gentle.gentleM).toBeGreaterThan(130);
    expect(steep.gentleM).toBe(0);
    expect(steep.steepM).toBeGreaterThan(125);
  });

  it('puts the boundary at 10%: up to it is gentle, above it steep', () => {
    expect(climbProfile(slope(2, 190)).steepM).toBe(0); // 9.5%
    expect(climbProfile(slope(2, 230)).gentleM).toBe(0); // 11.5%
  });

  it('ignores GPS jitter between neighbouring points', () => {
    // A flat track whose altimeter flickers by ±1.5 m climbs nothing.
    const flat = slope(5, 0).map((p, i): RoutePoint => [p[0], p[1], i % 2 ? 1.5 : -1.5]);
    const profile = climbProfile(flat);
    expect(profile.gentleM + profile.steepM).toBe(0);
  });

  it('drops points that did not move (a pause at a light) and counts nothing for them', () => {
    const track = slope(2, 40);
    const paused = track.flatMap((p, i) => (i % 5 === 0 ? [p, p, p] : [p]));
    expect(climbProfile(paused)).toEqual(climbProfile(track));
  });

  it('clamps a corrupt spike to a 35% grade', () => {
    const track = slope(2, 0);
    track[40] = [track[40][0], 0, 5_000];
    const profile = climbProfile(track);
    // One 75 m bucket can add at most 35% of its length; the smoothing spreads the rest.
    expect(profile.steepM).toBeLessThan(150);
  });

  it('has no climb for a track with no elevation, however it is written', () => {
    const none = slope(10, 0);
    expect(climbProfile(none).gentleM).toBe(0);
    const missing = slope(10, 300).map((p): RoutePoint => [p[0], p[1], Number.NaN]);
    const profile = climbProfile(missing);
    expect(profile.gentleM + profile.steepM).toBe(0);
    expect(profile.distanceKm).toBeCloseTo(10, 1);
    // Told the elevation is not known, the given values are ignored.
    const ignored = climbProfile(slope(10, 300), false);
    expect(ignored.gentleM + ignored.steepM).toBe(0);
  });

  it('copes with too few points', () => {
    expect(climbProfile([])).toEqual({ distanceKm: 0, gentleM: 0, steepM: 0 });
    expect(climbProfile([[0, 0, 5]])).toEqual({ distanceKm: 0, gentleM: 0, steepM: 0 });
  });
});

describe('roundDurationMinutes', () => {
  it('rounds to 5 minutes under 2 h, 10 up to 6 h, 15 beyond', () => {
    expect(roundDurationMinutes(72)).toBe(70); // 1h 12m
    expect(roundDurationMinutes(334)).toBe(330); // 5h 34m
    expect(roundDurationMinutes(924)).toBe(930); // 15h 24m
  });
});

describe('formatDuration', () => {
  it('reads as hours and minutes', () => {
    expect(formatDuration(45)).toBe('45m');
    expect(formatDuration(120)).toBe('2h');
    expect(formatDuration(930)).toBe('15h 30m');
  });
});

describe('stime dei tempi per percorsi a piedi', () => {
  it('usa 4,5 km/h per una escursione pianeggiante', () => {
    const estimate = estimateTrackDuration(slope(3, 0), 'hike');
    expect(estimate.minutes).toBe(40);
    expect(estimate.effectiveDistanceKm).toBeCloseTo(3, 1);
  });

  it('stima una salita ripida più lenta di una salita lieve a parità di dislivello', () => {
    const gentle = estimateProfile({ distanceKm: 10, gentleM: 500, steepM: 0 }, 'hike');
    const steep = estimateProfile({ distanceKm: 10, gentleM: 0, steepM: 500 }, 'hike');
    expect(gentle.effectiveDistanceKm).toBeCloseTo(15, 5);
    expect(steep.effectiveDistanceKm).toBeCloseTo(17, 5);
    expect(steep.minutes).toBeGreaterThan(gentle.minutes);
  });

  it('distingue escursione, trail running e ferrata senza introdurre il ciclismo', () => {
    const track = slope(12, 400);
    expect(minutes(track, 'trail')).toBeLessThan(minutes(track, 'hike'));
    expect(minutes(track, 'ferrata')).toBeGreaterThan(minutes(track, 'hike'));
    expect(minutes(track, undefined)).toBe(minutes(track, 'hike'));
  });

  it('rallenta il tempo stimato quando aumenta il fattore di passo', () => {
    const track = slope(10, 50);
    expect(estimateTrackDuration(track, 'hike', 1.2).minutes).toBeGreaterThan(minutes(track) * 1.15);
  });

  it('utilizza il dislivello totale quando manca il profilo', () => {
    expect(estimateRouteTimeS(10_000, 100, 'hike')).toBeGreaterThan(estimateRouteTimeS(10_000, 0, 'hike'));
    expect(estimateRouteTimeS(5_000, 0, undefined)).toBe(estimateRouteTimeS(5_000, 0, 'hike'));
    expect(estimateRouteTimeS(10_000, -50, 'trail')).toBe(estimateRouteTimeS(10_000, 0, 'trail'));
  });

  it('dichiara che le stime per le ferrate non sostituiscono quelle ufficiali', () => {
    const estimate = estimateProfile({ distanceKm: 4, gentleM: 500, steepM: 0 }, 'ferrata');
    expect(estimate.caption).toMatch(/ferrate/i);
    expect(estimate.effectiveDistanceKm).toBe(9);
  });
});

describe('routeEstimateS', () => {
  const route = (over: Partial<Route>): Route =>
    ({
      slug: 'r', name: 'R', venueSlugs: [], distanceM: 10_000,
      gainM: 100, lossM: 100, coordinates: slope(10, 100),
      source: 'curated', loop: false, activity: 'hike', ...over,
    });

  it('restituisce secondi arrotondati a cinque minuti', () => {
    const seconds = routeEstimateS(route({}));
    expect(seconds % 300).toBe(0);
    expect(seconds).toBeGreaterThan(2 * 3600);
  });

  it('ignora il dislivello se la quota è ignota', () => {
    expect(routeEstimateS(route({ elevationAvailable: false }))).toBe(estimateRouteTimeS(10_000, 0, 'hike'));
  });

  it('stima il tempo dalla distanza se la traccia manca', () => {
    expect(routeEstimateS(route({ coordinates: [] }))).toBe(estimateRouteTimeS(10_000, 100, 'hike'));
  });

  it('rispetta la regolazione del passo escursionistico', () => {
    expect(routeEstimateS(route({}), 1.25)).toBeGreaterThan(routeEstimateS(route({})));
  });
});

describe('formatEstimate', () => {
  it('arrotonda leggibilmente minuti e ore', () => {
    expect(formatEstimate(2 * 60)).toBe('~5 min');
    expect(formatEstimate(43 * 60)).toBe('~45 min');
    expect(formatEstimate(60 * 60)).toBe('~1 h');
    expect(formatEstimate((3 * 60 + 17) * 60)).toBe('~3 h 15 min');
    expect(formatEstimate((59 * 60) + 40)).toBe('~1 h');
  });
});
