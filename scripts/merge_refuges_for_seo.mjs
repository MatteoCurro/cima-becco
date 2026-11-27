/**
 * Read the same versioned static refuge release as the app, during SEO build.
 * Never invent OSM attribution for CAI-only records. Preserve old OSM slugs.
 */
export function mergeRefugesForSeo(original, release) {
  if (!release || release.schemaVersion !== '1.1' ||
      release.releaseChannel !== 'OSM_CAI_REFUGES' || !Array.isArray(release.entities)) {
    return original;
  }
  const result = new Map(original.map(place => [place.slug, { ...place }]));
  const byOsm = new Map(original.filter(place =>
    /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/\d+$/.test(place.osmUrl || '')
  ).map(place => [place.osmUrl.split('openstreetmap.org/')[1], place.slug]));
  for (const key of release.quarantinedOsmIds || []) {
    const slug = byOsm.get(key);
    if (slug) result.delete(slug);
  }
  for (const e of release.entities) {
    if (e.kind !== 'refuge' || !e.geo?.point ||
        !Number.isFinite(e.geo.point.lat) || !Number.isFinite(e.geo.point.lng)) continue;
    const originalSlug = byOsm.get(e.sourceIds?.osm) ||
      (e.slugAliases || []).find(slug => result.has(slug));
    const old = originalSlug ? result.get(originalSlug) : null;
    const first = (e.media || []).find(m => m.kind === 'photo' && m.url &&
      m.licence && m.sourceUrl && m.subjectVerified && m.reuseAllowed);
    const rawFacts = e.facts || {};
    const val = key => rawFacts[key]?.value;
    const lat = e.geo.point.lat, lng = e.geo.point.lng;
    const present = {
      ...(old || {}),
      kind: 'rifugio', slug: old?.slug || e.slug,
      name: old?.name || e.name, lat: old?.lat ?? lat, lng: old?.lng ?? lng,
      osmUrl: old?.osmUrl || 'https://www.openstreetmap.org/#map=14/' + lat + '/' + lng,
      id: e.id, sourceIds: e.sourceIds || {},
      officialUrl: e.officialUrl,
      facts: rawFacts,
      media: (e.media || []).filter(m=>m.subjectVerified && m.reuseAllowed && m.url && m.sourceUrl && m.licence),
      shortSummary: e.shortSummary || old?.shortSummary,
      description: e.description || old?.description,
      photo: first ? {
        url: first.url, sourceUrl: first.sourceUrl,
        author: first.author || 'Catalogo CAI',
        license: first.licence,
      } : old?.photo,
      elevationM: typeof val('elevationM') === 'number' ? val('elevationM') : old?.elevationM,
      elevationSource: e.sourceIds?.cai ? 'cai' : old?.elevationSource,
      capacity: typeof val('bedsTotal') === 'number' ? val('bedsTotal') : old?.capacity,
      operator: typeof val('manager') === 'string' ? val('manager') : old?.operator,
      phone: typeof val('phone') === 'string' ? val('phone') : old?.phone,
      email: typeof val('email') === 'string' ? val('email') : old?.email,
      website: typeof val('website') === 'string' ? val('website') : old?.website,
    };
    result.set(present.slug, present);
  }
  return Array.from(result.values());
}
