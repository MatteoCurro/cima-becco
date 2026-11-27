import { openMapWith } from '../lib/mapIntent';
import { LocateIcon } from './icons';
import '../homeHeroV2.css';

/**
 * Home editoriale e operativa. Niente illustrazioni di fantasia, bolloni
 * decorativi o azioni duplicate: a sinistra la promessa, a destra i cinque
 * ingressi reali agli strumenti del sito.
 */
const EXPLORE_LINKS = [
  { href: '#routes', index: '01', name: 'Sentieri', description: 'Tracce GPX, km e dislivelli' },
  { href: '#map', index: '02', name: 'Cime', description: 'Vette e cartografia' },
  { href: '#rifugi', index: '03', name: 'Rifugi', description: 'Posizione, accessi e contatti' },
  { href: '#bivacchi', index: '04', name: 'Bivacchi', description: 'Ripari in quota' },
  { href: '#paesi', index: '05', name: 'Paesi', description: 'Da dove comincia il percorso' },
] as const;

export function TrailHero() {
  return (
    <section className="cb-hero-v3" aria-labelledby="cb-hero-title">
      <div className="cb-hero-v3-inner">
        <div className="cb-hero-v3-intro">
          <span className="cb-hero-v3-kicker">CIMA BECCO / LA MONTAGNA A PORTATA DI MAPPA</span>
          <h1 id="cb-hero-title">DOVE SI VA?<br /><em>IN MONTAGNA.</em></h1>
          <p>Trova un sentiero, controlla il dislivello, scopri rifugi e paesi lungo la strada. Il resto lo fanno le gambe.</p>
          <div className="cb-hero-v3-actions">
            <a className="cb-hero-v3-primary" href="#routes">Esplora i sentieri <span aria-hidden="true">↗</span></a>
            <button type="button" className="cb-hero-v3-near" onClick={() => openMapWith({ kind: 'near-me' })}>
              <LocateIcon size={17} /> Vicino a me
            </button>
          </div>
        </div>
        <nav className="cb-hero-v3-directory" aria-label="Esplora Cima Becco per categoria">
          <span className="cb-hero-v3-directory-heading">SCEGLI COSA ESPLORARE <span>↘</span></span>
          {EXPLORE_LINKS.map(link => (
            <a key={link.href} href={link.href} className="cb-hero-v3-directory-link">
              <span className="cb-hero-v3-index">{link.index}</span>
              <span className="cb-hero-v3-link-label"><strong>{link.name}</strong><small>{link.description}</small></span>
              <span className="cb-hero-v3-arrow" aria-hidden="true">↗</span>
            </a>
          ))}
        </nav>
      </div>
    </section>
  );
}
