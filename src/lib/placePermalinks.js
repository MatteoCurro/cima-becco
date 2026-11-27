/**
 * Permalink pubblici parlanti per i rifugi; l'ID sorgente rende il nome
 * disambiguato senza cambiare gli slug interni usati dalle tappe GPX.
 * Applicabile sia in browser sia nel generatore statico SEO.
 */
export function atlasSlugPart(input) {
  return String(input || '')
    .normalize('NFKD').replace(/[\u0300-\u036f]/g,'')
    .replace(/ß/g,'ss').replace(/æ/g,'ae').replace(/ø/g,'o')
    .toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-+|-+$/g,'')
    .slice(0,73).replace(/-+$/,'');
}
export function canonicalAtlasSlug(place) {
  if (place.kind !== 'rifugio') return place.slug;
  const name=atlasSlugPart(place.name) || 'rifugio';
  // L'ID è l'identità, NON il nome; CAI per i record riconciliati, OSM per gli altri.
  const cai=String(place.sourceIds?.cai || '').match(/^\d+$/)?.[0];
  const legacy=String(place.slug || '');
  const token=cai ? 'cai-'+cai :
    /^(?:osm-[nwr]-\d+|cai-\d+)$/.test(legacy) ? legacy : null;
  return token ? name+'-'+token : legacy;
}
export function atlasCanonicalPath(place) {
  const kind=place.kind==='rifugio'?'rifugi':place.kind==='bivacco'?'bivacchi':'borghi';
  return '/'+kind+'/'+encodeURIComponent(canonicalAtlasSlug(place))+'/';
}
export function atlasLegacyPath(place) {
  const kind=place.kind==='rifugio'?'rifugi':place.kind==='bivacco'?'bivacchi':'borghi';
  return '/'+kind+'/'+encodeURIComponent(place.slug)+'/';
}
