import { DATA_BASE, type Bounds } from './venues';

export interface AlpinePlace {
  slug: string;
  name: string;
  kind: 'rifugio' | 'bivacco' | 'borgo';
  access?: string;
  fee?: string;
  /** Logo ufficiale verificato/licenziato, mai generato automaticamente. */
  logo?: {url:string;sourceUrl:string;author:string;license:string};
  winterRoom?: string;
  seasonal?: string;
  lat: number;
  lng: number;
  osmUrl: string;
  elevationM?: number;
  /** OSM = quota indicata dal mappatore; DEM = terreno stimato. */
  elevationSource?: 'osm' | 'dem';
  wikidata?: string;
  website?: string;
  operator?: string;
  /** OSM, Wikidata e Commons: mai foto associate dal solo nome. */
  photo?: {url:string;sourceUrl:string;author:string;license:string;licenseUrl?:string};
  photoCheckedAt?: string;
  description?:string;
  address?:string;
  openingHours?:string;
  phone?:string;
  email?:string;
  capacity?:number;
  wikipedia?:string;
  commonsFile?:string;
}
export interface AlpinePlacesDataset {
  generatedAt: string | null;
  source: string;
  coverage: string;
  places: AlpinePlace[];
}
const empty: AlpinePlacesDataset = { generatedAt: null, source: 'OpenStreetMap · ODbL 1.0', coverage: 'Dolomiti', places: [] };
let pending: Promise<AlpinePlacesDataset> | null = null;

/** Un solo JSON per il pilota, con cache di sessione e nessun dato fittizio. */
export function loadAlpinePlaces(): Promise<AlpinePlacesDataset> {
  pending ??= fetch(`${DATA_BASE}/alpine-places.json`)
    .then(async (response) => {
      if (!response.ok) throw new Error('Catalogo rifugi non disponibile');
      const doc = await response.json() as AlpinePlacesDataset;
      return doc && Array.isArray(doc.places) ? doc : empty;
    })
    .catch(() => { pending = null; return empty; });
  return pending;
}

export function atlasCategory(kind: AlpinePlace['kind']): 'rifugi' | 'bivacchi' | 'borghi' {
  return kind === 'rifugio' ? 'rifugi' : kind === 'bivacco' ? 'bivacchi' : 'borghi';
}

export function alpinePlaceLink(place: Pick<AlpinePlace, 'slug' | 'kind'>): string {
  return `#${place.kind==='borgo'?'paesi':atlasCategory(place.kind)}/${place.slug}`;
}

/** Box comodo per aprire la mappa sul POI, non finge un accesso stradale. */
export function placeBounds(place: Pick<AlpinePlace,'lng'|'lat'>, radiusKm=3): Bounds {
  const latDelta = radiusKm / 111.2;
  const lngDelta = radiusKm / (111.2 * Math.max(0.1, Math.cos(place.lat * Math.PI / 180)));
  return {
    west: place.lng - lngDelta, east: place.lng + lngDelta,
    south: place.lat - latDelta, north: place.lat + latDelta,
  };
}
