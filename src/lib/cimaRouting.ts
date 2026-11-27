import type { RoutePoint } from '../types';
import { computeGain, totalDistanceM } from './elevation';

export interface PlanWaypoint { lng: number; lat: number; name?: string }
export interface PlannedTrack {
  points: RoutePoint[];
  distanceM: number;
  gainM: number | null;
  lossM: number | null;
  elevationAvailable: boolean;
}

/** Routing occurs on a separate, authorised BRouter endpoint; never draw a straight line as a valid trail. */
export async function calculateTrailRoute(waypoints: PlanWaypoint[], signal?: AbortSignal): Promise<PlannedTrack> {
  if (waypoints.length < 2) throw new Error('Seleziona almeno due punti.');
  if (waypoints.length > 12) throw new Error('Il planner permette al massimo 12 punti.');
  const endpoint = (import.meta.env.VITE_BROUTER_ENDPOINT as string | undefined) || 'https://brouter.de/brouter';
  const profile = (import.meta.env.VITE_BROUTER_PROFILE as string | undefined) || 'trekking';
  const url = new URL(endpoint);
  if (url.protocol !== 'https:' && url.hostname !== 'localhost' && url.hostname !== '127.0.0.1') {
    throw new Error('Configura un endpoint di routing HTTPS.');
  }
  url.searchParams.set('lonlats', waypoints.map((p) => p.lng.toFixed(6) + ',' + p.lat.toFixed(6)).join('|'));
  url.searchParams.set('profile', profile);
  url.searchParams.set('alternativeidx', '0');
  url.searchParams.set('format', 'geojson');
  let response: Response;
  try { response = await fetch(url.toString(), { signal }); }
  catch { throw new Error('Il motore BRouter non è raggiungibile oppure non consente l’accesso dal browser.'); }
  if (!response.ok) throw new Error('Il servizio di routing ha risposto con HTTP ' + response.status + '.');
  const body = await response.json() as { features?: { geometry?: { type?: string; coordinates?: number[][] } }[]; geometry?: { type?: string; coordinates?: number[][] } };
  const geometry = body.features?.find((f) => f.geometry?.type === 'LineString')?.geometry ?? body.geometry;
  const raw = geometry?.coordinates;
  if (!Array.isArray(raw) || raw.length < 2 || raw.length > 200_000) throw new Error('La risposta del routing non contiene una traccia valida.');
  const elevationAvailable = raw.every((p) => p.length >= 3 && Number.isFinite(p[2]));
  const points: RoutePoint[] = raw.map((p) => {
    const lng = p[0], lat = p[1];
    if (!Number.isFinite(lng) || !Number.isFinite(lat) || Math.abs(lng) > 180 || Math.abs(lat) > 90) {
      throw new Error('BRouter ha restituito coordinate non valide.');
    }
    return [lng, lat, elevationAvailable ? p[2] : 0];
  });
  const alt = elevationAvailable ? computeGain(points) : null;
  return { points, distanceM: Math.round(totalDistanceM(points)), gainM: alt?.gainM ?? null, lossM: alt?.lossM ?? null, elevationAvailable };
}

export function directionsToStart(point: PlanWaypoint): string {
  return 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(point.lat.toFixed(6) + ',' + point.lng.toFixed(6)) + '&travelmode=driving';
}
