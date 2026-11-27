import { describe, expect, it } from 'vitest';
import type { AlpinePlace } from './alpinePlaces';
import { refugeSchemaProperties } from './refugeStructuredData';

const base:AlpinePlace={
  kind:'rifugio',name:'Rifugio di prova',slug:'cai-47',lat:46.1,lng:11.1,
  osmUrl:'https://www.openstreetmap.org/#map=15/46.1/11.1',
  sourceIds:{cai:'47'},
  officialUrl:'https://rifugi.cai.it/shelters/47',
};
const fact=(value:string|number|boolean)=>({value,sourceId:'cai:shelter:47',sourceUrl:'https://rifugi.cai.it/shelters/47'});
describe('schema.org del rifugio',()=>{
  it('codifica capacità come posti letto, non come numero di camere o disponibilità',()=>{
    const p:AlpinePlace={...base,facts:{
      bedsTotal:fact(42),bedsWinter:fact(8),yearBuilt:fact(1930),
      wifi:fact(true),showers:fact(false),pets:fact(false),
      waterAvailableReported:fact(true),
    }};
    const ld=refugeSchemaProperties(p);
    expect(ld).toMatchObject({
      identifier:{'@type':'PropertyValue',propertyID:'CAI',value:'47'},
      petsAllowed:false,
      amenityFeature:expect.arrayContaining([
        {'@type':'LocationFeatureSpecification',name:'Wi-Fi',value:true},
        {'@type':'LocationFeatureSpecification',name:'docce',value:false},
      ]),
    });
    expect(JSON.stringify(ld)).toContain('Posti letto invernali');
    expect(JSON.stringify(ld)).not.toMatch(/numberOfRooms|availability|aggregateRating|openingHoursSpecification|occupancy/);
  });
  it('non pubblica servizi ignoti, numeri impossibili o fatti privi di provenienza',()=>{
    const p:AlpinePlace={...base,facts:{
      pets:{value:false},wifi:fact(null as unknown as boolean),meals:fact(true),
      bedsTotal:fact(-10),bedsWinter:fact(0),yearBuilt:fact(1500),
    }};
    const ld=refugeSchemaProperties(p);
    expect(ld).not.toHaveProperty('petsAllowed');
    expect(ld).not.toHaveProperty('additionalProperty');
    expect(ld).toHaveProperty('amenityFeature',[{'@type':'LocationFeatureSpecification',name:'ristorazione',value:true}]);
  });
  it('usa contatti/indirizzo e link esterni solo quando effettivamente disponibili',()=>{
    const p:AlpinePlace={...base,website:'https://example.org',email:'info@example.org',
      address:'Loc. Esempio 1'};
    const ld=refugeSchemaProperties(p);
    expect(ld).toMatchObject({address:'Loc. Esempio 1',email:'info@example.org',
      sameAs:['https://rifugi.cai.it/shelters/47','https://example.org']});
  });
});
