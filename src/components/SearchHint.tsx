import { useEffect, useState } from 'react';
import { prefersReducedMotion } from '../lib/dom';

/** Places worth typing: each is found by the header search (or its place lookup). */
const HINTS = ['Casso', 'Erto', 'Sottoguda', 'Zoppè di Cadore', 'Colle Santa Lucia', 'Cibiana', 'Passo Giau', 'Cortina d’Ampezzo'];
const STEP_MS = 2600;

/**
 * The header search's placeholder: "Search" followed by a place that rolls
 * over every few seconds, so the box shows what it can find. It sits over the
 * empty input (the input keeps an aria-label) and disappears once you type.
 * Under reduced motion it is a plain, still line.
 */
export function SearchHint({ hidden }: { hidden: boolean }) {
  const [index, setIndex] = useState(0);
  const still = prefersReducedMotion();
  useEffect(() => {
    if (hidden || still) return;
    const timer = window.setInterval(() => setIndex((i) => (i + 1) % HINTS.length), STEP_MS);
    return () => window.clearInterval(timer);
  }, [hidden, still]);
  if (hidden) return null;
  return (
    <span className="search-hint" aria-hidden="true">
      {still ? (
        'Cerca cime, sentieri e paesini sperduti'
      ) : (
        <>
          Cerca{' '}
          <span className="search-hint-word" key={index}>
            {HINTS[index]}
          </span>
        </>
      )}
    </span>
  );
}
