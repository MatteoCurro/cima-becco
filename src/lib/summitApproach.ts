import type { Route, Venue } from '../types';
import type { AlpinePlace } from './alpinePlaces';
import { haversineM } from './elevation';
import { nearestPointOnRoute } from './routes';
import { routePresentationCategory } from './routeClassification';

/**
 * Presentation-only topographic relations. A GPS proximity never becomes a
 * verified ascent, passability assertion or official access.
 */
export type SummitRouteRelation = 'documented' | 'endpoint_near' | 'passes_near' | 'ferrata_area';
export interface SummitRouteConnection {
  route: Route;
  relation: SummitRouteRelation;
  distanceM: number;
  ferrata: boolean;
  categoryEvidence: 'catalogued' | 'inferred' | 'unverified';
}

function targetMatches(peak: Venue, target: { id?: string;slug?: string }): boolean {
  return Boolean((peak.id && target.id === peak.id) || (target.slug && target.slug === peak.slug));
}

export function summitRoutes(peak: Venue, routes: Route[], limit = 22): SummitRouteConnection[] {
  if (peak.type !== 'hill') return [];
  const seen=new Set<string>();
  const found:SummitRouteConnection[]=[];
  for(const route of routes){
    if(seen.has(route.slug)||route.held||route.rejected||route.coordinates.length===0)continue;
    seen.add(route.slug);
    const category=routePresentationCategory(route);
    const ferrata=category.kind==='ferrata'||category.kind==='attrezzato';
    const nearest=nearestPointOnRoute(route,peak.lng,peak.lat).distanceM;
    const first=route.coordinates[0],last=route.coordinates[route.coordinates.length-1];
    const atEnd=Math.min(
      haversineM(peak.lng,peak.lat,first[0],first[1]),
      haversineM(peak.lng,peak.lat,last[0],last[1]),
    );
    const documented=(route.relations??[]).some(rel=>
      rel.verified===true && rel.type==='ascends_to' && targetMatches(peak,rel.target));
    const relation:SummitRouteRelation|null=documented?'documented':
      atEnd<=100?'endpoint_near':
      nearest<=160?'passes_near':
      ferrata && nearest<=2500?'ferrata_area':null;
    if(!relation)continue;
    found.push({route,relation,distanceM:Math.round(nearest),
      ferrata,categoryEvidence:category.evidence});
  }
  const priority:Record<SummitRouteRelation,number>={
    documented:0,endpoint_near:1,passes_near:2,ferrata_area:3,
  };
  found.sort((a,b)=>priority[a.relation]-priority[b.relation]||a.distanceM-b.distanceM||
    a.route.slug.localeCompare(b.route.slug));
  // Do not allow a large set of low-confidence nearby tracks to hide ferratas.
  const core=found.filter(item=>item.relation!=='ferrata_area');
  const area=found.filter(item=>item.relation==='ferrata_area');
  return [...core.slice(0,limit),...area.slice(0,Math.min(6,Math.max(0,limit-core.length)))];
}

export type SummitSupportRelation = 'documented' | 'mapped_route' | 'nearby';
export interface SummitSupportPlace {
  place: AlpinePlace;
  relation: SummitSupportRelation;
  straightLineKm: number;
  viaRoute?: string;
}

export function summitSupportPlaces(peak:Venue,places:AlpinePlace[],routes:SummitRouteConnection[],limit=9):SummitSupportPlace[] {
  if(peak.type!=='hill')return[];
  const near=places.filter(place=>place.kind==='rifugio'||place.kind==='bivacco')
    .map(place=>({place,km:haversineM(peak.lng,peak.lat,place.lng,place.lat)/1000}))
    .filter(x=>x.km<=9);
  const inRoutes=new Map<string,string>();
  for(const match of routes.filter(x=>x.relation!=='ferrata_area')){
    for(const stop of match.route.stops??[]){
      if((stop.kind==='rifugio'||stop.kind==='bivacco')&&stop.distanceM<=180&&!inRoutes.has(stop.slug))
        inRoutes.set(stop.slug,match.route.name);
    }
  }
  const out:SummitSupportPlace[]=near.map(({place,km})=>{
    const documented=(peak.relations??[]).some(rel=>rel.verified===true &&
      rel.type==='accessible_from' &&
      ((place.id&&rel.target.id===place.id)||rel.target.slug===place.slug));
    const viaRoute=inRoutes.get(place.slug);
    return {place,straightLineKm:Math.round(km*10)/10,
      relation:documented?'documented':viaRoute?'mapped_route':'nearby',
      ...(viaRoute?{viaRoute}:{}),
    };
  });
  const priority:Record<SummitSupportRelation,number>={documented:0,mapped_route:1,nearby:2};
  out.sort((a,b)=>priority[a.relation]-priority[b.relation] ||
    a.straightLineKm-b.straightLineKm || a.place.slug.localeCompare(b.place.slug));
  return out.slice(0,limit);
}
