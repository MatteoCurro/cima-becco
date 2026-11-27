import { atlasCanonicalPath, atlasSlugPart } from './placePermalinks.js';

function distanceKm(a,b) {
  const r=Math.PI/180;
  const x=(b.lat-a.lat)*r,y=(b.lng-a.lng)*r;
  const h=Math.sin(x/2)**2+Math.cos(a.lat*r)*Math.cos(b.lat*r)*Math.sin(y/2)**2;
  return 12742.0176*Math.asin(Math.min(1,Math.sqrt(h)));
}
function namedFact(place,key) {
  const f=place?.facts?.[key];
  return f && (f.sourceId||f.sourceUrl) && typeof f.value==='string' ? f.value.trim() : '';
}
/**
 * Link cautelativi: solo stessa denominazione esatta, un unico borgo candidato
 * e coordinate coerenti. Non promuove la vicinanza a relazione amministrativa.
 * Non produce link a entità inesistenti o omonimi indistinguibili.
 */
export function resolveRefugeTerritory(place,allPlaces) {
  const declared=[
    {key:'municipalityNameReported',name:namedFact(place,'municipalityNameReported'),label:'Comune dichiarato',maxKm:40},
    {key:'localityNameReported',name:namedFact(place,'localityNameReported'),label:'Località dichiarata',maxKm:12},
  ].filter(item=>item.name);
  const villages=(allPlaces||[]).filter(p=>p.kind==='borgo'&&
    Number.isFinite(p.lat)&&Number.isFinite(p.lng)&&p.slug);
  return declared.map(item=>{
    const normalized=atlasSlugPart(item.name);
    const matches=villages.filter(p=>atlasSlugPart(p.name)===normalized &&
      distanceKm(place,p)<=item.maxKm);
    const target=matches.length===1?matches[0]:null;
    return {
      key:item.key,name:item.name,label:item.label,matched:Boolean(target),
      href:target?atlasCanonicalPath(target):null,
      distanceKm:target?distanceKm(place,target):null,
    };
  });
}

export function relatedAtlasPlaces(place,allPlaces,maxKm=7,limit=4) {
  return (allPlaces||[]).filter(p=>p.slug!==place.slug &&
    (p.kind==='rifugio'||p.kind==='bivacco'||p.kind==='borgo') &&
    Number.isFinite(p.lat)&&Number.isFinite(p.lng))
    .map(p=>({place:p,distanceKm:distanceKm(place,p)}))
    .filter(item=>item.distanceKm>0.02&&item.distanceKm<=maxKm)
    .sort((a,b)=>a.distanceKm-b.distanceKm||a.place.name.localeCompare(b.place.name,'it'))
    .slice(0,limit);
}
