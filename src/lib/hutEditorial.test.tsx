import { describe,expect,it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { createElement } from 'react';
import type { AlpinePlace } from './alpinePlaces';
import { hutAliases,hutServiceFacts,hutServiceChapters,shelterSeoDescription } from './hutEditorial';
import { shelterSchemaProperties } from './shelterStructuredData';
import { HutServices } from '../components/HutServices';

const base:AlpinePlace={name:'Bivacco Fiamme Gialle',slug:'cai-922005301',kind:'bivacco',
  shelterTypeLabel:'Bivacco fisso',lat:46.5,lng:11.6,osmUrl:'https://www.openstreetmap.org/#map=14/46.5/11.6',
  sourceIds:{cai:'922005301'},officialUrl:'https://rifugi.cai.it/shelters/922005301'};
const fact=(value:boolean|number|string|null)=>({
  value,sourceId:'cai:shelter:922005301',sourceUrl:'https://rifugi.cai.it/shelters/922005301',
});
describe('dossier bivacchi e servizi condivisi',()=>{
  it('separa servizi disponibili, esplicitamente non disponibili e ignoti',()=>{
    const place:AlpinePlace={...base,facts:{
      mattressAvailableReported:fact(true),blanketAvailableReported:fact(false),
      stoveAvailableReported:fact(null),gasAvailableReported:{value:false},
      waterAvailableReported:fact(false),bedsTotal:fact(9),
    }};
    const list=hutServiceFacts(place);
    expect(list.map(x=>x.key)).toEqual(expect.arrayContaining([
      'mattressAvailableReported','blanketAvailableReported','waterAvailableReported',
    ]));
    expect(list.map(x=>x.key)).not.toContain('stoveAvailableReported');
    expect(list.map(x=>x.key)).not.toContain('gasAvailableReported');
    expect(hutServiceChapters(place).map(x=>x.id)).toContain('riposo');
    const markup=renderToStaticMarkup(createElement(HutServices,{place}));
    expect(markup).toContain('is-unavailable');
    expect(markup).toContain('Non disponibile');
    expect(markup).toContain('Materassi');
    expect(markup).toContain('Coperte');
    expect(markup).not.toContain('Stufa');
    expect(markup).not.toContain("La disponibilità d'acqua");
    expect(markup).not.toContain('secondo le fonti');
  });
  it('ordina in ogni capitolo prima i servizi disponibili e poi alfabeticamente, senza nuovi titoli',()=>{
    const place:AlpinePlace={...base,facts:{
      mattressAvailableReported:fact(true),blanketAvailableReported:fact(false),
      sleepingBagLiner:fact(true),showers:fact(false),hotWater:fact(true),
      waterAvailableReported:fact(false),
    }};
    const riposo=hutServiceChapters(place).find(ch=>ch.id==='riposo');
    expect(riposo?.items.map(item=>item.label)).toEqual([
      'acqua calda','Materassi','sacco lenzuolo in vendita','Coperte','docce',
    ]);
    const markup=renderToStaticMarkup(createElement(HutServices,{place}));
    const names=['acqua calda','Materassi','sacco lenzuolo in vendita','Coperte','docce'];
    expect(names.map(name=>markup.indexOf(name))).toEqual(
      [...names.map(name=>markup.indexOf(name))].sort((a,b)=>a-b));
    expect(markup).not.toContain('Servizi disponibili');
    expect(markup).not.toContain('Servizi non disponibili');
  });
  it('non perde dotazioni CAI valide quando le categorie sono specifiche dei bivacchi',()=>{
    const place:AlpinePlace={...base,facts:{
      meals:fact(true),showers:fact(false),hotWater:fact(true),
      cardPayments:fact(false),defibrillator:fact(true),toiletAvailableReported:fact(true),
      electricity:fact(true),
    }};
    const keys=hutServiceChapters(place).flatMap(ch=>ch.items.map(item=>item.key));
    expect(keys.slice().sort()).toEqual(hutServiceFacts(place).map(item=>item.key).sort());
  });
  it('ricava nomi alternativi anche da fatti CAI dotati di provenienza',()=>{
    const place:AlpinePlace={...base,facts:{aliases:fact('Bivacco vecchio; Capanna del Passo')}};
    expect(hutAliases(place).map(item=>item.value)).toEqual(['Bivacco vecchio','Capanna del Passo']);
    expect(hutAliases({...base,facts:{aliases:{value:'Nome senza fonte'}}})).toEqual([]);
  });
  it('visualizza alias senza ripetere il titolo, con lingua e valore storico',()=>{
    const place={...base,aliases:[
      {value:'Bivacco Fiamme Gialle'}, {value:'Bivacco Fiame',historical:true},
      {value:'Feuerhütte',language:'de'}, {value:'Bivacco Fiame',historical:true},
    ]};
    expect(hutAliases(place)).toEqual([
      {value:'Bivacco Fiame',historical:true},{value:'Feuerhütte',language:'de'},
    ]);
  });
  it('schema Place con dotazioni documentate, senza prezzi, apertura o camere inventate',()=>{
    const place:AlpinePlace={...base,facts:{
      bedsTotal:fact(9),bedsWinter:fact(3),blanketAvailableReported:fact(false),
      waterAvailableReported:fact(true),keysRequired:fact(true),lastInspectionAt:fact('2026-10-03'),
    }};
    const schema=shelterSchemaProperties(place);
    expect(schema).toHaveProperty('amenityFeature',expect.arrayContaining([
      {'@type':'LocationFeatureSpecification',name:'Coperte',value:false},
    ]));
    const json=JSON.stringify(schema);
    expect(json).toContain('Posti invernali');
    expect(json).not.toMatch(/LodgingBusiness|numberOfRooms|price|openingHours|aggregateRating|availability/);
  });
  it('la descrizione completa è separata dalla meta-description SEO abbreviata',()=>{
    const full='Bivacco con storia. '.repeat(20);
    const place={...base,description:full};
    expect(shelterSeoDescription(place).length).toBeLessThanOrEqual(276);
    expect(place.description).toBe(full);
  });
});
