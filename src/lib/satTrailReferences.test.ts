import { describe, expect, it } from 'vitest';
import { parseSATRouteReferenceDataset } from './satTrailReferences';

const url='https://www.sat.tn.it/sentieri/mappa-sentieri/';
const reportedFacts=Object.fromEntries([
  'elevationStartReportedM','elevationEndReportedM','elevationMinReportedM',
  'elevationMaxReportedM','lengthPlanimetricReportedM','lengthInclinedReportedM',
  'durationOutReportedMin','durationBackReportedMin',
].map((k,i)=>[k,{value:100+i,unit:k.endsWith('Min')?'min':'m',
                       method:'reported',sourceUrl:url,licence:'ODbL 1.0'}]));

const record={
  routeSlug:'osm-hiking-7289913',
  sourceReference:{sourceId:'SAT',number:'E630',sourceUrl:url,licence:'ODbL 1.0',
                   retrievedAt:'2026-11-28T14:30:00Z',officialCatalogueSubtype:null},
  identityEvidence:{osmRelationId:'relation/7289913',sourceReferenceVerified:true,
                    method:'exact_sat_reg_ref_operator_source_difficulty_and_bilateral_geometry_v1',
                    osmSourceUrl:'https://www.openstreetmap.org/relation/7289913'},
  originalDifficulty:{value:'E',scale:'CAI/SAT source value'},
  sourceContext:{startPlaceAsText:'PASSO',endPlaceAsText:'RIFUGIO'},
  reportedFacts,
  quality:{gate:'G1',satSourceReferenceVerified:true,routeContinuityVerified:false,
           traversableVerified:false,ferrataSubtypeVerified:false,canonicalEntityMergePerformed:false,
           osmRelationMembershipIncomplete:true},
};

function dataset(value: unknown=record) {
  return {releaseChannel:'SAT_VERIFIED_ROUTE_SOURCE_REFERENCE_G1_V1',
    isPublished:true,seoIndexable:false,newCanonicalPagesCreated:false,
    routeCatalogueModified:false,
    quality:{gate:'G1',routingAllowed:false,safetyVerified:false,newPermalinksAllowed:false},
    records:{'osm-hiking-7289913':value}};
}

describe('SAT verified route-source G1 metadata guard',()=>{
  it('only exposes references with corroborated source identity and all 8 facts',()=>{
    const parsed=parseSATRouteReferenceDataset(dataset());
    expect(Object.keys(parsed)).toEqual(['osm-hiking-7289913']);
    expect(parsed['osm-hiking-7289913'].sourceReference.number).toBe('E630');
    expect(parsed['osm-hiking-7289913'].quality.routeContinuityVerified).toBe(false);
  });
  it('rejects an unverified or safety-positive shortcut',()=>{
    expect(parseSATRouteReferenceDataset(dataset({...record,quality:{...record.quality,traversableVerified:true}}))).toEqual({});
    expect(parseSATRouteReferenceDataset(dataset({...record,identityEvidence:{...record.identityEvidence,sourceReferenceVerified:false}}))).toEqual({});
  });
  it('rejects route slug, source title or grade misdirection',()=>{
    expect(parseSATRouteReferenceDataset(dataset({...record,routeSlug:'osm-hiking-99'}))).toEqual({});
    expect(parseSATRouteReferenceDataset(dataset({...record,sourceReference:{...record.sourceReference,number:'630'}}))).toEqual({});
    expect(parseSATRouteReferenceDataset(dataset({...record,originalDifficulty:{value:'X',scale:'NA'}}))).toEqual({});
  });
  it('rejects invented facts and a new canonical page claim',()=>{
    expect(parseSATRouteReferenceDataset(dataset({...record,reportedFacts:{}}))).toEqual({});
    expect(parseSATRouteReferenceDataset({...dataset(),newCanonicalPagesCreated:true})).toEqual({});
  });
});
