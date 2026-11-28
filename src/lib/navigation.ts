/** Navigation targets replace the previous path, query and fragment. */
export function homeHref(hash = ''): string {
  return import.meta.env.BASE_URL + (hash ? '#' + hash.replace(/^#/, '') : '');
}
export function routeHref(slug: string): string {
  return import.meta.env.BASE_URL + 'route/' + encodeURIComponent(slug) + '/';
}
export function navigateHome(hash: string): void {
  window.location.assign(homeHref(hash));
}

/** Solo i percorsi importati nella build hanno un file SEO su GitHub Pages. */
export function routeDetailHref(slug: string, source: 'curated' | 'community' | 'local'): string {
  return source === 'curated' ? routeHref(slug) : homeHref('route/' + encodeURIComponent(slug));
}

/** An explicit map URL takes precedence over the previous tab's preference. */
export function initialMapMode(hash: string, remembered: string | null, routeDetail = false): 'routes' | 'climbs' {
  if (routeDetail || hash === '#routes' || hash.startsWith('#route/')) return 'routes';
  if (hash === '#map' || hash.startsWith('#map/') || hash.startsWith('#venue/')) return 'climbs';
  return remembered === 'routes' ? 'routes' : 'climbs';
}
/** Navigation must work with storage blocked by privacy settings. */
export function lastMapMode(): string | null {
  try { return sessionStorage.getItem('hillgpx:mode'); } catch { return null; }
}
