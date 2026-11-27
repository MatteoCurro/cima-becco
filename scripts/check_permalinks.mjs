import { mergeRefugesForSeo } from './merge_refuges_for_seo.mjs';
import { canonicalAtlasSlug, atlasCanonicalPath } from '../src/lib/placePermalinks.js';
/** Verifica prerender SEO + hydration delle URL profonde sulla build reale. */
import {readFileSync,readdirSync,existsSync} from 'node:fs';
import {join} from 'node:path';

const dist=new URL('../dist/',import.meta.url).pathname;
const sections=['rifugi','bivacchi','borghi','route','trekking'];
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

const alpine=mergeRefugesForSeo(
  JSON.parse(readFileSync(join(dist,'data','alpine-places.json'),'utf8')).places,
  existsSync(join(dist,'data','atlas','refuges-v1.json')) ?
    JSON.parse(readFileSync(join(dist,'data','atlas','refuges-v1.json'),'utf8')) : null
);
for(const place of alpine){
  const section=place.kind==='rifugio'?'rifugi':place.kind==='bivacco'?'bivacchi':'borghi';
  const canonical=atlasCanonicalPath(place).replace(/^\//,'');
  const target=join(dist,canonical,'index.html');
  if(!existsSync(target))throw Error('Catalogo con link rotto: '+canonical);
  const canonicalHtml=readFileSync(target,'utf8');
  if(!canonicalHtml.includes('/'+canonical+'">'))throw Error('Canonical SEO del luogo assente: '+canonical);
  if(place.kind==='rifugio'&&canonicalAtlasSlug(place)!==place.slug){
    const legacy=join(dist,section,place.slug,'index.html');
    if(!existsSync(legacy))throw Error('Permalink storico non conservato: '+section+'/'+place.slug);
    const html=readFileSync(legacy,'utf8');
    if(!html.includes('http-equiv="refresh"')||!html.includes('noindex,follow'))
      throw Error('Permalink storico senza redirect e noindex: '+section+'/'+place.slug);
  }
}
const example=join(dist,'borghi','osm-n-240044790','index.html');
if(!existsSync(example))throw Error('Permalink Abfaltersbach mancante');
const html=readFileSync(example,'utf8');
if(!html.includes('noindex,follow'))throw Error('Pagina locale povera di dati senza noindex');
console.log('OK: '+alpine.length+' permalinks reali, compreso Abfaltersbach');
