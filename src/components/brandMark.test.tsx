import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { Mark } from './icons';

describe('Cima Becco · identità condivisa', () => {
  it('usa una cima e due corna separatamente animabili', () => {
    const html=renderToStaticMarkup(<Mark size={36}/>);
    expect(html).toContain('cb-mark__peak');
    expect(html).toContain('cb-mark__horn--left');
    expect(html).toContain('cb-mark__horn--right');
    expect(html).toContain('cb-mark__chin');
    expect(html).toContain('width="36"');
    expect(html).toContain('aria-hidden="true"');
  });
  it('assegna clipPath indipendenti a due marchi nella stessa pagina', () => {
    const html=renderToStaticMarkup(<><Mark/><Mark/></>);
    const ids=[...html.matchAll(/<clipPath id="([^"]+)"/g)].map(match=>match[1]);
    expect(ids).toHaveLength(2);
    expect(ids[0]).not.toBe(ids[1]);
    for (const id of ids) expect(html).toContain(`clip-path="url(#${id})"`);
  });
});
