import type { AlpinePlace } from './alpinePlaces';

export type AtlasLocation = { lat: number; lng: number };
export interface NearbyAtlasPlace { place: AlpinePlace; distanceKm: number; }

/** Distanza ortodromica in linea d'aria, non accesso e non tempo di cammino. */
export function straightLineKm(a: AtlasLocation, b: AtlasLocation): number {
  if (![a.lat,a.lng,b.lat,b.lng].every(Number.isFinite)) return Number.NaN;
  const r = 6371.0088; // raggio medio terrestre (km)
  const rad = Math.PI / 180;
  const dLat = (b.lat-a.lat)*rad;
  const dLng = (b.lng-a.lng)*rad;
  const h=Math.sin(dLat/2)**2+
    Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dLng/2)**2;
  return 2*r*Math.asin(Math.min(1,Math.sqrt(h)));
}

/** Adapter spaziale SOLO dei POI realmente presenti nel catalogo, senza inferire relazioni di accesso. */
export function nearbyAtlasPlaces(
  origin: AlpinePlace,
  allPlaces: readonly AlpinePlace[],
  options: {maxKm?:number;limit?:number}={},
): NearbyAtlasPlace[] {
  const maxKm=options.maxKm ?? 8;
  const limit=options.limit ?? 8;
  if (!Number.isFinite(maxKm)||maxKm<=0||!Number.isInteger(limit)||limit<=0) return [];
  return allPlaces
    .filter(p=>p.slug!==origin.slug && Number.isFinite(p.lat)&&Number.isFinite(p.lng))
    .map(p=>({place:p,distanceKm:straightLineKm(origin,p)}))
    .filter(item=>Number.isFinite(item.distanceKm) && item.distanceKm>0.02 && item.distanceKm<=maxKm)
    .sort((a,b)=>a.distanceKm-b.distanceKm||a.place.name.localeCompare(b.place.name,'it'))
    .slice(0,limit);
}
