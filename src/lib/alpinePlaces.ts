import { DATA_BASE, type Bounds } from './venues';
import type { AtlasEntityMetadata } from './atlasDossier';
import { canonicalAtlasSlug } from './placePermalinks';
import { mergeRefugeRelease } from './refugeRelease';
import { mergeShelterRelease } from './shelterRelease';
import { mergeMunicipalityRelease } from './municipalityRelease';

export interface AlpinePlace extends AtlasEntityMetadata {
  slug: string;
  name: string;
  kind: 'rifugio' | 'bivacco' | 'borgo';
  access?: string;
  fee?: string;
  /** Logo ufficiale verificato/licenziato, mai generato automaticamente. */
  logo?: {url:string;sourceUrl:string;author:string;license:string;symbolType?:'coat_of_arms'|'institutional_logo'};
  winterRoom?: string;
  seasonal?: string;
  lat: number;
  lng: number;
  osmUrl: string;
  /** Scheda della fonte CAI, dove presente. */
  officialUrl?: string;
  /** Sottotipo dichiarato (Bivacco, Capanna sociale, Punto d'appoggio). */
  shelterTypeLabel?: string;
  elevationM?: number;
  /** OSM = quota indicata dal mappatore; DEM = terreno stimato. */
  elevationSource?: 'osm' | 'dem' | 'cai';
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
  pending ??= Promise.all([
    fetch(`${DATA_BASE}/alpine-places.json`).then(async response => {
      if (!response.ok) throw new Error('Catalogo OSM non disponibile');
      const doc = await response.json() as AlpinePlacesDataset;
      return doc && Array.isArray(doc.places) ? doc : empty;
    }),
    // Non sostituisce l'importatore OSM esistente: è un secondo dataset
    // normalizzato con fonte CAI e identità riconciliate. Fallback compatibile.
    fetch(`${DATA_BASE}/atlas/refuges-v1.json`)
      .then(response => response.ok ? response.json() as Promise<unknown> : null)
      .catch(() => null),
    fetch(`${DATA_BASE}/atlas/shelters-v1.json`)
      .then(response => response.ok ? response.json() as Promise<unknown> : null)
      .catch(() => null),
    fetch(`${DATA_BASE}/atlas/municipalities-v1.json`)
      .then(response => response.ok ? response.json() as Promise<unknown> : null)
      .catch(() => null),
  ])
    .then(([legacy, refuges, shelters, municipalities]) => mergeMunicipalityRelease(
      mergeShelterRelease(mergeRefugeRelease(legacy, refuges), shelters), municipalities))
    .catch(() => { pending = null; return empty; });
  return pending;
}

export function atlasCategory(kind: AlpinePlace['kind']): 'rifugi' | 'bivacchi' | 'borghi' {
  return kind === 'rifugio' ? 'rifugi' : kind === 'bivacco' ? 'bivacchi' : 'borghi';
}

export function alpinePlaceLink(place: Pick<AlpinePlace, 'slug' | 'kind'> & Partial<Pick<AlpinePlace, 'name' | 'sourceIds' | 'subtype'>>): string {
  // Le tappe GPX legacy conoscono solo lo slug OSM: l'alias pubblico le
  // indirizza alla scheda canonica, senza inventare nome o identità CAI.
  if(place.subtype==='italian_municipality') return `${import.meta.env.BASE_URL}comuni/${encodeURIComponent(place.slug)}/`;
  const slug=(place.kind==='rifugio'||place.kind==='bivacco')&&place.name ? canonicalAtlasSlug({
    kind:place.kind,name:place.name,slug:place.slug,sourceIds:place.sourceIds,
  }) : place.slug;
  return `${import.meta.env.BASE_URL}${atlasCategory(place.kind)}/${encodeURIComponent(slug)}/`;
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
