import { describe, expect, it } from 'vitest';
import design from './design.css?raw';
import styles from './styles.css?raw';
import explore from './alpineExplore.css?raw';
import location from './locationProfile.css?raw';
import hero from './homeHeroV2.css?raw';

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
