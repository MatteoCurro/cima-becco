/** First-stage geographic envelope; authoritative national polygons will replace this before the full import. */
export function inCimaBeccoArea(lat: number, lng: number): boolean {
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return false;
  const italy = lng >= 6 && lng <= 19 && lat >= 35 && lat <= 47.5;
  const alpsWest = lng >= 5 && lng < 8 && lat >= 43.5 && lat <= 47.5;
  const alpsCentral = lng >= 6 && lng <= 11 && lat >= 45 && lat <= 48.2;
  const alpsEast = lng >= 9 && lng <= 17.5 && lat >= 45.3 && lat <= 48.5;
  return italy || alpsWest || alpsCentral || alpsEast;
}
