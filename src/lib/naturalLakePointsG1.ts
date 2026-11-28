import {DATA_BASE} from './venues';
import type {AtlasFact,AtlasMedia} from './atlasDossier';

export interface LakeIdentifiedG1 {
  id:string;
  name:string;
  slug:string;
  subtype:'lake';
  aliases:{value:string;language:string|null;sourceUrl:string}[];
  localNames:{value:string;language:string;sourceUrl:string}[];
  sourceIds:{
    geonames:string;wikidata:string;wikidataVerifiedBy:'P1566+P625';
    osm?:string;osmVerifiedBy?:string;
  };
  geo:{
    point:{lat:number;lng:number};
    method:'geonames_point';
    pointSourceUrl:string;
    area:{type:'MultiPolygon';coordinates:number[][][][]}|null;
    areaSourceUrl:string|null;
    areaMethod:string|null;
  };
  facts:Record<string,AtlasFact>;
  media:AtlasMedia[];
  textSources:{kind:string;sourceId:string;sourceUrl:string;licence:string;text:string}[];
  description:string|null;
  quality:{
    gate:'G1';seoIndexable:false;sourcePointVerified:true;
    wikidataIdentityVerified:true;
    hasVerifiedShoreline:boolean;needsAreaGeometryReview:boolean;
    photoSourceVerified:boolean;textLicenseVerified:boolean;
  };
  identitySource:'exact_P1566_P625_one_to_one';
  checkedAt:string;
}
export interface LakeIdentifiedG1Dataset {
  entities:LakeIdentifiedG1[];
  counts:{profiles:number;pointOnly:number;withOsmGeometry:number;
    withVerifiedP18:number;withVerifiedItwiki:number};
  sourceG1Candidates:number;
  excludedCanonicalG2:number;
}
const EMPTY:LakeIdentifiedG1Dataset={
  entities:[],counts:{profiles:0,pointOnly:0,withOsmGeometry:0,
    withVerifiedP18:0,withVerifiedItwiki:0},
  sourceG1Candidates:0,excludedCanonicalG2:0,
};
let pending:Promise<LakeIdentifiedG1Dataset>|null=null;
const slugRe=/^[a-z0-9]+(?:-[a-z0-9]+)*$/;
const gnRe=/^[1-9]\d*$/;
const qidRe=/^Q[1-9]\d*$/;
const validPoint=(p:LakeIdentifiedG1['geo']['point'])=>
  Number.isFinite(p?.lat)&&Number.isFinite(p?.lng)&&
  p.lat>=35&&p.lat<=48&&p.lng>=6&&p.lng<=20;
const vCount=(x:unknown):x is number=>typeof x==='number'&&
  Number.isInteger(x)&&x>=0;

export function verifiedIdentifiedLakePoints(raw:unknown):LakeIdentifiedG1Dataset {
  if(!raw||typeof raw!=='object')return EMPTY;
  const v=raw as Record<string,unknown>;
  if(v.releaseChannel!=='NATURAL_LAKE_IDENTIFIED_PROFILES_G1_V1'||
     v.isCanonicalPublished!==false||v.seoIndexable!==false||
     v.noindexFollow!==true||v.crossSourceWfsMerges!==0||
     v.g2Duplicated!==0||!vCount(v.sourceG1Candidates)||
     !vCount(v.excludedCanonicalG2)||!Array.isArray(v.entities)||
     !v.counts||typeof v.counts!=='object')return EMPTY;
  const counts=v.counts as LakeIdentifiedG1Dataset['counts'];
  if(!Object.values(counts).every(vCount)||counts.profiles!==v.entities.length||
      counts.pointOnly+counts.withOsmGeometry!==counts.profiles||
      counts.profiles+v.excludedCanonicalG2>v.sourceG1Candidates)return EMPTY;
  const rows=v.entities as LakeIdentifiedG1[];
  const used=new Set<string>(),gns=new Set<string>(),qids=new Set<string>();
  let withArea=0,withPhoto=0,withText=0;
  for(const e of rows){
    const g=e?.geo,ids=e?.sourceIds,quality=e?.quality;
    if(!e||e.subtype!=='lake'||!slugRe.test(e.slug||'')||
       typeof e.name!=='string'||e.name.trim().length<3||
       !gnRe.test(ids?.geonames||'')||!qidRe.test(ids?.wikidata||'')||
       ids.wikidataVerifiedBy!=='P1566+P625'||
       e.identitySource!=='exact_P1566_P625_one_to_one'||
       !validPoint(g?.point)||g?.method!=='geonames_point'||
       g.pointSourceUrl!=='https://www.geonames.org/'+ids.geonames+'/'||
       quality?.gate!=='G1'||quality.seoIndexable!==false||
       quality.sourcePointVerified!==true||
       quality.wikidataIdentityVerified!==true||
       quality.hasVerifiedShoreline!==Boolean(g.area)||
       quality.needsAreaGeometryReview!==!g.area||
       !Array.isArray(e.media)||!Array.isArray(e.textSources)||
       quality.photoSourceVerified!==Boolean(e.media.length)||
       quality.textLicenseVerified!==Boolean(e.textSources.length)||
       used.has(e.slug)||gns.has(ids.geonames)||qids.has(ids.wikidata))
       return EMPTY;
    used.add(e.slug);gns.add(ids.geonames);qids.add(ids.wikidata);
    if(g.area){
      const area=e.facts?.osmMappedWaterSurfaceKm2;
      if(g.area.type!=='MultiPolygon'||!g.area.coordinates?.length||
         !/^(?:way|relation)\/[1-9]\d*$/.test(ids.osm||'')||
         ids.osmVerifiedBy!=='P1566_P625_and_exact_OSM_QID_or_GeoNames_ID'||
         g.areaSourceUrl!=='https://www.openstreetmap.org/'+ids.osm||
         area?.unit!=='km2'||area?.licence!=='ODbL 1.0'||area?.method!=='derived'||
         area?.sourceId!=='osm:'+ids.osm+':geometry'||typeof area?.value!=='number'||
         !Number.isFinite(area.value)||area.value<=0)return EMPTY;
      withArea++;
    }else if(g.areaSourceUrl!==null||ids.osm||e.facts?.osmMappedWaterSurfaceKm2) {
      return EMPTY;
    }
    for(const m of e.media){
      if(m.kind!=='photo'||m.sourceId!=='wikidata:'+ids.wikidata+':P18'||
         m.subjectVerified!==true||m.reuseAllowed!==true||
         m.subjectMethod!=='verified_GeoNames_P1566_Wikidata_P625_P18'||
         !m.author||!m.licence||
         !m.sourceUrl?.startsWith('https://commons.wikimedia.org/wiki/File:')||
         !m.url?.startsWith('https://'))return EMPTY;
    }
    for(const t of e.textSources){
      if(t.licence!=='CC BY-SA 4.0'||t.text?.length<120||
         t.kind!=='source_excerpt_not_original_editorial'||
         !t.sourceId?.startsWith('wikipedia:it:')||
         !t.sourceUrl?.startsWith('https://it.wikipedia.org/wiki/'))return EMPTY;
    }
    if(e.media.length)withPhoto++;
    if(e.textSources.length)withText++;
  }
  if(counts.withOsmGeometry!==withArea||
     counts.withVerifiedP18!==withPhoto||
     counts.withVerifiedItwiki!==withText)return EMPTY;
  return {entities:rows,counts,sourceG1Candidates:v.sourceG1Candidates as number,
    excludedCanonicalG2:v.excludedCanonicalG2 as number};
}
export function loadIdentifiedLakePoints():Promise<LakeIdentifiedG1Dataset>{
  pending??=fetch(DATA_BASE+'/atlas/natural-lake-points-g1-v1.json')
    .then(async response=>response.ok?
      verifiedIdentifiedLakePoints(await response.json()):EMPTY)
    .catch(()=>{pending=null;return EMPTY});
  return pending;
}
export const lakeIdentifiedHref=(e:LakeIdentifiedG1):string=>
  import.meta.env.BASE_URL+'laghi/identificati/'+encodeURIComponent(e.slug)+'/';
export const lakeIdentifiedDisplayName=(e:LakeIdentifiedG1):string=>
  e.localNames.find(x=>x.language==='it')?.value||e.name;
