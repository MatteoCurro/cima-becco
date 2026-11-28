import {describe,it,expect} from 'vitest';
import {verifiedLakeSourceCensus,lakeSourceLabel,lakeSourceClass} from './naturalLakeCensus';

const geo={type:'MultiPolygon' as const,coordinates:[[[[11.7,46.6],[11.71,46.6],
  [11.71,46.61],[11.7,46.61],[11.7,46.6]]]]};
const source={
  sourceKey:'bolzano_lakes:Lakes.10',sourceFeatureId:'Lakes.10',
  provider:'bolzano_lakes',name:'Lago di prova',
  names:[{lang:'it',name:'Lago di prova'},{lang:'de',name:'Testsee'}],
  rawClass:null,canonicalSubtypeVerified:false,qualityGate:'G0',seoIndexable:false,
  geom:geo,derivedMappedKm2:1.12,agencyReportedAreaM2:1000000,
  agencyReportedElevationM:2100,sourceUrl:'https://data.civis.bz.it/dataset/laghi',
  licence:'CC0 1.0',
};
const sourceCounts={
  bolzano_lakes:{mappedSourceRecords:1,namedSourceRecords:1,geometryPendingReview:2,
    sourceFeatureIdsObserved:3,sourceLicence:'CC0 1.0',
    providerLabel:'Provincia autonoma di Bolzano',
    sourceDatasetUrl:'https://data.civis.bz.it/dataset/laghi'},
  arpav_water_surfaces:{mappedSourceRecords:0,namedSourceRecords:0,geometryPendingReview:0,
    sourceFeatureIdsObserved:0,sourceLicence:'CC BY 3.0',
    providerLabel:'ARPAV Veneto',
    sourceDatasetUrl:'https://geodati.gov.it/geoportale/visualizzazione-metadati/scheda-metadati?metadataid=arpa_ve:idrografia_specchio_acqua'},
};
const published={
  releaseChannel:'NATURAL_LAKE_SOURCE_CENSUS_MAP_G0_V1',
  sourceOnlyCatalogue:true,isPublishedG2:false,individualPagesAllowed:false,
  seoIndexable:false,sourceRecordsAreNotDeduplicatedPhysicalLakes:true,
  canonicalAtlasEntitiesAdded:0,crossSourceIdentityLinksAdded:0,
  shownPolygons:1,geometryPendingReview:2,sourceCounts,records:[source],
};
describe('G0-only public lake source map projection',()=>{
  it('shows a verified source polygon without creating a lake dossier',()=>{
    const x=verifiedLakeSourceCensus(published);
    expect(x.records).toHaveLength(1);
    expect(x.geometryPendingReview).toBe(2);
    expect(lakeSourceLabel(x.records[0])).toBe('Lago di prova');
    expect(lakeSourceClass(x.records[0])).toBe('Categoria non confermata');
    expect(x.records[0]).not.toHaveProperty('slug');
    expect(x.records[0]).not.toHaveProperty('point');
  });
  it('rejects any SEO or individual page promotion',()=>{
    expect(verifiedLakeSourceCensus({...published,seoIndexable:true}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,individualPagesAllowed:true}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,canonicalAtlasEntitiesAdded:1}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,records:[{...source,qualityGate:'G2'}]}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,records:[{...source,slug:'fake-lake'}]}).records).toHaveLength(0);
  });
  it('rejects incorrect source provenance, fake polygon, or false totals',()=>{
    expect(verifiedLakeSourceCensus({...published,shownPolygons:500}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,records:[source,source]}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,records:[{...source,sourceFeatureId:'Lakes.99'}]}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,records:[{...source,geom:{type:'Point',coordinates:[11.7,46.6]}}]}).records).toHaveLength(0);
    expect(verifiedLakeSourceCensus({...published,records:[{...source,agencyReportedAreaM2:-1}]}).records).toHaveLength(0);
  });
});
