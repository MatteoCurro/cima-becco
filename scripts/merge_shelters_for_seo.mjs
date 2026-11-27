/** Static SEO joins the identical canonical data as the live atlas. */
export function mergeSheltersForSeo(original, release) {
  if (!release || release.releaseChannel !== 'CAI_OSM_BIVOUACS_SHELTERS' ||
      release.schemaVersion !== '2.0' ||
      !Array.isArray(release.entities) || !Array.isArray(release.reclassifiedOsmIds)) return original;

  const places = new Map(original.map(place => [place.slug, {...place}]));
  const byOsm = new Map(original.filter(p =>
    /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/\d+$/.test(p.osmUrl || '')
  ).map(p => [p.osmUrl.replace('https://www.openstreetmap.org/',''), p]));
  for (const source of release.reclassifiedOsmIds) {
    const old = byOsm.get(source);
    if (old && old.kind === 'rifugio') places.delete(old.slug);
  }
  for (const e of release.entities) {
    if (!['bivouac','shelter'].includes(e.kind) ||
        !e.name || !e.slug || !e.sourceIds || !e.geo?.point ||
        !Number.isFinite(e.geo.point.lat) || !Number.isFinite(e.geo.point.lng)) continue;
    const old = e.sourceIds.osm ? (byOsm.get(e.sourceIds.osm) ||
      (e.slugAliases || []).map(alias => places.get(alias)).find(Boolean)) : null;
    const lat=e.geo.point.lat, lng=e.geo.point.lng;
    const f=e.facts||{},val=key=>f[key]?.value;
    const media = (e.media || []).find(m =>
      m.kind==='photo' && m.subjectVerified && m.reuseAllowed &&
      m.url?.startsWith('https://') && m.licence && m.sourceUrl);
    const photo = media ? {
      url:media.url, author:media.author || 'Archivio CAI', license:media.licence,
      sourceUrl:media.sourceUrl
    } : old?.photo;
    const elevation = val('elevationM'), beds = val('bedsTotal');
    const item = {
      ...(old || {}), id:e.id, kind:'bivacco', subtype:e.subtype,
      shelterTypeLabel:e.shelterTypeLabel, slug:old?.slug||e.slug,
      name:old?.name||e.name, lat:old?.lat??lat,lng:old?.lng??lng,
      osmUrl:old?.osmUrl ||
        'https://www.openstreetmap.org/#map=14/'+lat+'/'+lng,
      sourceIds:e.sourceIds, officialUrl:e.officialUrl,
      facts:f, media:e.media || [],
      description:e.description||old?.description,
      photo,
      elevationM:typeof elevation==='number'?elevation:old?.elevationM,
      elevationSource:e.sourceIds.cai?'cai':old?.elevationSource,
      capacity:typeof beds==='number'?beds:old?.capacity,
      operator:typeof val('owner')==='string'?val('owner'):old?.operator,
      phone:typeof val('phone')==='string'?val('phone'):old?.phone,
      email:typeof val('email')==='string'?val('email'):old?.email,
      website:typeof val('website')==='string'?val('website'):old?.website,
    };
    if (old) places.delete(old.slug);
    places.set(item.slug,item);
  }
  return Array.from(places.values());
}
