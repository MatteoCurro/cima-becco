import { memo, useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { routeIntersects } from '../lib/routes';
import { trailMood, trailTitle, trailArea } from '../lib/routeEditorial';
import { useTrailGain } from '../lib/useTrailGain';
import type { Bounds } from '../lib/venues';

import { RouteThumb } from './RouteThumb';
import { ActivityTag } from './ActivityIcon';
import { routeActivity } from '../lib/routeAnalysis';
import { formatEstimate, routeEstimateS } from '../lib/routeTime';
import { useUnits } from './UnitsContext';
import { DownloadIcon, HeartIcon, UploadIcon } from './icons';
import { downloadRoute } from './VenueCard';
import { RouteBookmarkButton } from './RouteBookmarkButton';

interface RoutesListProps {
  routes: Route[];
  bounds: Bounds | null;
  selectedSlug: string | null;
  onSelect: (slug: string) => void;
  onHover: (slug: string | null) => void;
  onImport: () => void;
  onShowAll: (routes: Route[]) => void;
  /**
   * Set when the routes are ranked for a run (lib/routeMatch.ts): every
   * ranked route is listed, best first, wherever the map is, under this heading.
   */
  ranking?: { title: string } | null;
  /** The Saved category is picked: an empty list says how to save a route. */
  savedOnly?: boolean;
}

function TrailStats({ route }: { route: Route }) {
  const units = useUnits();
  const { gain, pending } = useTrailGain(route);
  return (
    <span className="result-card-gain cima-route-facts">
      <span><strong>{units.distance(route.distanceM)}</strong><small>Distanza</small></span>
      <span><strong>{gain == null ? (pending ? '…' : 'n.d.') : units.height(gain)}</strong><small>Dislivello +{gain != null && route.elevationAvailable === false ? ' · stimato' : ''}</small></span>
      <span><strong>{formatEstimate(routeEstimateS(route))}</strong><small>Tempo indicativo</small></span>
    </span>
  );
}

/** Routes are shown in the order given: the map page decides it. */
function RoutesListInner({ routes, bounds, selectedSlug, onSelect, onHover, onImport, onShowAll, ranking = null, savedOnly = false }: RoutesListProps) {
  const [limit, setLimit] = useState(18);
  const inView = useMemo(
    () => (bounds && !ranking ? routes.filter((route) => routeIntersects(route, bounds)) : routes),
    [routes, bounds, ranking],
  );
  // A route list that goes blank the moment you pan off the two places that
  // have routes reads as broken. Fall back to everything, and say so.
  const showingAll = inView.length === 0 && routes.length > 0;
  const rows = showingAll ? routes : inView;
  useEffect(() => setLimit(18), [bounds, ranking, savedOnly]);
  const visible = rows.slice(0, limit);

  return (
    <section className="results">
      <header className="results-head">
        <div>
          <h2>
            {rows.length} percors{rows.length === 1 ? 'o' : 'i'}
            {ranking ? ` ${ranking.title}` : showingAll ? ' disponibili' : ' nella zona'}
          </h2>
          {showingAll && (
            <p className="results-sub">
              Non ci sono percorsi in questa inquadratura.{' '}
              <button type="button" className="linkish" onClick={() => onShowAll(routes)}>
                Mostra tutti sulla mappa
              </button>
            </p>
          )}
        </div>
      </header>

      {routes.length === 0 && savedOnly ? (
        <div className="empty-state">
          <div className="empty-state-icon"><HeartIcon size={24} /></div>
          <h3>Ancora nessun percorso salvato</h3>
          <p>Tocca il cuore di un itinerario per ritrovarlo qui.</p>
        </div>
      ) : routes.length === 0 ? (
        <div className="empty-state">
          <div className="empty-state-icon"><UploadIcon size={24} /></div>
          <h3>Nessun percorso trovato</h3>
          <p>Prova a modificare i filtri oppure importa una traccia GPX.</p>
          <button type="button" className="btn btn-dark" onClick={onImport}>Importa GPX</button>
        </div>
      ) : (
        <ul className="results-grid">
          {visible.map((route, index) => {
            const region = trailArea(route);
            const mood = trailMood(route);
            return (
              <li
                key={route.slug}
                className={`result-item route-item${route.slug === selectedSlug ? ' selected' : ''}`}
                style={{ '--i': index } as React.CSSProperties}
                onMouseEnter={() => onHover(route.slug)}
                onMouseLeave={() => onHover(null)}
              >
                <span className={`result-badge cima-effort cima-effort--${mood.level}`} title={mood.basis}>{mood.label}</span>
                <RouteBookmarkButton route={route} variant="card" />
                <button
                  type="button"
                  className="result-action"
                  aria-label={`Scarica ${trailTitle(route)} in GPX`}
                  onClick={() => downloadRoute(route)}
                >
                  <DownloadIcon size={16} />
                </button>
                <button type="button" className="result-card" onClick={() => onSelect(route.slug)}>
                  <RouteThumb route={route} />
                  <span className="result-card-top">
                    <span className="result-card-name">{trailTitle(route)}</span>
                    <ActivityTag activity={routeActivity(route)} />
                  </span>
                  <span className="result-card-meta">
                    {[region, route.loop ? 'Anello' : 'Andata', route.source === 'local' ? 'Sul dispositivo' : null]
                      .filter(Boolean)
                      .join(' · ')}
                    {route.downloads !== undefined && (
                      <span className="card-dls">
                        <DownloadIcon size={11} />
                        {route.downloads}
                      </span>
                    )}
                  </span>
                  {mood.quip && <span className="cima-route-quip">{mood.quip}</span>}
                  <TrailStats route={route} />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      {rows.length > limit && <button type="button" className="btn btn-light cima-more-routes" onClick={() => setLimit((n) => n + 18)}>Mostra altri percorsi ({rows.length - limit} ancora)</button>
    </section>
  );
}

export const RoutesList = memo(RoutesListInner);
