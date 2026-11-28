/**
 * Product analytics, all optional and all switched on by build-time settings
 * (see README "Analytics"), so a fork or a local build sends nothing.
 *
 * - VITE_CF_ANALYTICS_TOKEN: Cloudflare Web Analytics. Visits, pages,
 *   countries, referrers and load speed. No cookies, no personal data.
 * - VITE_CF_ANALYTICS_AUTO=1: the same, but Cloudflare adds the script itself
 *   at the edge ("automatic setup" on a proxied domain, as hillgpx.com is), so
 *   nothing is loaded here; it only tells the Privacy page it is running.
 * - VITE_CLARITY_ID: Microsoft Clarity. Heatmaps, scroll depth, rage clicks
 *   and session replays with typed text masked. Free. Set its project to
 *   "cookies off" so it stays cookieless.
 *
 * `track` records the handful of actions that say whether the product works
 * (searching, opening and downloading routes, contributing). Events go to
 * Clarity as custom events; with nothing configured it does nothing.
 */

const CF_TOKEN = (import.meta.env.VITE_CF_ANALYTICS_TOKEN as string | undefined) || '';
const CLARITY_ID = (import.meta.env.VITE_CLARITY_ID as string | undefined) || '';

/** What the privacy page should say is running. */
const CF_AUTO = (import.meta.env.VITE_CF_ANALYTICS_AUTO as string | undefined) === '1';
export const ANALYTICS = { cloudflare: Boolean(CF_TOKEN) || CF_AUTO, clarity: Boolean(CLARITY_ID) };

type ClarityFn = ((...args: unknown[]) => void) & { q?: unknown[][] };
declare global {
  interface Window {
    clarity?: ClarityFn;
  }
}

function addScript(src: string, attributes: Record<string, string> = {}) {
  const script = document.createElement('script');
  script.async = true;
  script.defer = true;
  script.src = src;
  for (const [name, value] of Object.entries(attributes)) script.setAttribute(name, value);
  document.head.appendChild(script);
}

let started = false;

/** Start whatever is configured, after the page has painted, so it never slows the first view. */
export function initAnalytics(): void {
  if (started || typeof window === 'undefined') return;
  started = true;
  if (!CF_TOKEN && !CLARITY_ID) return;
  const start = () => {
    if (CF_TOKEN) addScript('https://static.cloudflareinsights.com/beacon.min.js', { 'data-cf-beacon': JSON.stringify({ token: CF_TOKEN, spa: true }) });
    if (CLARITY_ID) {
      // Clarity's queue stub: calls made before its script arrives are replayed.
      const queue: ClarityFn = (...args: unknown[]) => {
        (queue.q ??= []).push(args);
      };
      window.clarity ??= queue;
      // Cookieless, whatever the Clarity project is set to: with storage
      // consent denied (Consent API v2, queued before the tag loads) Clarity
      // sets no cookies and shares nothing with Microsoft Ads. Each visit is
      // recorded on its own instead of being linked to earlier ones.
      window.clarity('consentv2', { ad_Storage: 'denied', analytics_Storage: 'denied' });
      addScript(`https://www.clarity.ms/tag/${encodeURIComponent(CLARITY_ID)}`);
    }
  };
  if ('requestIdleCallback' in window) window.requestIdleCallback(start, { timeout: 4000 });
  else setTimeout(start, 2000);
}

export type TrackedEvent =
  | 'search'
  | 'route_open'
  | 'gpx_download'
  | 'gpx_upload'
  | 'photo_upload'
  | 'review_post'
  | 'route_review_post'
  | 'report_sent'
  | 'contact_sent'
  | 'place_suggested'
  | 'sign_up'
  | 'log_in'
  | 'username_change'
  | 'password_reset'
  | 'map_expand'
  | 'run_needs_submit'
  | 'ranked_route_open'
  | 'route_bookmarked'
  | 'route_edit'
  | 'ghealth_connect'
  | 'ghealth_import'
  | 'atlas_place_view'
  | 'atlas_pass_view'
  | 'atlas_lake_view'
  | 'atlas_place_search'
  | 'hut_claim_request'
  | 'water_source_open';

/** Solo per diagnosi di questo browser. Nessun cookie e nessun evento remoto
 * finché non sarà attivo un backend di statistiche con policy e rate limit. */
export interface LocalInsightEvent {
  event: TrackedEvent;
  label: string;
  at: string;
}
const LOCAL_KEY='cimabecco:insights:v1';
const INTERESTING = new Set<TrackedEvent>([
  'search','route_open','gpx_download','route_bookmarked','atlas_place_view','atlas_pass_view','atlas_lake_view',
  'atlas_place_search','hut_claim_request','water_source_open',
]);
export function localInsights():LocalInsightEvent[]{
  try{
    const events=JSON.parse(localStorage.getItem(LOCAL_KEY)||'[]') as LocalInsightEvent[];
    return Array.isArray(events)?events.filter(x=>x&&typeof x.event==='string'&&typeof x.at==='string').slice(-1800):[];
  }catch{return [];}
}
function recordLocal(event:TrackedEvent,label=''):void{
  if(typeof window==='undefined'||!INTERESTING.has(event))return;
  try{
    const now=new Date().toISOString();const events=localInsights();
    const last=events[events.length-1];
    if(last&&last.event===event&&last.label===label&&Date.now()-Date.parse(last.at)<1200)return;
    events.push({event,label:label.trim().slice(0,100),at:now});
    localStorage.setItem(LOCAL_KEY,JSON.stringify(events.slice(-1800)));
  }catch{/* modalità privata: no storage */}
}
export function summarizeInsights(events:LocalInsightEvent[]=localInsights()){
  const counts:Record<string,number>={};
  const subjects=new Map<string,Map<string,number>>();
  for(const row of events){
    counts[row.event]=(counts[row.event]||0)+1;
    if(!row.label)continue;
    if(!subjects.has(row.event))subjects.set(row.event,new Map());
    const map=subjects.get(row.event)!;
    map.set(row.label,(map.get(row.label)||0)+1);
  }
  const top=(event:TrackedEvent,limit=12)=>[...(subjects.get(event)||new Map()).entries()]
    .sort((a,b)=>b[1]-a[1]||a[0].localeCompare(b[0])).slice(0,limit)
    .map(([name,total])=>({name,total}));
  return {total:events.length,counts,
    searches:top('search'),routes:top('route_open'),places:top('atlas_place_view'),
    downloads:top('gpx_download'),bookmarks:top('route_bookmarked')};
}

/** Record one product action (and an optional short label, e.g. the route). */
export function track(event: TrackedEvent, label?: string): void {
  recordLocal(event,label);
  if (!CLARITY_ID || typeof window === 'undefined' || !window.clarity) return;
  window.clarity('event', event);
  if (label) window.clarity('set', event, label.slice(0, 80));
}
