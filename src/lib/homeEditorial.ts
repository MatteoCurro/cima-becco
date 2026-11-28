/** A tiny, already-published projection, never a second catalogue or importer. */
export interface HomeEditorialPlace {
  kind:'town'|'refuge'|'bivacco'|'summit';
  id:string;slug:string;name:string;href:string;lat:number;lng:number;
  cover:{url:string;sourceUrl:string;author:string;licence:string;sourceId:string|null}|null;
  text:string;elevationM:number|null;factsCount:number;
  sourceIds:Record<string,string>;
  distanceToRouteKm?:number;relation?:'mapped_route'|'nearby';
}
export interface HomeEditorialTerritory {
  key:string;title:string;location:string;center:{lat:number;lng:number};
  town:HomeEditorialPlace;refuge:HomeEditorialPlace;
  bivacco:HomeEditorialPlace|null;summit:HomeEditorialPlace|null;
  person:{name:string;role:string;portrait:string|null;relation:string;
    description:string;href:string;placeName:string;sourceUrl:string;qid:string}|null;
  route:{kind:'route';name:string;slug:string;href:string;distanceKm:number;
    gainM:number|null;difficulty:string|null;activity:string;trailRef:string|null};
  score:number;
}
export interface HomeEditorialFeed {
  schemaVersion:'1.0';generatedAt:string;policy:'published-source-only';
  territories:HomeEditorialTerritory[];
  discovery:Record<'town'|'refuge'|'bivacco'|'summit',HomeEditorialPlace[]>;
}
export type HomeEditorialKind=keyof HomeEditorialFeed['discovery'];

export function romeDay(date:Date):{key:string;ordinal:number;label:string} {
  const parts=new Intl.DateTimeFormat('en-GB',{timeZone:'Europe/Rome',
    year:'numeric',month:'2-digit',day:'2-digit'}).formatToParts(date);
  const at=(type:string)=>parts.find(p=>p.type===type)?.value||'01';
  const year=Number(at('year')),month=Number(at('month')),day=Number(at('day'));
  return {
    key:[year,String(month).padStart(2,'0'),String(day).padStart(2,'0')].join('-'),
    ordinal:Math.floor(Date.UTC(year,month-1,day)/86400000),
    label:new Intl.DateTimeFormat('it-IT',{timeZone:'Europe/Rome',
      day:'numeric',month:'long',year:'numeric'}).format(date),
  };
}
export function homeTerritoryForDay(feed:HomeEditorialFeed,date:Date):HomeEditorialTerritory|null {
  const candidates=feed.territories.filter(item=>item.town?.href && item.refuge?.href &&
    item.route?.href && item.route?.slug);
  if(!candidates.length)return null;
  const index=((romeDay(date).ordinal%candidates.length)+candidates.length)%candidates.length;
  return candidates[index];
}
/** Category variety without duplicating the territory's featured entities. */
export function homeDiscoveryForDay(feed:HomeEditorialFeed,date:Date,territory:HomeEditorialTerritory|null) {
  const exclude=new Set([territory?.town?.href,territory?.refuge?.href,
    territory?.bivacco?.href,territory?.summit?.href].filter(Boolean));
  const daily=romeDay(date).ordinal;
  const kinds:HomeEditorialKind[]=['refuge','bivacco','town','summit'];
  return kinds.map(kind=>{
    const items=(feed.discovery?.[kind]||[]).filter(x=>x?.href&&x?.cover?.url&&!exclude.has(x.href));
    if(!items.length)return {kind,items:[] as HomeEditorialPlace[]};
    const start=((daily%items.length)+items.length)%items.length;
    return {kind,items:Array.from({length:Math.min(2,items.length)},(_,i)=>items[(start+i)%items.length])};
  }).filter(group=>group.items.length>0);
}
export function validHomeEditorialFeed(raw:unknown):raw is HomeEditorialFeed {
  if(!raw || typeof raw!=='object')return false;
  const feed=raw as Partial<HomeEditorialFeed>;
  return feed.schemaVersion==='1.0'&&feed.policy==='published-source-only'&&
    Array.isArray(feed.territories)&&!!feed.discovery&&
    ['town','refuge','bivacco','summit'].every(k=>Array.isArray(feed.discovery?.[k as HomeEditorialKind]));
}
