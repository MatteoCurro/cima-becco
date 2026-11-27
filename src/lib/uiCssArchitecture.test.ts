import { describe, expect, it } from 'vitest';
import legacyDesign from '../design.css?raw';
import legacyStyles from '../styles.css?raw';
import systemCss from '../cimaSystem.css?raw';
import polishCss from '../cimaPolish.css?raw';
import workspaceCss from '../cimaWorkspace.css?raw';
import routeCss from '../routeDetail.css?raw';
import atlasCss from '../alpineAtlas.css?raw';
import locationCss from '../locationProfile.css?raw';
import chromeCss from '../components/siteChrome.css?raw';
import jumpSource from '../components/DetailJumpNav.tsx?raw';
import faSource from '../components/FaIcon.tsx?raw';
import placeIconSource from '../components/AlpinePlaceIcon.tsx?raw';
const SOURCE: Record<string,string>={
  '../design.css':legacyDesign,'../styles.css':legacyStyles,
  '../cimaSystem.css':systemCss,'../cimaPolish.css':polishCss,
  '../cimaWorkspace.css':workspaceCss,'../routeDetail.css':routeCss,
  '../alpineAtlas.css':atlasCss,'../locationProfile.css':locationCss,
  '../components/siteChrome.css':chromeCss,
  '../components/DetailJumpNav.tsx':jumpSource,
  '../components/FaIcon.tsx':faSource,
  '../components/AlpinePlaceIcon.tsx':placeIconSource,
};
function source(path:string) { return SOURCE[path] ?? ''; }
describe('proprietà CSS del design system',()=>{
  it('impedisce la stratificazione di header/footer/wordmark nel legacy',()=>{
    const legacy=['../design.css','../styles.css','../cimaSystem.css','../cimaPolish.css',
      '../cimaWorkspace.css','../routeDetail.css','../alpineAtlas.css','../locationProfile.css'];
    for(const path of legacy){
      const css=source(path).replace(/\/\*[\s\S]*?\*\//g,'');
      expect(css,'Chrome fuori dal proprietario: '+path)
        .not.toMatch(/\.(site-header|site-footer|wordmark)(?![\w-])/);
    }
    const owner=source('../components/siteChrome.css');
    expect(owner).toContain('.site-header-row');
    expect(owner).toContain('.site-footer-inner');
  });
  it('la navigazione interna non usa href con hash, riservati al router',()=>{
    const nav=source('../components/DetailJumpNav.tsx');
    expect(nav).not.toContain("href={'#");
    expect(nav).toContain('scrollToDetailSection');
  });
  it('SVG Font Awesome sono locali e non richiedono un webfont o CDN',()=>{
    const fa=source('../components/FaIcon.tsx');
    expect(fa).toContain('Font Awesome Free');
    expect(fa).toContain('viewBox');
    expect(fa).not.toContain('https://kit.fontawesome.com/');
    expect(source('../components/AlpinePlaceIcon.tsx')).toContain('<FaIcon');
  });
});
