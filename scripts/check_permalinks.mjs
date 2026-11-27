/** Verifica prerender SEO + hydration delle URL profonde sulla build reale. */
import {readFileSync,readdirSync,existsSync} from 'node:fs';
import {join} from 'node:path';

const dist=new URL('../dist/',import.meta.url).pathname;
const sections=['rifugi','bivacchi','borghi','route','trekking'];
for(const section of sections){
  const base=join(dist,section);
  if(!existsSync(base))throw Error('Manca la categoria '+section);
  const slug=readdirSync(base,{withFileTypes:true}).find(x=>x.isDirectory())?.name;
  if(!slug)throw Error('Nessun permalink generato: '+section);
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
