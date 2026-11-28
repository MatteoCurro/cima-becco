/** Verified SAT source-reference enrichment for existing OSM route pages ONLY.
 * An exact official SAT reference does NOT certify physical routing, access,
 * passage through POIs, current conditions or the presence of a via ferrata.
 */
export interface SATReportedFact {
  value: number;
  unit: 'm' | 'min';
  method: 'reported';
  sourceUrl: string;
  licence: string;
  retrievedAt?: string | null;
}

export interface SATRouteReference {
  routeSlug: string;
  sourceReference: {
    sourceId: 'SAT';
    number: string;
    sourceUrl: string;
    licence: string;
    retrievedAt: string | null;
    officialCatalogueSubtype: null;
  };
  identityEvidence: {
    osmRelationId: string;
    sourceReferenceVerified: true;
    method: string;
    osmSourceUrl: string;
  };
  originalDifficulty: {
    value: string;
    scale: string;
  };
  sourceContext: {
    startPlaceAsText?: string | null;
    endPlaceAsText?: string | null;
    mountainGroup?: string | null;
    competentEntity?: string | null;
  } | null;
  reportedFacts: Record<string, SATReportedFact>;
  quality: {
    gate: 'G1';
    satSourceReferenceVerified: true;
    routeContinuityVerified: false;
    traversableVerified: false;
    ferrataSubtypeVerified: false;
    canonicalEntityMergePerformed: false;
    osmRelationMembershipIncomplete: boolean;
  };
}

const REQUIRED_FACTS = [
  'elevationStartReportedM', 'elevationEndReportedM',
  'elevationMinReportedM', 'elevationMaxReportedM',
  'lengthPlanimetricReportedM', 'lengthInclinedReportedM',
  'durationOutReportedMin', 'durationBackReportedMin',
] as const;

function object(value: unknown): Record<string, unknown> | null {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : null;
}

function validRecord(value: unknown, routeSlug: string): value is SATRouteReference {
  const r = object(value);
  if (!r || r.routeSlug !== routeSlug || !/^osm-hiking-[1-9][0-9]*$/.test(routeSlug)) return false;
  const src = object(r.sourceReference);
  const ev = object(r.identityEvidence);
  const q = object(r.quality);
  const diff = object(r.originalDifficulty);
  const facts = object(r.reportedFacts);
  if (!src || !ev || !q || !diff || !facts) return false;
  if (src.sourceId !== 'SAT' || !/^E[0-9]{3}[A-Z]?$|^O[0-9]{3}[A-Z]?$/.test(String(src.number ?? ''))) return false;
  if (src.officialCatalogueSubtype !== null ||
      src.sourceUrl !== 'https://www.sat.tn.it/sentieri/mappa-sentieri/' ||
      src.licence !== 'ODbL 1.0') return false;
  const expectedRelation = 'relation/' + routeSlug.slice('osm-hiking-'.length);
  if (ev.osmRelationId !== expectedRelation || ev.sourceReferenceVerified !== true ||
      typeof ev.method !== 'string' || !ev.method.startsWith('exact_sat_reg_ref_') ||
      ev.osmSourceUrl !== 'https://www.openstreetmap.org/' + expectedRelation) return false;
  if (q.gate !== 'G1' || q.satSourceReferenceVerified !== true ||
      q.routeContinuityVerified !== false || q.traversableVerified !== false ||
      q.ferrataSubtypeVerified !== false || q.canonicalEntityMergePerformed !== false ||
      typeof q.osmRelationMembershipIncomplete !== 'boolean') return false;
  if (typeof diff.value !== 'string' || !/^(T|E|EE|EEA-(F|PD|D|MD|E))$/.test(diff.value)) return false;
  for (const key of REQUIRED_FACTS) {
    const f = object(facts[key]);
    if (!f || typeof f.value !== 'number' || !Number.isFinite(f.value) || f.value < 0 ||
        f.method !== 'reported' || f.unit !== (key.endsWith('Min') ? 'min' : 'm') ||
        f.sourceUrl !== src.sourceUrl || f.licence !== 'ODbL 1.0') return false;
  }
  return true;
}

export function parseSATRouteReferenceDataset(raw: unknown): Record<string, SATRouteReference> {
  const doc = object(raw);
  const q = object(doc?.quality);
  const records = object(doc?.records);
  if (!doc || !records ||
      doc.releaseChannel !== 'SAT_VERIFIED_ROUTE_SOURCE_REFERENCE_G1_V1' ||
      doc.isPublished !== true || doc.seoIndexable !== false ||
      doc.newCanonicalPagesCreated !== false || doc.routeCatalogueModified !== false ||
      q?.gate !== 'G1' || q?.routingAllowed !== false ||
      q?.safetyVerified !== false || q?.newPermalinksAllowed !== false) return {};
  const result: Record<string, SATRouteReference> = {};
  for (const [slug, value] of Object.entries(records)) {
    if (validRecord(value, slug)) result[slug] = value;
  }
  return result;
}

let cached: Promise<Record<string, SATRouteReference>> | null = null;
export function loadSATRouteReference(routeSlug: string): Promise<SATRouteReference | null> {
  if (!/^osm-hiking-[1-9][0-9]*$/.test(routeSlug)) return Promise.resolve(null);
  if (!cached) {
    cached = fetch(import.meta.env.BASE_URL + 'data/atlas/trail-sat-verified-references-v1.json')
      .then(async response => response.ok ? parseSATRouteReferenceDataset(await response.json()) : {})
      .catch(() => ({}));
  }
  return cached.then(records => records[routeSlug] ?? null);
}
