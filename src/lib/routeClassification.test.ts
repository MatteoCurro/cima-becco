import { describe, it, expect } from 'vitest';
import type { Route } from '../types';
import { routePresentationCategory, routePhysicalEffort } from './routeClassification';
const example=(over:Partial<Route>={}):Route=>({
  slug:'test',name:'Sentiero 12',venueSlugs:[],distanceM:6000,gainM:300,lossM:200,
  elevationAvailable:true,loop:false,coordinates:[[12,46,1000],[12.03,46.04,1300]],
  source:'curated',activity:'hike',...over,
});
describe('Catalogazione cauta senza modificare l’importatore',()=>{
  it('riconosce le ferrate dai dati espliciti e dai nomi come indizio',()=>{
    expect(routePresentationCategory(example({activity:'ferrata'})).kind).toBe('ferrata');
    expect(routePresentationCategory(example({viaFerrataScale:'3+'})).evidence).toBe('catalogued');
    expect(routePresentationCategory(example({name:'Via Ferrata delle Aquile'})).evidence).toBe('inferred');
  });
  it('non equipara un EEA o poche corde fisse a una ferrata verificata',()=>{
    expect(routePresentationCategory(example({caiDifficulty:'EEA'})).kind).toBe('attrezzato');
    expect(routePresentationCategory(example({caiDifficulty:'EE'})).kind).toBe('escursione');
    expect(routePresentationCategory(example({name:'Sentiero attrezzato degli Alpini'})).kind).toBe('attrezzato');
  });
  it('non confonde fatica fisica e difficoltà tecnica',()=>{
    const strenuous=example({distanceM:18000,gainM:1230,caiDifficulty:'E'});
    expect(routePhysicalEffort(strenuous).level).toBe('demanding');
    expect(routePhysicalEffort(strenuous).explanation).toContain('salita');
    expect(routePresentationCategory(strenuous).kind).toBe('escursione');
  });
  it('non tratta un dislivello non disponibile come 0 metri reali',()=>{
    const missing=routePhysicalEffort(example({elevationAvailable:false,gainM:0,distanceM:10000}));
    expect(missing.gainM).toBeNull();
    expect(missing.explanation).toMatch(/parziale/);
  });
});
