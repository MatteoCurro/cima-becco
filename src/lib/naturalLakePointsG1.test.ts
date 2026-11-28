import {describe,it,expect} from 'vitest';
import {verifiedIdentifiedLakePoints} from './naturalLakePointsG1';
const profile={
  id:'bfbce08c-26a4-5f70-9c5a-350a5aafc142',
  name:'Lago verificato',slug:'lago-verificato',subtype:'lake',
  aliases:[],localNames:[],
  sourceIds:{geonames:'100',wikidata:'Q123',wikidataVerifiedBy:'P1566+P625'},
  geo:{point:{lat:46.6,lng:12.3},method:'geonames_point',
    pointSourceUrl:'https://www.geonames.org/100/',
    area:null,areaSourceUrl:null,areaMethod:null},
  facts:{elevationM:{value:2200,unit:'m',sourceId:'geonames:100',
    sourceUrl:'https://www.geonames.org/100/',method:'reported',licence:'CC BY 4.0'}},
  media:[],textSources:[],description:null,
  quality:{gate:'G1',seoIndexable:false,sourcePointVerified:true,
    wikidataIdentityVerified:true,hasVerifiedShoreline:false,needsAreaGeometryReview:true,
    photoSourceVerified:false,textLicenseVerified:false},
  identitySource:'exact_P1566_P625_one_to_one',
  checkedAt:'2026-11-28T12:00:00Z',
};
const release={
  releaseChannel:'NATURAL_LAKE_IDENTIFIED_PROFILES_G1_V1',
  isCanonicalPublished:false,seoIndexable:false,noindexFollow:true,
  crossSourceWfsMerges:0,g2Duplicated:0,
  sourceG1Candidates:1,excludedCanonicalG2:0,
  counts:{profiles:1,pointOnly:1,withOsmGeometry:0,
    withVerifiedP18:0,withVerifiedItwiki:0},
  entities:[profile],
};
describe('G1 source-exact lake point profiles',()=>{
  it('publishes an independently located noindex point with no invented shore',()=>{
    const d=verifiedIdentifiedLakePoints(release);
    expect(d.entities).toHaveLength(1);
    expect(d.counts.pointOnly).toBe(1);
    expect(d.entities[0].geo.area).toBeNull();
    expect(d.entities[0].quality.gate).toBe('G1');
    expect(d.entities[0].sourceIds.wikidata).toBe('Q123');
    expect(d.entities[0].facts.elevationM.method).toBe('reported');
  });
  it('blocks G2, SEO, fictitious OSM area and unverified QID',()=>{
    expect(verifiedIdentifiedLakePoints({...release,seoIndexable:true}).entities).toHaveLength(0);
    expect(verifiedIdentifiedLakePoints({...release,g2Duplicated:1}).entities).toHaveLength(0);
    expect(verifiedIdentifiedLakePoints({...release,entities:[{
      ...profile,quality:{...profile.quality,gate:'G2'}}]}).entities).toHaveLength(0);
    expect(verifiedIdentifiedLakePoints({...release,entities:[{
      ...profile,sourceIds:{...profile.sourceIds,wikidataVerifiedBy:'name_similarity'}}]}).entities).toHaveLength(0);
    expect(verifiedIdentifiedLakePoints({...release,entities:[{
      ...profile,geo:{...profile.geo,areaSourceUrl:'https://www.openstreetmap.org/way/100'}}]}).entities).toHaveLength(0);
  });
  it('rejects mismatched licensed media or invented image evidence',()=>{
    const media={id:'p1',kind:'photo',sourceId:'wikidata:Q456:P18',
      subjectMethod:'verified_GeoNames_P1566_Wikidata_P625_P18',
      subjectVerified:true,reuseAllowed:true,author:'Author',licence:'CC BY 4.0',
      sourceUrl:'https://commons.wikimedia.org/wiki/File:Lake.jpg',
      url:'https://upload.wikimedia.org/wikipedia/commons/1/11/Lake.jpg'};
    const changed={...profile,media:[media],
      quality:{...profile.quality,photoSourceVerified:true}};
    expect(verifiedIdentifiedLakePoints({...release,
      counts:{...release.counts,withVerifiedP18:1},entities:[changed]}).entities).toHaveLength(0);
    const okay={...changed,media:[{...media,sourceId:'wikidata:Q123:P18'}]};
    expect(verifiedIdentifiedLakePoints({...release,
      counts:{...release.counts,withVerifiedP18:1},entities:[okay]}).entities).toHaveLength(1);
  });
});
