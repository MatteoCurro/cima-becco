import { useEffect, useState } from 'react';
import type { Route } from '../types';
import { loadSATRouteReference, type SATRouteReference } from '../lib/satTrailReferences';
import { DetailMetrics, DetailSectionHeading } from './DetailPrimitives';

/** Source-aligned SAT facts do NOT certify trail continuity, access or safety. */
export function RouteSATSourceFacts({
  routeSlug, source, enabled,
}: {
  routeSlug: string;
  source: Route['source'];
  enabled: boolean;
}) {
  const [current, setCurrent] = useState<{ slug: string; value: SATRouteReference | null } | null>(null);
  useEffect(() => {
    if (!enabled || source !== 'curated' || !/^osm-hiking-[1-9][0-9]*$/.test(routeSlug)) return;
    let active = true;
    void loadSATRouteReference(routeSlug).then(value => {
      if (active) setCurrent({ slug: routeSlug, value });
    });
    return () => { active = false; };
  }, [enabled, routeSlug, source]);
  const sat = current?.slug === routeSlug ? current.value : null;
  if (!sat) return null;

  const facts = sat.reportedFacts;
  const value = (key: string) => facts[key]?.value ?? null;
  const metres = (key: string) => {
    const number = value(key);
    return number === null ? 'Non disponibile' : Math.round(number).toLocaleString('it-IT') + ' m';
  };
  const kilometres = (key: string) => {
    const number = value(key);
    return number === null ? 'Non disponibile' :
      (number / 1000).toLocaleString('it-IT', { maximumFractionDigits: 2 }) + ' km';
  };
  const duration = (key: string) => {
    const minutes = value(key);
    if (minutes === null) return 'Non disponibile';
    const h = Math.floor(minutes / 60);
    const m = minutes % 60;
    return h ? String(h) + ' h' + (m ? ' ' + m + ' min' : '') : String(m) + ' min';
  };
  const sourceDate = sat.sourceReference.retrievedAt
    ? new Date(sat.sourceReference.retrievedAt).toLocaleDateString('it-IT')
    : null;

  return (
    <section className="route-official-data cb-route-sat-source" aria-label="Riferimento verificato al catasto SAT">
      <DetailSectionHeading
        kicker="CATASTO SAT / FONTE VERIFICATA"
        title={'Sentiero SAT ' + sat.sourceReference.number}
      />
      <p className="route-meta">
        Il codice del catasto SAT corrisponde al riferimento documentato della relazione OSM.
        Le informazioni seguenti sono dichiarate dalla SAT e restano distinte dalle stime della traccia cartografica.
      </p>
      <p className="route-meta muted">
        Difficoltà originale SAT: <strong>{sat.originalDifficulty.value}</strong>
        {' · '}Tipologia catastale SA / SAA / VF ancora da accertare
      </p>
      {(sat.sourceContext?.startPlaceAsText || sat.sourceContext?.endPlaceAsText) && (
        <p className="route-meta">
          {sat.sourceContext?.startPlaceAsText && <>Partenza dichiarata: <strong>{sat.sourceContext.startPlaceAsText}</strong></>}
          {sat.sourceContext?.startPlaceAsText && sat.sourceContext?.endPlaceAsText && ' · '}
          {sat.sourceContext?.endPlaceAsText && <>Arrivo dichiarato: <strong>{sat.sourceContext.endPlaceAsText}</strong></>}
        </p>
      )}
      <DetailMetrics label="Dati dichiarati SAT (non stimati dal GPX)" items={[
        { label: 'Lunghezza planimetrica', value: kilometres('lengthPlanimetricReportedM') },
        { label: 'Lunghezza inclinata', value: kilometres('lengthInclinedReportedM') },
        { label: 'Tempo andata', value: duration('durationOutReportedMin') },
        { label: 'Tempo ritorno', value: duration('durationBackReportedMin') },
        { label: 'Quota iniziale', value: metres('elevationStartReportedM') },
        { label: 'Quota finale', value: metres('elevationEndReportedM') },
        { label: 'Quota minima', value: metres('elevationMinReportedM') },
        { label: 'Quota massima', value: metres('elevationMaxReportedM') },
      ]} />
      <p className="route-meta muted">
        Il riferimento condiviso non certifica percorribilità, continuità geometrica, accessi a rifugi o cime,
        condizioni e attrezzature attuali.
        {sat.quality.osmRelationMembershipIncomplete &&
          ' Nel campione OSM non sono presenti tutti i tratti della relazione.'}
      </p>
      <p className="route-meta muted">
        <a href={sat.sourceReference.sourceUrl} target="_blank" rel="noopener noreferrer">Catasto e cartografia SAT</a>
        {' · '}
        <a href={sat.identityEvidence.osmSourceUrl} target="_blank" rel="noopener noreferrer">Relazione OSM originale</a>
        {sourceDate && ' · Fonte consultata il ' + sourceDate}
      </p>
    </section>
  );
}
