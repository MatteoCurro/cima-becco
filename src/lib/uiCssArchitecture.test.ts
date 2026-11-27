import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

function source(path:string) {
  return readFileSync(fileURLToPath(new URL(path, import.meta.url)), 'utf8');
}
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
