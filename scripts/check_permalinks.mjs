import { mergeRefugesForSeo } from './merge_refuges_for_seo.mjs';
import { mergeSheltersForSeo } from './merge_shelters_for_seo.mjs';
import { applyRuralStructureEvidence } from '../src/lib/ruralStructureEvidence.js';
import { canonicalAtlasSlug, atlasCanonicalPath } from '../src/lib/placePermalinks.js';
/** Verifica prerender SEO + hydration delle URL profonde sulla build reale. */
import {readFileSync,readdirSync,existsSync} from 'node:fs';
import {join} from 'node:path';

const dist=new URL('../dist/',import.meta.url).pathname;
const hasComuni=existsSync(join(dist,'data','atlas','municipalities-v1.json'));
const sections=['rifugi','bivacchi','borghi','route','trekking',...(hasComuni?['comuni']:[])];
for(const section of sections){
  const base=join(dist,section);
  if(!existsSync(base))throw Error('Manca la categoria '+section);
  const slugs=readdirSync(base,{withFileTypes:true}).filter(x=>x.isDirectory()).map(x=>x.name);
  const slug=slugs.find(name=>{
    const filename=join(base,name,'index.html');
    return existsSync(filename)&&readFileSync(filename,'utf8').includes('id="root"');
  });
  if(!slug)throw Error('Nessun permalink SEO completo generato: '+section);
  const file=join(base,slug,'index.html');
  if(!existsSync(file))throw Error('Manca '+file);
  const html=readFileSync(file,'utf8');
  if(!html.includes('id="root"'))throw Error('Manca root React: '+file);
  if(!/<script[^>]*type="module"[^>]*src="[^"]*\/assets\//i.test(html))
    throw Error('Manca entrypoint Vite nel permalink '+file);
  if(!html.includes('<link rel="canonical"'))throw Error('Manca canonical: '+file);
  if(!html.includes('application/ld+json'))throw Error('Mancano i dati strutturati: '+file);
  console.log('OK',section,slug,'→ SEO + SPA');
}

const canonical='https://www.cimabecco.it';
const home=readFileSync(join(dist,'index.html'),'utf8');
const sitemap=readFileSync(join(dist,'sitemap.xml'),'utf8');
const robots=readFileSync(join(dist,'robots.txt'),'utf8');
if(!home.includes('<link rel="canonical" href="'+canonical+'/"'))throw Error('Canonical home non corretto');
if(!home.includes('src="/assets/')||home.includes('src="/cima-becco/assets/'))throw Error('Asset Vite non pubblicati alla radice');
if(!sitemap.includes('<loc>'+canonical+'/</loc>'))throw Error('Sitemap non usa il dominio principale');
if(!robots.includes('Sitemap: '+canonical+'/sitemap.xml'))throw Error('Robots non usa la sitemap principale');
console.log('OK: dominio canonico, base Vite, sitemap e robots');

const alpineBase=mergeSheltersForSeo(mergeRefugesForSeo(
  JSON.parse(readFileSync(join(dist,'data','alpine-places.json'),'utf8')).places,
  existsSync(join(dist,'data','atlas','refuges-v1.json')) ?
    JSON.parse(readFileSync(join(dist,'data','atlas','refuges-v1.json'),'utf8')) : null
), existsSync(join(dist,'data','atlas','shelters-v1.json')) ?
    JSON.parse(readFileSync(join(dist,'data','atlas','shelters-v1.json'),'utf8')) : null
);
const evidencePath=join(dist,'data','atlas','alpine-structure-evidence-v1.json');
const evidence=existsSync(evidencePath)?JSON.parse(readFileSync(evidencePath,'utf8')):null;
const alpine=applyRuralStructureEvidence(alpineBase,evidence);
for(const place of alpine){
  const section=place.kind==='rifugio'?'rifugi':place.kind==='bivacco'?'bivacchi':'borghi';
  const canonical=atlasCanonicalPath(place).replace(/^\//,'');
  const target=join(dist,canonical,'index.html');
  if(!existsSync(target))throw Error('Catalogo con link rotto: '+canonical);
  const canonicalHtml=readFileSync(target,'utf8');
  if(!canonicalHtml.includes('/'+canonical+'">')){
    const authorized=hasComuni && place.kind==='borgo' &&
      JSON.parse(readFileSync(join(dist,'data','atlas','municipalities-v1.json'),'utf8')).entities.some(e=>
       e.sourceIds?.osm===place.osmUrl.replace('https://www.openstreetmap.org/','') &&
       canonicalHtml.includes('/comuni/'+e.slug+'/') && canonicalHtml.includes('noindex,follow'));
    if(!authorized)throw Error('Canonical SEO del luogo assente: '+canonical);
  }
  if((place.kind==='rifugio'||place.kind==='bivacco')&&canonicalAtlasSlug(place)!==place.slug){
    const legacy=join(dist,section,place.slug,'index.html');
    if(!existsSync(legacy))throw Error('Permalink storico non conservato: '+section+'/'+place.slug);
    const html=readFileSync(legacy,'utf8');
    if(!html.includes('http-equiv="refresh"')||!html.includes('noindex,follow'))
      throw Error('Permalink storico senza redirect e noindex: '+section+'/'+place.slug);
  }
}
// Check previous wrong-category URLs and allow G1 rural support points to
// remain present but explicitly noindex until stronger evidence is acquired.
if(evidence?.releaseChannel==='VERIFIED_RURAL_STRUCTURE_TYPES'){
  for(const record of evidence.entries||[]){
    if(record.sourceIds?.osm){
      const item=alpine.find(p=>p.sourceIds?.osm===record.sourceIds.osm||
        p.osmUrl==='https://www.openstreetmap.org/'+record.sourceIds.osm);
      if(!item)throw Error('Casera verified but absent from atlas: '+record.name);
      if(item.kind!=='bivacco')throw Error('Casera still shown as refuge: '+item.name);
      const newPath=atlasCanonicalPath(item);
      const oldItem={...item,kind:'rifugio'};
      for(const oldPath of [atlasCanonicalPath(oldItem),'/rifugi/'+item.slug+'/']){
        const file=join(dist,oldPath.slice(1),'index.html');
        if(!existsSync(file))throw Error('Missing former refuge redirect '+oldPath);
        const html=readFileSync(file,'utf8');
        if(!html.includes('noindex,follow')||!html.includes(newPath))
          throw Error('Former refuge URL lacks safe canonical redirect '+oldPath);
      }
    }else if(record.sourceIds?.official){
      const item=alpine.find(p=>p.sourceIds?.official===record.sourceIds.official);
      if(!item||item.kind!=='bivacco'||item.subtype!=='support_point')
        throw Error('Rural support point missing '+record.name);
      const file=join(dist,'bivacchi',item.slug,'index.html');
      if(!existsSync(file)||!readFileSync(file,'utf8').includes('noindex,follow'))
        throw Error('G1 rural support must stay accessible but noindex '+item.name);
    }
  }
}
const example=join(dist,'borghi','osm-n-240044790','index.html');
if(!existsSync(example))throw Error('Permalink Abfaltersbach mancante');
const html=readFileSync(example,'utf8');
if(!html.includes('noindex,follow'))throw Error('Pagina locale povera di dati senza noindex');
console.log('OK: '+alpine.length+' permalinks reali, compreso Abfaltersbach');

if(hasComuni){
  const release=JSON.parse(readFileSync(join(dist,'data','atlas','municipalities-v1.json'),'utf8'));
  const published=release.entities.filter(e=>e.quality?.gate==='G2'&&e.quality?.seoIndexable);
  if(!published.length)throw Error('Comuni: nessuna scheda G2');
  for(const e of published){
    const filename=join(dist,'comuni',e.slug,'index.html');
    if(!existsSync(filename))throw Error('Comune senza permalink: '+e.slug);
    const html=readFileSync(filename,'utf8');
    if(!html.includes('<link rel="canonical" href="https://www.cimabecco.it/comuni/'+e.slug+'/">'))
      throw Error('Canonical non coerente per comune '+e.slug);
    if(html.includes('noindex,follow'))throw Error('Comune G2 non indicizzato: '+e.slug);
    if(!sitemap.includes('/comuni/'+e.slug+'/'))throw Error('Comune G2 fuori sitemap: '+e.slug);
    if(!e.media.some(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&m.licence&&m.author))
      throw Error('Comune senza fotografia verificata: '+e.slug);
    if(!e.textSources?.length)throw Error('Comune G2 senza testo attribuito: '+e.slug);
  }
  console.log('OK: '+published.length+' comuni G2 con URL, foto, testi, schema e sitemap');
}
