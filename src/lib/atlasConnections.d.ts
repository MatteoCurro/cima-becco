import type { AlpinePlace } from './alpinePlaces';
export interface AtlasTerritoryMatch {
  key:string;name:string;label:string;matched:boolean;href:string|null;distanceKm:number|null;
}
export function resolveRefugeTerritory(place:Partial<AlpinePlace>,allPlaces:readonly AlpinePlace[]):AtlasTerritoryMatch[];
export function relatedAtlasPlaces(place:AlpinePlace,allPlaces:readonly AlpinePlace[],maxKm?:number,limit?:number):
  Array<{place:AlpinePlace;distanceKm:number}>;
