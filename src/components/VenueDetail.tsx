import { Suspense, lazy, useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState, useSyncExternalStore, type ChangeEvent, type ReactNode } from 'react';
import { createPortal } from 'react-dom';
import type { Route, Venue, VenuePhoto } from '../types';
import {
  HEIGHT_LABEL,
  commonsFileName,
  photoKey,
  photoSrc,
  tallestWithin,
  titleCaseStreet,
  townName,
  venueHeight,
  venueKindLabel,
  venuePhotoKeys,
  venuePhotos,
} from '../lib/venues';
import { useUnits } from './UnitsContext';
import { ElevationProfile } from './ElevationProfile';
import { PlaceArt, VenueThumb } from './VenueThumb';
import { CheckIcon, ChevronLeftIcon, ChevronRightIcon, CloseIcon, DownloadIcon, HeartIcon, MapIcon, StarIcon, UploadIcon } from './icons';
import { FlagIcon, LinkIcon, PlusIcon, ReportModal } from './ReportModal';
import { useReveal } from './useReveal';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';
import { SummitConnections } from './SummitConnections';
import { DetailJumpNav } from './DetailJumpNav';
import { FaIcon } from './FaIcon';
import { MapContextLabel } from './MapContextLabel';
import { SEARCH_OPENS_MAP, SearchBar, SiteSearch } from './SearchBar';
import { RatingLabel } from './ResultsList';
import { ReviewCard, StarPicker } from './ReviewCard';
import { directionsUrl, venueConditions, type Conditions } from '../lib/conditions';
import { downloadRoute } from './VenueCard';
import { RouteThumb } from './RouteThumb';
import { Modal } from './Modal';
import { FadeImage } from './FadeImage';
import { OpenSourceBadge } from './OpenSourceNotice';
import { openImportHere, requestReport, requestReviewReport } from '../lib/contribute';
import {
  type CommunityPhoto,
  type Review,
  combinedRating,
  fetchPhotos,
  errorText,
  fetchReviews,
  submitPhoto,
  submitReview,
} from '../lib/api';
import { useAuthUser } from '../lib/auth';
import { CreditChips } from './CreditChips';
import { regionOf } from '../lib/regions';
import { lockPageScroll } from '../lib/dom';
import { routeHasElevation } from '../lib/routes';
import { ACTIVITY_LABEL, routeActivity } from '../lib/routeAnalysis';
import { isWorldPeakSlug, loadPeakPhotos } from '../lib/worldPeaks';
import { commonsPhotos, generatedDescription, wikiSummary, type GeneratedDescription, type WikiSummary } from '../lib/wiki';

const MiniMap = lazy(() => import('./MiniMap').then((module) => ({ default: module.MiniMap })));

/** Airbnb's grid: one large photo and up to four small ones. */
const GRID_SIZE = 5;

/** Built climbs: a Commons photo "within 1 km" of a block is a photo of somewhere else. */
const BUILT_TYPES: ReadonlySet<Venue['type']> = new Set(['hdb_block', 'stairs', 'carpark']);

/** One photo in the gallery, from whichever source it came. */
interface GalleryPhoto {
  key: string;
  src: string;
  /** Lower-resolution file to fall back to if the sharp one is missing. */
  fallback?: string;
  credit: string;
  creditUrl?: string;
  licence?: string;
  /** Identities used to drop the same file arriving from two sources (see `photoKey`). */
  keys: string[];
  /** Set for photos people added here, which anyone can report. */
  communityId?: string;
}

/**
 * The stored files are 420 px card thumbnails (and world-summit links are
 * 960 px thumbs), soft at page width. Commons photos are fetched sharp straight
 * from Wikimedia (Special:FilePath scales on request); Mapillary originals are
 * not kept, so those stay at card size.
 */
function sharpPhoto(photo: VenuePhoto): string | undefined {
  const name = commonsFileName(photo.sourceUrl ?? '') ?? commonsFileName(photo.file);
  return name ? `https://commons.wikimedia.org/wiki/Special:FilePath/${encodeURIComponent(name)}?width=1280` : undefined;
}

function storedGalleryPhoto(photo: VenuePhoto): GalleryPhoto {
  const sharp = sharpPhoto(photo);
  return {
    key: photo.file,
    src: sharp ?? photoSrc(photo),
    fallback: sharp ? photoSrc(photo) : undefined,
    credit: photo.credit ?? (photo.source ?? 'Mapillary'),
    creditUrl: photo.sourceUrl,
    licence: photo.license ?? (photo.source ? undefined : 'CC BY-SA · Mapillary'),
    keys: venuePhotoKeys(photo),
  };
}

function useVenueContent(venue: Venue) {
  const [reviews, setReviews] = useState<Review[]>([]);
  const [communityPhotos, setCommunityPhotos] = useState<CommunityPhoto[]>([]);
  const [commons, setCommons] = useState<GalleryPhoto[]>([]);
  const [wiki, setWiki] = useState<WikiSummary | null>(null);
  const [generated, setGenerated] = useState<GeneratedDescription | null>(null);

  useEffect(() => {
    let cancelled = false;
    const guard = <T,>(set: (value: T) => void) => (value: T) => {
      if (!cancelled) set(value);
    };
    fetchReviews(venue.slug).then(guard(setReviews)).catch(() => undefined);
    fetchPhotos(venue.slug).then(guard(setCommunityPhotos)).catch(() => undefined);
    wikiSummary(venue).then(guard(setWiki)).catch(() => undefined);
    generatedDescription(venue.slug).then(guard(setGenerated)).catch(() => undefined);
    // Open-licence photos taken nearby fill out a hill's grid, after its own
    // photos. Never for blocks and stairs: nearby is not the place.
    const stored = venuePhotos(venue);
    if (!BUILT_TYPES.has(venue.type) && venue.sourceIds?.wikidataVerifiedBy !== 'P1566+P625' && stored.length < GRID_SIZE) {
      const peakPhoto = stored.length === 0 && isWorldPeakSlug(venue.slug)
        ? loadPeakPhotos().then((photos) => photos.get(venue.slug))
        : Promise.resolve(undefined);
      Promise.all([peakPhoto, commonsPhotos(venue)])
        .then(([lead, nearby]) => [
          ...(lead ? [{ url: lead.url, pageUrl: lead.pageUrl, artist: lead.credit, licence: lead.licence, nearby: false }] : []),
          ...nearby.map((photo) => ({ ...photo, nearby: true })),
        ])
        .then((photos) => photos.map((photo, i): GalleryPhoto => ({
          key: `commons-${i}`,
          src: photo.url,
          credit: photo.artist,
          creditUrl: photo.pageUrl,
          licence: `${photo.licence} · Wikimedia Commons${photo.nearby ? ', taken nearby' : ''}`,
          keys: [photoKey(photo.url), photoKey(photo.pageUrl)],
        })))
        .then(guard(setCommons))
        .catch(() => undefined);
    }
    return () => {
      cancelled = true;
    };
  }, [venue]);

  // After someone adds photos they are live, so fetch the list again.
  const reloadPhotos = useCallback(() => {
    fetchPhotos(venue.slug).then(setCommunityPhotos).catch(() => undefined);
  }, [venue.slug]);

  return { reviews, setReviews, communityPhotos, reloadPhotos, commons, wiki, generated };
}

const NARROW_QUERY = '(max-width: 743px)';
function subscribeNarrow(onChange: () => void) {
  const query = window.matchMedia(NARROW_QUERY);
  query.addEventListener('change', onChange);
  return () => query.removeEventListener('change', onChange);
}
/** Phones get the swipe carousel; wider screens get Airbnb's photo grid. */
function useNarrow(): boolean {
  return useSyncExternalStore(subscribeNarrow, () => window.matchMedia(NARROW_QUERY).matches);
}

function swapToFallback(photo: GalleryPhoto) {
  return (event: React.SyntheticEvent<HTMLImageElement>) => {
    if (photo.fallback && event.currentTarget.src !== photo.fallback) event.currentTarget.src = photo.fallback;
  };
}

function PhotoCreditText({ photo }: { photo: GalleryPhoto }) {
  return (
    <>
      Foto di {photo.creditUrl ? <a href={photo.creditUrl} target="_blank" rel="noreferrer">{photo.credit}</a> : photo.credit}
      {photo.licence ? ` · ${photo.licence}` : ''}
    </>
  );
}

const creditTitle = (photo: GalleryPhoto) => `Foto di ${photo.credit}${photo.licence ? ` · ${photo.licence}` : ''}`;

/** No photo at all: the same drawn placeholder the cards use, with the invitation on top. */
function NoPhotos({ venue, onAdd, actions }: { venue: Venue; onAdd: () => void; actions?: ReactNode }) {
  return (
    <div className="venue-gallery-empty has-art">
      <PlaceArt venue={venue} />
      {actions && <div className="carousel-actions">{actions}</div>}
      <div className="venue-gallery-empty-copy">
        <CameraGlyph />
        <strong>Nessuna fotografia disponibile</strong>
        <p>Conosci questo luogo? Una fotografia pertinente può arricchirne la scheda.</p>
        <button type="button" className="btn btn-dark" onClick={onAdd}>Aggiungi una foto</button>
      </div>
    </div>
  );
}

/**
 * Airbnb's listing photos on wide screens: one large photo on the left and up
 * to four on the right, rounded on the outside corners only. Any photo opens
 * the full-screen viewer, which steps through every photo with its credit; the
 * last cell says how many more there are. One photo fills the frame.
 */
function PhotoGrid({ photos, venueName, onAdd, centralCreditsOnly = false }: { photos: GalleryPhoto[]; venueName: string; onAdd: () => void; centralCreditsOnly?: boolean }) {
  const [viewer, setViewer] = useState<number | null>(null);
  const closeViewer = useCallback(() => setViewer(null), []);
  const shown = photos.slice(0, GRID_SIZE);
  const count = photos.length;
  const hidden = count - shown.length;

  return (
    <div className="venue-photo-grid-wrap">
      <div className="venue-photo-frame">
        <div className={`venue-photo-grid n${shown.length}`}>
          {shown.map((photo, i) => (
            <button
              type="button"
              key={photo.key}
              className="venue-photo-cell"
              title={centralCreditsOnly ? venueName : creditTitle(photo)}
              aria-label={`Apri foto ${i + 1} of ${count} of ${venueName}`}
              onClick={() => setViewer(i)}
            >
              <FadeImage src={photo.src} alt="" loading={i === 0 ? 'eager' : 'lazy'} decoding="async" onError={swapToFallback(photo)} />
              {hidden > 0 && i === shown.length - 1 && <span className="venue-photo-more">+{hidden}</span>}
            </button>
          ))}
        </div>
        <div className="venue-photo-grid-actions">
          <button type="button" className="venue-photo-pill" onClick={onAdd}><PlusIcon />Aggiungi foto</button>
        </div>
      </div>
      {!centralCreditsOnly && <p className="venue-photo-credit"><PhotoCreditText photo={photos[0]} /></p>}
      {viewer != null && <Lightbox photos={photos} index={viewer} onIndex={setViewer} onClose={closeViewer} centralCreditsOnly={centralCreditsOnly} />}
    </div>
  );
}

const AUTOPLAY_MS = 5000;

/**
 * One photo at a time, with arrows on either side, a counter, and gentle
 * auto-advance that pauses while you are hovering or have interacted — the
 * Airbnb listing carousel on phones. Tapping the photo opens it a schermo intero.
 */
function PhotoCarousel({ photos, onAdd, actions, centralCreditsOnly = false }: { photos: GalleryPhoto[]; onAdd: () => void; actions: ReactNode; centralCreditsOnly?: boolean }) {
  const [index, setIndex] = useState(0);
  const [paused, setPaused] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const closeFullscreen = useCallback(() => setFullscreen(false), []);
  const count = photos.length;
  const go = (delta: number) => setIndex((i) => (i + delta + count) % count);

  useEffect(() => {
    if (count < 2 || paused || fullscreen || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % count), AUTOPLAY_MS);
    return () => window.clearInterval(timer);
  }, [count, paused, fullscreen]);

  return (
    <>
      <div
        className="carousel"
        onMouseEnter={() => setPaused(true)}
        onMouseLeave={() => setPaused(false)}
        onFocus={() => setPaused(true)}
        onTouchStart={() => setPaused(true)}
      >
        <Slides photos={photos} index={index} onIndex={setIndex} onOpen={() => setFullscreen(true)} />
        {count > 1 && (
          <>
            <button type="button" className="carousel-arrow prev" aria-label="Foto precedente" onClick={() => { setPaused(true); go(-1); }}>
              <ChevronLeftIcon size={16} />
            </button>
            <button type="button" className="carousel-arrow next" aria-label="Foto successiva" onClick={() => { setPaused(true); go(1); }}>
              <ChevronRightIcon size={16} />
            </button>
            <span className="carousel-count">{index + 1} / {count}</span>
            <span className="carousel-dots" aria-hidden="true">
              {photos.slice(0, 8).map((photo, i) => <i key={photo.key} className={i === index % 8 ? 'on' : ''} />)}
            </span>
          </>
        )}
        <div className="carousel-actions">{actions}</div>
        <button type="button" className="carousel-add" onClick={onAdd} aria-label="Aggiungi foto" data-tip="Aggiungi foto"><PlusIcon /></button>
        {!centralCreditsOnly && <p className="carousel-credit"><PhotoCreditText photo={photos[index]} /></p>}
      </div>
      {fullscreen && <Lightbox photos={photos} index={index} onIndex={setIndex} onClose={closeFullscreen} centralCreditsOnly={centralCreditsOnly} />}
    </>
  );
}

/** A horizontal strip that snaps one photo per view: swipe on touch, arrows elsewhere. */
function Slides({ photos, index, onIndex, onOpen }: { photos: GalleryPhoto[]; index: number; onIndex: (i: number) => void; onOpen?: () => void }) {
  const trackRef = useRef<HTMLDivElement>(null);
  const programmatic = useRef(false);

  useEffect(() => {
    const track = trackRef.current;
    if (!track) return;
    const target = index * track.clientWidth;
    if (Math.abs(track.scrollLeft - target) < 2) return;
    programmatic.current = true;
    track.scrollTo({ left: target, behavior: window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth' });
    const done = window.setTimeout(() => (programmatic.current = false), 600);
    return () => window.clearTimeout(done);
  }, [index]);

  return (
    <div
      className="carousel-track"
      ref={trackRef}
      onScroll={(event) => {
        if (programmatic.current) return;
        const track = event.currentTarget;
        const next = Math.round(track.scrollLeft / track.clientWidth);
        if (next !== index) onIndex(next);
      }}
    >
      {photos.map((photo, i) => (
        <button type="button" key={photo.key} className="carousel-slide" onClick={onOpen} aria-label={onOpen ? `Apri foto ${i + 1} a schermo intero` : undefined} tabIndex={onOpen ? 0 : -1}>
          <FadeImage
            src={photo.src}
            alt=""
            loading={Math.abs(i - index) <= 1 ? 'eager' : 'lazy'}
            decoding="async"
            onError={swapToFallback(photo)}
          />
        </button>
      ))}
    </div>
  );
}

function Lightbox({ photos, index, onIndex, onClose, centralCreditsOnly = false }: { photos: GalleryPhoto[]; index: number; onIndex: (i: number) => void; onClose: () => void; centralCreditsOnly?: boolean }) {
  const count = photos.length;
  useEffect(() => {
    // Capture on window, ahead of the dialog underneath: Escape closes only this.
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        event.stopPropagation();
        onClose();
      }
      if (event.key === 'ArrowRight') onIndex((index + 1) % count);
      if (event.key === 'ArrowLeft') onIndex((index - 1 + count) % count);
    };
    window.addEventListener('keydown', onKey, true);
    return () => window.removeEventListener('keydown', onKey, true);
  }, [index, count, onIndex, onClose]);

  useEffect(() => lockPageScroll(), []);

  return createPortal(
    <div className="lightbox" role="dialog" aria-modal="true" aria-label="Fotografie">
      <header className="lightbox-head">
        <button type="button" onClick={onClose} aria-label="Chiudi fotografie"><CloseIcon size={14} />Chiudi</button>
        <span>{index + 1} / {count}</span>
        {photos[index].communityId && (
          <button
            type="button"
            className="lightbox-report"
            onClick={() => {
              const id = photos[index].communityId;
              onClose();
              if (id) requestReport({ targetType: 'photo', targetSlug: id, targetName: 'this photo' });
            }}
          >
            <FlagIcon />Segnala
          </button>
        )}
      </header>
      <div className="lightbox-stage">
        <Slides photos={photos} index={index} onIndex={onIndex} />
        {count > 1 && (
          <>
            <button type="button" className="carousel-arrow prev" aria-label="Foto precedente" onClick={() => onIndex((index - 1 + count) % count)}><ChevronLeftIcon size={18} /></button>
            <button type="button" className="carousel-arrow next" aria-label="Foto successiva" onClick={() => onIndex((index + 1) % count)}><ChevronRightIcon size={18} /></button>
          </>
        )}
      </div>
      {!centralCreditsOnly && <p className="lightbox-credit"><PhotoCreditText photo={photos[index]} /></p>}
    </div>,
    document.body,
  );
}

function ReviewForm({ venue, initialRating, first, onPosted }: { venue: Venue; initialRating: number; first: boolean; onPosted: (review: Review) => void }) {
  const user = useAuthUser();
  const [mine, setMine] = useState(initialRating);
  const [comment, setComment] = useState('');
  const [anonymous, setAnonymous] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const post = async () => {
    setSubmitting(true);
    setError(null);
    try {
      onPosted(await submitReview({ venueSlug: venue.slug, rating: mine, comment, author: user && !anonymous ? user.username : '' }));
      setDone(true);
    } catch (err) {
      setError(`Impossibile pubblicare la recensione: ${errorText(err)}`);
    } finally {
      setSubmitting(false);
    }
  };

  if (done) return <p className="review-thanks">Grazie, la tua recensione è pubblicata.</p>;
  return (
    <div className="review-form inline">
      <h3>{first ? 'Scrivi la prima recensione' : 'La tua recensione'}</h3>
      <StarPicker value={mine} onChange={setMine} />
      <textarea className="review-comment" placeholder="Com’è andata? Accesso, ombra, acqua, stagione: racconta la tua esperienza (facoltativo)" rows={2} value={comment} maxLength={1000} onChange={(event) => setComment(event.target.value)} />
      {user ? (
        <CreditChips username={user.username} anonymous={anonymous} onChange={setAnonymous} />
      ) : (
        <p className="photo-note">Pubblicazione anonima. Accedi per mostrare il tuo nome utente.</p>
      )}
      <div className="review-form-row">
        <button type="button" className="btn btn-dark" disabled={mine === 0 || submitting} onClick={() => void post()}>{submitting ? 'Pubblicazione…' : 'Pubblica recensione'}</button>
      </div>
      {error && <p className="review-error">{error}</p>}
    </div>
  );
}

const REVIEWS_SHOWN = 6;

/** Airbnb's reviews block: the score as the heading, a grid of short cards, then "Show all". */
function ReviewsSection({ venue, reviews, rating, initialRating, onPosted, sectionRef }: { venue: Venue; reviews: Review[]; rating: { average: number; count: number } | undefined; initialRating: number; onPosted: (review: Review) => void; sectionRef: React.RefObject<HTMLElement> }) {
  const [showAll, setShowAll] = useState(false);
  return (
    <section className="venue-detail-section reviews-section" ref={sectionRef} id="reviews">
      <div className="reviews-head">
        <h2>
          {rating ? <><StarIcon size={18} filled /> {rating.average.toFixed(2)} · {rating.count} recensioni</> : 'Recensioni'}
        </h2>
      </div>
      {reviews.length > 0 && (
        <div className="review-grid">
          {reviews.slice(0, REVIEWS_SHOWN).map((review) => <ReviewCard key={review.id} review={review} onReport={() => requestReviewReport('review', review)} />)}
        </div>
      )}
      {reviews.length > REVIEWS_SHOWN && (
        <button type="button" className="reviews-all" onClick={() => setShowAll(true)}>Mostra tutte le {reviews.length} recensioni</button>
      )}
      <ReviewForm key={initialRating} venue={venue} initialRating={initialRating} first={reviews.length === 0} onPosted={onPosted} />
      {showAll && (
        <Modal title={`${reviews.length} recensioni`} onClose={() => setShowAll(false)} wide>
          <div className="review-grid single">{reviews.map((review) => <ReviewCard key={review.id} review={review} onReport={() => requestReviewReport('review', review)} />)}</div>
        </Modal>
      )}
    </section>
  );
}

/** The side card: what you need right before you go — conditions now, light, and getting there. */
function PlanCard({ venue }: { venue: Venue }) {
  const [conditions, setConditions] = useState<Conditions | null | undefined>(undefined);
  useEffect(() => {
    let cancelled = false;
    void venueConditions(venue).then((value) => {
      if (!cancelled) setConditions(value);
    });
    return () => {
      cancelled = true;
    };
  }, [venue]);

  return (
    <div className="plan-card">
      <p className="plan-kicker">Condizioni attuali{venue.type === 'hill' ? ' in quota' : ''}</p>
      {conditions === undefined ? (
        <div className="plan-weather loading" aria-busy="true" />
      ) : conditions ? (
        <>
          <div className="plan-weather">
            <strong>{conditions.temperatureC}°</strong>
            <div>
              <span>{conditions.summary}</span>
              <span className="muted">Percepiti {conditions.feelsLikeC}° · Vento {conditions.windKmh} km/h</span>
            </div>
          </div>
          <dl className="plan-facts">
            <div><dt>Probabilità pioggia</dt><dd>{conditions.rainChance != null ? `${conditions.rainChance}%` : '—'}</dd></div>
            <div><dt>Alba</dt><dd>{conditions.sunrise ?? '—'}</dd></div>
            <div><dt>Tramonto</dt><dd>{conditions.sunset ?? '—'}</dd></div>
          </dl>
        </>
      ) : (
        <p className="muted">Previsioni non disponibili al momento.</p>
      )}
      <a className="venue-primary-action" href={directionsUrl(venue)} target="_blank" rel="noreferrer"><MapIcon size={16} />Apri la posizione</a>
      <p className="plan-credit">Dati meteo: <a href="https://open-meteo.com" target="_blank" rel="noreferrer">Open-Meteo</a></p>
    </div>
  );
}

const MAX_PHOTOS = 12;

interface PendingPhoto {
  id: string;
  file: File;
  url: string;
  status: 'ready' | 'uploading' | 'done' | 'failed';
}

/**
 * Several photos at once: drop or pick them, keep adding more, remove any
 * before sending. Each tile shows its own progress, and a failed one stays
 * behind to retry while the rest are already through.
 */
function AddPhotosModal({ venue, onClose, onUploaded }: { venue: Venue; onClose: () => void; onUploaded: () => void }) {
  const user = useAuthUser();
  const [items, setItems] = useState<PendingPhoto[]>([]);
  const [anonymous, setAnonymous] = useState(false);
  const [busy, setBusy] = useState(false);
  const [dragging, setDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const itemsRef = useRef(items);
  useEffect(() => {
    itemsRef.current = items;
  }, [items]);
  useEffect(() => () => itemsRef.current.forEach((item) => URL.revokeObjectURL(item.url)), []);

  const add = (list: FileList | null) => {
    const known = new Set(items.map((item) => `${item.file.name}:${item.file.size}`));
    const images = [...(list ?? [])].filter((file) => file.type.startsWith('image/') && !known.has(`${file.name}:${file.size}`));
    if (images.length === 0) return;
    const room = MAX_PHOTOS - items.length;
    setError(images.length > room ? `Fino a ${MAX_PHOTOS} foto at a time. Send these, then add more.` : null);
    const fresh = images
      .slice(0, Math.max(0, room))
      .map((file): PendingPhoto => ({ id: `${file.name}:${file.size}:${file.lastModified}`, file, url: URL.createObjectURL(file), status: 'ready' }));
    setItems([...items, ...fresh]);
  };

  const remove = (id: string) =>
    setItems((current) => {
      const gone = current.find((item) => item.id === id);
      if (gone) URL.revokeObjectURL(gone.url);
      return current.filter((item) => item.id !== id);
    });

  const setStatus = (id: string, status: PendingPhoto['status']) =>
    setItems((current) => current.map((item) => (item.id === id ? { ...item, status } : item)));

  const upload = async () => {
    setBusy(true);
    setError(null);
    const credit = user && !anonymous ? user.username : '';
    let failed = 0;
    for (const item of items.filter((entry) => entry.status !== 'done')) {
      setStatus(item.id, 'uploading');
      try {
        await submitPhoto({ venueSlug: venue.slug, file: item.file, credit, licence: 'CC BY-SA 4.0', author: credit });
        setStatus(item.id, 'done');
      } catch (err) {
        failed += 1;
        setStatus(item.id, 'failed');
        setError(errorText(err));
      }
    }
    if (failed) setError((message) => `${failed} photo${failed === 1 ? '' : 's'} did not upload${message ? `: ${message}` : ''}. Try again.`);
    setBusy(false);
    onUploaded();
  };

  const sent = items.filter((item) => item.status === 'done').length;
  const toSend = items.length - sent;
  const finished = items.length > 0 && toSend === 0 && !busy;
  const uploadingIndex = items.findIndex((item) => item.status === 'uploading');

  const picker = (className: string, content: ReactNode) => (
    <label
      className={`${className}${dragging ? ' dragging' : ''}`}
      onDragOver={(event) => {
        event.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(event) => {
        event.preventDefault();
        setDragging(false);
        add(event.dataTransfer.files);
      }}
    >
      {content}
      <input
        type="file"
        accept="image/*"
        multiple
        disabled={busy}
        onChange={(event: ChangeEvent<HTMLInputElement>) => {
          add(event.target.files);
          event.target.value = '';
        }}
      />
    </label>
  );

  return (
    <Modal
      title="Aggiungi foto"
      onClose={onClose}
      footer={finished ? (
        <button type="button" className="btn btn-dark" onClick={onClose}>Fine</button>
      ) : (
        <>
          <span className="photo-count">{items.length === 0 ? `Fino a ${MAX_PHOTOS} foto` : `${items.length} foto su ${MAX_PHOTOS} selezionate`}</span>
          <button type="button" className="btn btn-accent" disabled={toSend === 0 || busy} onClick={() => void upload()}>
            {busy ? `Caricamento ${uploadingIndex + 1} di ${items.length}…` : `Carica ${toSend || ''} foto`}
          </button>
        </>
      )}
    >
      {finished ? (
        <div className="photo-done">
          <span className="photo-done-icon"><CheckIcon size={22} /></span>
          <h3>Grazie</h3>
          <p>{sent} photo{sent === 1 ? ' is' : 's are'} now on {venue.name}'s page.</p>
        </div>
      ) : (
        <div className="photo-form">
          {items.length === 0 ? (
            picker('photo-upload', (
              <>
                <CameraGlyph size={30} />
                <strong>Trascina qui le fotografie</strong>
                <span>oppure <u>sceglile dal dispositivo</u>. Pubblica solo immagini pertinenti al luogo.</span>
              </>
            ))
          ) : (
            <ul className="photo-picks" aria-label="Fotografie da caricare">
              {items.map((item) => (
                <li key={item.id} className={`photo-pick ${item.status}`}>
                  <img src={item.url} alt="" />
                  {item.status === 'uploading' && <span className="photo-pick-state" aria-label="Caricamento"><span className="spinner" /></span>}
                  {item.status === 'done' && <span className="photo-pick-state" aria-label="Caricata"><CheckIcon size={16} /></span>}
                  {item.status === 'failed' && <span className="photo-pick-state failed" aria-label="Operazione non riuscita">!</span>}
                  {(item.status === 'ready' || item.status === 'failed') && !busy && (
                    <button type="button" className="photo-pick-remove" aria-label="Rimuovi foto" onClick={() => remove(item.id)}>
                      <CloseIcon size={10} />
                    </button>
                  )}
                </li>
              ))}
              {items.length < MAX_PHOTOS && !busy && (
                <li>{picker('photo-pick-add', <><PlusIcon /><span>Aggiungi altre</span></>)}</li>
              )}
            </ul>
          )}
          {user ? (
            <CreditChips username={user.username} anonymous={anonymous} onChange={setAnonymous} />
          ) : (
            <p className="photo-note">Le immagini saranno attribuite in forma anonima. Accedi per mostrare il nome utente.</p>
          )}
          <p className="photo-note">Le fotografie sono pubblicate nel rispetto delle <a href="#terms">regole del sito</a>; i contenuti segnalati possono essere nascosti. Condivisione CC BY-SA 4.0; i metadati di geolocalizzazione vengono rimossi.</p>
          {error && <p className="review-error">{error}</p>}
        </div>
      )}
    </Modal>
  );
}

interface VenueDetailProps {
  venue: Venue;
  routes: Route[];
  allVenues: Venue[];
  /**
   * Unused: the page opens in its own tab and has no back. Kept optional so
   * callers that still pass it compile.
   */
  onClose?: () => void;
  /** Leave this page for the map, framed on the place (or on one of its routes). */
  onShowOnMap: (routeSlug?: string) => void;
  /** The header's centre. Defaults to the site search over `allVenues`. */
  headerCenter?: ReactNode;
  isFavorite: boolean;
  onToggleFavorite: () => void;
  onRemoveLocalRoute: (slug: string) => void;
}


function CameraGlyph({ size = 34 }: { size?: number }) {
  return <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.5" aria-hidden="true"><path d="M3 7h4l1.5-2h7L17 7h4v12H3V7Z" /><circle cx="12" cy="13" r="4" /></svg>;
}

/** A trace between two points: the empty-routes icon, in the same stroke style as the others. */
function RouteGlyph() {
  return (
    <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <circle cx="6" cy="18" r="2.2" />
      <path d="M18 3.5c-1.9 0-3.4 1.5-3.4 3.3 0 2.4 3.4 5.7 3.4 5.7s3.4-3.3 3.4-5.7c0-1.8-1.5-3.3-3.4-3.3z" />
      <circle cx="18" cy="6.8" r="1" />
      <path d="M8.2 18H15a3 3 0 0 0 0-6h-4a3 3 0 0 1 0-6h1.5" />
    </svg>
  );
}

/**
 * A nearby place's cover. With no stored photo, a hill gets the same picture
 * its own page leads with (its summit photo, else the first open-licence
 * photo taken nearby), so the card and the page agree. Both lookups are
 * cached, so opening the place afterwards costs nothing.
 */
function NearbyThumb({ venue }: { venue: Venue }) {
  const [cover, setCover] = useState<{ slug: string; url: string } | null>(null);
  const needsLookup = venuePhotos(venue).length === 0 && !BUILT_TYPES.has(venue.type);
  useEffect(() => {
    if (!needsLookup) return;
    let cancelled = false;
    const lead = isWorldPeakSlug(venue.slug) ? loadPeakPhotos().then((photos) => photos.get(venue.slug)?.url) : Promise.resolve(undefined);
    lead
      .then((url) => url ?? commonsPhotos(venue).then((photos) => photos[0]?.url))
      .then((url) => {
        if (!cancelled && url) setCover({ slug: venue.slug, url });
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [needsLookup, venue]);
  if (cover?.slug === venue.slug) {
    return (
      <span className="card-thumb">
        <FadeImage src={cover.url} alt={venue.name} loading="lazy" decoding="async" onError={() => setCover(null)} />
      </span>
    );
  }
  return <VenueThumb venue={venue} />;
}

function aboutFallback(venue: Venue, typeLabel: string, area: string | null, heightText: string, routeCount: number): string {
  const where = area ? ` in ${area}` : '';
  if (venue.type === 'hdb_block') {
    return `A ${venue.storeys ?? ''}-storey residential block${where}, climbed by its public stairwell. ${heightText} from the ground floor to the top landing. Check the stairwell is open before you go and keep noise down for residents.`.replace('  ', ' ');
  }
  if (venue.type === 'hill') return `Cima${area ? ' nell’area ' + area : ''}. ${heightText}. Le informazioni sugli accessi e sui punti di appoggio vengono presentate solo quando i dati cartografici permettono collegamenti espliciti o di prossimità.`;
  const routes = routeCount > 0 ? `${routeCount} percorsi associati al luogo.` : 'Non ci sono ancora percorsi collegati al luogo.';
  return `${typeLabel}${where}, ${heightText}. ${routes}`;
}

function VenueDetailInner({
  venue,
  routes,
  allVenues,
  onShowOnMap,
  headerCenter,
  isFavorite,
  onToggleFavorite,
  onRemoveLocalRoute,
}: VenueDetailProps) {
  const units = useUnits();
  const [copied, setCopied] = useState(false);
  const [aboutExpanded, setAboutExpanded] = useState(false);
  const [aboutOverflows, setAboutOverflows] = useState(false);
  const aboutRef = useRef<HTMLDivElement>(null);
  const [addingPhotos, setAddingPhotos] = useState(false);
  const [reporting, setReporting] = useState(false);
  const [quickRating, setQuickRating] = useState(0);
  const copyTimer = useRef<number | null>(null);
  const reviewsRef = useRef<HTMLElement>(null);
  const pageRef = useRef<HTMLDivElement>(null);
  useReveal(pageRef, venue.slug);
  // The page is a fixed layer over the map page. Locking the map page behind
  // it leaves one scrollbar (this page's own), so the header lines up with
  // every other page and does not shift when a dialog opens.
  useEffect(() => lockPageScroll(), []);
  const { reviews, setReviews, communityPhotos, reloadPhotos, commons, wiki, generated } = useVenueContent(venue);
  const narrow = useNarrow();
  const isSummit = venue.type === 'hill';
  const height = venueHeight(venue);
  const typeLabel = isSummit ? 'Cima' : venueKindLabel(venue);
  const area = townName(venue.town) ?? regionOf(venue.lng, venue.lat);
  const street = venue.street ? titleCaseStreet(venue.street) : null;
  const address = [venue.blkNo ? titleCaseStreet(venue.blkNo) : null, street].filter(Boolean).join(' ');
  const heightText = height ? `${units.height(height.value)} ${isSummit ? 'di quota' : HEIGHT_LABEL[height.kind]}` : 'quota non disponibile';
  const rating = combinedRating(venue.rating, reviews);
  const nearby = useMemo(
    () => tallestWithin(allVenues, venue.lng, venue.lat, 1000, 7).filter((item) => item.venue.slug !== venue.slug).slice(0, 6),
    [allVenues, venue],
  );

  // The stored cover first, as on every card; then the rest of the stored
  // gallery, community photos, and Commons photos taken nearby. The same file
  // from two sources appears once.
  const photos: GalleryPhoto[] = useMemo(() => {
    const seen = new Set<string>();
    const unique = (photo: GalleryPhoto) => {
      if (photo.keys.some((key) => seen.has(key))) return false;
      photo.keys.forEach((key) => seen.add(key));
      return true;
    };
    return [
      ...venuePhotos(venue).map(storedGalleryPhoto),
      ...communityPhotos.map((photo): GalleryPhoto => ({ key: photo.id, src: photo.url, credit: photo.credit, licence: photo.licence, keys: [photoKey(photo.url)], communityId: photo.id })),
      ...commons,
    ].filter(unique);
  }, [venue, communityPhotos, commons]);

  const isVerifiedSummit = venue.type === 'hill' && venue.sourceIds?.wikidataVerifiedBy === 'P1566+P625';
  const documentedSummitText = isVerifiedSummit ? venue.textSources?.find(t => t.sourceId?.startsWith('wikipedia:it:'))?.text : undefined;
  const about = isSummit
    ? documentedSummitText ?? venue.shortSummary ?? aboutFallback(venue,typeLabel,area,heightText,routes.length)
    : generated?.text ?? wiki?.extract ?? aboutFallback(venue,typeLabel,area,heightText,routes.length);

  // Only offer "Read more" when three lines actually cut the text off.
  useLayoutEffect(() => {
    const el = aboutRef.current;
    if (el && !aboutExpanded) setAboutOverflows(el.scrollHeight > el.clientHeight + 2);
  }, [about, aboutExpanded]);

  useEffect(() => () => {
    if (copyTimer.current != null) window.clearTimeout(copyTimer.current);
  }, []);

  const share = async () => {
    const url = window.location.href;
    if (navigator.share) await navigator.share({ title: venue.name, url }).catch(() => undefined);
    else {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      if (copyTimer.current != null) window.clearTimeout(copyTimer.current);
      copyTimer.current = window.setTimeout(() => setCopied(false), 2000);
    }
  };

  const iconActions = (
    <div className="venue-icon-actions">
      <button type="button" className={`icon-action${isFavorite ? ' on' : ''}`} aria-label={isFavorite ? 'Salvato' : 'Salva'} title={isFavorite ? 'Salvato' : 'Salva'} onClick={onToggleFavorite}>
        <HeartIcon size={18} filled={isFavorite} />
      </button>
      <button type="button" className="icon-action" aria-label={copied ? 'Link copiato' : 'Copia link'} title={copied ? 'Link copiato' : 'Copia link'} onClick={() => void share()}>
        {copied ? <CheckIcon size={16} /> : <LinkIcon />}
      </button>
    </div>
  );

  const heightBlock = height ? <><strong>{units.height(height.value)}</strong> {isSummit?'di quota':HEIGHT_LABEL[height.kind]}</> : 'Quota non disponibile';

  return createPortal(
    <div className="venue-detail" ref={pageRef}>
      {/* A page of its own (cards open it in a new tab): the site header with
          search on top, no back button. */}
      <SiteHeader
        center={headerCenter ?? (
          <SearchBar venues={allVenues} {...SEARCH_OPENS_MAP} />
        )}
      />

      <main className={`venue-detail-content cb-venue-document cb-document-page${isSummit?' cb-is-summit':''}`}>
        <div className="venue-detail-layout cb-venue-grid">
          <div className="venue-detail-head">
            <div className="venue-detail-title-row">
          <div>
            <h1>{venue.name}</h1>
            <p className="venue-detail-sub">
              {!isSummit&&<button type="button" className="venue-rating-link" onClick={() => reviewsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })}>
                {rating ? (
                  <><StarIcon size={12} filled /> {rating.average.toFixed(2)} · <u>{rating.count} recensioni</u></>
                ) : (
                  <RatingLabel />
                )}
              </button>}
              {!isSummit&&<span aria-hidden="true"> · </span>}
              {area ? `${typeLabel} · ${area}` : typeLabel}
            </p>
          </div>
          {!narrow && (
            <div className="venue-detail-title-actions">
              <button type="button" onClick={() => void share()} aria-label={copied ? 'Link copiato' : 'Condividi'}>
                {copied ? <CheckIcon size={16} /> : <LinkIcon />}
                <span className="venue-action-label">{copied ? 'Link copiato' : 'Condividi'}</span>
              </button>
              <button type="button" className={isFavorite ? 'on' : undefined} onClick={onToggleFavorite} aria-label={isFavorite ? 'Salvato' : 'Salva'} aria-pressed={isFavorite}>
                <HeartIcon size={16} filled={isFavorite} />
                <span className="venue-action-label">{isFavorite ? 'Salvato' : 'Salva'}</span>
              </button>
            </div>
          )}
        </div>

        <div className="cb-venue-hero-media">
          {photos.length===0?<NoPhotos venue={venue} onAdd={()=>setAddingPhotos(true)} actions={iconActions}/>:
            <PhotoCarousel photos={photos} onAdd={()=>setAddingPhotos(true)} actions={iconActions} centralCreditsOnly={isVerifiedSummit}/>}
          {photos.length>1&&!narrow&&<details className="cb-venue-gallery-more">
            <summary>Apri tutte le {photos.length} fotografie</summary>
            <PhotoGrid photos={photos} venueName={venue.name} onAdd={()=>setAddingPhotos(true)} centralCreditsOnly={isVerifiedSummit}/>
          </details>}
        </div>

          </div>
          <div className="venue-detail-main">
            <AtlasDossierBlocks record={venue} placement="alerts"/>
            <DetailJumpNav items={[
              {id:'cb-venue-overview',label:'In breve',icon:'mountain'},
              {id:'cb-venue-about',label:'Descrizione',icon:'compass'},
              ...(isSummit?[
                {id:'cb-summit-access',label:'Accessi e ferrate',icon:'route' as const},
                {id:'cb-summit-support',label:'Rifugi e bivacchi',icon:'house' as const},
              ]:[
                {id:'cb-venue-routes',label:'Percorsi',icon:'map' as const},
              ]),
              {id:'cb-venue-planning',label:'Meteo e pianificazione',icon:'route'},
              {id:'reviews',label:'Recensioni'},
              ...(nearby.length?[{id:'cb-venue-nearby',label:'Dintorni',icon:'location-dot' as const}]:[]),
              {id:'cb-venue-map',label:'Mappa',icon:'map'},
            ]}/>
            <section id="cb-venue-overview" className="venue-detail-intro cb-detail-group cb-detail-group--first">
              <div className="venue-intro-row">
                <h2>{heightBlock}</h2>
                {!isSummit&&<div className="quick-rate" role="radiogroup" aria-label="Valuta questo luogo">
              <span>Valuta</span>
              {[1, 2, 3, 4, 5].map((value) => (
                <button
                  key={value}
                  type="button"
                  role="radio"
                  aria-checked={quickRating === value}
                  aria-label={`${value} ${value === 1 ? 'stella' : 'stelle'}`}
                  className={value <= quickRating ? 'on' : ''}
                  onClick={() => {
                    setQuickRating(value);
                    window.setTimeout(() => reviewsRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 120);
                  }}
                >
                  <StarIcon size={18} filled={value <= quickRating} />
                </button>
              ))}
            </div>}
              </div>
              {isSummit&&<p className="cb-summit-overview-line">{isVerifiedSummit?'Identità della cima verificata · dati topografici documentati':'Dati cartografici della cima · quota e accessi da approfondire'}</p>}
              {(venue.storeys || address) && <p>{[venue.storeys ? `${venue.storeys} piani` : null, address || null].filter(Boolean).join(' · ')}</p>}
            </section>

            <section id="cb-venue-about" className="venue-detail-section cb-detail-group">
              <h2>Il luogo e la sua storia</h2>
              {/* Three lines; a clear "Read more" (or a double-click) opens the rest. */}
              <div
                ref={aboutRef}
                className={`venue-about-copy${aboutExpanded ? '' : ' clamp3'}`}
                onDoubleClick={() => setAboutExpanded((value) => !value)}
              >
                <p>{about}</p>
                {venue.notes && !venue.notes.startsWith('Summit elevation from') && <p>{venue.notes}</p>}
              </div>
              {(aboutOverflows || aboutExpanded) && (
                <button type="button" className="venue-read-more" aria-expanded={aboutExpanded} onClick={() => setAboutExpanded((value) => !value)}>
                  {aboutExpanded ? 'Mostra meno' : 'Leggi tutto'}
                  <ChevronRightIcon size={12} />
                </button>
              )}
              {!isSummit&&<p className="venue-about-source">
                {generated
                  ? `Sintesi da: ${generated.sources.join(', ')}`
                  : wiki
                    ? <>Testo da <a href={wiki.url} target="_blank" rel="noreferrer">Wikipedia</a>, CC BY-SA</>
                    : 'Conosci il luogo? Puoi contribuire con una recensione.'}
              </p>}
            </section>

            <AtlasDossierBlocks record={venue} placement="core"/>
            {isSummit&&<SummitConnections venue={venue} connectedRoutes={routes}/>}
            <section id="cb-venue-planning" className="venue-detail-section cb-detail-group cb-venue-planning" aria-label="Pianificazione e meteo">
              <PlanCard venue={venue}/>
              <button type="button" className="plan-report" onClick={() => setReporting(true)}><FlagIcon/> Segnala un problema su questo luogo</button>
            </section>

            {!isSummit&&<section id="cb-venue-routes" className="venue-detail-section cb-detail-group venue-routes-section">
              <h2>Percorsi e itinerari collegati</h2>
              {routes.length > 0 ? (
                  <div className="venue-route-grid">
                    {routes.map((route) => (
                      <article className="venue-route-card" key={route.slug} tabIndex={0} aria-label={route.name}>
                        <RouteThumb route={route} />
                        <div className="venue-route-tools">
                          <button type="button" className="venue-route-tool" aria-label="Mostra sulla mappa" data-tip="Mostra sulla mappa" onClick={() => onShowOnMap(route.slug)}>
                            <MapIcon size={15} />
                          </button>
                          <button type="button" className="venue-route-tool" aria-label="Download GPX" data-tip="Download GPX" onClick={() => downloadRoute(route)}>
                            <DownloadIcon size={15} />
                          </button>
                          {route.source === 'local' && (
                            <button type="button" className="venue-route-tool" aria-label="Rimuovi dal dispositivo" data-tip="Remove" onClick={() => onRemoveLocalRoute(route.slug)}>
                              <CloseIcon size={12} />
                            </button>
                          )}
                        </div>
                        <div className="venue-route-caption">
                          <h3>{route.name}</h3>
                          <p>
                            {ACTIVITY_LABEL[routeActivity(route)]} · {units.distance(route.distanceM)}
                            {route.source === 'local' ? ' · su questo dispositivo' : ''}
                          </p>
                        </div>
                        {/* Hover (or focus, or a tap on touch screens) lifts the details over the map. */}
                        <div className="venue-route-details">
                          <dl>
                            <div><dt>Distanza</dt><dd>{units.distance(route.distanceM)}</dd></div>
                            <div><dt>EG</dt><dd>{routeHasElevation(route) ? units.height(route.gainM) : '—'}</dd></div>
                            <div><dt>EL</dt><dd>{routeHasElevation(route) ? units.height(route.lossM) : '—'}</dd></div>
                          </dl>
                          {routeHasElevation(route) && <ElevationProfile points={route.coordinates} height={44} />}
                        </div>
                      </article>
                    ))}
                  </div>
              ) : (
                <div className="venue-empty">
                  <span className="venue-empty-icon" aria-hidden="true"><RouteGlyph /></span>
                  <div className="venue-empty-copy">
                    <h3>Nessuna traccia ancora associata</h3>
                    <p>Hai un tracciato pertinente a {venue.name}? Puoi condividerlo con la community.</p>
                  </div>
                  <a className="btn btn-dark venue-empty-btn" href="#import" onClick={openImportHere}><UploadIcon size={15} />Carica GPX</a>
                </div>
              )}
            </section>}

            <ReviewsSection venue={venue} reviews={reviews} rating={rating} initialRating={quickRating} sectionRef={reviewsRef} onPosted={(review) => setReviews((current) => [review, ...current])} />

            {nearby.length > 0 && (
              <section id="cb-venue-nearby" className="venue-detail-section cb-detail-group">
                <div className="venue-section-heading"><h2>Luoghi nei dintorni</h2><span>Entro 1 km in linea d'aria</span></div>
                <div className="nearby-grid">
                  {nearby.map(({ venue: item }) => {
                    const itemHeight = venueHeight(item);
                    return (
                      <a className="nearby-card" href={`#venue/${item.slug}`} target="_blank" rel="noopener" key={item.slug}>
                        <NearbyThumb venue={item} />
                        <strong>{item.name}</strong>
                        <span>{venueKindLabel(item)}{itemHeight ? ` · ${units.height(itemHeight.value)} ${HEIGHT_LABEL[itemHeight.kind]}` : ''}</span>
                      </a>
                    );
                  })}
                </div>
              </section>
            )}

            <AtlasDossierBlocks record={venue} placement="connections"/>
            <AtlasDossierBlocks record={venue} placement="media"/>
            <AtlasDossierBlocks record={venue} placement="credits"/>
          </div>

          <aside id="cb-venue-map" tabIndex={-1} className="venue-detail-side" aria-label={'Mappa di '+venue.name}>
            <div className="cb-venue-map-pane">
              <MapContextLabel kicker="CARTOGRAFIA DEL LUOGO" title={venue.name}/>
              <Suspense fallback={<div className="mini-map mini-map-fallback" />}><MiniMap venue={venue}/></Suspense>
              <button type="button" className="cb-venue-map-open" onClick={()=>onShowOnMap()}><MapIcon size={15}/> Esplora i percorsi sulla mappa <FaIcon name="arrow-up-right-from-square" size={12}/></button>
            </div>
          </aside>
        </div>
      </main>
      <SiteFooter />

      <div className="venue-mobile-bar">
        <button type="button" className="venue-mobile-secondary" onClick={() => onShowOnMap()}>Mostra sulla mappa</button>
        <a className="venue-mobile-primary" href={directionsUrl(venue)} target="_blank" rel="noreferrer"><MapIcon size={16} />Posizione</a>
      </div>

      {/* Outside the page layer: it slides in with a transform, which would
          carry a fixed badge along with it for the length of the animation. */}
      {createPortal(<OpenSourceBadge placement="corner" />, document.body)}
      {addingPhotos && <AddPhotosModal venue={venue} onClose={() => setAddingPhotos(false)} onUploaded={reloadPhotos} />}
      {reporting && <ReportModal targetType="venue" targetSlug={venue.slug} targetName={venue.name} onClose={() => setReporting(false)} />}
    </div>,
    document.body,
  );
}

/**
 * The place page's shape while its data loads: header, a title line, the
 * photo frame and a few lines, so a card opened in a new tab lands on the
 * place page straight away instead of showing the map page first.
 */
export function VenueDetailSkeleton() {
  useEffect(() => lockPageScroll(), []);
  return createPortal(
    <div className="venue-detail venue-detail-loading" aria-busy="true" aria-label="Caricamento del luogo">
      <SiteHeader center={<SearchBar venues={[]} {...SEARCH_OPENS_MAP} />} />
      <main className="venue-detail-content">
        <div className="sk-line sk-title" />
        <div className="sk-line sk-sub" />
        <div className="sk-photo" />
        <div className="sk-line" />
        <div className="sk-line" />
        <div className="sk-line sk-short" />
      </main>
    </div>,
    document.body,
  );
}

/**
 * A place link nobody answers to (mistyped, or a place since removed): the
 * same page chrome as a place, a short message and a way back. Shown only once
 * the data has loaded and no place matched, never while it is still loading.
 */
export function VenueNotFound() {
  useEffect(() => lockPageScroll(), []);
  return createPortal(
    <div className="venue-detail venue-detail-notfound">
      <SiteHeader center={<SiteSearch />} />
      <main className="venue-detail-content venue-notfound">
        <h1>Non troviamo questo luogo</h1>
        <p>Il collegamento potrebbe essere errato oppure la scheda non è più disponibile. Prova a cercare il luogo o torna alla mappa.</p>
        <a className="venue-open-map" href="#map">
          <MapIcon size={16} />
          Torna alla mappa
        </a>
      </main>
      <SiteFooter />
    </div>,
    document.body,
  );
}

/**
 * The venue page. App can hand over a fresh object for the same place (map
 * tiles reload), so the page pins one venue per slug: content is fetched once
 * per place, and a new slug remounts the page at the top.
 */
export function VenueDetail(props: VenueDetailProps) {
  const [venue, setVenue] = useState(props.venue);
  if (venue.slug !== props.venue.slug) setVenue(props.venue);
  const current = venue.slug === props.venue.slug ? venue : props.venue;
  return <VenueDetailInner key={current.slug} {...props} venue={current} />;
}
