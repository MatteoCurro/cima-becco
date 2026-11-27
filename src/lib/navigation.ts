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
