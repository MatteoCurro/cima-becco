import {describe,it,expect} from 'vitest';
import type {RoutePoint} from '../types';
import {nearestRoutePointIndex} from './routeHover';
const points:RoutePoint[]=[[11.9,46.1,1600],[12,46.2,1200],[12.1,46.3,2000]];
describe('altimetry hover mapping',()=>{
 it('preserves GPX vertex order',()=>{expect(nearestRoutePointIndex(points,11.9,46.1)).toBe(0);expect(nearestRoutePointIndex(points,12,46.2)).toBe(1);expect(nearestRoutePointIndex(points,12.1,46.3)).toBe(2);});
 it('handles empty route',()=>{expect(nearestRoutePointIndex([],12,46)).toBeNull();});
});
