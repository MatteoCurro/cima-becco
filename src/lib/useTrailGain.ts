import { useEffect, useState } from 'react';
import type { Route, RoutePoint } from '../types';
import { haversineM, computeGain } from './elevation';
import { terrainElevations } from './terrain';

/** Solo i percorsi visibili richiedono la stima, una volta per sessione. */
const cache = new Map<string, Promise<number | null>>();
function sampleRoute(points: RoutePoint[]): RoutePoint[] {
  if (points.length < 3) return points;
  const output = [points[0]];
  let since = 0;
  for (let i = 1; i < points.length - 1; i++) {
    since += haversineM(points[i - 1][0], points[i - 1][1], points[i][0], points[i][1]);
    if (since >= 70) {
      output.push(points[i]);
      since = 0;
    }
  }
  output.push(points[points.length - 1]);
  if (output.length <= 180) return output;
  const step = Math.ceil(output.length / 180);
  return output.filter((_, i) => i % step === 0 || i === output.length - 1);
}

function routeGain(route: Route): Promise<number | null> {
  let pending = cache.get(route.slug);
  if (!pending) {
    pending = terrainElevations(sampleRoute(route.coordinates))
      .then((points) => points ? computeGain(points).gainM : null)
      .catch(() => null);
    cache.set(route.slug, pending);
  }
  return pending;
}

/** Dislivello in lista: dato importato se disponibile, altrimenti stima terreno progressiva. */
export function useTrailGain(route: Route): { gain: number | null; pending: boolean } {
  const supplied = route.elevationAvailable !== false ? route.gainM : null;
  const [state, setState] = useState<{ slug: string; gain: number | null } | null>(null);
  useEffect(() => {
    if (supplied != null) return;
    let active = true;
    void routeGain(route).then((gain) => { if (active) setState({ slug: route.slug, gain }); });
    return () => { active = false; };
  }, [route, supplied]);
  return supplied != null ? { gain: supplied, pending: false }
    : state?.slug === route.slug ? { gain: state.gain, pending: false }
      : { gain: null, pending: true };
}
