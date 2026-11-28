import { describe, expect, it } from 'vitest';
import raw from '../public/data/peaks/index.json';

type Row = [number,string,number,number,number,string,string,string];
const index = raw as unknown as {
  total:number;countries:number;cells:Record<string,number>;
  byCountry:Record<string,[number,number,number,number,number]>;
  rows:Record<string,number[]>;top:Row[];overview:Row[];
};

describe('GeoNames raw census and low-zoom map',()=>{
  it('counts exactly the stored tiles, including neighboring alpine countries',()=>{
    expect(index.total).toBe(Object.values(index.cells).reduce((a,b)=>a+b,0));
    expect(index.total).toBeGreaterThan(20_000);
    expect(index.countries).toBe(Object.keys(index.byCountry).length);
    expect(Object.values(index.byCountry).reduce((sum,stats)=>sum+stats[0],0)).toBe(index.total);
    for(const country of ['IT','CH','AT','FR','SI'])expect(index.byCountry).toHaveProperty(country);
  });
  it('distributes low-zoom markers geographically without duplicating GeoNames IDs',()=>{
    expect(index.overview.length).toBeGreaterThan(300);
    expect(new Set(index.overview.map(row=>row[0])).size).toBe(index.overview.length);
    expect(index.overview.some(row=>row[6]==='IT' && row[2]>46 && row[3]>11 && row[3]<13.5)).toBe(true);
    const featured=new Set(index.top.map(row=>row[0]));
    for(const ids of Object.values(index.rows)){
      expect(ids).toHaveLength(12);
      for(const id of ids)expect(featured.has(id)).toBe(true);
    }
  });
});
