import type { RouteActivity } from '../types';
import { ACTIVITY_PATHS } from '../lib/activityGlyphs';
import { ACTIVITY_LABEL } from '../lib/routeAnalysis';

export function ActivityIcon({ activity, size = 14 }: { activity: RouteActivity; size?: number }) {
  return (
    <svg viewBox="0 0 24 24" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
      <path d={ACTIVITY_PATHS[activity]} />
    </svg>
  );
}

/** Escursione, trail running o ferrata, con icona dedicata. */
export function ActivityTag({ activity }: { activity: RouteActivity }) {
  return (
    <span className={`activity-tag ${activity}`}>
      <ActivityIcon activity={activity} />
      {ACTIVITY_LABEL[activity]}
    </span>
  );
}
