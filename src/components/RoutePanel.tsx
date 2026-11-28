import { routeDetailHref } from '../lib/navigation';
import { alpinePlaceLink } from '../lib/alpinePlaces';
import { DetailMetrics, DetailSectionHeading } from './DetailPrimitives';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';
import { DetailJumpNav } from './DetailJumpNav';
import { FaIcon } from './FaIcon';
import { scrollToDetailSection } from '../lib/detailNavigation';
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { endpointIconMarkup } from '../map/endpoints';
import { RouteBookmarkButton } from './RouteBookmarkButton';
import type { Route, RoutePoint, Venue } from '../types';
import { computeGain, cumulativeDistances, totalDistanceM } from '../lib/elevation';
import { linkVenues, routeDirectionsUrl, routeEndpoints, routeHasElevation } from '../lib/routes';
import { trailArea, trailDescription, trailMood, trailTitle } from '../lib/routeEditorial';
import { routePresentationCategory } from '../lib/routeClassification';
import { hasRealElevation, terrainElevations } from '../lib/terrain';
import { assessRoute } from '../lib/routeQuality';
import { toGpx } from '../lib/gpx';
import { ACTIVITY_LABEL, findOverlaps, routeActivity, routeFingerprint, type RouteOverlap } from '../lib/routeAnalysis';
import { errorText, publicUrl, uploadRouteThumb, SUPABASE_CONFIGURED } from '../lib/api';
import { editMyRoute, useAuthUser } from '../lib/auth';
import { updateMyRoute, useMyRoutes } from '../lib/myRoutes';
import { useRouteReviews } from '../lib/useRouteReviews';
import { CreditChips } from './CreditChips';
import { HeldBadge, QualityNotice } from './QualityNotice';
import { RouteTrim } from './RouteTrim';
import { ElevationProfile } from './ElevationProfile';
import { TypeGlyph } from './TypeGlyph';
import { useUnits } from './UnitsContext';
import { downloadRoute } from './VenueCard';
import { estimateTrackDuration, formatEstimate } from '../lib/routeTime';
import { ArrowLeftIcon, ChevronRightIcon, CloseIcon, DownloadIcon, MapIcon, PencilIcon, ShareIcon } from './icons';
import { ShareRouteDialog } from './ShareRouteDialog';
import type { RoutePhoto } from '../lib/api';
import { RoutePhotoModal } from './RoutePhotoModal';
import { FlagIcon, ReportModal } from './ReportModal';
import { RatingLabel } from './ResultsList';
import { RouteReviews } from './RouteReviews';

/**
 * The route's name: it wraps onto up to two lines and never moves. If it is still too long it
 * ends in "…", and then it is a button that opens the whole name (and closes it again). Short
 * names are plain text. Everyone, screen readers included, always has the full name.
 */
function RouteTitle({ name, headingLevel = 2 }: { name: string; headingLevel?: 1 | 2 }) {
  const headingRef = useRef<HTMLHeadingElement>(null);
  const [cut, setCut] = useState(false);
  const [open, setOpen] = useState(false);
  useLayoutEffect(() => {
    const heading = headingRef.current;
    if (!heading) return;
    // Measured on the heading, which stays put when the text swaps between plain and button.
    const measure = () => {
      const text = heading.querySelector<HTMLElement>('.route-name');
      if (text && !open) setCut(text.scrollHeight > text.clientHeight + 1);
    };
    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(heading);
    return () => observer.disconnect();
  }, [name, open]);
  const text = <span className={`route-name${open ? ' open' : ''}`}>{name}</span>;
  const Heading = headingLevel === 1 ? 'h1' : 'h2';
  return (
    <Heading ref={headingRef} title={name} className="route-title-heading">
      {cut || open ? (
        <button type="button" className="route-name-toggle" aria-expanded={open} onClick={() => setOpen((current) => !current)}>
          {text}
        </button>
      ) : (
        text
      )}
    </Heading>
  );
}

interface RoutePanelProps {
  route: Route;
  venuesBySlug: Map<string, Venue>;
  allRoutes: Route[];
  hoverIndex: number | null;
  onHoverIndex: (index: number | null) => void;
  onClose: () => void;
  fullDetail?: boolean;
  /**
   * `map`: a card over the map (the expanded map, or a narrow screen).
   * `sidebar`: the left column of a split page, in place of the list, with every
   * detail open, so the map beside it can frame the whole route.
   */
  placement?: 'map' | 'sidebar';
  /**
   * Where both layouts fit (a wide split page), "More details" docks the details into the left
   * column and "Fewer details" floats the compact card back over the map. Absent where only the
   * card fits (narrow screens, the expanded map): there it opens in place.
   */
  onToggleDock?: () => void;
  /** Folded to a slim strip (name and the three numbers) while the map is moved by hand. */
  folded?: boolean;
  onUnfold?: () => void;
  spotlightSlug: string | null;
  onShowVenue: (slug: string) => void;
  onShowRoute: (slug: string) => void;
  routePhotos: RoutePhoto[];
  onFocusPhoto: (photo: RoutePhoto) => void;
  onPhotoAdded: (photo: RoutePhoto) => void;
  /** The signed-in owner is editing this route's name, credit and kept range. */
  editing?: boolean;
  /** Kept point range while editing; the ends outside it draw ghosted on the map. */
  editTrim?: [number, number] | null;
  onEditTrimChange?: (trim: [number, number] | null) => void;
  onEditStart?: () => void;
  /** Saved (the updated route) or cancelled (null). */
  onEditEnd?: (route: Route | null) => void;
}

const YEAR_MS = 365.25 * 24 * 3600 * 1000;

/** "Recorded 12 Mar 2024 · 2 years ago", with a nudge when a track is old enough that trails may have changed. */
export function RecordedLine({ recordedAt }: { recordedAt: string | null | undefined }) {
  // Read once per mount: "2 years ago" does not need to tick while the panel is open.
  const [now] = useState(() => Date.now());
  if (!recordedAt) return <p className="route-meta muted">Recording date not in file</p>;
  const date = new Date(recordedAt);
  const years = (now - date.getTime()) / YEAR_MS;
  const ago = years < 1 / 12 ? 'this month' : years < 1 ? `${Math.round(years * 12)} months ago` : `${Math.floor(years)} year${Math.floor(years) === 1 ? '' : 's'} ago`;
  return (
    <p className={`route-meta${years >= 3 ? ' stale' : ''}`}>
      Recorded {date.toLocaleDateString(undefined, { day: 'numeric', month: 'short', year: 'numeric' })} · {ago}
      {years >= 3 && ' · trails may have changed since'}
    </p>
  );
}

const TIP_W = 290;

/**
 * Secondary facts (when it was recorded, where EG/EL came from) behind an (i),
 * not in the way. The card floats over the page in a portal, placed under the
 * button: inside the panel it was clipped by the panel's own scrolling edge.
 */
export function InfoTip({ children, label = 'About these numbers' }: { children: React.ReactNode; label?: string }) {
  const [pos, setPos] = useState<{ top: number; left: number } | null>(null);
  const buttonRef = useRef<HTMLButtonElement>(null);
  const popRef = useRef<HTMLSpanElement>(null);
  const closeTimer = useRef<number | undefined>(undefined);
  const open = pos !== null;

  const show = () => {
    window.clearTimeout(closeTimer.current);
    const rect = buttonRef.current?.getBoundingClientRect();
    if (!rect) return;
    const left = Math.min(Math.max(12, rect.left + rect.width / 2 - 24), window.innerWidth - TIP_W - 12);
    setPos({ top: rect.bottom + 8, left });
  };
  const hide = () => {
    window.clearTimeout(closeTimer.current);
    closeTimer.current = window.setTimeout(() => setPos(null), 140);
  };

  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => {
      const target = event.target as Node;
      if (!buttonRef.current?.contains(target) && !popRef.current?.contains(target)) setPos(null);
    };
    // The button moves with the map panel; a floating card left behind would point at nothing.
    const away = () => setPos(null);
    document.addEventListener('mousedown', outside);
    window.addEventListener('resize', away);
    window.addEventListener('scroll', away, true);
    return () => {
      document.removeEventListener('mousedown', outside);
      window.removeEventListener('resize', away);
      window.removeEventListener('scroll', away, true);
    };
  }, [open]);
  useEffect(() => () => window.clearTimeout(closeTimer.current), []);

  // Hover shows it on a mouse; a tap toggles it on touch screens.
  const hoverable = () => window.matchMedia('(hover: hover)').matches;
  return (
    <span className="info-tip" onMouseEnter={() => hoverable() && show()} onMouseLeave={() => hoverable() && hide()}>
      <button
        ref={buttonRef}
        type="button"
        className="info-tip-btn"
        aria-label={label}
        aria-expanded={open}
        onClick={() => (open && !hoverable() ? setPos(null) : show())}
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" aria-hidden="true">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 11v5.5" />
          <circle cx="12" cy="7.8" r="0.6" fill="currentColor" />
        </svg>
      </button>
      {pos &&
        createPortal(
          <span
            ref={popRef}
            className="info-tip-pop floating"
            role="tooltip"
            style={{ top: pos.top, left: pos.left, width: TIP_W }}
            onMouseEnter={() => window.clearTimeout(closeTimer.current)}
            onMouseLeave={() => hoverable() && hide()}
          >
            {children}
          </span>,
          document.body,
        )}
    </span>
  );
}

export function ElevationSourceLine({ source }: { source: Route['elevationSource'] | 'dem' }) {
  const text = source === 'terrain'
    ? 'EG/EL measured from terrain data (the file had no elevation)'
    : source === 'dem'
      ? 'Dislivello stimato dal modello altimetrico'
      : 'Dislivello dai dati altimetrici della traccia';
  return <p className="route-meta muted">{text}</p>;
}

export function OverlapChips({ overlaps, onShowRoute }: { overlaps: RouteOverlap[]; onShowRoute: (slug: string) => void }) {
  if (overlaps.length === 0) return null;
  return (
    <div className="gpx-touches route-overlaps">
      <strong>Shares ground with</strong>
      {overlaps.slice(0, 4).map(({ route, share }) => (
        <button type="button" key={route.slug} onClick={() => onShowRoute(route.slug)} title={`${Math.round(share * 100)}% of this route runs along ${route.name}`}>
          {route.name} · {Math.round(share * 100)}%
        </button>
      ))}
    </div>
  );
}

/** Ground elevation for routes whose file had none, measured once per route on demand. */
function useTerrainFill(route: Route): { points: RoutePoint[]; gainM: number; lossM: number; fromTerrain: boolean; pending: boolean } {
  const needsFill = !routeHasElevation(route);
  const [filled, setFilled] = useState<{ slug: string; points: RoutePoint[] | null } | null>(null);
  useEffect(() => {
    if (!needsFill) return;
    let cancelled = false;
    void terrainElevations(route.coordinates).then((points) => {
      if (!cancelled) setFilled({ slug: route.slug, points });
    });
    return () => {
      cancelled = true;
    };
  }, [needsFill, route.coordinates, route.slug]);
  const ready = filled?.slug === route.slug ? filled.points : null;
  return useMemo(() => {
    if (!needsFill) return { points: route.coordinates, gainM: route.gainM, lossM: route.lossM, fromTerrain: false, pending: false };
    if (!ready) return { points: route.coordinates, gainM: 0, lossM: 0, fromTerrain: false, pending: filled?.slug !== route.slug };
    const { gainM, lossM } = computeGain(ready);
    return { points: ready, gainM, lossM, fromTerrain: true, pending: false };
  }, [needsFill, ready, route, filled]);
}

interface RouteEditFormProps {
  route: Route;
  /** Every place the app knows, to re-link the kept range's "Passes" list. */
  venues: Venue[];
  username: string;
  trim: [number, number] | null;
  onTrimChange: (trim: [number, number] | null) => void;
  hoverIndex: number | null;
  onHoverIndex: (index: number | null) => void;
  onSaved: (route: Route) => void;
  onCancel: () => void;
}

/**
 * Rename, re-credit or re-trim one of your own uploads. Mounted only while
 * the panel is in edit mode, so its fields always start from the stored
 * route. The trim drags ghost the ends on the map exactly like the
 * pre-publish cut; saving swaps the stored GPX for the kept slice.
 */
function RouteEditForm({ route, venues, username, trim, onTrimChange, hoverIndex, onHoverIndex, onSaved, onCancel }: RouteEditFormProps) {
  const [name, setName] = useState(route.name);
  const [anonymous, setAnonymous] = useState(!route.contributor);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const trimmed = trim !== null;
  const kept = useMemo(
    () => (trim ? route.coordinates.slice(trim[0], trim[1] + 1) : route.coordinates),
    [route.coordinates, trim],
  );
  const { gainM, lossM } = useMemo(() => computeGain(kept), [kept]);
  // Stored points are already simplified and carry no timestamps, so only the checks that survive that run.
  const keptQuality = useMemo(
    () => assessRoute({
      points: kept,
      activity: routeActivity(route),
      hasElevation: hasRealElevation(kept),
      deviceElevation: route.elevationSource === 'gps',
      spacing: 'simplified',
    }),
    [kept, route.activity, route.elevationSource],
  );
  const keptDistanceM = useMemo(() => Math.round(totalDistanceM(kept)), [kept]);
  const keepRange = useMemo<[number, number] | null>(() => {
    if (!trim) return null;
    const distances = cumulativeDistances(route.coordinates);
    const total = distances[distances.length - 1] || 1;
    return [distances[trim[0]] / total, distances[trim[1]] / total];
  }, [route.coordinates, trim]);

  const nextName = name.trim();
  const renamed = nextName !== route.name;
  const recredited = anonymous !== !route.contributor;
  const canSave = Boolean(nextName) && !busy && (renamed || recredited || trimmed);

  const save = async () => {
    setBusy(true);
    setError(null);
    try {
      const linked = trimmed ? linkVenues(kept, venues).slice(0, 200) : route.venueSlugs;
      const { gpxPath } = await editMyRoute(route.slug, {
        name: renamed ? nextName : undefined,
        anonymous: recredited ? anonymous : undefined,
        track: trimmed
          ? {
              points: kept,
              distanceM: keptDistanceM,
              gainM,
              lossM,
              venueSlugs: linked,
              fingerprint: routeFingerprint(kept),
              gpxText: toGpx(nextName, kept),
              qualityFlags: keptQuality.flags,
            }
          : undefined,
      });
      const first = kept[0];
      const last = kept[kept.length - 1];
      const updated: Route = {
        ...route,
        name: nextName,
        contributor: anonymous ? undefined : username,
        coordinates: kept,
        distanceM: keptDistanceM,
        gainM,
        lossM,
        venueSlugs: linked,
        loop: trimmed ? Boolean(first && last && Math.hypot(first[0] - last[0], first[1] - last[1]) < 0.001) : route.loop,
        gpxUrl: gpxPath ? publicUrl('gpx', gpxPath) : route.gpxUrl,
        // The database re-decides from the flags: a pass releases a held route, a fail holds a published one.
        held: trimmed ? keptQuality.verdict === 'held' || undefined : route.held,
      };
      updateMyRoute(route.slug, {
        name: updated.name,
        anonymous,
        distanceM: updated.distanceM,
        gainM: updated.gainM,
        ...(trimmed ? { status: keptQuality.verdict === 'held' ? 'pending' as const : 'approved' as const, qualityFlags: keptQuality.flags } : {}),
      });
      onSaved(updated);
      if (trimmed) {
        // The card image shows the old line; re-render it like a fresh publish.
        void import('../map/renderThumb')
          .then(({ renderRouteThumb }) => renderRouteThumb(updated))
          .then((thumb) => (thumb ? uploadRouteThumb(updated.slug, thumb.key, thumb.blob) : undefined))
          .catch(() => undefined);
      }
    } catch (caught) {
      setError(errorText(caught));
      setBusy(false);
    }
  };

  return (
    <div className="route-edit">
      <label className="field">
        <span>Route name</span>
        <input value={name} onChange={(event) => setName(event.target.value)} maxLength={120} required />
      </label>
      <CreditChips username={username} anonymous={anonymous} onChange={setAnonymous} />
      <ElevationProfile
        points={route.coordinates}
        height={96}
        hoverIndex={hoverIndex}
        onHoverIndex={onHoverIndex}
        keepRange={keepRange}
      />
      <RouteTrim points={route.coordinates} trim={trim} onChange={onTrimChange} />
      {trimmed && <QualityNotice flags={keptQuality.flags} heading={keptQuality.verdict === 'held' ? 'Only you will see this route until it is fixed:' : undefined} />}
      {trimmed && (
        <p className="route-meta muted small">
          The stored GPX is replaced with the kept track — the greyed ends leave the archive for good.
        </p>
      )}
      {error && <p className="gpx-import-error" role="alert">{error}</p>}
      <div className="route-edit-actions">
        <button type="button" className="btn btn-light" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className="btn btn-accent" disabled={!canSave} onClick={() => void save()}>
          {busy ? 'Saving…' : 'Save changes'}
        </button>
      </div>
    </div>
  );
}

/**
 * The selected route, over the map with its profile: a side sheet down the
 * left of a wide map, a sheet along the bottom of a narrow one.
 *
 * Compact by default — title, the three numbers people compare routes by, and
 * a short profile — so the route itself keeps most of the map. "More details"
 * grows it into the full sheet (every stat, places passed, overlaps, photos).
 *
 * While the visitor pans or zooms by hand it folds to a slim strip so the
 * route's outline is in view; the rest stays mounted (and "More details"
 * keeps its state), only hidden, and comes back on a tap or once the map
 * rests. Its size changes never re-frame the map: framing reads the panel
 * only when the app itself moves the camera.
 */
export function RoutePanel({ placement = 'map', onToggleDock, fullDetail = false, route, venuesBySlug, allRoutes, hoverIndex, onHoverIndex, onClose, folded = false, onUnfold, spotlightSlug, onShowVenue, onShowRoute, routePhotos, onFocusPhoto, onPhotoAdded, editing = false, editTrim = null, onEditTrimChange, onEditStart, onEditEnd }: RoutePanelProps) {
  const [adding, setAdding] = useState(false);
  const [reporting, setReporting] = useState(false);
  const sidebar = placement === 'sidebar';
  const [expandedByHand, setExpanded] = useState(false);
  const expanded = fullDetail || sidebar || expandedByHand;
  const user = useAuthUser();
  const { routes: myUploads } = useMyRoutes();
  // Only the owner may edit a community route; the upload list is the
  // authority (server-side ownership — contributor text is just the credit).
  const mine = route.source === 'community' && Boolean(myUploads?.some((upload) => upload.slug === route.slug));
  const editMode = editing && mine && Boolean(user);
  const moreRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    moreRef.current?.toggleAttribute('inert', !expanded);
  }, [expanded]);
  // Only approved routes take reviews: nobody else can see a held, rejected or on-device one.
  const reviewable = route.source !== 'local' && !route.held && !route.rejected;
  const reviewsState = useRouteReviews(route.slug, reviewable, user?.id ?? null);
  const units = useUnits();
  // Only a route anyone can open has a link worth sharing: not one held, rejected or kept on this device.
  const shareable = reviewable;
  const directionsHref = routeDirectionsUrl(route.coordinates);
  const [sharing, setSharing] = useState(false);
  const elevation = useTerrainFill(route);
  const hasElevation = routeHasElevation(route) || elevation.fromTerrain;
  // Terrain-filled elevation counts once it has arrived; the estimate is by distance alone until then.
  const estimate = useMemo(
    () => estimateTrackDuration(elevation.points, routeActivity(route), 1, hasElevation),
    [elevation.points, route, hasElevation],
  );
  const endpoints = useMemo(() => routeEndpoints(route.coordinates), [route.coordinates]);
  // Said once when the route opens: the markers are only on the map, where a screen reader cannot see them.
  const [announced, setAnnounced] = useState('');
  useEffect(() => {
    if (!endpoints) return;
    const timer = window.setTimeout(
      () => setAnnounced(`${route.name} selected. ${endpoints.isLoop ? 'Start and finish are at the same point.' : 'Start and finish are marked on the map.'}`),
      400,
    );
    return () => window.clearTimeout(timer);
  }, [route.slug, route.name, endpoints]);
  const { minM, maxM } = useMemo(() => computeGain(elevation.points), [elevation.points]);
  const overlaps = useMemo(() => findOverlaps(route.coordinates, allRoutes, route.slug), [route, allRoutes]);
  const region = trailArea(route);
  const mood = trailMood(route, {gainM:elevation.gainM,elevationAvailable:hasElevation});
  const routeKind = routePresentationCategory(route);
  const displayTitle = trailTitle(route);
  const touches = route.venueSlugs
    .map((slug) => venuesBySlug.get(slug))
    .filter((venue): venue is Venue => Boolean(venue));
  const km = totalDistanceM(route.coordinates) / 1000 || 1;
  const unavailable = elevation.pending ? 'Calcolo…' : 'Non disponibile';

  return (
    <section className={`gpx-panel route-panel ${expanded ? 'expanded' : 'compact'}${folded ? ' folded' : ''}${sidebar ? ' in-sidebar' : ''}${fullDetail ? ' is-full-detail' : ''}`} aria-label={`Route: ${route.name}`} key={route.slug}>
      {sidebar ? (
        <button type="button" className="route-back" onClick={onClose}>
          <ArrowLeftIcon size={16} />
          Tutti i percorsi
        </button>
      ) : (
        /* A light runs once round the card's edge when a route opens. */
        <span className="route-panel-orbit" aria-hidden="true" />
      )}
      {folded && (
        <button type="button" className="route-panel-unfold" onClick={onUnfold} aria-label={`Show details for ${route.name}`} />
      )}
      {fullDetail&&<figure className="cb-route-hero">
        {route.photos?.[0]?<img src={route.photos[0].url} loading="lazy" alt={route.photos[0].caption||displayTitle}/>:
          <div className="cb-route-hero-fallback" role="img" aria-label="Illustrazione topografica del sentiero: fotografia non disponibile"/>}
        <figcaption><span>{routeKind.kind==='ferrata'?(routeKind.evidence==='inferred'?'POSSIBILE VIA FERRATA':'VIA FERRATA'):routeKind.kind==='attrezzato'?'ITINERARIO ATTREZZATO · DA VERIFICARE':'SENTIERO / ESCURSIONE'}</span>
          {route.photos?.[0]?<small>Foto: {route.photos[0].author||'Wikimedia Commons'} · {route.photos[0].license||'Licenza nella fonte'}</small>:<small>Foto da documentare</small>}</figcaption>
      </figure>}
      <header className="gpx-panel-head">
        <div className="route-panel-title">
          <RouteTitle name={displayTitle} headingLevel={fullDetail ? 1 : 2} />
          <InfoTip>
            <RecordedLine recordedAt={route.recordedAt} />
            {hasElevation && <ElevationSourceLine source={elevation.fromTerrain ? 'terrain' : route.elevationSource ?? 'gps'} />}
            <span className="route-meta muted">{[routeKind.label, region, route.loop ? 'Anello' : 'Percorso lineare'].filter(Boolean).join(' · ')}</span>
            <button type="button" className="info-tip-action" onClick={() => setReporting(true)}>
              <FlagIcon />
              Segnala un problema con il percorso
            </button>
          </InfoTip>
        </div>
        <div className="gpx-panel-actions">
          {mine && !editMode && (
            <button
              type="button"
              className="gpx-icon-btn"
              onClick={() => {
                onUnfold?.();
                onEditStart?.();
              }}
              aria-label={`Edit ${route.name}`}
              data-tip="Edit route"
            >
              <PencilIcon size={15} />
            </button>
          )}
          <RouteBookmarkButton route={route} variant="panel" />
          {shareable && (
            <button type="button" className="gpx-icon-btn" onClick={() => setSharing(true)} aria-label="Share this route" aria-haspopup="dialog" data-tip="Share">
              <ShareIcon size={15} />
            </button>
          )}
          <button type="button" className="gpx-icon-btn" onClick={() => downloadRoute(route)} aria-label="Download GPX" data-tip="Download GPX">
            <DownloadIcon size={15} />
          </button>
          {!sidebar && (
            <button type="button" className="gpx-close" onClick={onClose} aria-label="Close route">
              <CloseIcon size={12} />
            </button>
          )}
        </div>
      </header>
      {fullDetail&&<DetailJumpNav items={[
        {id:'cb-route-summary',label:'In breve',icon:'route'},
        {id:'cb-route-elevation',label:'Altimetria',icon:'mountain'},
        ...(route.stops?.length?[{id:'cb-route-destinations',label:'Rifugi e paesi',icon:'house' as const}]:[]),
        ...(route.waterSources?.length?[{id:'cb-route-water',label:'Acqua',icon:'water' as const}]:[]),
        {id:'cb-route-technical',label:'Dettagli',icon:'compass'},
        {id:'cb-route-photos',label:'Foto',icon:'camera'},
      ]}/>}
      <span className="visually-hidden" role="status">{announced}</span>
      {mine && route.held && (
        <div className="route-held">
          <HeldBadge />
          <QualityNotice
            flags={(myUploads?.find((upload) => upload.slug === route.slug)?.qualityFlags ?? []).filter((f) => f.severity === 'key')}
            heading="Held until it is fixed. Trim the problem out, or ask a maintainer to review it."
          />
        </div>
      )}

      {editMode && user ? (
        <RouteEditForm
          route={route}
          venues={[...venuesBySlug.values()]}
          username={user.username}
          trim={editTrim}
          onTrimChange={(next) => onEditTrimChange?.(next)}
          hoverIndex={hoverIndex}
          onHoverIndex={onHoverIndex}
          onSaved={(updated) => onEditEnd?.(updated)}
          onCancel={() => onEditEnd?.(null)}
        />
      ) : (
        <>
      {fullDetail&&<AtlasDossierBlocks record={route} placement="alerts"/>}
      {(routeKind.kind==='ferrata'||routeKind.kind==='attrezzato')&&<div className="cb-route-equipment-warning" role="note">
        <strong>{routeKind.evidence==='inferred'?'TIPOLOGIA TECNICA DA CONFERMARE':'ATTENZIONE: PERCORSO ATTREZZATO'}</strong>
        <p>{routeKind.reason}. Un GPX non documenta protezioni, esposizione, condizioni degli infissi né chiusure.
          {routeKind.kind==='ferrata'?' Per affrontare una ferrata occorrono preparazione e dispositivi di protezione specifici; verifica una relazione tecnica aggiornata.':' Verifica con una fonte qualificata se occorre il kit da ferrata.'}</p>
      </div>}
      <div id={fullDetail?'cb-route-summary':undefined} className="cima-trail-mood">
        <strong className={`cima-mood-pill cima-mood-pill--${mood.level}`} title={mood.basis}>{mood.quip}</strong>
        <span className="cima-mood-technical">{mood.label}</span>
        <span className="cima-trail-area">{region}{route.loop ? ' · Anello' : ''}</span>
      </div>
      <p className="cima-route-description">{trailDescription(route)}</p>
      {(fullDetail||expanded)&&<div className="cb-route-effort-explanation">
        <strong>Perché questa etichetta?</strong>
        <p>{mood.explanation}</p>
      </div>}
      <DetailMetrics label="Dati principali del percorso" items={[
        { label: 'Distanza', value: units.distance(route.distanceM) },
        { label: 'Dislivello positivo', value: hasElevation ? units.height(elevation.gainM) : unavailable },
        { label: 'Dislivello negativo', value: hasElevation ? units.height(elevation.lossM) : unavailable },
        { label: 'Tempo stimato', value: formatEstimate(estimate.minutes * 60), title: estimate.caption },
        ...(route.downloads !== undefined ? [{ label: 'Download', value: String(route.downloads) }] : []),
      ]}/>

      <div id={fullDetail?'cb-route-elevation':undefined} className={fullDetail?'cb-detail-group cb-route-elevation-section':undefined}>
        {hasElevation ? (
          <ElevationProfile points={elevation.points} height={sidebar ? 132 : 72} hoverIndex={hoverIndex} onHoverIndex={onHoverIndex} />
        ) : (
          <p className="route-elevation-unavailable">{elevation.pending ? 'Sto stimando il dislivello dal terreno…' : 'Dislivello non disponibile per questo tracciato.'}</p>
        )}
      </div>

      {!fullDetail && route.photos?.[0] && <figure className="cima-route-cover">
        <img src={route.photos[0].url} alt={route.photos[0].caption || displayTitle} loading="lazy" />
        <small>Fotografia: {route.photos[0].author || 'Wikimedia Commons'} · {route.photos[0].license || 'licenza nella fonte'}</small>
      </figure>}
      {route.stops && route.stops.length > 0 && (
        <section id={fullDetail?'cb-route-destinations':undefined} className={fullDetail?'cb-route-destinations cb-detail-group':'cb-route-destinations'} aria-label="Rifugi e località vicine alla traccia">
          <h3>RIFUGI &amp; POSTI DOVE FINIRE</h3>
          <p>Questi luoghi sono stati trovati vicino alla traccia. Il sentiero non garantisce accesso diretto.</p>
          <div className="cb-route-destination-list">
            {route.stops.slice(0, 7).map((stop) => (
              <a key={stop.slug} href={alpinePlaceLink({kind:stop.kind,slug:stop.slug})}>
                <strong>{stop.name}</strong>
                <small>{stop.kind === 'rifugio' ? 'RIFUGIO' : stop.kind === 'bivacco' ? 'BIVACCO' : 'PAESE'} · {stop.relation === 'arrivo' ? 'ZONA ARRIVO' : stop.relation === 'partenza' ? 'ZONA PARTENZA' : 'LUNGO IL TRACCIATO'} ↗</small>
              </a>
            ))}
          </div>
        </section>
      )}
      {route.waterSources && route.waterSources.length>0 && (
        <section id={fullDetail?'cb-route-water':undefined} className={fullDetail?'cb-route-water cb-detail-group':'cb-route-water'} aria-label="Punti acqua nei pressi del GPX">
          <strong>QUA L'ACQUA NON LA PORTA LO SHERPA.</strong>
          <p>Nei dati cartografici risultano <b>{route.waterSources.length}</b> punti acqua entro 120 metri dalla traccia.
            {' '}{route.waterSources.filter(w=>w.potable==='yes').length} con indicazione OSM di potabilità; per gli altri non darla per scontata.</p>
          <div className="cb-route-water-points">
            {route.waterSources.slice(0,8).map(w=>(
              <a key={w.slug} href={routeDetailHref(route.slug,route.source)} onClick={fullDetail?event=>{event.preventDefault();scrollToDetailSection('cb-route-map');}:undefined}>
                <span>{w.name}</span>
                <small>{w.potable==='yes'?'POTABILITÀ INDICATA':w.potable==='no'?'NON POTABILE':'NON VERIFICATA'} · {w.distanceM} m dal GPX · APRI SULLA MAPPA</small>
              </a>
            ))}
          </div>
          <small>Prossimità geometrica ≠ accesso, disponibilità o sicurezza dell’acqua. Verifica sul posto.</small>
        </section>
      )}
      {reviewable && !reviewsState.error && (
        <p className="route-rating">{reviewsState.reviews && <RatingLabel rating={reviewsState.rating} />}</p>
      )}
      {endpoints && (
        <p className="route-legend">
          {endpoints.isLoop ? (
            <span><span aria-hidden="true" dangerouslySetInnerHTML={{ __html: endpointIconMarkup('loop', 18) }} />Partenza e arrivo</span>
          ) : (
            <>
              <span><span aria-hidden="true" dangerouslySetInnerHTML={{ __html: endpointIconMarkup('start', 18) }} />Partenza</span>
              <span><span aria-hidden="true" dangerouslySetInnerHTML={{ __html: endpointIconMarkup('finish', 18) }} />Arrivo</span>
            </>
          )}
        </p>
      )}

      {directionsHref && (
        <a className="venue-primary-action route-directions" href={directionsHref} target="_blank" rel="noreferrer" aria-label="Get directions to the start (opens in maps)">
          <MapIcon size={16} />
          Indicazioni per la partenza
        </a>
      )}

      {/* Always rendered, so opening it can slide; inert while folded. */}
      <div className="route-more" id={`route-more-${route.slug}`} ref={moreRef}>
        <div className="route-more-inner">
          <div id={fullDetail?'cb-route-technical':undefined} className={fullDetail?'cb-detail-group cb-route-technical-section':undefined}>
            {fullDetail&&<DetailSectionHeading kicker="03 / TRACCIA" title="Dati tecnici e quote"/>}
          {(route.trailRef || route.caiDifficulty || route.viaFerrataScale || route.sacScale || route.officialDescriptionUrl || route.sourceUrl) && (
            <section className="route-official-data" aria-label="Segnavia e dati tecnici">
              <DetailSectionHeading kicker="03 / DETTAGLI TECNICI" title="Segnavia e dati tecnici"/>
              <p className="route-meta muted">
                {[
                  route.caiTrailNumber ? `Sentiero CAI ${route.caiTrailNumber}` : route.trailRef ? `Segnavia ${route.trailRef}` : null,
                  route.caiDifficulty ? `Difficoltà CAI ${route.caiDifficulty}` : null,
                  route.sacScale ? `Scala SAC: ${route.sacScale}` : null,
                  route.viaFerrataScale ? `Scala ferrata: ${route.viaFerrataScale}` : null,
                  route.operator ? `Gestore: ${route.operator}` : null,
                ].filter(Boolean).join(' · ')}
              </p>
              {(routeKind.kind === 'ferrata'||routeKind.kind==='attrezzato') && <p className="route-meta muted">{routeKind.label}: la sola traccia GPX non certifica condizioni, difficoltà tecnica, protezioni o accessibilità. Consulta una relazione e una fonte aggiornata.</p>}
            </section>
          )}
          <DetailMetrics label="Quote e pendenze del percorso" items={[
            { label: 'Quota massima', value: hasElevation ? units.height(maxM) : unavailable },
            { label: 'Quota minima', value: hasElevation ? units.height(minM) : unavailable },
            { label: 'Salita per km', value: hasElevation ? units.height(elevation.gainM / km) : unavailable },
          ]}/>

          {fullDetail && <AtlasDossierBlocks record={route} placement="core"/>}
          </div>
          {touches.length > 0 && (
            <div className="gpx-touches route-passes">
              <strong>Luoghi attraversati</strong>
              <div className="route-passes-line">
                {touches.map((venue) => (
                  <button
                    type="button"
                    key={venue.slug}
                    className={venue.slug === spotlightSlug ? 'on' : undefined}
                    aria-pressed={venue.slug === spotlightSlug}
                    title={venue.slug === spotlightSlug ? 'Show the whole route again' : `Show ${venue.name} on the map`}
                    onClick={() => onShowVenue(venue.slug)}
                  >
                    <TypeGlyph type={venue.type} />
                    {venue.name}
                  </button>
                ))}
              </div>
            </div>
          )}

          <OverlapChips overlaps={overlaps} onShowRoute={onShowRoute} />
          {fullDetail && <AtlasDossierBlocks record={route} placement="connections"/>}
          {fullDetail && <AtlasDossierBlocks record={route} placement="media"/>}
          {fullDetail && <AtlasDossierBlocks record={route} placement="credits"/>}

          <div id={fullDetail?'cb-route-photos':undefined} className={fullDetail?'route-photos cb-detail-group':'route-photos'}>
            <strong>Fotografie lungo il percorso</strong>
            {(route.photos ?? []).map((photo) => (
              <a key={`${photo.url}-${photo.sourceUrl}`} className="route-photo-thumb" href={photo.sourceUrl} target="_blank" rel="noopener noreferrer" title={[photo.caption, photo.author, photo.license].filter(Boolean).join(' · ')}>
                <img src={photo.url} alt={photo.caption || `Fotografia associata a ${route.name}`} loading="lazy" />
              </a>
            ))}
            {(route.photos ?? []).length > 0 && (
              <p className="photo-credit small muted">
                Fonti: {(route.photos ?? []).map((photo, i) => (
                  <span key={photo.sourceUrl}>
                    {i > 0 ? ' · ' : ''}
                    <a href={photo.sourceUrl} target="_blank" rel="noopener noreferrer">{photo.author || 'Wikimedia Commons'}</a>
                    {photo.license ? ` (${photo.license})` : ''}
                  </span>
                ))}
              </p>
            )}
            {routePhotos.map((photo) => (
              <button type="button" key={photo.id} className={`route-photo-thumb ${photo.kind}`} onClick={() => onFocusPhoto(photo)} title={photo.caption || (photo.kind === 'hazard' ? 'Hazard' : 'Photo')}>
                <img src={photo.url} alt="" loading="lazy" />
                {photo.kind === 'hazard' && <span aria-label="Hazard">!</span>}
              </button>
            ))}
            {SUPABASE_CONFIGURED && <button type="button" className="route-photo-add" onClick={() => setAdding(true)}>
              <FaIcon name="camera" size={14}/>
              Aggiungi foto o segnalazione
            </button>}
          </div>

          {reviewable && <RouteReviews key={route.slug} routeSlug={route.slug} state={reviewsState} />}
        </div>
      </div>

      {!fullDetail && (shareable ? (
        <a className="route-more-toggle" href={routeDetailHref(route.slug, route.source)}
          aria-label={`Apri la scheda completa di ${displayTitle}`}>
          <span>VEDI SCHEDA COMPLETA</span><ChevronRightIcon size={13} />
        </a>
      ) : (
        <button type="button" className="route-more-toggle"
          onClick={() => (onToggleDock ? onToggleDock() : setExpanded(value => !value))}
          aria-expanded={expanded} aria-controls={`route-more-${route.slug}`}>
          <span>{expanded ? 'Meno dettagli' : 'Più dettagli'}</span><ChevronRightIcon size={13} />
        </button>
      ))}
        </>
      )}

      {adding && <RoutePhotoModal route={route} startIndex={hoverIndex ?? Math.floor(route.coordinates.length / 2)} onPreviewIndex={onHoverIndex} onClose={() => setAdding(false)} onAdded={onPhotoAdded} />}
      {sharing && <ShareRouteDialog route={route} gainM={hasElevation ? elevation.gainM : null} onClose={() => setSharing(false)} />}
      {reporting && <ReportModal targetType="route" targetSlug={route.slug} targetName={route.name} onClose={() => setReporting(false)} />}
    </section>
  );
}
