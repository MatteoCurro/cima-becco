/**
 * Contratto UI del dossier canonico Cima Becco.
 * Non è l'importatore: gli adapter degli importatori popolano solo valori documentati.
 * docs/MODELLO_METADATI_E_LAYOUT.md è la fonte vincolante.
 */
export type AtlasFactValue = string | number | boolean | null;
export type AtlasMethod = 'reported' | 'derived' | 'estimated';
export interface AtlasFact {
  value: AtlasFactValue;
  unit?: string;
  label?: string;
  group?: string;
  sourceId?: string;
  sourceUrl?: string;
  licence?: string;
  retrievedAt?: string;
  sourceUpdatedAt?: string;
  validFrom?: string;
  validUntil?: string;
  method?: AtlasMethod;
  confidence?: number;
  notes?: string;
  rawValue?: unknown;
}
export type AtlasRelationKind =
  | 'located_in' | 'part_of' | 'contains' | 'near'
  | 'starts_at' | 'ends_at' | 'passes_near' | 'passes_through' | 'ascends_to'
  | 'accessible_from' | 'managed_by' | 'owned_by' | 'founded_by'
  | 'first_ascended_by' | 'opened_by' | 'overlaps' | 'alternative_to'
  | 'stage_of' | 'previous_stage' | 'next_stage' | 'served_by'
  | 'recorded_by' | 'restricted_by';
export interface AtlasRelation {
  type: AtlasRelationKind;
  target: { id: string; kind: string; name: string; href?: string };
  straightLineKm?: number;
  method?: string;
  sourceUrl?: string;
  verified?: boolean;
}
export interface AtlasMedia {
  id: string;
  kind: 'photo' | 'historical_photo' | 'logo' | 'topo' | 'video';
  url: string;
  sourceUrl: string;
  author?: string;
  licence: string;
  caption?: string;
  capturedAt?: string;
  /** Il soggetto deve essere identificato, non dedotto dal nome. */
  subjectVerified: boolean;
  /** Uso autorizzato dalla licenza/permesso della singola risorsa. */
  reuseAllowed: boolean;
}
export interface AtlasWebcam {
  id: string;
  name: string;
  operator: string;
  officialUrl: string;
  direction?: string;
  target?: string;
  refreshedAt?: string;
  status?: 'active' | 'offline' | 'unknown';
  stillUrl?: string;
  stillLicence?: string;
  /** Mai incorporare still o video senza verifica del permesso. */
  stillReuseAllowed?: boolean;
}
export interface AtlasAlert {
  id: string;
  title: string;
  message: string;
  sourceUrl: string;
  checkedAt: string;
  validFrom?: string;
  validUntil?: string;
}
export interface AtlasStage {
  id: string;
  ordinal: number;
  title: string;
  href?: string;
  official?: boolean;
  lengthKm?: number;
  gainM?: number;
  sourceUrl?: string;
}
export interface AtlasTechnical {
  grade?: string;
  gradeScale?: string;
  protection?: string;
  bolts?: number;
  quickdraws?: number;
  ropeLengthM?: number;
  belay?: string;
  exposure?: string;
  rock?: string;
}
export interface AtlasPitch {
  id: string;
  ordinal: number;
  grade?: string;
  lengthM?: number;
  bolts?: number;
  quickdraws?: number;
  belay?: string;
}
export interface AtlasClimateSeries {
  id: string;
  name: string;
  unit: string;
  period: string;
  sourceUrl: string;
  values: { month: number; value: number | null }[];
}
/** I campi d'identità sono opzionali finché la migrazione dei dataset legacy non è completata. */
export interface AtlasNameVariant {
  value:string;
  language?:string;
  sourceUrl?:string;
  historical?:boolean;
}
export interface AtlasAdministrativeHierarchy {
  country?:string;
  region?:string;
  province?:string;
  municipality?:string;
  municipalityCodeISTAT?:string;
  parentMunicipalityId?:string;
}
export interface AtlasGeo {
  point?: {lat:number;lng:number};
  area?: unknown;
  method?:'reported'|'derived'|'estimated';
  precisionM?:number;
  sourceUrl?:string;
}
export interface AtlasFactAlternative {
  key:string;
  fact:AtlasFact;
  reason?:string;
}
export interface AtlasEntityMetadata {
  /** ID di entità stabile e separato da slug/codici fonte. */
  id?:string;
  subtype?:string;
  aliases?:AtlasNameVariant[];
  localNames?:AtlasNameVariant[];
  slugAliases?:string[];
  shortSummary?:string;
  geo?:AtlasGeo;
  administrativeHierarchy?:AtlasAdministrativeHierarchy;
  sourceIds?:Record<string,string>;
  factsAlternatives?:AtlasFactAlternative[];
  restrictions?:AtlasAlert[];
  weatherRef?:string;
  climateRef?:string;
  facts?: Record<string, AtlasFact>;
  relations?: AtlasRelation[];
  media?: AtlasMedia[];
  webcams?: AtlasWebcam[];
  alerts?: AtlasAlert[];
  history?: string;
  historySourceUrl?: string;
  stages?: AtlasStage[];
  technical?: AtlasTechnical;
  pitches?: AtlasPitch[];
  climate?: AtlasClimateSeries[];
  checkedAt?: string;
  updatedAt?: string;
  editorialStatus?: 'raw' | 'linked' | 'enriched' | 'reviewed';
}
export const ATLAS_RELATION_LABELS: Record<AtlasRelationKind, string> = {
  located_in: 'Si trova in', part_of: 'Fa parte di', contains: 'Comprende', near: 'Nelle vicinanze',
  starts_at: 'Parte da', ends_at: 'Termina a', passes_near: 'Passa vicino a',
  passes_through: 'Attraversa', ascends_to: 'Sale a', accessible_from: 'Accessibile da',
  managed_by: 'Gestito da', owned_by: 'Di proprietà di', founded_by: 'Fondato da',
  first_ascended_by: 'Prima ascensione', opened_by: 'Aperto da', overlaps: 'Condivide il tracciato con',
  alternative_to: 'Alternativa a', stage_of: 'Tappa di', previous_stage: 'Tappa precedente',
  next_stage: 'Tappa successiva', served_by: 'Servito da', recorded_by: 'Documentato da',
  restricted_by: 'Soggetto a restrizioni',
};
export function presentAtlasFacts(facts?: Record<string, AtlasFact>) {
  return Object.entries(facts ?? {}).filter(([, fact]) =>
    fact != null && fact.value !== null && fact.value !== undefined &&
    (typeof fact.value !== 'number' || Number.isFinite(fact.value))
  );
}
export function formatAtlasFact(fact: AtlasFact): string {
  const value = typeof fact.value === 'boolean' ? (fact.value ? 'Sì' : 'No') :
    typeof fact.value === 'number' ? fact.value.toLocaleString('it-IT') : String(fact.value);
  return value + (fact.unit ? ' ' + fact.unit : '');
}
function alertDateBoundary(value: string, endOfDay: boolean): number {
  // ISO data senza ora: il giorno di validità finale è incluso interamente.
  const dateOnly=/^\d{4}-\d{2}-\d{2}$/.test(value);
  const timestamp=Date.parse(dateOnly ? value+'T00:00:00Z' : value);
  return dateOnly && endOfDay ? timestamp+86_400_000-1 : timestamp;
}
export function activeAtlasAlerts(alerts?: AtlasAlert[], today = new Date()) {
  return (alerts ?? []).filter(alert => Boolean(alert.id && alert.title && alert.message && alert.sourceUrl && alert.checkedAt) &&
    (!alert.validFrom || alertDateBoundary(alert.validFrom,false) <= today.getTime()) &&
    (!alert.validUntil || alertDateBoundary(alert.validUntil,true) >= today.getTime()));
}
export function authorizedAtlasMedia(media?: AtlasMedia[]) {
  return (media ?? []).filter(item => item.subjectVerified && item.reuseAllowed &&
    Boolean(item.id && item.url && item.sourceUrl && item.licence));
}
export function usableAtlasClimate(series?: AtlasClimateSeries[]) {
  return (series ?? []).filter(item => Boolean(item.name && item.unit && item.period && item.sourceUrl) &&
    item.values.filter(point => point.value != null && Number.isFinite(point.value) && point.month >= 1 && point.month <= 12).length >= 6);
}
