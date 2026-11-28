import { DATA_BASE } from './venues';
import type { AtlasEntityMetadata, AtlasFact, AtlasGeo, AtlasMedia } from './atlasDossier';

/** A sourced water polygon, not a bathing or access recommendation. */
export interface NaturalLake extends AtlasEntityMetadata {
  id:string;
  kind:'natural_feature';
  subtype:'lake'|'reservoir';
  name:string;
  displayName?:string;
  slug:string;
  geo:AtlasGeo & {
    point:{lat:number;lng:number};
    area:{type:'MultiPolygon';coordinates:number[][][][]};
    areaSourceUrl:string;
    areaMethod:string;
  };
  sourceIds:Record<string,string>;
  facts:Record<string,AtlasFact>;
  media:AtlasMedia[];
  description:string;
  quality:{
    gate:'G2';seoIndexable:true;
    geometryTopologyVerified:true;
    areaNotVerified?:false;
    reviewRequired?:false;
    slugRequiresReview?:false;
    elevationConflictReview?:false;
    wikiAltitudeDisagreementReview?:false;
  };
}
export type NaturalLakeDataset={generatedAt:string|null;features:NaturalLake[]};
const EMPTY:NaturalLakeDataset={generatedAt:null,features:[]};
let pending:Promise<NaturalLakeDataset>|null=null;

function isValid(e:NaturalLake):boolean{
  if(!e||e.kind!=='natural_feature'||
    (e.subtype!=='lake'&&e.subtype!=='reservoir')||
    e.quality?.gate!=='G2'||e.quality?.seoIndexable!==true||
    e.quality?.geometryTopologyVerified!==true||e.quality?.areaNotVerified||
    e.quality?.reviewRequired||e.quality?.slugRequiresReview||
    e.quality?.elevationConflictReview||e.quality?.wikiAltitudeDisagreementReview||
    !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(e.slug||'')||
    !/^[1-9]\d*$/.test(e.sourceIds?.geonames||'')||
    !/^Q[1-9]\d*$/.test(e.sourceIds?.wikidata||'')||
    !/^(way|relation)\/[1-9]\d*$/.test(e.sourceIds?.osm||'')||
    e.sourceIds?.wikidataVerifiedBy!=='P1566+P625'||
    e.sourceIds?.osmVerifiedBy!=='P1566_P625_and_exact_OSM_QID_or_GeoNames_ID'||
    !Number.isFinite(e.geo?.point?.lat)||!Number.isFinite(e.geo?.point?.lng)||
    e.geo?.area?.type!=='MultiPolygon'||!e.geo?.area?.coordinates?.length||
    e.geo?.areaSourceUrl!=='https://www.openstreetmap.org/'+e.sourceIds?.osm||
    e.geo?.areaMethod!=='osm_out_geom_multipolygon'||
    e.facts?.osmMappedWaterSurfaceKm2?.method!=='derived'||
    e.facts?.osmMappedWaterSurfaceKm2?.unit!=='km2'||
    e.facts?.osmMappedWaterSurfaceKm2?.licence!=='ODbL 1.0'||
    typeof e.facts?.osmMappedWaterSurfaceKm2?.value!=='number'||
    !Number.isFinite(e.facts.osmMappedWaterSurfaceKm2.value)||
    e.facts.osmMappedWaterSurfaceKm2.value<=0||
    typeof e.facts?.elevationM?.value!=='number'||
    !Number.isFinite(e.facts.elevationM.value)||
    typeof e.description!=='string'||e.description.length<120)
    return false;
  return !!e.media?.some(m=>m.kind==='photo'&&m.subjectVerified===true&&
    m.reuseAllowed===true&&!!m.licence&&!!m.author&&
    m.sourceId==='wikidata:'+e.sourceIds.wikidata+':P18'&&
    m.sourceUrl?.startsWith('https://commons.wikimedia.org/')&&
    m.url?.startsWith('https://'))&&
    !!e.textSources?.some(t=>t.text?.length>=120&&
      t.sourceId?.startsWith('wikipedia:it:')&&
      t.sourceUrl?.startsWith('https://it.wikipedia.org/')&&
      t.licence==='CC BY-SA 4.0');
}

export function verifiedNaturalLakes(input:unknown):NaturalLakeDataset{
  if(!input||typeof input!=='object')return EMPTY;
  const data=input as {releaseChannel?:string;isPublished?:boolean;
    generatedAt?:string;entities?:NaturalLake[]};
  if(data.releaseChannel!=='NATURAL_FEATURES_LAKES_G2'||
    data.isPublished!==true||!Array.isArray(data.entities))return EMPTY;
  const ids=new Set<string>(),slugs=new Set<string>(),qids=new Set<string>(),
    osms=new Set<string>(),gns=new Set<string>();
  for(const e of data.entities){
    if(!isValid(e)||ids.has(e.id)||slugs.has(e.slug)||qids.has(e.sourceIds.wikidata)||
       gns.has(e.sourceIds.geonames)||osms.has(e.sourceIds.osm))
      return EMPTY; // fail closed, never duplicate lake pins or canonical URLs
    ids.add(e.id);slugs.add(e.slug);qids.add(e.sourceIds.wikidata);
    gns.add(e.sourceIds.geonames);osms.add(e.sourceIds.osm);
  }
  return {generatedAt:data.generatedAt||null,
    features:[...data.entities].sort((a,b)=>a.name.localeCompare(b.name,'it'))};
}
export function loadNaturalLakes():Promise<NaturalLakeDataset>{
  pending ??=fetch(DATA_BASE+'/atlas/natural-lakes-v1.json')
    .then(async r=>r.ok?verifiedNaturalLakes(await r.json()):EMPTY)
    .catch(()=>{pending=null;return EMPTY;});
  return pending;
}
export function naturalLakeHref(slug:string):string{
  return import.meta.env.BASE_URL+'laghi/'+encodeURIComponent(slug)+'/';
}
export const naturalLakeLabel=(x:Pick<NaturalLake,'subtype'>)=>
  x.subtype==='lake'?'Lago alpino':'Invaso artificiale';
