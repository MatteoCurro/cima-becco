import type { AlpinePlace } from './alpinePlaces';
export function atlasSlugPart(value:string):string;
export function canonicalAtlasSlug(place:Pick<AlpinePlace,'name'|'slug'|'kind'|'sourceIds'>):string;
export function atlasCanonicalPath(place:Pick<AlpinePlace,'name'|'slug'|'kind'|'sourceIds'>):string;
export function atlasLegacyPath(place:Pick<AlpinePlace,'slug'|'kind'>):string;
