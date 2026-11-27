import { useEffect, useRef, type PointerEvent } from 'react';
import { prefersReducedMotion } from '../lib/dom';
import { openMapWith } from '../lib/mapIntent';
import { LocateIcon, SearchIcon } from './icons';
import { focusSiteSearch } from './SearchBar';

/**
 * Where each step sits on the drawn trail, in the SVG's 1000 × 140 box: x as
 * a share of the width (each step is centred over its third of the page) and
 * y in pixels, read off the path below at that x.
 */
const STEPS = [
  { x: 16.7, y: 72, title: 'PUNTA LA CIMA', text: 'Vetta, borgo o rifugio: trova la tua scusa per salire.' },
  { x: 50, y: 40, title: 'CONTA I METRI', text: 'Dislivello, sentieri e difficoltà. Poi non dire che non lo sapevi.' },
  { x: 83.3, y: 60, title: 'PORTA IL GPX', text: 'Sul sentiero serve la testa. E una traccia fatta bene.' },
];

/** A ridge from the start (left, low) through the three steps to the summit flag (right, high). */
const TRAIL = 'M10 112 C 60 108, 110 76, 167 72 S 250 104, 300 100 S 420 44, 500 40 S 600 92, 650 96 S 770 64, 833 60 S 940 34, 990 28';

/** Trama topografica *illustrata*, nessun riferimento ai rilievi asiatici di HillGPX. */
function HeroMap({ mapRef }: { mapRef: React.RefObject<HTMLDivElement> }) {
  return <div className="trail-hero-map cb-hero-topo" ref={mapRef} aria-hidden="true">
    <svg className="cb-hero-topo-lines" viewBox="0 0 1000 500" preserveAspectRatio="xMidYMid slice" focusable="false">
      <g fill="none" stroke="#42674e" strokeWidth="1.4" opacity=".34">
        {Array.from({length:12},(_,i)=>(
          <path key={i} d={`M ${-210+i*23} ${440-i*25} C 30 ${270-i*20}, 140 ${390-i*38}, 320 ${200-i*6} S 750 ${315-i*27}, 1200 ${55+i*7}`}/>
        ))}
        {Array.from({length:8},(_,i)=>(
          <path key={`b${i}`} d={`M ${90+i*20} ${-50+i*24} C 310 ${120+i*21}, 650 ${-80+i*10}, 950 ${190+i*32}`}/>
        ))}
      </g>
      <path d="M570 450 750 135 843 260 906 155 1060 450Z" fill="#c2d7b6" opacity=".53"/>
      <path d="M655 450 750 135 819 270 905 156 1030 450" fill="none" stroke="#143d2f" strokeWidth="4" opacity=".14"/>
      <path d="m748 135 33 58-26-13-38 19Z" fill="#f2f8e8"/>
      <circle cx="752" cy="160" r="16" fill="#ff2677"/>
      <path d="m741 161 8 8 17-22" stroke="#fff" strokeWidth="5" fill="none" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>
    <span className="cb-hero-topo-stamp">ALTA QUOTA, BASSA PAZIENZA.</span>
  </div>;
}

/** Pointer position over the hero as -0.5…0.5 each way, written straight to CSS (no re-render). */
function useParallax() {
  const mapRef = useRef<HTMLDivElement>(null);
  const frame = useRef(0);
  const enabled = useRef(false);
  useEffect(() => {
    enabled.current = window.matchMedia('(hover: hover) and (pointer: fine)').matches && !prefersReducedMotion();
    return () => cancelAnimationFrame(frame.current);
  }, []);
  const move = (event: PointerEvent<HTMLElement>) => {
    if (!enabled.current) return;
    const box = event.currentTarget.getBoundingClientRect();
    const x = (event.clientX - box.left) / box.width - 0.5;
    const y = (event.clientY - box.top) / box.height - 0.5;
    cancelAnimationFrame(frame.current);
    frame.current = requestAnimationFrame(() => {
      mapRef.current?.style.setProperty('--px', x.toFixed(3));
      mapRef.current?.style.setProperty('--py', y.toFixed(3));
    });
  };
  const leave = () => {
    cancelAnimationFrame(frame.current);
    mapRef.current?.style.setProperty('--px', '0');
    mapRef.current?.style.setProperty('--py', '0');
  };
  return { mapRef, move, leave };
}

/**
 * "Cerca una località": back to the top and into the header search, with its
 * suggestions open. The focus happens in this same click, so phones open the
 * keyboard; the scroll is instant under reduced motion.
 */
function searchByRegion() {
  window.scrollTo({ top: 0, behavior: prefersReducedMotion() ? 'auto' : 'smooth' });
  focusSiteSearch();
}

/**
 * The landing page's hero, shown on every visit: one line of promise, what
 * the site is, three ways in (near me, search, upload), and how it works as three steps on a trail
 * that draws itself from the start to the summit. On phones the trail turns
 * into a vertical line down the steps. Under reduced motion it is drawn
 * already. Behind it all, a live topographic map of Bukit Timah (HeroMap).
 */
export function TrailHero() {
  const { mapRef, move, leave } = useParallax();
  return (
    <section className="trail-hero" onPointerMove={move} onPointerLeave={leave}>
      <HeroMap mapRef={mapRef} />
      <div className="home-shell">
        <h1 className="trail-hero-title">
          MA CHI TE L’HA <span>FATTO FARE?</span>
        </h1>
        <p className="trail-hero-lead">
          Rifugi, sentieri, borghi, ferrate e GPX. Il panorama te lo guadagni. Le scuse lasciale a valle.
        </p>
        <div className="trail-hero-actions">
          <button type="button" className="btn btn-dark" onClick={() => openMapWith({ kind: 'near-me' })}>
            <LocateIcon size={16} />
            FAMMI SALIRE
          </button>
          <button type="button" className="btn btn-light" onClick={searchByRegion}>
            <SearchIcon size={16} />
            CERCA LA SCUSA
          </button>
          <a className="btn btn-light" href="#pianifica">
            <SearchIcon size={16} />
            DISEGNA LA FOLLIA
          </a>
          <a className="btn btn-light" href="#atlante/rifugi">RIFUGI &amp; BORGHI ↗</a>
        </div>

        <div className="hero-trail">
          <svg className="trail-line" viewBox="0 0 1000 140" preserveAspectRatio="none" aria-hidden="true" focusable="false">
            <path className="trail-ghost" d={TRAIL} />
            <path className="trail-path" d={TRAIL} pathLength={1} />
          </svg>
          <span className="trail-end start" aria-hidden="true" />
          <span className="trail-end finish" aria-hidden="true">
            <svg viewBox="0 0 16 20" width="16" height="20" focusable="false">
              <path d="M2 19V2M2 3h11l-3 3.5L13 10H2" />
            </svg>
          </span>
          <ol className="trail-steps" aria-label="How it works">
            {STEPS.map((step, i) => (
              <li key={step.title} style={{ '--x': step.x, '--y': step.y, '--i': i } as React.CSSProperties}>
                <span className="trail-dot" aria-hidden="true">{i + 1}</span>
                <strong>{step.title}</strong>
                <span>{step.text}</span>
              </li>
            ))}
          </ol>
        </div>
      </div>
    </section>
  );
}
