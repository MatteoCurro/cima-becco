import { DATA_BASE } from './venues';
import type { AtlasEntityMetadata, AtlasFact, AtlasGeo, AtlasMedia } from './atlasDossier';

/** Shared atlas data contract; source-specific IDs are not public URLs. */
export interface NaturalPass extends AtlasEntityMetadata {
  id: string;
  name: string;
  displayName?: string;
  slug: string;
  kind: 'natural_feature';
  subtype: 'mountain_pass' | 'saddle';
  geo: AtlasGeo & {point:{lat:number;lng:number}};
  sourceIds: Record<string,string>;
  facts: Record<string,AtlasFact>;
  media: AtlasMedia[];
  description: string;
  quality: {
    gate:'G2';
    seoIndexable:true;
    reviewRequired?:false;
    slugRequiresReview?:false;
    elevationConflictReview?:false;
    wikiAltitudeDisagreementReview?:false;
  };
}
export interface NaturalPassDataset {
  generatedAt:string|null;
  features: NaturalPass[];
}
const EMPTY:NaturalPassDataset={generatedAt:null,features:[]};
let pending:Promise<NaturalPassDataset>|null=null;

function qualified(row:NaturalPass):boolean{
  if(!row||row.kind!=='natural_feature'||
    (row.subtype!=='mountain_pass'&&row.subtype!=='saddle')||
    row.quality?.gate!=='G2'||row.quality?.seoIndexable!==true||
    row.quality?.reviewRequired||row.quality?.slugRequiresReview||
    row.quality?.elevationConflictReview||row.quality?.wikiAltitudeDisagreementReview||
    !/^[1-9]\d*$/.test(row.sourceIds?.geonames||'')||
    !/^Q[1-9]\d*$/.test(row.sourceIds?.wikidata||'')||
    row.sourceIds?.wikidataVerifiedBy!=='P1566+P625'||
    !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(row.slug||'')||
    !Number.isFinite(row.geo?.point?.lat)||
    !Number.isFinite(row.geo?.point?.lng)||
    typeof row.facts?.elevationM?.value!=='number'||
    !Number.isFinite(row.facts.elevationM.value)||
    !row.description||row.description.length<120)return false;
  return Boolean(row.media?.some(m=>
    m.kind==='photo'&&m.subjectVerified===true&&m.reuseAllowed===true&&
    m.subjectMethod==='verified_GeoNames_P1566_Wikidata_P625_P18'&&
    m.sourceId==='wikidata:'+row.sourceIds.wikidata+':P18'&&
    !!m.author&&!!m.licence&&
    m.sourceUrl?.startsWith('https://commons.wikimedia.org/')&&
    m.url?.startsWith('https://')
  )) && Boolean(row.textSources?.some(t=>
    t.licence==='CC BY-SA 4.0'&&
    t.sourceId?.startsWith('wikipedia:it:')&&
    t.sourceUrl?.startsWith('https://it.wikipedia.org/')&&
    !!t.text&&t.text.length>=120
  ));
}

/** Invalid provider release, duplicate QID or suspect rows fail closed. */
export function verifiedNaturalPasses(raw:unknown):NaturalPassDataset{
  if(!raw||typeof raw!=='object')return EMPTY;
  const doc=raw as {releaseChannel?:string;isPublished?:boolean;
    generatedAt?:string;entities?:NaturalPass[]};
  if(doc.releaseChannel!=='NATURAL_FEATURES_PASSES_G2'||
     doc.isPublished!==true||!Array.isArray(doc.entities))return EMPTY;
  const found=new Set<string>(),slugs=new Set<string>(),qids=new Set<string>(),gns=new Set<string>();
  for(const row of doc.entities){
    if(!qualified(row)||found.has(row.id)||slugs.has(row.slug)||
       qids.has(row.sourceIds.wikidata)||gns.has(row.sourceIds.geonames))return EMPTY;
    found.add(row.id);slugs.add(row.slug);qids.add(row.sourceIds.wikidata);gns.add(row.sourceIds.geonames);
  }
  return {
    generatedAt:doc.generatedAt||null,
    features:[...doc.entities].sort((a,b)=>a.name.localeCompare(b.name,'it')),
  };
}

/** Fetch only on /passi/ routes, never on the landing page or map viewport. */
export function loadNaturalPasses():Promise<NaturalPassDataset>{
  pending ??=fetch(DATA_BASE+'/atlas/natural-features-v1.json')
    .then(async r=>r.ok?verifiedNaturalPasses(await r.json()):EMPTY)
    .catch(()=>{pending=null;return EMPTY;});
  return pending;
}
export function naturalPassUrl(slug:string):string{
  return import.meta.env.BASE_URL+'passi/'+encodeURIComponent(slug)+'/';
}
export const naturalPassLabel=(e:Pick<NaturalPass,'subtype'>)=>
  e.subtype==='saddle'?'Sella o forcella':'Passo alpino';
