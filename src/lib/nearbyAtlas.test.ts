import { describe, expect, it } from 'vitest';
import { nearbyAtlasPlaces, straightLineKm } from './nearbyAtlas';
import type { AlpinePlace } from './alpinePlaces';

function point(slug:string,lat:number,lng:number,kind:AlpinePlace['kind']='rifugio'):AlpinePlace {
  return {slug,name:slug,kind,lat,lng,osmUrl:'https://www.openstreetmap.org/'};
}
describe('relazioni geografiche locali',()=>{
  const base=point('origine',46.5,12);
  it('calcola distanza in linea d’aria, non indicazioni di accesso',()=>{
    expect(straightLineKm(base,point('nord',46.51,12))).toBeGreaterThan(1);
    expect(straightLineKm(base,base)).toBeCloseTo(0);
    expect(Number.isNaN(straightLineKm(base,point('nan',NaN,12)))).toBe(true);
  });
  it('ordina e limita senza creare link duplicati o punti senza posizione',()=>{
    const items=[
      base,point('far',46.6,12),point('near',46.502,12,'borgo'),
      point('near2',46.506,12,'bivacco'),point('bad',NaN,12),
      point('duplicate',46.5,12),
    ];
    expect(nearbyAtlasPlaces(base,items,{maxKm:2,limit:2}).map(x=>x.place.slug)).toEqual(['near','near2']);
  });
  it('non trasforma distanze negative o invalide in un elenco',()=>{
    expect(nearbyAtlasPlaces(base,[point('other',46.501,12)],{maxKm:-1})).toEqual([]);
  });
});
