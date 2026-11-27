#!/usr/bin/env node
/**
 * CSS ownership gate: validates the actual source files, not CSS imports
 * (Vitest may replace CSS imports with empty strings in a test environment).
 *
 * The old cascading layout patches caused header/footer widths to differ by
 * page. A stylesheet outside the owner must not define any chrome selector.
 */
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root=fileURLToPath(new URL('../',import.meta.url));
const read=(path)=>readFileSync(resolve(root,path),'utf8');
const stripComments=(css)=>css.replace(/\/\*[\s\S]*?\*\//g,'');
const owner='src/components/siteChrome.css';
const detailOwner='src/components/detailSections.css';
const cssFiles=[
  'src/styles.css','src/design.css','src/cimaPolish.css','src/cimaSystem.css',
  'src/cimaWorkspace.css','src/exploreNavigation.css','src/alpineExplore.css',
  'src/alpineAtlas.css','src/locationProfile.css','src/routeDetail.css',
  'src/components/atlasDossier.css','src/components/atlasNearby.css',
  owner,detailOwner,'src/components/fontAwesome.css',
];
const errors=[];
for(const path of cssFiles){
  const css=stripComments(read(path));
  if(path!==owner){
    const match=css.match(/\.(?:site-header|site-footer|wordmark|cb-explore-trigger|cb-explore-menu)[\w-]*/);
    if(match)errors.push(path+' contains a Chrome selector: '+match[0]);
  }
  if(path!==detailOwner){
    const match=css.match(/\.cb-detail-jump[\w-]*/);
    if(match)errors.push(path+' contains a quick navigation style: '+match[0]);
  }
}
const chrome=read(owner);
for(const required of ['.site-header','.site-header-row','.site-footer','.site-footer-inner','.wordmark','.cb-explore-menu']){
  if(!chrome.includes(required))errors.push('Chrome missing ownership of '+required);
}
if(chrome.includes('!important'))errors.push('Chrome owner must not rely on !important');
const detail=read(detailOwner);
if(!detail.includes('.cb-detail-jump') || !detail.includes('.cb-detail-group')){
  errors.push('Detail styles owner missing quick links or sections');
}
const quickSource=read('src/components/DetailJumpNav.tsx');
if(/href\s*=\s*\{\s*['"]#/.test(quickSource))errors.push('Quick navigation uses SPA-reserved # hash links');
const fa=read('src/components/FaIcon.tsx');
if(!fa.includes('Font Awesome Free') || !fa.includes('viewBox'))errors.push('Missing local Font Awesome SVG implementation');
if(errors.length){
  for(const error of errors)console.error('CSS ownership error:',error);
  process.exitCode=1;
}else{
  console.log('UI CSS ownership verified across '+cssFiles.length+' stylesheets.');
}
