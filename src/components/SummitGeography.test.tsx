import { describe, expect, it } from 'vitest';
import type { Venue } from '../types';
import { summitGeography } from './SummitGeography';

const summit:Venue={
  slug:'gn123-45x10',name:'Cima Focobon',type:'hill',lat:46.33,lng:12.11,
  summitM:3054,gainM:null,elevationSource:'community',routeSlugs:[],
  administrativeHierarchy:{country:'IT'},
  facts:{
    elevationM:{value:3054,unit:'m',method:'reported',sourceId:'geonames:123'},
    featureClass:{value:'PK',sourceId:'geonames:123'},
    wikidataElevationReportedM:{value:3057,unit:'m',method:'reported'},
    wikidataIdentityVerified:{value:true},
  },
  aliases:[],localNames:[{value:'Cima Focobon'},{value:'Focobon',language:'it'}],
};
describe('Scheda editoriale cima',()=>{
  it('presenta identità geografica, coordinate e toponimi con nomi leggibili',()=>{
    const geo=summitGeography(summit);
    expect(geo.country).toBe('Italia');
    expect(geo.type).toBe('Cima');
    expect(geo.names.map(v=>v.value)).toEqual(['Focobon']);
    expect(geo.method).toBe('reported');
  });
  it('conserva le quote alternative soltanto quando differiscono',()=>{
    expect(summitGeography(summit).differs).toBe(true);
    expect(summitGeography({...summit,facts:{...summit.facts,wikidataElevationReportedM:{value:3054}}}).differs).toBe(false);
  });
  it('non inventa quota o toponimi quando il record non li contiene',()=>{
    const empty=summitGeography({...summit, facts:undefined,localNames:[]});
    expect(empty.sourceAltitude).toBeNull();
    expect(empty.differs).toBe(false);
    expect(empty.names).toEqual([]);
  });
});
