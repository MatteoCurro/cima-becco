/**
 * Final semantic projection of official rural-place evidence.
 * Runs AFTER CAI/OSM releases, and in SEO with identical input.
 * Never promote a malga to a bookable refuge solely from tourism=alpine_hut.
 * Preserve original OSM identity, media, trails, user aliases and provenance.
 */
export function applyRuralStructureEvidence(places, source) {
  if (!source || source.schemaVersion !== '1.0' ||
      source.releaseChannel !== 'VERIFIED_RURAL_STRUCTURE_TYPES' ||
      !Array.isArray(source.entries)) return places;
  const result = new Map(places.map(p => [p.slug, p]));
  const byOsm = new Map(places.filter(p => /^https:\/\/www\.openstreetmap\.org\/(?:node|way|relation)\/[1-9]\d*$/.test(p.osmUrl || ''))
    .map(p => [p.osmUrl.replace('https://www.openstreetmap.org/', ''), p.slug]));
  const officialIds = new Set(places.map(p => p.sourceIds?.official).filter(Boolean));
  const validUrl = u => typeof u === 'string' && /^https:\/\//.test(u);
  for (const e of source.entries) {
    if (e.kind !== 'bivacco' || !e.name || !validUrl(e.classificationSource) ||
        !e.shelterTypeLabel || !e.subtype) continue;
    const osm = e.sourceIds?.osm;
    if (osm) {
      const slug = byOsm.get(osm);
      if (!slug) continue; // evidence stays available until OSM source is acquired
      const prior = result.get(slug);
      if (!prior || prior.kind === 'borgo') continue;
      const before = prior.kind;
      result.set(slug, {
        ...prior, kind: 'bivacco', subtype: e.subtype,
        shelterTypeLabel: e.shelterTypeLabel,
        officialUrl: e.officialUrl || prior.officialUrl,
        aliases: [...(prior.aliases || []), ...(e.aliases || [])],
        classificationEvidence: {
          sourceUrl:e.classificationSource, note:e.classificationNote || '',
          recordedAt:source.checkedAt, previousKind:before,
        },
      });
      continue;
    }
    // A genuinely documented POI missing from OSM category queries.
    // A new official source ID is mandatory, not a name-based OSM merge.
    if (!e.slug || !/^[a-z0-9][a-z0-9-]{5,100}$/.test(e.slug) ||
        !e.sourceIds?.official || officialIds.has(e.sourceIds.official) ||
        result.has(e.slug) || !validUrl(e.officialUrl) ||
        !Number.isFinite(e.lat) || !Number.isFinite(e.lng) ||
        e.lat < 35 || e.lat > 48 || e.lng < 6 || e.lng > 19 ||
        !validUrl(e.coordinateSource)) continue;
    result.set(e.slug, {
      ...e, classificationEvidence:{
        sourceUrl:e.classificationSource, note:e.classificationNote || '',
        coordinateSource:e.coordinateSource, recordedAt:source.checkedAt,
      },
      // Keep original source-scoped review status; do not claim a G2 dossier.
      editorialStatus:'linked',
    });
    officialIds.add(e.sourceIds.official);
  }
  return [...result.values()].sort((a,b) => a.name.localeCompare(b.name, 'it') || a.slug.localeCompare(b.slug));
}
