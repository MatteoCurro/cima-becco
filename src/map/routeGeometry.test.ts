import {describe,it,expect} from 'vitest';
import type {RoutePoint} from '../types';
import {routeDisplayGeometry} from './routeGeometry';

describe('geometria mappa ottimizzata',()=>{
  it('preserva estremi e forme significative, senza modificare il GPX originale',()=>{
    const points:RoutePoint[]=Array.from({length:1500},(_,i)=>[12+i*.00001,46.5+Math.sin(i/60)*.002,1000+i]);
    const original=points.map(p=>[...p]);
    const lightweight=routeDisplayGeometry(points);
    expect(lightweight.length).toBeLessThan(600);
    expect(lightweight[0]).toEqual([points[0][0],points[0][1]]);
    expect(lightweight.at(-1)).toEqual([points.at(-1)![0],points.at(-1)![1]]);
    expect(points).toEqual(original);
  });
  it('riutilizza la geometria semplificata per la stessa traccia',()=>{
    const points:RoutePoint[]=[[12,46,0],[12.01,46.001,25]];
    expect(routeDisplayGeometry(points)).toBe(routeDisplayGeometry(points));
  });
});
