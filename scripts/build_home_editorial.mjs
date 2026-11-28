/**
 * Presentation-only home feed, derived AFTER build_seo.mjs from already
 * published catalogues and existing permalink pages. This is not an importer.
 * Never promote G0/G1, infer a technical route or invent a biography URL.
 */
import { existsSync, readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { atlasCanonicalPath } from '../src/lib/placePermalinks.js';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..');
const DIST = join(ROOT, 'dist');
const DATA = join(ROOT, 'public', 'data');
const read = path => existsSync(path) ? JSON.parse(readFileSync(path, 'utf8')) : null;
const release = name => read(join(DATA, 'atlas', name + '-v1.json'));
const publishedPath = href => /^\/[a-z0-9/%-]+$/i.test(href) &&
  existsSync(join(DIST, href.slice(1), 'index.html'));
const safe = value => typeof value === 'string' ? value.trim() : '';
const validPoint = value => Number.isFinite(value?.lat) && Number.isFinite(value?.lng) &&
  Math.abs(value.lat) <= 90 && Math.abs(value.lng) <= 180;
const validName = name => safe(name).length >= 3 && !/^[\d\s.,m-]+$/i.test(name);
const richness = item => (safe(item.description || item.text).length >= 110 ? 4 : 0) +
  Math.min(7, item.factsCount ?? Object.values(item.facts || {}).filter(f => f?.value != null).length) +
  (item.cover || photo(item) ? 4 : 0);
const excerpt = value => {
  const s = safe(value).replace(/\s+/g, ' ');
  if (s.length <= 195) return s;
  return s.slice(0, 193).replace(/\s+\S*$/, '') + '…';
};
function photo(entity) {
  const m = (entity.media || []).find(m => m.kind === 'photo' && m.subjectVerified === true &&
    m.reuseAllowed === true && safe(m.url).startsWith('https://') &&
    safe(m.sourceUrl).startsWith('https://') && m.licence && m.author);
  return m ? { url:m.url, sourceUrl:m.sourceUrl, author:m.author,
    licence:m.licence, sourceId:m.sourceId || null } : null;
}
function item(kind, entity, href, { gateRequired = false } = {}) {
  const p = entity.geo?.point;
  if (!validPoint(p) || !validName(entity.name) || !safe(entity.slug) ||
    !publishedPath(href) || entity.quality?.reviewRequired ||
    (entity.quality?.gate && entity.quality.gate !== 'G2') ||
    (gateRequired && (entity.quality?.gate !== 'G2' || entity.quality?.seoIndexable !== true))) return null;
  const cover = photo(entity);
  const record = {
    kind, id:entity.id || entity.slug, slug:entity.slug, name:entity.name, href,
    lat:p.lat, lng:p.lng, cover, text:excerpt(entity.description || entity.shortSummary),
    elevationM: typeof entity.facts?.elevationM?.value === 'number' ? entity.facts.elevationM.value :
      typeof entity.facts?.quotaCentroM?.value === 'number' ? entity.facts.quotaCentroM.value : null,
    factsCount:Object.values(entity.facts || {}).filter(f => f?.value != null).length,
    sourceIds:entity.sourceIds || {},
  };
  if (!cover || richness(record) < 8) return null;
  return record;
}
const places = { town:[], refuge:[], bivacco:[], summit:[] };
const townRelease = release('municipalities');
if (townRelease?.isPublished && townRelease?.releaseChannel === 'ISTAT_DAIT_MUNICIPALITIES') {
  for (const e of townRelease.entities || []) {
    if (e.kind !== 'municipality' || e.subtype !== 'italian_municipality') continue;
    const x = item('town', e, '/comuni/' + encodeURIComponent(e.slug) + '/', {gateRequired:true});
    if (!x) continue;
    const person = (e.connectedPeople || []).find(p => p.verified === true && p.category === 'montagna' &&
      safe(p.qid).match(/^Q[1-9]\d*$/) && safe(p.sourceUrl).startsWith('https://') &&
      safe(p.sourceId) && safe(p.role) && safe(p.biography).length >= 110);
    if (person) {
      const portrait = person.portrait?.portraitCandidate === true &&
        person.portrait.subjectVerified === true && person.portrait.reuseAllowed === true &&
        safe(person.portrait.url).startsWith('https://') ? person.portrait.url : null;
      x.person = { name:person.name, role:person.role, portrait,
        relation:person.relationType, description:excerpt(person.biography),
        sourceUrl:person.sourceUrl, qid:person.qid };
    }
    places.town.push(x);
  }
}
const settlementRelease = release('settlements');
if (settlementRelease?.isPublished && settlementRelease?.releaseChannel === 'ISTAT21_OSM_SETTLEMENTS') {
  for (const e of settlementRelease.entities || []) {
    if (e.kind !== 'settlement') continue;
    const x = item('town', e, '/borghi/' + encodeURIComponent(e.slug) + '/', {gateRequired:true});
    if (x) places.town.push(x);
  }
}
const refugeRelease = release('refuges');
if (refugeRelease?.releaseChannel === 'OSM_CAI_REFUGES' &&
  refugeRelease?.schemaVersion === '1.1') {
  for (const e of refugeRelease.entities || []) {
    if (e.kind !== 'refuge' || !e.sourceIds?.cai && !e.sourceIds?.osm) continue;
    const x = item('refuge', e, atlasCanonicalPath({...e,kind:'rifugio'}));
    if (x) places.refuge.push(x);
  }
}
console.log('Home source audit: rifugi', (refugeRelease?.entities||[]).length,
  (refugeRelease?.entities||[]).slice(0,2).map(e=>({
    name:e.name,kind:e.kind,slug:e.slug,geo:!!e.geo?.point,
    photoCount:e.media?.filter(m=>m.kind==='photo').length,
    authors:e.media?.filter(m=>m.kind==='photo').slice(0,1).map(m=>Boolean(m.author)),
    textLength:safe(e.description||e.shortSummary).length,
    factsCount:Object.keys(e.facts||{}).length,
    published:publishedPath(atlasCanonicalPath({...e,kind:'rifugio'})),
    sourceIds:e.sourceIds
  })));
const sheltersRelease = release('shelters');
if (sheltersRelease?.releaseChannel === 'CAI_OSM_BIVOUACS_SHELTERS' &&
  sheltersRelease?.schemaVersion === '2.0') {
  for (const e of sheltersRelease.entities || []) {
    if (!['bivouac','shelter'].includes(e.kind) ||
      !e.sourceIds?.cai && !e.sourceIds?.osm) continue;
    const x = item('bivacco', e, atlasCanonicalPath({...e,kind:'bivacco'}));
    if (x) places.bivacco.push(x);
  }
}
console.log('Home source audit: bivacchi', (sheltersRelease?.entities||[]).length,
  (sheltersRelease?.entities||[]).slice(0,2).map(e=>({
    name:e.name,kind:e.kind,slug:e.slug,geo:!!e.geo?.point,
    photoCount:e.media?.filter(m=>m.kind==='photo').length,
    authors:e.media?.filter(m=>m.kind==='photo').slice(0,1).map(m=>Boolean(m.author)),
    textLength:safe(e.description||e.shortSummary).length,
    factsCount:Object.keys(e.facts||{}).length,
    published:publishedPath(atlasCanonicalPath({...e,kind:'bivacco'})),
    sourceIds:e.sourceIds
  })));
const summitRelease = release('summits');
if (summitRelease?.isPublished && summitRelease?.releaseChannel === 'GEONAMES_SUMMITS_G2') {
  for (const e of summitRelease.entities || []) {
    if (e.kind !== 'summit' || e.quality?.slugRequiresReview ||
      e.sourceIds?.wikidataVerifiedBy !== 'P1566+P625' ||
      !e.textSources?.some(t => t.text && t.sourceUrl && t.licence)) continue;
    const x = item('summit', e, '/cime/' + encodeURIComponent(e.slug) + '/', {gateRequired:true});
    if (x) places.summit.push(x);
  }
}
const rad = Math.PI/180;
function distKm(a,b) {
  const dlat=(b.lat-a.lat)*rad, dlng=(b.lng-a.lng)*rad;
  const h=Math.sin(dlat/2)**2+Math.cos(a.lat*rad)*Math.cos(b.lat*rad)*Math.sin(dlng/2)**2;
  return 12742.0176*Math.asin(Math.min(1,Math.sqrt(h)));
}
function routeDistanceKm(place,route) {
  // Short local planar projection of each segment; geographical proximity only.
  const cos=Math.cos(place.lat*rad), p=route.coordinates;
  let best=Infinity;
  for (let i=1;i<p.length;i++) {
    const a=p[i-1],b=p[i];
    const ax=(a[0]-place.lng)*111.195*cos,ay=(a[1]-place.lat)*111.195;
    const bx=(b[0]-place.lng)*111.195*cos,by=(b[1]-place.lat)*111.195;
    const dx=bx-ax,dy=by-ay,t=Math.max(0,Math.min(1,-(ax*dx+ay*dy)/(dx*dx+dy*dy||1)));
    best=Math.min(best,Math.hypot(ax+t*dx,ay+t*dy));
  }
  return best;
}
function stopLinked(place,route) {
  const ids=new Set([place.slug,...(place.slugAliases || [])]);
  const osm=safe(place.sourceIds?.osm);
  if (osm.match(/^(node|way|relation)\/\d+$/)) {
    const [kind,id]=osm.split('/');
    ids.add('osm-'+({node:'n',way:'w',relation:'r'}[kind])+'-'+id);
  }
  return (route.stops || []).some(s => ids.has(s.slug) && s.distanceM <= 180 &&
    (s.kind === 'rifugio' || s.kind === 'bivacco'));
}
function closest(kind,route,maxKm,except=new Set()) {
  return places[kind].map(x=>({item:x,km:routeDistanceKm(x,route)}))
    .filter(x=>x.km<=maxKm && !except.has(x.item.id))
    .sort((a,b) => (richness(b.item)-richness(a.item))*0.4 +
      (stopLinked(b.item,route)?6:0) - (stopLinked(a.item,route)?6:0) ||
      a.km-b.km || a.item.slug.localeCompare(b.item.slug))[0] || null;
}
const featured=read(join(DIST,'data','featured-routes.json'))?.routes || [];
const territories=[];
for (const r of featured) {
  if (r.source !== 'curated' || r.held || r.rejected ||
    !Array.isArray(r.coordinates) || r.coordinates.length<2 ||
    !(r.distanceM>=1200 && r.distanceM<=32000) ||
    !publishedPath('/route/'+encodeURIComponent(r.slug)+'/')) continue;
  const town=closest('town',r,25), refuge=closest('refuge',r,17),
    bivacco=closest('bivacco',r,19), summit=closest('summit',r,19);
  if (!town || !refuge || (!bivacco && !summit)) continue;
  const chosen=[town,refuge,bivacco,summit].filter(Boolean);
  const midpoint=r.coordinates[Math.floor(r.coordinates.length/2)];
  const person=town.item.person || null;
  const attach=x=>x && ({...x.item,distanceToRouteKm:Math.round(x.km*10)/10,
    relation:stopLinked(x.item,r)?'mapped_route':'nearby'});
  territories.push({
    key:r.slug, title:'Intorno a ' + town.item.name,
    location:town.item.name,
    center:{lat:midpoint[1],lng:midpoint[0]},
    town:attach(town), refuge:attach(refuge), bivacco:attach(bivacco),
    summit:attach(summit), person:person ? {...person,href:town.item.href,placeName:town.item.name} : null,
    route:{kind:'route',name:r.name,slug:r.slug,href:'/route/'+encodeURIComponent(r.slug)+'/',
      distanceKm:Math.round(r.distanceM/100)/10,
      gainM:r.elevationAvailable!==false?Math.round(r.gainM):null,
      difficulty:r.caiDifficulty || r.sacScale || r.viaFerrataScale || null,
      activity:r.activity || 'hike',trailRef:r.trailRef || null},
    score:chosen.length*10+Number(Boolean(person))*4+
      chosen.reduce((s,x)=>s+richness(x.item)-x.km/6,0),
  });
}
territories.sort((a,b)=>b.score-a.score||a.key.localeCompare(b.key));
const diverse=[], cells=new Set();
for(const t of territories) {
  const cell=Math.floor(t.center.lat*3)+':'+Math.floor(t.center.lng*3);
  if(cells.has(cell))continue;
  cells.add(cell);
  diverse.push(t);
}
const selected=(diverse.length>=4?diverse:territories).slice(0,18);
for(const group of Object.values(places))group.sort((a,b)=>richness(b)-richness(a)||
  a.name.localeCompare(b.name,'it')||a.slug.localeCompare(b.slug));
// Limit payload to editorial metadata. No GPX geometry, full catalogue or raw facts.
const discovery=Object.fromEntries(Object.entries(places).map(([key,group])=>{
  const seen=new Set(),out=[];
  for(const x of group) {
    const cell=Math.floor(x.lat*4)+':'+Math.floor(x.lng*4);
    if(seen.has(cell))continue;
    seen.add(cell);out.push(x);
    if(out.length>=14)break;
  }
  return [key,out];
}));
const feed={schemaVersion:'1.0',generatedAt:new Date().toISOString(),
  policy:'published-source-only',territories:selected,discovery};
if (!selected.length)console.warn('Home: nessun focus territoriale completo; fallback alle categorie G2.');
const output=join(DIST,'data','home-editorial-v1.json');
mkdirSync(dirname(output),{recursive:true});
writeFileSync(output,JSON.stringify(feed));
console.log('Home editoriale:',selected.length,'territori,',Object.fromEntries(
  Object.entries(discovery).map(([key,v])=>[key,v.length])),'categorie');
