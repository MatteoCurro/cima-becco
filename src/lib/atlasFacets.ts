import type { AlpinePlace } from './alpinePlaces';
import { authorizedAtlasMedia } from './atlasDossier';

/**
 * Registro di faccette per i cataloghi locali. Ogni faccetta è disponibile solo
 * se il dataset possiede effettivamente almeno un valore positivo e attribuito.
 * Un record con valore nullo NON soddisfa un filtro.
 */
export type LocalAtlasFacetId = 'webcam'|'wifi'|'defibrillator'|'shower'|'pets';
export type LocalAtlasFacet = {
  id:LocalAtlasFacetId;
  label:string;
  appliesTo:ReadonlyArray<AlpinePlace['kind']>;
  /** Chiavi alternative ammesse solo se corrispondono a un fatto tipizzato. */
  factKeys?:readonly string[];
};
export const LOCAL_ATLAS_FACETS: ReadonlyArray<LocalAtlasFacet>=[
  {id:'webcam',label:'Con webcam',appliesTo:['rifugio','bivacco','borgo']},
  {id:'wifi',label:'Wi-Fi indicato',appliesTo:['rifugio'],factKeys:['wifi_service','wifi']},
  {id:'defibrillator',label:'Defibrillatore indicato',appliesTo:['rifugio'],factKeys:['defibrillatore_service','defibrillator']},
  {id:'shower',label:'Docce indicate',appliesTo:['rifugio'],factKeys:['docce_service','showers']},
  {id:'pets',label:'Animali ammessi',appliesTo:['rifugio'],factKeys:['pets_allowed','dogs_allowed']},
];
export function atlasHasPhoto(p:AlpinePlace):boolean {
  return Boolean(p.photo?.url && p.photo.sourceUrl &&
    p.photo.author && p.photo.license) ||
    authorizedAtlasMedia(p.media).some(media=>media.kind==='photo'||media.kind==='historical_photo');
}
export function atlasHasContact(p:AlpinePlace):boolean {
  return Boolean(p.phone||p.email||p.website);
}
function factYes(place:AlpinePlace,keys:readonly string[]):boolean {
  return keys.some(key=>{
    const fact=place.facts?.[key];
    if (!fact || !fact.sourceId && !fact.sourceUrl) return false;
    return fact.value===true || (typeof fact.value==='string' && ['yes','true'].includes(fact.value.trim().toLowerCase()));
  });
}
export function atlasMatchesFacet(p:AlpinePlace,facet:LocalAtlasFacet):boolean {
  if (!facet.appliesTo.includes(p.kind)) return false;
  if (facet.id==='webcam') return (p.webcams ?? []).some(cam=>Boolean(cam.officialUrl && cam.name && cam.operator));
  return facet.factKeys ? factYes(p,facet.factKeys) : false;
}
export function availableLocalFacets(places:readonly AlpinePlace[],kind:AlpinePlace['kind']):LocalAtlasFacet[]{
  return LOCAL_ATLAS_FACETS.filter(f=>f.appliesTo.includes(kind) && places.some(p=>atlasMatchesFacet(p,f)));
}
