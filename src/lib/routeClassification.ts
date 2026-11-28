import type { Route } from '../types';
import { routeActivity } from './routeAnalysis';

export type RoutePresentationKind = 'ferrata' | 'attrezzato' | 'escursione' | 'trail';
export interface RoutePresentationCategory {
  kind: RoutePresentationKind;
  label: string;
  /** Catalogued evidence is not an inspection of the installed equipment. */
  evidence: 'catalogued' | 'inferred' | 'unverified';
  reason: string;
}

/**
 * Non-destructive frontend classification. Do not rewrite the importer or
 * confer a formal CAI/SAC grade inferred from a name or GPX.
 */
export function routePresentationCategory(route: Route): RoutePresentationCategory {
  if (route.activity === 'ferrata' || Boolean(route.viaFerrataScale?.trim())) {
    return { kind:'ferrata', label:'Via ferrata', evidence:'catalogued',
      reason: route.viaFerrataScale ? 'Scala di ferrata presente nei dati sorgente' : 'Tipologia ferrata presente nel catalogo' };
  }
  if (/\b(?:via[\s-]+ferrata|ferrata|klettersteig)\b/i.test(route.name)) {
    return { kind:'ferrata', label:'Possibile via ferrata', evidence:'inferred',
      reason:'Denominazione suggestiva: classificazione tecnica da confermare alla fonte' };
  }
  if (route.caiDifficulty === 'EEA' || /\b(?:sentiero|percorso|via)\s+attrezzat[oa]\b/i.test(route.name)) {
    return { kind:'attrezzato', label:'Itinerario attrezzato da verificare', evidence:'inferred',
      reason:route.caiDifficulty==='EEA'?'Presente grado CAI EEA, non necessariamente una ferrata':'Denominazione di sentiero attrezzato' };
  }
  if (routeActivity(route)==='trail') {
    return {kind:'trail',label:'Trail running',evidence:'catalogued',reason:'Attività di corsa in montagna'};
  }
  return {kind:'escursione',label:'Sentiero / escursione',evidence:'unverified',
    reason:'Nessuna prova specifica di attrezzatura tecnica nei dati attuali'};
}

export interface RoutePhysicalEffort {
  level: 'gentle' | 'regular' | 'demanding' | 'unknown';
  distanceKm: number | null;
  gainM: number | null;
  risePerKm: number | null;
  /** Methodologically separate from technical exposure and CAI grade. */
  label: string;
  explanation: string;
}
export function routePhysicalEffort(
  route: Route,
  options?: { gainM?: number; elevationAvailable?: boolean },
): RoutePhysicalEffort {
  const distanceKm=Number.isFinite(route.distanceM)&&route.distanceM>0?route.distanceM/1000:null;
  const available=options?.elevationAvailable ?? route.elevationAvailable !== false;
  const elevation=options?.gainM ?? route.gainM;
  const gainM=available && Number.isFinite(elevation)&&elevation>=0?elevation:null;
  const risePerKm=distanceKm!==null&&distanceKm>0&&gainM!==null?gainM/distanceKm:null;
  const distScore=distanceKm===null?0:distanceKm>=18?3:distanceKm>=12?2:distanceKm>=7?1:0;
  const gainScore=gainM===null?0:gainM>=1200?3:gainM>=800?2:gainM>=400?1:0;
  const riseScore=risePerKm!==null && distanceKm!==null && distanceKm>=2 && risePerKm>=160?2:0;
  const score=Math.max(distScore,gainScore,riseScore);
  // A short trace without ascent data must not be presented as an easy outing.
  // A high recorded distance OR gain may still establish a demanding lower bound.
  const incomplete=distanceKm===null||gainM===null;
  const level=score>=2?'demanding':incomplete?'unknown':score===1?'regular':'gentle';
  const label=level==='demanding'?'Impegno fisico elevato':level==='regular'?'Impegno fisico intermedio':
    level==='unknown'?'Impegno fisico da verificare':'Impegno fisico contenuto nei dati disponibili';
  const inputs=[
    distanceKm!==null ? distanceKm.toLocaleString('it-IT',{maximumFractionDigits:1})+' km di sviluppo' : null,
    gainM!==null ? Math.round(gainM).toLocaleString('it-IT')+' m di salita' : null,
    risePerKm!==null ? Math.round(risePerKm)+' m di salita per km di percorso' : null,
  ].filter(Boolean).join(', ');
  const limitation=incomplete
    ? 'Sviluppo o dislivello non disponibili: la valutazione è parziale e non consente di escludere un impegno maggiore.'
    : 'La salita media non identifica pendenza dei singoli passaggi, esposizione o attrezzatura.';
  return {level,distanceKm,gainM,risePerKm,label,
    explanation:(inputs?'Valutazione orientativa basata su '+inputs+'. ':'Non sono disponibili metriche sufficienti. ')+limitation};
}
