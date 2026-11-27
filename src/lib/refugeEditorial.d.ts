import type { AlpinePlace } from './alpinePlaces';

export interface RefugeAmenityDefinition {
  readonly key:string;
  readonly label:string;
  readonly schema:string;
}
export const REFUGE_AMENITIES:readonly RefugeAmenityDefinition[];
export function refugeFact(place:Partial<AlpinePlace>, key:string): string|number|boolean|null;
export function refugeOverview(place:Partial<AlpinePlace>):string;
export function refugeSeoDescription(place:Partial<AlpinePlace>):string;
export function refugeServiceFacts(place:Partial<AlpinePlace>): Array<RefugeAmenityDefinition & {value:boolean}>;
