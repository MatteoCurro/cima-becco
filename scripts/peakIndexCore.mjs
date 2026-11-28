/**
 * Rebuild the overview metadata from immutable GeoNames 5-degree source tiles.
 * This is a visibility/census index, not an editorial release: it must not
 * modify source IDs, legacy map slugs or G2 summit dossiers.
 */
export function buildPeakIndex(previous, tiles) {
  const all = [], byCode = new Map(), cells = {}, ids = new Set();
  for (const key of Object.keys(tiles).sort()) {
    const sourceRows = tiles[key];
    if (!Array.isArray(sourceRows)) throw new Error('Invalid tile: ' + key);
    cells[key] = sourceRows.length;
    for (const row of sourceRows) {
      const [id, name, lat, lng, altitude, source, country, feature] = row;
      if (!Number.isSafeInteger(id) || id < 1 ||
          typeof name !== 'string' || !name.trim() ||
          !Number.isFinite(lat) || lat < -90 || lat > 90 ||
          !Number.isFinite(lng) || lng < -180 || lng > 180 ||
          !Number.isFinite(altitude) || typeof source !== 'string' ||
          !/^[A-Z]{2}$/.test(country) || typeof feature !== 'string') {
        throw new Error('Invalid GeoNames row: ' + key + ' / ' + id);
      }
      if (ids.has(id)) throw new Error('Duplicate GeoNames peak ID: ' + id);
      ids.add(id);
      all.push(row);
      if (!byCode.has(country)) byCode.set(country, []);
      byCode.get(country).push(row);
    }
  }

  const ordered = (a, b) => b[4] - a[4] || a[0] - b[0];
  const isSummit = row => row[7] !== 'MTS' && row[7] !== 'HLLS';
  function distinctHigh(sourceRows, limit) {
    const result = [];
    for (const row of sourceRows.filter(isSummit).sort(ordered)) {
      if (result.every(other =>
        111.195 * Math.hypot(
          row[2] - other[2],
          (row[3] - other[3]) * Math.cos((row[2] + other[2]) * Math.PI / 360)
        ) >= 3)) result.push(row);
      if (result.length === limit) break;
    }
    return result;
  }

  const byCountry = {}, rows = {}, topById = new Map();
  const byId = new Map(all.map(row => [row[0], row]));
  // Preserve previous landing highlights if their source ID still exists.
  for (const row of previous.top || []) {
    const fresh = byId.get(row[0]);
    if (fresh) topById.set(fresh[0], fresh);
  }
  for (const code of [...byCode.keys()].sort()) {
    const list = byCode.get(code);
    byCountry[code] = [
      list.length,
      Number(Math.min(...list.map(row => row[3])).toFixed(5)),
      Number(Math.min(...list.map(row => row[2])).toFixed(5)),
      Number(Math.max(...list.map(row => row[3])).toFixed(5)),
      Number(Math.max(...list.map(row => row[2])).toFixed(5)),
    ];
    const picks = distinctHigh(list, 12);
    rows[code] = picks.map(row => row[0]);
    for (const row of picks) topById.set(row[0], row);
  }

  // One actual summit per approximately 0.4° square, plus the already
  // curated highlights. Broad views stay small yet cover all five countries.
  const winners = new Map();
  for (const row of all) {
    if (!isSummit(row)) continue;
    const cell = Math.floor(row[2] / 0.4) + ':' + Math.floor(row[3] / 0.4);
    const held = winners.get(cell);
    if (!held || ordered(row, held) < 0) winners.set(cell, row);
  }
  const top = [...topById.values()].sort(ordered);
  const overviewById = new Map(
    [...winners.values(), ...top.filter(isSummit)].map(row => [row[0], row])
  );
  return {
    tile: previous.tile,
    total: all.length,
    countries: byCode.size,
    byCountry,
    rows,
    cells,
    top,
    overviewStepDeg: 0.4,
    overview: [...overviewById.values()].sort(ordered),
  };
}
