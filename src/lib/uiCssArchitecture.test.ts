import { describe, expect, it } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { DetailJumpNav } from '../components/DetailJumpNav';
import { FaIcon } from '../components/FaIcon';
import { AlpinePlaceIcon } from '../components/AlpinePlaceIcon';

/** Checks real DOM output; CSS source ownership is verified by scripts/check_chrome_css.mjs. */
describe('shared UI icons and internal navigation',()=>{
  it('renders SVG path markup without font dependency',()=>{
    const html=renderToStaticMarkup(createElement(FaIcon,{name:'mountain',size:24}));
    expect(html).toContain('viewBox="0 0 512 512"');
    expect(html).toContain('class="cb-fa-icon"');
    expect(html).toContain('<path');
    expect(html).not.toContain('font-awesome');
  });
  it('all mountain place categories render SVG, not emoji',()=>{
    for(const kind of ['rifugio','bivacco','borgo','acqua'] as const){
      const html=renderToStaticMarkup(createElement(AlpinePlaceIcon,{kind,size:24}));
      expect(html).toContain('<svg');
      expect(html).toContain('<path');
      expect(html).not.toContain('🏔');
    }
  });
  it('quick links use buttons and cannot overwrite the SPA route hash',()=>{
    const html=renderToStaticMarkup(createElement(DetailJumpNav,{items:[
      {id:'cb-place-contacts',label:'Contatti',icon:'house'},
      {id:'cb-place-map',label:'Mappa',icon:'map'},
    ]}));
    expect(html).toContain('Naviga questa scheda');
    expect(html).toContain('<button');
    expect(html).not.toContain('href="#');
    expect(html.match(/<button/g)).toHaveLength(2);
  });
});
