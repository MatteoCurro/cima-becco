import type { Route } from '../types';
import { routeActivity } from './routeAnalysis';

export type EffortLevel = 'gentle' | 'regular' | 'demanding' | 'technical' | 'unknown';
export interface TrailMood {
  level: EffortLevel;
  label: string;
  quip: string | null;
  basis: string;
}

/** Macroarea indicativa ricavata dal punto medio, non un comune di partenza inventato. */
export function trailArea(route: Route): string {
  const pts = route.coordinates;
  const p = pts[Math.floor(pts.length / 2)] ?? [0, 0, 0];
  const [lng, lat] = p;
  if (lat > 46.1 && lat < 47.2 && lng >= 10.8 && lng < 12) return 'Dolomiti occidentali';
  if (lat > 46.1 && lat < 47.2 && lng >= 12 && lng < 13.5) return 'Dolomiti orientali';
  if (lat > 45 && lat < 47.8 && lng >= 6 && lng < 11) return 'Alpi occidentali e centrali';
  if (lat > 45 && lat < 47.8 && lng >= 11 && lng < 17) return 'Alpi orientali';
  if (lat > 43.3 && lat <= 45.5 && lng >= 8 && lng <= 15) return 'Appennino settentrionale';
  if (lat > 40.5 && lat <= 43.5 && lng >= 10 && lng <= 17) return 'Appennino centrale';
  if (lat > 37 && lat <= 41 && lng >= 13 && lng <= 19) return 'Appennino meridionale';
  if (lat > 36 && lat <= 39 && lng >= 12 && lng <= 16) return 'Sicilia';
  if (lat > 38 && lat <= 42 && lng >= 8 && lng <= 10) return 'Sardegna';
  return route.country === 'Italy' ? 'Italia' : (route.country || 'Area alpina');
}

const generic = /^(?:sentiero(?:\s+(?:cai|sat|si))?(?:\s+[\w\-/]+)?|percorso(?:\s+[\w\-/]+)?|route\s*\d+|hiking route)$/i;

/** Le denominazioni ufficiali restano; i nomi generici ricevono contesto geografico. */
export function trailTitle(route: Route): string {
  const raw = route.name.trim().replace(/\s+/g, ' ');
  const area = trailArea(route);
  if (/^sentiero si$/i.test(raw)) return `Sentiero Italia · ${area}`;
  if (/^sentiero\s+(\d+[a-z]?)$/i.test(raw)) {
    const number = raw.match(/\d+[a-z]?/i)?.[0] ?? route.trailRef ?? '';
    return `Sentiero ${number} · ${area}`;
  }
  if (generic.test(raw) || /^\d+[a-z]?$/i.test(raw)) {
    const ref = route.trailRef || raw.match(/\d+[a-z]?/i)?.[0];
    return `${routeActivity(route) === 'ferrata' ? 'Via ferrata' : 'Itinerario a piedi'}${ref ? ' ' + ref : ''} · ${area}`;
  }
  return raw || `${routeActivity(route) === 'ferrata' ? 'Via ferrata' : 'Escursione'} · ${area}`;
}

function viaFerrataValue(raw: string | undefined): number | null {
  if (!raw) return null;
  const v = raw.match(/(?:^|\D)([1-6])\+?/);
  return v ? Number(v[1]) : null;
}

/** Distinguere sempre una scala CAI/SAC da un soprannome editoriale. */
export function trailMood(route: Route): TrailMood {
  if (routeActivity(route) === 'ferrata') {
    const num = viaFerrataValue(route.viaFerrataScale);
    if (num == null) return { level: 'unknown', label: 'Difficoltà da verificare', quip: null, basis: 'Scala ferrata non disponibile' };
    if (num <= 2) return { level: 'regular', label: 'Ferrata poco difficile', quip: 'Attaccati e vai', basis: 'Scala ferrata: ' + route.viaFerrataScale };
    if (num === 3) return { level: 'demanding', label: 'Ferrata impegnativa', quip: 'Strattona', basis: 'Scala ferrata: ' + route.viaFerrataScale };
    return { level: 'technical', label: 'Ferrata molto impegnativa', quip: num >= 5 ? 'Vai bomber' : 'Braccia in leasing', basis: 'Scala ferrata: ' + route.viaFerrataScale };
  }
  const level = route.caiDifficulty;
  if (level === 'T') return { level: 'gentle', label: 'Turistico', quip: 'Due curve e spiana', basis: 'Classificazione CAI T' };
  if (level === 'E') return { level: 'regular', label: 'Escursionistico', quip: 'Si fa sentire', basis: 'Classificazione CAI E' };
  if (level === 'EE') return { level: 'demanding', label: 'Per escursionisti esperti', quip: 'Non spiana', basis: 'Classificazione CAI EE' };
  if (level === 'EEA') return { level: 'technical', label: 'Esperti con attrezzatura', quip: 'Vai bomber', basis: 'Classificazione CAI EEA' };
  // Se la classificazione tecnica manca, evitare una difficoltà inventata da km/dislivello.
  return { level: 'unknown', label: 'Difficoltà da verificare', quip: null, basis: 'Classificazione CAI assente' };
}

export function trailDescription(route: Route): string {
  const raw = (route.description ?? '').trim();
  if (raw && !/Tracciato OSM da verificare|non certifica percorribilità|^GPX route/i.test(raw)) return raw;
  const area = trailArea(route);
  const kind = routeActivity(route) === 'ferrata' ? 'Il tratto attrezzato' : 'Il percorso';
  const km = (route.distanceM / 1000).toLocaleString('it-IT', { maximumFractionDigits: 1, minimumFractionDigits: 1 });
  const basic = `${kind} si sviluppa ${area === 'Italia' ? 'in Italia' : 'nell’area ' + area} per circa ${km} km${route.loop ? ', con partenza e arrivo nello stesso punto' : ''}.`;
  const ref = route.trailRef || route.name.match(/^sentiero\s+(\d+[a-z]?)$/i)?.[1];
  const number = ref ? ` Il riferimento segnaletico presente nei dati è ${ref}.` : '';
  const gain = route.elevationAvailable !== false && Number.isFinite(route.gainM)
    ? ` Il dislivello positivo stimato è di ${Math.round(route.gainM)} metri.`
    : '';
  const technical = routeActivity(route) === 'ferrata'
    ? ` È una via ferrata: verifica relazione tecnica, attrezzatura e condizioni prima di affrontarla.`
    : route.caiDifficulty
      ? ` La classificazione riportata è CAI ${route.caiDifficulty}.`
      : '';
  return `${basic}${number}${gain}${technical}`;
}

/** Link puntuali: la homepage dell'ente non è una descrizione ufficiale del sentiero. */
export function trailSources(route: Route): { label: string; href: string; kind: 'official' | 'map' }[] {
  const links: { label: string; href: string; kind: 'official' | 'map' }[] = [];
  const official = route.officialDescriptionUrl;
  if (official) {
    try {
      const u = new URL(official);
      if (u.protocol === 'https:' && u.pathname.split('/').filter(Boolean).length >= 2) {
        const label = /sat\.tn\.it/i.test(u.hostname) ? 'Scheda SAT' : /cai\.it/i.test(u.hostname) ? 'Scheda CAI' : 'Scheda del gestore';
        links.push({ label, href: official, kind: 'official' });
      }
    } catch { /* link malformato: non mostrarlo */ }
  }
  if (route.sourceUrl?.startsWith('https://www.openstreetmap.org/relation/')) {
    links.push({ label: 'Tracciato originale su OpenStreetMap', href: route.sourceUrl, kind: 'map' });
  } else if (route.sourceUrl?.startsWith('https://')) {
    links.push({ label: 'Fonte del percorso', href: route.sourceUrl, kind: 'map' });
  }
  return links;
}
