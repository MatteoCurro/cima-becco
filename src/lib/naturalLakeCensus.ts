import {DATA_BASE} from './venues';

/** Thin G0 agency record for map and listing only; never a NaturalLake G2. */
export interface LakeSourceCensusRecord {
  sourceKey:string;
  sourceFeatureId:string;
  provider:'bolzano_lakes'|'arpav_water_surfaces';
  name:string|null;
  names:{lang:'it'|'de';name:string}[];
  rawClass:string|null;
  municipalityReported:string|null;
  sourceDescriptionName:string|null;
  previewSlug:string|null;
  previewOnly:boolean;
  previewNoindex:true;
  agencyReportedVolumeM3:number|null;
  agencyReportedWidthM:number|null;
  agencyReportedLengthM:number|null;
  canonicalSubtypeVerified:false;
  qualityGate:'G0';
  seoIndexable:false;
  geom:{type:'MultiPolygon';coordinates:number[][][][]};
  derivedMappedKm2:number;
  agencyReportedAreaM2:number|null;
  agencyReportedElevationM:number|null;
  sourceUrl:string;
  licence:string;
}
interface CensusSource {
  mappedSourceRecords:number;
  namedSourceRecords:number;
  geometryPendingReview:number;
  sourceFeatureIdsObserved:number;
  sourceLicence:string;
  providerLabel:string;
  sourceDatasetUrl:string;
}
export interface LakeSourceCensus {
  records:LakeSourceCensusRecord[];
  shownPolygons:number;
  geometryPendingReview:number;
  sourcePreviewsReady:number;
  sourceCounts:Record<'bolzano_lakes'|'arpav_water_surfaces',CensusSource>;
}
const EMPTY:LakeSourceCensus={records:[],shownPolygons:0,geometryPendingReview:0,sourcePreviewsReady:0,
  sourceCounts:{
    bolzano_lakes:{mappedSourceRecords:0,namedSourceRecords:0,geometryPendingReview:0,
      sourceFeatureIdsObserved:0,sourceLicence:'CC0 1.0',providerLabel:'Provincia autonoma di Bolzano',
      sourceDatasetUrl:'https://data.civis.bz.it/dataset/laghi'},
    arpav_water_surfaces:{mappedSourceRecords:0,namedSourceRecords:0,geometryPendingReview:0,
      sourceFeatureIdsObserved:0,sourceLicence:'CC BY 3.0',providerLabel:'ARPAV Veneto',
      sourceDatasetUrl:'https://geodati.gov.it/geoportale/visualizzazione-metadati/scheda-metadati?metadataid=arpa_ve:idrografia_specchio_acqua'},
  }};
let pending:Promise<LakeSourceCensus>|null=null;
const pnames=['bolzano_lakes','arpav_water_surfaces'] as const;
const fidCheck={
  bolzano_lakes:/^Lakes\.[1-9]\d*$/,
  arpav_water_surfaces:/^idrografia_specchio_acqua\.[1-9]\d*$/,
};
const count=(v:unknown):v is number=>typeof v==='number'&&Number.isInteger(v)&&v>=0;
const optional=(v:unknown):v is number|null=>v===null||
  (typeof v==='number'&&Number.isFinite(v)&&v>=0);
const validPolygon=(row:LakeSourceCensusRecord)=>row.geom?.type==='MultiPolygon'&&
  Array.isArray(row.geom.coordinates)&&row.geom.coordinates.length>0&&
  row.geom.coordinates.every(group=>Array.isArray(group)&&group.length>0&&
    group.every(ring=>Array.isArray(ring)&&ring.length>=4&&
      ring.every(p=>Array.isArray(p)&&p.length===2&&
        Number.isFinite(p[0])&&Number.isFinite(p[1])&&
        p[0]>=6&&p[0]<=20&&p[1]>=35&&p[1]<=48)&&
      ring[0][0]===ring[ring.length-1][0]&&
      ring[0][1]===ring[ring.length-1][1]));

export function verifiedLakeSourceCensus(input:unknown):LakeSourceCensus{
  if(!input||typeof input!=='object')return EMPTY;
  const d=input as Record<string,unknown>;
  if(d.releaseChannel!=='NATURAL_LAKE_SOURCE_CENSUS_MAP_G0_V1'||
      d.sourceOnlyCatalogue!==true||d.isPublishedG2!==false||
      d.individualPagesAllowed!==false||d.seoIndexable!==false||
      d.sourceRecordsAreNotDeduplicatedPhysicalLakes!==true||
      d.canonicalAtlasEntitiesAdded!==0||d.crossSourceIdentityLinksAdded!==0||
      d.sourcePreviewPagesNoindexAllowed!==true||!count(d.sourcePreviewsReady)||
      !Array.isArray(d.records)||!count(d.shownPolygons)||
      !count(d.geometryPendingReview)||d.records.length!==d.shownPolygons||
      !d.sourceCounts||typeof d.sourceCounts!=='object')return EMPTY;
  const counts=d.sourceCounts as LakeSourceCensus['sourceCounts'];
  if(!pnames.every(p=>{
    const x=counts[p];return x&&count(x.mappedSourceRecords)&&
      count(x.namedSourceRecords)&&count(x.geometryPendingReview)&&
      count(x.sourceFeatureIdsObserved)&&
      x.mappedSourceRecords+x.geometryPendingReview===x.sourceFeatureIdsObserved&&
      x.namedSourceRecords<=x.mappedSourceRecords&&
      typeof x.providerLabel==='string'&&
      x.sourceDatasetUrl?.startsWith('https://')&&
      x.sourceLicence?.length>0;
  }))return EMPTY;
  if(pnames.reduce((n,p)=>n+counts[p].mappedSourceRecords,0)!==d.shownPolygons||
     pnames.reduce((n,p)=>n+counts[p].geometryPendingReview,0)!==d.geometryPendingReview)return EMPTY;
  const ids=new Set<string>(),previewSlugs=new Set<string>();
  let previewsReady=0;
  const records=d.records as LakeSourceCensusRecord[];
  for(const r of records){
    if(!r||!pnames.includes(r.provider)||
        typeof r.sourceFeatureId!=='string'||
        !fidCheck[r.provider].test(r.sourceFeatureId)||
        r.sourceKey!==r.provider+':'+r.sourceFeatureId||
        r.qualityGate!=='G0'||r.seoIndexable!==false||
        r.canonicalSubtypeVerified!==false||
        !validPolygon(r)||
        !optional(r.agencyReportedAreaM2)||!optional(r.agencyReportedElevationM)||
        !optional(r.agencyReportedVolumeM3)||!optional(r.agencyReportedWidthM)||
        !optional(r.agencyReportedLengthM)||
        !Number.isFinite(r.derivedMappedKm2)||r.derivedMappedKm2<=0||
        (r.name!==null&&(typeof r.name!=='string'||r.name.length>180))||
        (r.municipalityReported!==null&&typeof r.municipalityReported!=='string')||
        (r.sourceDescriptionName!==null&&typeof r.sourceDescriptionName!=='string')||
        r.previewNoindex!==true||r.previewOnly!==Boolean(r.previewSlug)||
        (r.previewSlug!==null&&(
          !/^[a-z0-9]+(?:-[a-z0-9]+)*-[a-f0-9]{7}$/.test(r.previewSlug)||
          !r.name||previewSlugs.has(r.previewSlug)))||
        !Array.isArray(r.names)||
        r.names.some(n=>!['it','de'].includes(n.lang)||typeof n.name!=='string')||
        r.sourceUrl!==counts[r.provider].sourceDatasetUrl||
        r.licence!==counts[r.provider].sourceLicence||
        // A G0 index cannot embed canonical URLs or entity relations.
        'slug' in r||'relations' in r||'sourceIds' in r||
        ids.has(r.sourceKey))return EMPTY;
    ids.add(r.sourceKey);
    if(r.previewSlug){previewSlugs.add(r.previewSlug);previewsReady++;}
  }
  if(pnames.some(p=>records.filter(x=>x.provider===p).length!==counts[p].mappedSourceRecords)||
      previewsReady!==d.sourcePreviewsReady)return EMPTY;
  return {records,shownPolygons:d.shownPolygons,geometryPendingReview:d.geometryPendingReview,
    sourcePreviewsReady:previewsReady,
    sourceCounts:counts};
}

export function loadLakeSourceCensus():Promise<LakeSourceCensus>{
  pending??=fetch(DATA_BASE+'/atlas/natural-lake-census-map-v1.json')
    .then(async res=>res.ok?verifiedLakeSourceCensus(await res.json()):EMPTY)
    .catch(()=>{pending=null;return EMPTY;});
  return pending;
}
export const lakeSourceLabel=(r:LakeSourceCensusRecord):string=>
  r.name||'Specchio d’acqua censito · '+r.sourceFeatureId;
export const lakeSourceClass=(r:LakeSourceCensusRecord):string=>
  r.rawClass||'Categoria non confermata';
export const lakeSourceProvider=(provider:LakeSourceCensusRecord['provider']):string=>
  provider==='bolzano_lakes'?'Provincia di Bolzano':'ARPAV Veneto';

/** Preview of agency data only, permanently separate from canonical G2 URLs. */
export const lakeSourcePreviewHref=(r:LakeSourceCensusRecord):string|null=>
  r.previewSlug?import.meta.env.BASE_URL+'laghi/censiti/'+encodeURIComponent(r.previewSlug)+'/':null;
