/** Controlla il CSS reale da disco; jsdom può ignorare gli import ?raw. */
import { readFileSync } from 'node:fs';

const files = [
  'src/styles.css','src/design.css','src/alpineExplore.css',
  'src/locationProfile.css','src/homeHeroV2.css',
  'src/alpineMap.css','src/exploreNavigation.css','src/cimaWorkspace.css',
  'src/routeDetail.css','src/cimaSystem.css','src/alpineAtlas.css',
];
const cssByFile = new Map();
for (const file of files) {
  const css = readFileSync(new URL('../'+file,import.meta.url),'utf8');
  cssByFile.set(file,css);
  const stripped = css.replace(/\/\*[\s\S]*?\*\//g,'')
    .replace(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g,'""');
  let level=0;
  for (let i=0;i<stripped.length;i++) {
    if(stripped[i]==='{')level++;
    if(stripped[i]==='}')level--;
    if(level<0)throw Error('CSS con parentesi di chiusura in eccesso: '+file);
  }
  if(level!==0)throw Error('CSS con regole non chiuse: '+file+' ('+level+')');
  console.log('OK CSS bilanciato',file);
}
const explore=cssByFile.get('src/alpineExplore.css');
const hero=cssByFile.get('src/homeHeroV2.css');
if(!explore.includes('.cb-explore-screen{height:100vh;height:100dvh'))
  throw Error('Manca il layout viewport per i luoghi');
if(!explore.includes('container-type:inline-size')||!explore.includes('@container'))
  throw Error('Mancano container queries per le card');
if(explore.includes('height:calc(100dvh - 205px)'))
  throw Error('Il vecchio valore fisso di altezza è ancora presente');
if(!hero.includes('.cb-hero-v3-directory')||hero.includes('.cb-hero-v2-landscape'))
  throw Error('La hero non è quella editoriale');
console.log('OK layout adattivo e hero editoriale');
