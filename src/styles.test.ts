import { describe, expect, it } from 'vitest';
import { readFileSync } from 'node:fs';

/** Vitest con jsdom può restituire stringhe vuote per gli import CSS ?raw. */
const readCss = (name: string) => readFileSync(new URL(name, import.meta.url), 'utf8');
const design = readCss('./design.css');
const styles = readCss('./styles.css');
const explore = readCss('./alpineExplore.css');
const location = readCss('./locationProfile.css');
const hero = readCss('./homeHeroV2.css');

/** Una regola non chiusa può invalidare tutto il CSS successivo. */
function unclosed(css: string): { depth: number; negativeAt: number | null } {
  const text = css.replace(/\/\*[\s\S]*?\*\//g, '').replace(/"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*'/g, '""');
  let depth = 0;
  let negativeAt: number | null = null;
  for (let i = 0; i < text.length; i++) {
    if (text[i] === '{') depth += 1;
    else if (text[i] === '}') {
      depth -= 1;
      if (depth < 0 && negativeAt === null) negativeAt = text.slice(0, i).split('\n').length;
    }
  }
  return { depth, negativeAt };
}

describe('stylesheets', () => {
  it.each([
    ['design.css', design],
    ['styles.css', styles],
    ['alpineExplore.css', explore],
    ['locationProfile.css', location],
    ['homeHeroV2.css', hero],
  ])('%s closes every rule it opens', (_name, css) => {
    expect(unclosed(css)).toEqual({ depth: 0, negativeAt: null });
  });

  it('riserva spazio reale a elenco e mappa senza sottrazioni hard-coded', () => {
    expect(explore).toContain('.cb-explore-screen{height:100vh;height:100dvh');
    expect(explore).toContain('container-type:inline-size');
    expect(explore).not.toContain('height:calc(100dvh - 205px)');
  });

  it('la hero non usa il precedente paesaggio decorativo', () => {
    expect(hero).toContain('.cb-hero-v3-directory');
    expect(hero).not.toContain('.cb-hero-v2-landscape');
  });
});
