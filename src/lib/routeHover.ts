import { haversineM } from './elevation';
import type { RoutePoint } from '../types';

/** Shared vertex indexing for elevation profiles and all maps. */
export function nearestRoutePointIndex(points: readonly RoutePoint[], lng:number, lat:number):number|null {
  if(!points.length)return null;
  let nearest=0;
  let distance=Infinity;
  for(let i=0;i<points.length;i++){
    const next=haversineM(lng,lat,points[i][0],points[i][1]);
    if(next<distance){distance=next;nearest=i;}
  }
  return nearest;
}
