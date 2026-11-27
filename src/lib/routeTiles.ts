import type { Route } from '../types';
import { DATA_BASE, type Bounds } from './venues';

/** Catalogo geometrico a celle: una visita non scarica tutti i sentieri d'Italia. */
interface RouteTile {
  id: string;
  bbox: [number, number, number, number]; // south, west, north, east
  files: string[];
  count: number;
  updatedAt: string;
}
interface RouteManifest {
  version: number;
  generatedAt: string;
  routeCount: number;
  completedTiles: number;
  plannedTiles: number;
  lookup: Record<string, string>;
  tiles: RouteTile[];
}

let manifestPromise: Promise<RouteManifest | null> | null = null;
const fileCache = new Map<string, Promise<Route[]>>();
const MAX_FILE_CACHE = 30;

export function loadRouteManifest(): Promise<RouteManifest | null> {
  manifestPromise ??= fetch(DATA_BASE + '/routes-manifest.json')
    .then(async (response) => {
      if (response.status === 404) return null;
      if (!response.ok) throw new Error('Catalogo itinerari: HTTP ' + response.status);
      return response.json() as Promise<RouteManifest>;
    })
    .catch(() => {
      manifestPromise = null;
      return null;
    });
  return manifestPromise;
}

function tileRoutes(file: string): Promise<Route[]> {
  const cached = fileCache.get(file);
  if (cached) return cached;
  const promise = fetch(DATA_BASE + '/' + file)
    .then(async (response) => {
      if (!response.ok) throw new Error('Impossibile caricare ' + file);
      const data = (await response.json()) as { routes?: Route[] };
      return Array.isArray(data.routes) ? data.routes.filter((route) =>
        route.activity !== ('cycle' as string) && route.activity !== ('run' as string)) : [];
    })
    .catch((error: unknown) => {
      fileCache.delete(file);
      throw error;
    });
  fileCache.set(file, promise);
  if (fileCache.size > MAX_FILE_CACHE) {
    const oldest = fileCache.keys().next().value;
    if (oldest && oldest !== file) fileCache.delete(oldest);
  }
  return promise;
}

function intersects(tile: RouteTile, view: Bounds): boolean {
  const [s, w, n, e] = tile.bbox;
  return e >= view.west && w <= view.east && n >= view.south && s <= view.north;
}

async function loadTile(tile: RouteTile): Promise<Route[]> {
  const chunks: Route[][] = [];
  for (const file of tile.files) chunks.push(await tileRoutes(file));
  return chunks.flat();
}

/** Scarica soltanto le celle attorno alla zona effettivamente esplorata. */
export async function loadRoutesInBounds(view: Bounds): Promise<Route[]> {
  if (view.east - view.west > 5 || view.north - view.south > 4) return [];
  const manifest = await loadRouteManifest();
  if (!manifest) return [];
  const center = { lat: (view.north + view.south) / 2, lng: (view.west + view.east) / 2 };
  const near = manifest.tiles.filter((tile) => intersects(tile, view))
    .sort((a, b) => {
      const am = Math.abs((a.bbox[0] + a.bbox[2]) / 2 - center.lat) + Math.abs((a.bbox[1] + a.bbox[3]) / 2 - center.lng);
      const bm = Math.abs((b.bbox[0] + b.bbox[2]) / 2 - center.lat) + Math.abs((b.bbox[1] + b.bbox[3]) / 2 - center.lng);
      return am - bm;
    }).slice(0, 9);
  const loaded = await Promise.allSettled(near.map(loadTile));
  const unique = new Map<string, Route>();
  for (const result of loaded) {
    if (result.status === 'fulfilled') for (const route of result.value) unique.set(route.slug, route);
  }
  return [...unique.values()];
}

/** Apre un percorso condiviso senza conoscere in anticipo la sua cella. */
export async function loadRouteBySlug(slug: string): Promise<Route | null> {
  const manifest = await loadRouteManifest();
  const tileId = manifest?.lookup?.[slug];
  if (!tileId) return null;
  const tile = manifest!.tiles.find((item) => item.id === tileId);
  if (!tile) return null;
  const routes = await loadTile(tile);
  return routes.find((route) => route.slug === slug) ?? null;
}
