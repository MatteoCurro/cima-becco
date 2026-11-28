import { describe,it,expect } from 'vitest';
import type { Route,Venue } from '../types';
import type { AlpinePlace } from './alpinePlaces';
import { summitRoutes,summitSupportPlaces } from './summitApproach';
const peak={slug:'gn100-45x10',name:'Cima delle prove',type:'hill',lat:46.5,lng:12,
  gainM:null,elevationSource:'community',routeSlugs:[],id:'summit-id'} as Venue;
const route=(over:Partial<Route>={}):Route=>({
  slug:'osm-123',name:'Sentiero 12',venueSlugs:[],distanceM:8500,
  gainM:820,lossM:800,loop:false,source:'curated',activity:'hike',
  coordinates:[[11.98,46.49,1200],[12,46.5,2200]],...over,
});
const hut=(over:Partial<AlpinePlace>={}):AlpinePlace=>({
  kind:'rifugio',slug:'rif-test',name:'Rifugio Test',
  lat:46.49,lng:12,osmUrl:'https://www.openstreetmap.org/node/1',...over,
});
describe('Collegamenti topografici prudenti delle cime',()=>{
  it('una traccia con capolinea vicino non diventa accesso verificato',()=>{
    const result=summitRoutes(peak,[route()]);
    expect(result).toHaveLength(1);
    expect(result[0].relation).toBe('endpoint_near');
    expect(result[0].distanceM).toBe(0);
  });
  it('un link ascends_to è documentato solo se verificato e riferito alla stessa cima',()=>{
    const link={type:'ascends_to' as const,target:{id:'summit-id',kind:'summit',name:'Test'},verified:true};
    expect(summitRoutes(peak,[route({relations:[link]})])[0].relation).toBe('documented');
    expect(summitRoutes(peak,[route({relations:[{...link,verified:false}]})])[0].relation).not.toBe('documented');
  });
  it('una ferrata a distanza non diventa un sentiero che arriva in vetta',()=>{
    const out=summitRoutes(peak,[route({
      activity:'ferrata',viaFerrataScale:'3',
      coordinates:[[12.01,46.51,1800],[12.013,46.514,2100]],
    })]);
    expect(out).toHaveLength(1);
    expect(out[0].relation).toBe('ferrata_area');
  });
  it('non associa luoghi o tracciati soltanto perché condividono un nome',()=>{
    expect(summitRoutes(peak,[route({coordinates:[[13,45,500],[13.02,45.02,700]],name:'Cima delle prove'})])).toHaveLength(0);
    const a=summitRoutes(peak,[route({stops:[{slug:'rif-test',name:'Rifugio Test',kind:'rifugio',distanceM:20,relation:'passaggio',at:0.5}]})]);
    const places=summitSupportPlaces(peak,[hut(),hut({slug:'other',name:'Altro',lng:12.025})],a);
    expect(places[0].relation).toBe('mapped_route');
    expect(places[1].relation).toBe('nearby');
  });
  it('non propone rifugi o bivacchi dall’altra parte delle Alpi',()=>{
    expect(summitSupportPlaces(peak,[hut({lat:45,lng:10})],[])).toHaveLength(0);
  });
});
