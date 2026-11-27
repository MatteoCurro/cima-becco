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
