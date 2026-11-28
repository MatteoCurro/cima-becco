import type { Venue, VenuePhoto } from '../types';

export interface PublishedSummit {
  id: string;
  kind: 'summit';
  subtype: string;
  slug: string;
  slugAliases: string[];
  name: string;
  sourceIds: Record<string, string>;
  geo: { point: { lat: number; lng: number }; sourceUrl?: string };
  facts?: Venue['facts'];
  relations?: Venue['relations'];
  media?: Venue['media'];
  textSources?: Venue['textSources'];
  aliases?: Venue['aliases'];
  localNames?: Venue['localNames'];
  shortSummary?: string;
  administrativeHierarchy?: Venue['administrativeHierarchy'];
  checkedAt?: string;
  updatedAt?: string;
  quality: { gate: string; seoIndexable: boolean; reviewRequired?: boolean; slugRequiresReview?: boolean };
}

function validSummit(e: PublishedSummit): boolean {
  const ids=e?.sourceIds;
  if(e?.kind!=='summit'||e?.quality?.gate!=='G2'||e.quality?.seoIndexable!==true||
     e.quality?.reviewRequired||e.quality?.slugRequiresReview||!e.id||!e.slug||
     !/^[1-9]\d*$/.test(ids?.geonames||'')||!/^Q[1-9]\d*$/.test(ids?.wikidata||'')||
     ids.wikidataVerifiedBy!=='P1566+P625'||!e.geo?.point||!Array.isArray(e.slugAliases)||
     !Array.isArray(e.media)||!Array.isArray(e.textSources))return false;
  return e.media.some(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&
     !!m.sourceUrl&&!!m.licence&&!!m.author) &&
    e.textSources.some(t=>!!t.text&&!!t.licence&&!!t.sourceUrl);
}

/** Only G2, source-verified records are allowed to reach map/details. */
export function summitByGeonames(release: unknown): Map<string, PublishedSummit> {
  const map=new Map<string, PublishedSummit>();
  if(!release||typeof release!=='object')return map;
  const doc=release as {releaseChannel?:string;isPublished?:boolean;entities?:PublishedSummit[]};
  if(doc.releaseChannel!=='GEONAMES_SUMMITS_G2'||doc.isPublished!==true||!Array.isArray(doc.entities))
    return map;
  const qids=new Set<string>();
  for(const e of doc.entities) {
    if(!validSummit(e))continue;
    const gn=e.sourceIds.geonames,qid=e.sourceIds.wikidata;
    if(map.has(gn)||qids.has(qid))return new Map();
    map.set(gn,e);
    qids.add(qid);
  }
  return map;
}

function distKm(a:{lat:number;lng:number},b:{lat:number;lng:number}):number{
  const lat=(a.lat-b.lat)*Math.PI/180;
  const lng=(a.lng-b.lng)*Math.PI/180;
  return 6371.009*Math.hypot(lat,lng*Math.cos(a.lat*Math.PI/180));
}

/** Reuse the existing 'gn...tile' slug. Never mint a second map marker. */
export function withVerifiedSummit(venue:Venue, summits:Map<string,PublishedSummit>):Venue{
  const match=/^gn([1-9]\d+)-m?\d+xm?\d+$/.exec(venue.slug);
  if(!match||venue.type!=='hill')return venue;
  const verified=summits.get(match[1]);
  if(!verified||!verified.slugAliases.includes(venue.slug)||
     distKm(verified.geo.point,{lat:venue.lat,lng:venue.lng})>2)return venue;
  const media=verified.media?.find(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed);
  const curatedPhoto:VenuePhoto|undefined=media?.url?{
    file:media.url,credit:media.author||null,
    license:media.licence,sourceUrl:media.sourceUrl,
    source:'Wikimedia Commons'
  }:undefined;
  return {...venue,
    id:verified.id, subtype:verified.subtype,
    sourceIds:verified.sourceIds,
    shortSummary:verified.shortSummary,
    aliases:verified.aliases,
    localNames:verified.localNames,
    textSources:verified.textSources,
    media:verified.media,
    facts:verified.facts,
    relations:verified.relations,
    administrativeHierarchy:verified.administrativeHierarchy,
    checkedAt:verified.checkedAt,
    updatedAt:verified.updatedAt,
    geo:{point:verified.geo.point,method:'reported',sourceUrl:verified.geo.sourceUrl},
    ...(curatedPhoto?{photo:curatedPhoto}:{}),
  };
}
