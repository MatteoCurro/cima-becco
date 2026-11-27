import type { AlpinePlace, AlpinePlacesDataset } from './alpinePlaces';
import type { AtlasEntityMetadata, AtlasMedia } from './atlasDossier';

/** Versioned, explicitly normalized publisher output. Never load raw CAI JSON in the browser. */
export interface RefugeReleaseEntity extends AtlasEntityMetadata {
  id: string;
  kind: 'refuge';
  name: string;
  slug: string;
  slugAliases?: string[];
  geo: { point: { lat: number; lng: number } };
  sources: Array<{ id: string; url: string; licence?: string }>;
  sourceIds: Record<string, string>;
  description?: string | null;
  shortSummary?: string;
  officialUrl?: string;
  facts?: NonNullable<AtlasEntityMetadata['facts']>;
  media?: AtlasMedia[];
}

export interface RefugeRelease {
  schemaVersion: string;
  releaseChannel: 'OSM_CAI_REFUGES';
  entities: RefugeReleaseEntity[];
  quarantinedOsmIds?: string[];
  attribution: Array<{ source: string; url: string; licence?: string }>;
}

const caiPage = (code: string): string => 'https://rifugi.cai.it/shelters/' + encodeURIComponent(code);

function mappedPhoto(media: AtlasMedia[] | undefined): AlpinePlace['photo'] | undefined {
  const first = media?.find(item =>
    item.kind === 'photo' && item.subjectVerified && item.reuseAllowed &&
    Boolean(item.url && item.sourceUrl && item.licence)
  );
  return first ? {
    url: first.url,
    sourceUrl: first.sourceUrl,
    author: first.author || 'Archivio CAI · autore non indicato',
    license: first.licence,
  } : undefined;
}

function extendPlace(place: AlpinePlace | undefined, entity: RefugeReleaseEntity): AlpinePlace {
  const sources = entity.sourceIds || {};
  const lat = entity.geo.point.lat;
  const lng = entity.geo.point.lng;
  const facts = entity.facts ?? {};
  const estimatedHeight = facts.elevationM?.value;
  const beds = facts.bedsTotal?.value;
  const contact = facts.phone?.value;
  const email = facts.email?.value;
  const website = facts.website?.value;
  const owner = facts.manager?.value ?? facts.operatorReported?.value;
  const days = facts.openingHoursReported?.value;
  const media = (entity.media ?? []).filter(item => item.subjectVerified && item.reuseAllowed);
  const first = mappedPhoto(media);
  const legacy: AlpinePlace = place ?? {
    name: entity.name,
    slug: entity.slug,
    kind: 'rifugio',
    lat,
    lng,
    // Map navigation link, not an attribution of CAI data to OSM.
    osmUrl: 'https://www.openstreetmap.org/#map=14/' + lat + '/' + lng,
  };
  return {
    ...legacy,
    id: entity.id,
    sourceIds: { ...(place?.sourceIds ?? {}), ...sources },
    slugAliases: entity.slugAliases,
    geo: entity.geo,
    facts: { ...(place?.facts ?? {}), ...facts },
    factsAlternatives: entity.factsAlternatives,
    relations: entity.relations,
    media,
    webcams: entity.webcams,
    alerts: entity.alerts,
    editorialStatus: entity.editorialStatus,
    subtype: entity.subtype,
    officialUrl: entity.officialUrl ?? (sources.cai ? caiPage(sources.cai) : undefined),
    description: entity.description || place?.description,
    shortSummary: entity.shortSummary || place?.shortSummary,
    photo: first ?? place?.photo,
    logo: place?.logo,
    elevationM: typeof estimatedHeight === 'number' ? estimatedHeight : place?.elevationM,
    elevationSource: typeof estimatedHeight === 'number' && sources.cai ? 'cai' : place?.elevationSource,
    capacity: typeof beds === 'number' && beds > 0 ? beds : place?.capacity,
    operator: typeof owner === 'string' ? owner : place?.operator,
    phone: typeof contact === 'string' ? contact : place?.phone,
    email: typeof email === 'string' ? email : place?.email,
    website: typeof website === 'string' ? website : place?.website,
    openingHours: typeof days === 'string' ? days : place?.openingHours,
  };
}

/** Maintain existing OSM permalinks while enriching with a CAI record. */
export function mergeRefugeRelease(legacy: AlpinePlacesDataset, value: unknown): AlpinePlacesDataset {
  if (!value || typeof value !== 'object') return legacy;
  const release = value as Partial<RefugeRelease>;
  if (release.releaseChannel !== 'OSM_CAI_REFUGES' || !Array.isArray(release.entities) ||
      release.schemaVersion !== '1.1') return legacy;

  const quarantined = new Set(release.quarantinedOsmIds ?? []);
  const byLegacySlug = new Map(legacy.places.map(p => [p.slug, p]));
  const byOsm = new Map(
    legacy.places.filter(p => /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/\d+$/.test(p.osmUrl))
      .map(p => [p.osmUrl.replace('https://www.openstreetmap.org/', ''), p])
  );
  const merged = new Map<string, AlpinePlace>();
  const matchedLegacySlugs = new Set<string>();
  for (const entity of release.entities) {
    if (entity.kind !== 'refuge' || !entity.slug || !entity.name ||
        !entity.geo?.point || !Number.isFinite(entity.geo.point.lat) ||
        !Number.isFinite(entity.geo.point.lng) || !entity.sourceIds) continue;
    const original = entity.sourceIds.osm
      ? (byOsm.get(entity.sourceIds.osm) ||
          entity.slugAliases?.map(s => byLegacySlug.get(s)).find(Boolean))
      : undefined;
    if (original) matchedLegacySlugs.add(original.slug);
    const enriched = extendPlace(original, entity);
    // Legacy URL stays stable; new CAI-only refuges use cai-<id>.
    merged.set(enriched.slug, enriched);
  }
  for (const place of legacy.places) {
    if (matchedLegacySlugs.has(place.slug)) continue;
    const osm = place.osmUrl?.replace('https://www.openstreetmap.org/', '');
    if (place.kind === 'rifugio' && osm && quarantined.has(osm)) continue;
    merged.set(place.slug, place);
  }
  return {
    ...legacy,
    coverage: 'Italia e territori alpini confinanti',
    source: legacy.source + ' · Club Alpino Italiano',
    places: Array.from(merged.values()).sort((a, b) => a.name.localeCompare(b.name, 'it')),
  };
}
