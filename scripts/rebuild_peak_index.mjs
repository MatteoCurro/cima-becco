import { readFileSync, readdirSync, writeFileSync } from 'node:fs';
import { resolve, join } from 'node:path';
import { buildPeakIndex } from './peakIndexCore.mjs';

const directory = resolve('public/data/peaks');
const indexPath = join(directory, 'index.json');
const previous = JSON.parse(readFileSync(indexPath, 'utf8'));
const filenames = readdirSync(directory).filter(name => /^\d+_\d+\.json$/.test(name)).sort();
const tiles = Object.fromEntries(filenames.map(name => [
  name.slice(0, -5), JSON.parse(readFileSync(join(directory, name), 'utf8'))
]));
const rebuilt = buildPeakIndex(previous, tiles);
const searchPath = join(directory, 'search.json');
// A single lazy-loaded search snapshot; it preserves all raw source identities.
const searchRows = filenames.flatMap(name => tiles[name.slice(0, -5)]);
if (searchRows.length !== rebuilt.total) throw new Error('Missing GeoNames search records');
if (process.argv.includes('--check')) {
  const storedSearch = JSON.parse(readFileSync(searchPath, 'utf8'));
  if (JSON.stringify(rebuilt) !== JSON.stringify(previous) ||
      JSON.stringify(searchRows) !== JSON.stringify(storedSearch)) {
    console.error('GeoNames index or search catalog is out of sync: run node scripts/rebuild_peak_index.mjs');
    process.exitCode = 1;
  } else {
    console.log('GeoNames census OK:', rebuilt.total, 'source records,', rebuilt.overview.length, 'overview peaks');
  }
} else {
  writeFileSync(indexPath, JSON.stringify(rebuilt) + '\n', 'utf8');
  writeFileSync(searchPath, JSON.stringify(searchRows) + '\n', 'utf8');
  console.log('GeoNames census rebuilt:', rebuilt.total, 'source records,', rebuilt.overview.length, 'overview peaks');
}
