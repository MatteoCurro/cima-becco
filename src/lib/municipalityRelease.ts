import type { AlpinePlacesDataset, AlpinePlace } from './alpinePlaces';

type Municipality = {
  id:string;kind:string;subtype:string;slug:string;name:string;
  sourceIds:Record<string,string>;
  geo:{point?:{lat:number;lng:number}|null;sourceUrl?:string};
  facts?:Record<string,{value:unknown;unit?:string}>;
  relations?:AlpinePlace['relations'];media?:AlpinePlace['media'];
  description?:string;shortSummary?:string;quality:{gate:string;seoIndexable:boolean};
  textSources?:{sourceUrl:string;licence:string}[];
  administrativeHierarchy?:AlpinePlace['administrativeHierarchy'];
  aliases?:AlpinePlace['aliases'];
};
export interface MunicipalityRelease {
  schemaVersion:string;releaseChannel:string;isPublished:boolean;entities:Municipality[];
}
export function municipalityAsAlpinePlace(e:Municipality):AlpinePlace|null {
  const point=e.geo?.point;
  if(e.kind!=='municipality'||e.subtype!=='italian_municipality'||!e.quality?.seoIndexable ||
     e.quality.gate!=='G2'||!point||!Number.isFinite(point.lat)||!Number.isFinite(point.lng)||
     !e.slug||!e.name||!e.sourceIds?.istat) return null;
  const photo=e.media?.find(m=>m.kind==='photo' && m.reuseAllowed&&m.subjectVerified&&m.sourceUrl&&m.licence);
  const logo=e.media?.find(m=>m.kind==='logo' && m.reuseAllowed&&m.subjectVerified&&m.sourceUrl&&m.licence);
  return {
    id:e.id,subtype:e.subtype,name:e.name,slug:e.slug,kind:'borgo',
    lat:point.lat,lng:point.lng,
    osmUrl:e.sourceIds.osm?.match(/^(node|way|relation)\/[0-9]+$/)
      ?'https://www.openstreetmap.org/'+e.sourceIds.osm
      :'https://www.openstreetmap.org/#map=12/'+point.lat+'/'+point.lng,
    sourceIds:e.sourceIds,geo:e.geo as AlpinePlace['geo'],
    facts:e.facts as AlpinePlace['facts'],media:e.media,relations:e.relations,
    description:e.description,shortSummary:e.shortSummary,
    aliases:e.aliases,administrativeHierarchy:e.administrativeHierarchy,
    elevationM:typeof e.facts?.quotaCentroM?.value==='number'?e.facts.quotaCentroM.value:
      typeof e.facts?.elevationReportedM?.value==='number'?e.facts.elevationReportedM.value:undefined,
    elevationSource:undefined,
    website:typeof e.facts?.sitoUfficiale?.value==='string'?e.facts.sitoUfficiale.value:undefined,
    photo:photo?{url:photo.url,sourceUrl:photo.sourceUrl,author:photo.author||'',license:photo.licence}:undefined,
    logo:logo?{url:logo.url,sourceUrl:logo.sourceUrl,author:logo.author||'',license:logo.licence}:undefined,
  };
}
/** Adapter UI: preserves canonical kind municipality in source JSON.
 * The existing 'paesi' navigation and map layer are reused as view family. */
export function mergeMunicipalityRelease(base:AlpinePlacesDataset,release:unknown):AlpinePlacesDataset {
  const doc=release as Partial<MunicipalityRelease>|null;
  if(!doc||doc.releaseChannel!=='ISTAT_DAIT_MUNICIPALITIES'||!doc.isPublished||
    !Array.isArray(doc.entities))return base;
  const municipalities=doc.entities.map(municipalityAsAlpinePlace).filter((p):p is AlpinePlace=>Boolean(p));
  const osmMerged=new Set(municipalities.map(m=>m.sourceIds?.osm).filter(Boolean));
  const older=base.places.filter(p=>{
    const id=p.osmUrl?.replace('https://www.openstreetmap.org/','');
    return !(p.kind==='borgo'&&id&&osmMerged.has(id));
  });
  return {...base,places:[...older,...municipalities]};
}
