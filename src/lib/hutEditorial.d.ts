import type { AlpinePlace } from './alpinePlaces';
export const BIVOUAC_AMENITIES:ReadonlyArray<{key:string;label:string}>;
export const HUT_SERVICE_CHAPTERS:Record<string,ReadonlyArray<{id:string;title:string;keys:readonly string[]}>>;
export function hutServiceFacts(place:Partial<AlpinePlace>):Array<{key:string;label:string;value:boolean}>;
export function hutServiceChapters(place:Partial<AlpinePlace>):Array<{id:string;title:string;keys:readonly string[];items:Array<{key:string;label:string;value:boolean}>}>;
export function hutAliases(place:Partial<AlpinePlace>):Array<{value:string;language?:string;historical?:boolean;sourceUrl?:string}>;
export function shelterOverview(place:Partial<AlpinePlace>):string;
export function shelterSeoDescription(place:Partial<AlpinePlace>):string;
export const HUT_FACT_GROUP_LABELS:Readonly<Record<string,string>>;
