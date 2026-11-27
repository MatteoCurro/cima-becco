import type { AlpinePlace, AlpinePlacesDataset } from './alpinePlaces';
import type { AtlasEntityMetadata, AtlasMedia } from './atlasDossier';

/** The source archive remains complete at /data/atlas/cai-refuges-v1.json.
 * Only this intentionally normalized, versioned projection reaches the atlas. */
export interface ShelterReleaseEntity extends AtlasEntityMetadata {
  id: string;
  kind: 'bivouac' | 'shelter';
  subtype: 'fixed_bivouac' | 'social_cabin' | 'support_point' |
    'osm_bivouac_or_basic_hut';
  name: string;
  slug: string;
  shelterTypeLabel: string;
  sourceIds: Record<string, string>;
  geo: { point: { lat: number; lng: number } };
  facts: NonNullable<AtlasEntityMetadata['facts']>;
  media?: AtlasMedia[];
  description?: string | null;
  officialUrl?: string;
  safety?: {
    accessConfirmed: false;
    occupancyConfirmed: false;
    waterPotabilityConfirmed: false;
    openingConfirmed: false;
  };
}

export interface ShelterRelease {
  schemaVersion: '2.0';
  releaseChannel: 'CAI_OSM_BIVOUACS_SHELTERS';
  entities: ShelterReleaseEntity[];
  reclassifiedOsmIds: string[];
  creditPolicy?: string;
}

const sourceForCAI = (id: string): string =>
  'https://rifugi.cai.it/shelters/' + encodeURIComponent(id);

export function mergeShelterRelease(
  catalogue: AlpinePlacesDataset, incoming: unknown,
): AlpinePlacesDataset {
  if (incoming === null || typeof incoming !== 'object') return catalogue;
  const release = incoming as Partial<ShelterRelease>;
  if (release.schemaVersion !== '2.0' ||
      release.releaseChannel !== 'CAI_OSM_BIVOUACS_SHELTERS' ||
      !Array.isArray(release.entities) || !Array.isArray(release.reclassifiedOsmIds)) {
    return catalogue;
  }
  const bySlug = new Map<string, AlpinePlace>(
    catalogue.places.map(place => [place.slug, place]),
  );
  const byOsm = new Map<string, AlpinePlace>(
    catalogue.places.filter(p =>
      /^https:\/\/www\.openstreetmap\.org\/(node|way|relation)\/\d+$/.test(p.osmUrl),
    ).map(p => [p.osmUrl.replace('https://www.openstreetmap.org/', ''), p]),
  );
  const reclassified = new Set(release.reclassifiedOsmIds);
  for (const old of catalogue.places) {
    const source = old.osmUrl?.replace('https://www.openstreetmap.org/', '');
    if (source && old.kind === 'rifugio' && reclassified.has(source)) {
      bySlug.delete(old.slug);
    }
  }
  const seenIds = new Set<string>();
  const seenNewSlugs = new Set<string>();
  for (const entity of release.entities) {
    if ((entity.kind !== 'bivouac' && entity.kind !== 'shelter') ||
        !entity.id || !entity.name || !entity.slug ||
        !entity.sourceIds || !entity.geo?.point ||
        !Number.isFinite(entity.geo.point.lat) ||
        !Number.isFinite(entity.geo.point.lng) ||
        seenIds.has(entity.id)) continue;
    seenIds.add(entity.id);
    const original = entity.sourceIds.osm ?
      (byOsm.get(entity.sourceIds.osm) ||
        entity.slugAliases?.map(slug => bySlug.get(slug)).find(Boolean)) : undefined;
    const slug = original?.slug ?? entity.slug;
    if (seenNewSlugs.has(slug)) continue;
    seenNewSlugs.add(slug);
    const facts = entity.facts || {};
    const value = (key: string) => facts[key]?.value;
    const media = (entity.media ?? []).filter(item => item.subjectVerified &&
      item.reuseAllowed && item.url?.startsWith('https://') &&
      Boolean(item.licence && item.sourceUrl));
    const cover = media.find(m => m.kind === 'photo');
    const photo: AlpinePlace['photo'] | undefined = cover ? {
      url: cover.url, sourceUrl: cover.sourceUrl,
      author: cover.author || 'Archivio della fonte',
      license: cover.licence,
    } : original?.photo;
    const lat = entity.geo.point.lat;
    const lng = entity.geo.point.lng;
    const link = entity.sourceIds.osm ?
      'https://www.openstreetmap.org/' + entity.sourceIds.osm :
      'https://www.openstreetmap.org/#map=14/' + lat + '/' + lng;
    const elevation = value('elevationM');
    const beds = value('bedsTotal');
    const contact = value('phone');
    const email = value('email');
    const website = value('website');
    const owner = value('owner') ?? value('operatorReported');
    const label = entity.shelterTypeLabel;
    const result: AlpinePlace = {
      ...original,
      kind: 'bivacco', // shared view; canonical shelter subtype stays explicit
      slug,
      name: original?.name || entity.name,
      lat: original?.lat ?? lat,
      lng: original?.lng ?? lng,
      osmUrl: original?.osmUrl || link,
      id: entity.id,
      subtype: entity.subtype,
      shelterTypeLabel: label,
      sourceIds: { ...original?.sourceIds, ...entity.sourceIds },
      officialUrl: entity.officialUrl ||
        (entity.sourceIds.cai ? sourceForCAI(entity.sourceIds.cai) : undefined),
      geo: entity.geo,
      facts: { ...original?.facts, ...facts },
      factsAlternatives: entity.factsAlternatives,
      administrativeHierarchy: entity.administrativeHierarchy,
      relations: entity.relations,
      media, webcams: entity.webcams,
      editorialStatus: entity.editorialStatus,
      description: entity.description || original?.description,
      shortSummary: entity.description?.slice(0, 165) || original?.shortSummary,
      photo,
      elevationM: typeof elevation === 'number' ? elevation : original?.elevationM,
      elevationSource: typeof elevation === 'number' && entity.sourceIds.cai ?
        'cai' : original?.elevationSource,
      capacity: typeof beds === 'number' ? beds : original?.capacity,
      operator: typeof owner === 'string' ? owner : original?.operator,
      phone: typeof contact === 'string' ? contact : original?.phone,
      email: typeof email === 'string' ? email : original?.email,
      website: typeof website === 'string' ? website : original?.website,
    };
    if (original) bySlug.delete(original.slug);
    bySlug.set(slug, result);
  }
  return {
    ...catalogue,
    source: catalogue.source + ' · CAI Unico Rifugi / bivacchi e ricoveri',
    places: [...bySlug.values()].sort((a, b) =>
      a.name.localeCompare(b.name, 'it') || a.slug.localeCompare(b.slug)),
  };
}
