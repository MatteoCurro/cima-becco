import type { Route } from '../types';
import { routeActivity } from './routeAnalysis';
import { routePhysicalEffort, routePresentationCategory } from './routeClassification';

export type EffortLevel = 'gentle' | 'regular' | 'demanding' | 'technical' | 'unknown';
export interface TrailMood {
  level: EffortLevel;
  label: string;
  quip: string | null;
  basis: string;
  /** Explains the editorial quip without promoting computed exertion to a technical grade. */
  explanation: string;
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

/** Solo POI vicini al tracciato OSM; mai associare un rifugio per assonanza. */
export function trailDestinations(route: Route): string[] {
  const stops = route.stops ?? [];
  const huts = stops.filter((stop) => stop.kind === 'rifugio' && stop.distanceM <= 180);
  const endpoints = huts.filter((stop) => stop.relation === 'arrivo');
  const top = [...endpoints, ...huts.filter((stop) => stop.relation !== 'arrivo')];
  const names = new Set<string>();
  for (const stop of top) {
    if (names.size === 2) break;
    names.add(stop.name);
  }
  if (!names.size) {
    for (const stop of stops.filter((item) => item.kind === 'borgo' && item.distanceM <= 350)) {
      names.add(stop.name);
      if (names.size === 2) break;
    }
  }
  return [...names];
}

/** Descrizione geografica cauta: vicinanza al sentiero ≠ accesso garantito. */
export function trailStopLine(route: Route): string {
  const stops = route.stops ?? [];
  const huts = stops.filter((p) => p.kind === 'rifugio' && p.distanceM <= 180).slice(0, 4);
  const towns = stops.filter((p) => p.kind === 'borgo' && p.distanceM <= 350).slice(0, 3);
  if (!huts.length && !towns.length) return '';
  const text = [
    huts.length ? 'Nei pressi della traccia sono segnalati ' + huts.map((p) => p.name).join(', ') + '.' : '',
    towns.length ? 'Tra le località vicine al percorso: ' + towns.map((p) => p.name).join(', ') + '.' : '',
  ].filter(Boolean).join(' ');
  return text + ' La presenza nei dati cartografici non garantisce l’accesso alle strutture.';
}

/** Le denominazioni ufficiali restano; i nomi generici ricevono contesto geografico. */
export function trailTitle(route: Route): string {
  const raw = (route.name || '').trim().replace(/\s+/g, ' ');
  const area = trailArea(route);
  const poi = trailDestinations(route);
  const destination = poi.length > 0 ? poi.join(' · ') : area;
  if (/^sentiero si$/i.test(raw)) return `Sentiero Italia · ${destination}`;
  if (/^sentiero\s+(\d+[a-z]?)$/i.test(raw)) {
    const number = raw.match(/\d+[a-z]?/i)?.[0] ?? route.trailRef ?? '';
    return `Sentiero ${number} · ${destination}`;
  }
  if (generic.test(raw) || /^\d+[a-z]?$/i.test(raw)) {
    const ref = route.trailRef || raw.match(/\d+[a-z]?/i)?.[0];
    return `${routeActivity(route) === 'ferrata' ? 'Via ferrata' : 'Sentiero'}${ref ? ' ' + ref : ''} · ${destination}`;
  }
  if (!raw) return `${routeActivity(route) === 'ferrata' ? 'Via ferrata' : 'Escursione'} · ${destination}`;
  // I nomi ufficiali OSM non si riscrivono: aggiungi al massimo un POI verificato.
  const leading = poi.find((name) => !raw.toLocaleLowerCase('it').includes(name.toLocaleLowerCase('it')));
  return leading && raw.length < 54 ? `${raw} · ${leading}` : raw;
}

function viaFerrataValue(raw: string | undefined): number | null {
  if (!raw) return null;
  const code=raw.trim().toUpperCase().replace(/\s+/g,'').replace(/^EEA[-–]/, '');
  // Interpret only complete, recognizable source grades. A number embedded
  // in arbitrary text is not a documented technical grade.
  const match=code.match(/^(?:K)?([0-6])[+-]?$/);
  if(match)return Number(match[1]);
  // Source-specific classifications, not CAI T/E/EE conversions.
  const grades:{[key:string]:number}={F:1,PD:2,D:4,MD:5,ED:6};
  return grades[code]??null;
}

/**
 * Irreverent titles are an editorial layer, never technical certification.
 * Combine original CAI/SAC/ferrata metadata with independently computed
 * route length and ascent. Fitness and exposure remain distinct dimensions.
 */
export function trailMood(route: Route, metrics?: {gainM?:number;elevationAvailable?:boolean}): TrailMood {
  const category=routePresentationCategory(route);
  const physical=routePhysicalEffort(route,metrics);
  const effort=physical.level;
  const effortNote=physical.explanation;
  const knownCategory=category.evidence==='inferred' ? 'Categoria da verificare: '+category.reason+'. ' : '';
  if (category.kind==='ferrata') {
    const num=viaFerrataValue(route.viaFerrataScale);
    if(num===null)return {
      level:'unknown',
      label:route.viaFerrataScale
        ? 'Scala ferrata '+route.viaFerrataScale+' · grado non interpretato'
        : category.evidence==='inferred'?'Possibile ferrata · grado non verificato':'Scala ferrata non disponibile',
      quip:'GRADO IN LATITANZA',
      basis:route.viaFerrataScale?'Scala originale presente; conversione non effettuata':'Difficoltà tecnica da verificare',
      explanation:knownCategory+(route.viaFerrataScale
        ? 'La fonte riporta la scala '+route.viaFerrataScale+'; non sono disponibili elementi sufficienti per convertirla in un grado editoriale.'
        : 'Nessuna difficoltà tecnica originale della ferrata disponibile.')+' '+effortNote,
    };
    const strength=num<=2?'regular':num===3?'demanding':'technical';
    const quip=num<=2?'BRACCIA IN GITA':num===3?'AVAMBRACCI IN LEASING':num>=5?'IL VUOTO TI FA CIAO':'LA ROCCIA TI SGAMA';
    const label=num<=2?'Ferrata poco difficile':num===3?'Ferrata impegnativa':'Ferrata molto impegnativa';
    return {level:strength,label,quip,basis:'Scala ferrata: '+route.viaFerrataScale,
      explanation:'Scala tecnica dichiarata nei dati: '+route.viaFerrataScale+'. '+knownCategory+effortNote+
      ' Il grado tecnico non certifica lo stato delle attrezzature.'};
  }
  const level=route.caiDifficulty;
  const scale=route.sacScale;
  const physicalLevel=effort;
  const effortUnknown=effort==='unknown';
  const tough=effort==='demanding';
  if(level==='T')return {level:tough?'demanding':effortUnknown?'unknown':'gentle',label:'Turistico · CAI T',
    quip:effortUnknown?null:tough?'GAMBE IN SCIOPERO':'MERENDEROS',basis:'Classificazione CAI T',
    explanation:'Difficoltà tecnica dichiarata CAI T. '+effortNote+
      ' La fatica della traccia non cambia il grado CAI.'};
  if(level==='E')return {level:effortUnknown?'unknown':physicalLevel==='demanding'?'demanding':'regular',
    label:'Escursionistico · CAI E',quip:effortUnknown?null:tough?'GAMBE IN SCIOPERO':'MUOVI QUELLE GAMBE',
    basis:'Classificazione CAI E',
    explanation:'Difficoltà tecnica dichiarata CAI E. '+effortNote+
      ' Il maggiore sforzo non implica passaggi tecnici di livello EE.'};
  if(level==='EE')return {level:'demanding',label:'Escursionisti esperti · CAI EE',
    quip:tough?'DO VETO MORE?':'OGGI SI BESTEMMIA',basis:'Classificazione CAI EE',
    explanation:'Difficoltà dichiarata CAI EE, distinta dall’impegno fisico. '+effortNote};
  if(level==='EEA'||category.kind==='attrezzato')return {
    level:'technical',label:level==='EEA'?'Esperti con attrezzatura · CAI EEA':'Itinerario attrezzato · classe da verificare',
    quip:'NON FARE IL FENOMENO',basis:level==='EEA'?'Classificazione CAI EEA':'Presenza di attrezzatura suggerita dal nome',
    explanation:(level==='EEA'?'Classificazione CAI EEA dichiarata. ':'Attrezzatura tecnica ipotizzata dalla denominazione. ')+
      'Il grado EEA non prova di per sé che si tratti di una via ferrata. '+effortNote,
  };
  const sac=/^T[1-6]$/i.test(scale||'')?scale!.toUpperCase():null;
  if(sac)return {level:sac==='T1'||sac==='T2'?'regular':'demanding',label:'Scala SAC '+sac,
    quip:tough?'GAMBE IN SCIOPERO':'OGGI SI BESTEMMIA',basis:'Scala SAC dichiarata',
    explanation:'Scala SAC '+sac+' presente nei dati originali, senza conversione artificiale in CAI. '+effortNote};
  if(physical.distanceKm!==null||physical.gainM!==null)return {
    level:physicalLevel,label:physical.label+' · grado tecnico da verificare',
    quip:effortUnknown?null:tough?'GAMBE IN SCIOPERO':effort==='regular'?'MUOVI QUELLE GAMBE':'MERENDEROS',
    basis:'Stima editoriale basata su lunghezza e salita',
    explanation:effortNote+' Manca una classificazione tecnica CAI/SAC confermata: non si deducono esposizione, passaggi attrezzati o percorribilità dal solo GPX.',
  };
  return {level:'unknown',label:'Difficoltà da verificare',quip:'GRADO IN LATITANZA',
    basis:'Classificazione CAI assente',explanation:'Nessuna classe tecnica e nessuna metrica sufficiente per stimare l’impegno fisico.'};
}

export function trailDescription(route: Route): string {
  const raw = (route.description ?? '').trim();
  if (raw && !/Tracciato OSM da verificare|non certifica percorribilità|^GPX route/i.test(raw)) return `${raw} ${trailStopLine(route)}`.trim();
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
  return `${basic}${number}${gain}${technical} ${trailStopLine(route)}`.trim();
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
