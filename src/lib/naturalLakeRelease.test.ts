import {describe,it,expect} from 'vitest';
import {verifiedNaturalLakes} from './naturalLakeRelease';

const geo={point:{lat:46.5,lng:12.3},area:{
  type:'MultiPolygon',coordinates:[[[[12.29,46.49],[12.31,46.49],
    [12.31,46.51],[12.29,46.51],[12.29,46.49]]]]},
  areaSourceUrl:'https://www.openstreetmap.org/way/10',
  areaMethod:'osm_out_geom_multipolygon'};
const lake={
  id:'db1f50b9-63dd-5317-9baa-3a836e3d4c67',
  kind:'natural_feature',subtype:'lake',slug:'lago-di-prova',name:'Lago di Prova',
  geo,
  sourceIds:{geonames:'100',wikidata:'Q123',osm:'way/10',
    wikidataVerifiedBy:'P1566+P625',
    osmVerifiedBy:'P1566_P625_and_exact_OSM_QID_or_GeoNames_ID'},
  facts:{elevationM:{value:2200,unit:'m',sourceId:'geonames:100'},
    osmMappedWaterSurfaceKm2:{value:1.1,unit:'km2',method:'derived',licence:'ODbL 1.0'}},
  quality:{gate:'G2',seoIndexable:true,geometryTopologyVerified:true},
  description:'Il lago documentato ha una geometria cartografica e una fonte enciclopedica verificata. '.repeat(3),
  media:[{kind:'photo',sourceId:'wikidata:Q123:P18',subjectVerified:true,
    reuseAllowed:true,author:'Autore',licence:'CC BY-SA 4.0',
    url:'https://upload.wikimedia.org/test.jpg',
    sourceUrl:'https://commons.wikimedia.org/wiki/File:Photo.jpg'}],
  textSources:[{sourceId:'wikipedia:it:11',licence:'CC BY-SA 4.0',
    sourceUrl:'https://it.wikipedia.org/wiki/Lago_di_Prova',
    text:'Il lago documentato ha una voce ufficialmente collegata al QID di Wikidata. '.repeat(3)}],
};
const published={releaseChannel:'NATURAL_FEATURES_LAKES_G2',
  isPublished:true,generatedAt:'2026-11-28T10:00:00Z',entities:[lake]};
describe('Verified natural lake release adapter',()=>{
  it('only emits G2 published verified lakes',()=>{
    expect(verifiedNaturalLakes(published).features).toHaveLength(1);
    expect(verifiedNaturalLakes({...published,isPublished:false}).features).toHaveLength(0);
    expect(verifiedNaturalLakes({...published,releaseChannel:'NATURAL_WATER_G2_CANDIDATES_STAGING_V1'}).features).toHaveLength(0);
  });
  it('rejects lake without true geometry provenance',()=>{
    expect(verifiedNaturalLakes({...published,entities:[{...lake,
      geo:{...geo,areaSourceUrl:'https://www.openstreetmap.org/way/999'}}]}).features).toHaveLength(0);
    expect(verifiedNaturalLakes({...published,entities:[{...lake,
      quality:{...lake.quality,geometryTopologyVerified:false}}]}).features).toHaveLength(0);
  });
  it('rejects absent photo, wiki source and any G1 lake',()=>{
    expect(verifiedNaturalLakes({...published,entities:[{...lake,media:[]}]}).features).toHaveLength(0);
    expect(verifiedNaturalLakes({...published,entities:[{...lake,textSources:[]}]}).features).toHaveLength(0);
    expect(verifiedNaturalLakes({...published,entities:[{...lake,
      quality:{...lake.quality,gate:'G1',seoIndexable:false}}]}).features).toHaveLength(0);
  });
  it('fails entire dataset on GN, QID, OSM or slug duplicate',()=>{
    const other={...lake,id:'a2',slug:'another-lake'};
    expect(verifiedNaturalLakes({...published,entities:[lake,other]}).features).toHaveLength(0);
    expect(verifiedNaturalLakes({...published,entities:[lake,{...other,
      sourceIds:{...other.sourceIds,geonames:'101',wikidata:'Q124'}}]}).features).toHaveLength(0);
  });
});
