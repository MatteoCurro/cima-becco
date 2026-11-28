import type { AlpinePlace, AlpinePlacesDataset } from './alpinePlaces';

type PublishedSettlement = {
  id:string;kind:string;subtype:string;name:string;slug:string;
  slugAliases?:string[];
  sourceIds:Record<string,string>;
  geo:{point?:{lat:number;lng:number}|null;sourceUrl?:string};
  facts?:AlpinePlace['facts'];
  relations?:AlpinePlace['relations'];
  media?:AlpinePlace['media'];
  aliases?:AlpinePlace['aliases'];
  administrativeHierarchy?:AlpinePlace['administrativeHierarchy'];
  connectedPeople?:AlpinePlace['connectedPeople'];
  description?:string;shortSummary?:string;
  textSources?:AlpinePlace['textSources'];
  quality:{gate:string;seoIndexable:boolean;reviewRequired?:boolean};
};
type Release = {releaseChannel:string;isPublished:boolean;entities:PublishedSettlement[]};

export function settlementAsAlpinePlace(entity:PublishedSettlement):AlpinePlace|null {
  const point=entity.geo?.point;
  const photo=entity.media?.find(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&
    m.url?.startsWith('https://')&&m.sourceUrl?.startsWith('https://')&&m.licence&&m.author);
  if(entity.kind!=='settlement'||entity.quality?.gate!=='G2'||!entity.quality.seoIndexable||
     !entity.id||!entity.name||!entity.slug||!point||
     !Number.isFinite(point.lat)||!Number.isFinite(point.lng)||!entity.sourceIds?.wikidata||
     !photo||!entity.description||entity.description.trim().length<120) return null;
  const osm=entity.sourceIds.osm;
  const osmUrl=osm&&/^(node|way|relation)\/[1-9][0-9]*$/.test(osm)
    ?'https://www.openstreetmap.org/'+osm
    :'https://www.openstreetmap.org/#map=13/'+point.lat+'/'+point.lng;
  const elevation=entity.facts?.elevationM?.value;
  return {
    id:entity.id,slug:entity.slug,name:entity.name,kind:'borgo',
    subtype:entity.subtype,slugAliases:entity.slugAliases||[],
    lat:point.lat,lng:point.lng,osmUrl,
    sourceIds:entity.sourceIds,geo:entity.geo as AlpinePlace['geo'],
    facts:entity.facts,relations:entity.relations,media:entity.media,
    aliases:entity.aliases,administrativeHierarchy:entity.administrativeHierarchy,
    connectedPeople:entity.connectedPeople,
    description:entity.description,shortSummary:entity.shortSummary,
    textSources:entity.textSources,
    elevationM:typeof elevation==='number'?elevation:undefined,
    photo:{url:photo.url,sourceUrl:photo.sourceUrl,author:photo.author||'',license:photo.licence},
  };
}

/** Solo G2 entrano nel catalogo UI e SEO, e sostituiscono l'identità OSM.
 * G0/G1 rimangono archivio raw in staging, non migliaia di schede povere.
 */
export function mergeSettlementRelease(base:AlpinePlacesDataset,raw:unknown):AlpinePlacesDataset {
  const release=raw as Partial<Release>|null;
  if(!release||release.releaseChannel!=='ISTAT21_OSM_SETTLEMENTS'||
      release.isPublished!==true||!Array.isArray(release.entities))return base;
  const candidates=release.entities.map(settlementAsAlpinePlace)
    .filter((x):x is AlpinePlace=>Boolean(x));
  const osmIds=new Set(candidates.map(x=>x.sourceIds?.osm).filter(Boolean));
  const qids=new Set(candidates.map(x=>x.sourceIds?.wikidata).filter(Boolean));
  const old=base.places.filter(p=>{
    if(p.kind!=='borgo'||p.subtype==='italian_municipality')return true;
    const legacyId=p.osmUrl?.replace('https://www.openstreetmap.org/','');
    return !(legacyId&&osmIds.has(legacyId)) && !(p.wikidata&&qids.has(p.wikidata));
  });
  const unique=new Set(old.map(x=>x.slug));
  const fresh=candidates.filter(p=>{if(unique.has(p.slug))return false;unique.add(p.slug);return true;});
  return {...base,places:[...old,...fresh]};
}
