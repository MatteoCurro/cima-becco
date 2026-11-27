#!/usr/bin/env node
/** Release gate: every displayed CAI/OSM shelter photo must be listed centrally. */
import assert from 'node:assert/strict';
import {existsSync,readFileSync} from 'node:fs';
import {join} from 'node:path';

const root = new URL('../dist/',import.meta.url).pathname;
const read = path => JSON.parse(readFileSync(join(root,path),'utf8'));
const credits = read('data/atlas/credits-v1.json');
const refuges = read('data/atlas/refuges-v1.json');
const shelters = read('data/atlas/shelters-v1.json');
assert.equal(credits.schemaVersion,'1.0');
assert.equal(credits.centralPage,'/fonti-e-crediti/');
assert.ok(Array.isArray(credits.providers) && credits.providers.length>=7);
assert.ok(credits.counts.total>=1000,'regressione dell’indice attribuzioni');
const allMedia = [...refuges.entities,...shelters.entities].flatMap(e=>e.media || []);
const uniqueUrls = new Set(credits.photoCredits.map(p=>p.mediaUrl));
const missing=allMedia.filter(m=>m.kind==='photo' && m.reuseAllowed && m.subjectVerified &&
  m.url?.startsWith('https://') && m.sourceUrl && m.licence && !uniqueUrls.has(m.url));
assert.equal(missing.length,0,String(missing.length)+' fotografie pubblicate senza attribuzione centrale');
const links = credits.photoCredits.filter(p=>p.sourceUrl && p.author && p.licence &&
  p.entityUrl.startsWith('/'));
assert.equal(links.length,credits.counts.total);
const municipalityFile=join(root,'data','atlas','municipalities-v1.json');
if(existsSync(municipalityFile)){
  const communes=read('data/atlas/municipalities-v1.json').entities;
  const creditsByMedia=new Set(credits.photoCredits.map(p=>p.mediaUrl));
  const texts=credits.textCredits||[];
  for(const e of communes){
    if(e.quality?.gate!=='G2')continue;
    for(const media of e.media||[]){
      if(media.reuseAllowed&&media.subjectVerified&&media.url&&media.licence){
        assert.ok(creditsByMedia.has(media.url),e.name+' foto senza credito centrale');
      }
    }
    for(const source of e.textSources||[]){
      assert.ok(texts.some(t=>t.slug===e.slug&&t.sourceId===source.sourceId&&
          t.sourceUrl===source.sourceUrl&&t.licence===source.licence),
        e.name+' testo senza credito centrale');
    }
  }
}
assert.ok(existsSync(join(root,'fonti-e-crediti','index.html')));
const body=readFileSync(join(root,'fonti-e-crediti','index.html'),'utf8');
assert.ok(body.includes('https://www.cimabecco.it/fonti-e-crediti/'));
console.log(JSON.stringify({
  credits:credits.counts.total,caimedia:allMedia.length,
  missingPhotoCredits:missing.length,sourceProviders:credits.providers.length,
  dedicatedPage:true,
}));
