import { useEffect, useRef, useState, type ReactNode } from 'react';
import './siteChrome.css';
import './brandMark.css';
import './fontAwesome.css';
import { FaIcon } from './FaIcon';
import { openImportHere, requestAddPlace } from '../lib/contribute';
import { AccountMenu } from './AccountMenu';
import { SUPABASE_CONFIGURED } from '../lib/api';
import { HeaderControls } from './HeaderControls';
import { CoverageModal, useCoverage } from './Coverage';
import { Mark } from './icons';
import { exploreGroups } from '../lib/exploreNavigation';
import { SiteSearch } from './SearchBar';

/** Marchio condiviso: segno brutalista e tipografia già in uso nel sito. */
export function Wordmark({ size = 36, href = '/#' }: { size?: number; href?: string }) {
  return (
    <a className="wordmark" href={href} aria-label="Cima Becco — home" title="Non è un cervo. Grazie.">
      <Mark size={size} />
      <span className="wordmark-text"><b>CIMA</b><em>BECCO</em></span>
    </a>
  );
}

/**
 * The one header every page uses: logo on the left, the page's own control
 * (search) in the centre, and the same actions on the right. It keeps one
 * fixed size, so a sticky header never resizes on scroll.
 */
export function SiteHeader({ center = <SiteSearch />, sticky = false }: { center?: ReactNode; sticky?: boolean }) {
  const [exploreOpen, setExploreOpen] = useState(false);
  const headerRef=useRef<HTMLElement>(null);
  useEffect(()=>{
    if(!exploreOpen)return;
    const closeOutside=(event:PointerEvent)=>{
      if(event.target instanceof Node && !headerRef.current?.contains(event.target))setExploreOpen(false);
    };
    const onKey=(event:KeyboardEvent)=>{if(event.key==='Escape')setExploreOpen(false);};
    const onHash=()=>setExploreOpen(false);
    document.addEventListener('pointerdown',closeOutside);
    document.addEventListener('keydown',onKey);
    window.addEventListener('hashchange',onHash);
    return ()=>{
      document.removeEventListener('pointerdown',closeOutside);
      document.removeEventListener('keydown',onKey);
      window.removeEventListener('hashchange',onHash);
    };
  },[exploreOpen]);
  return (
    <header ref={headerRef} className={`site-header${sticky ? ' sticky' : ''}`}>
      <div className="site-header-row">
        <div className="site-header-left">
          <Wordmark />
        </div>
        <div className="site-header-center">{center}</div>
        <div className="site-header-right">
          <button type="button" className="site-header-cta cb-explore-trigger" aria-controls="cb-explore-menu" aria-expanded={exploreOpen} onClick={() => setExploreOpen(v => !v)}><FaIcon name="compass" size={14}/> Esplora</button>
          <a className="site-header-cta cb-plan-link" href="/#pianifica" aria-label="Pianifica un percorso"><FaIcon name="route" size={14}/> Pianifica</a>
          <a className="site-header-cta" href="/#import" onClick={openImportHere} aria-label="Carica GPX" data-tip="Carica GPX">
            <FaIcon name="arrow-up-right-from-square" size={14}/>
            <span className="site-header-cta-label" aria-hidden="true">Carica GPX</span>
          </a>
          <HeaderControls />
          {SUPABASE_CONFIGURED && <AccountMenu />}
        </div>
      </div>
      {exploreOpen && <nav id="cb-explore-menu" className="cb-explore-menu" aria-label="Esplora Cima Becco">{exploreGroups.map(group => <section key={group.title}><strong>{group.title}</strong>{group.items.map(item => item.href ? <a key={item.label} href={item.href} onClick={() => setExploreOpen(false)}>{item.label}</a> : <span key={item.label}>{item.label} · prossimamente</span>)}</section>)}<section><strong>Strumenti</strong><a href="/#pianifica" onClick={() => setExploreOpen(false)}>Pianifica un percorso</a></section></nav>}
    </header>
  );
}

/**
 * The same footer on every page. On the map it sits at the end of the list,
 * so it only shows once you have scrolled past the results.
 */
export function SiteFooter({ openSourcePill = false }: { openSourcePill?: boolean }) {
  const [coverageOpen, setCoverageOpen] = useState(false);
  const [beccoClicks, setBeccoClicks] = useState(0);
  const beccoLines = [
    'Non è un cervo. E non accetta reclami.',
    'Stambecco sbloccato. Polpacci venduti separatamente.',
    'Se cercavi la discesa, lui non è il tipo giusto.',
    'Do veto more? Chiedilo al becco.',
  ];
  return (
    <footer className={`site-footer${openSourcePill ? ' site-footer--featured' : ''}`}>
      <div className="site-footer-inner">
        <div className="site-footer-cols">
          <div>
            <h3>Vai a vedere</h3>
            <a href="/#map">Cime e montagne</a>
            <a href="/#routes">Escursioni e ferrate</a>
            <a href="/#rifugi">Rifugi</a>
            <a href="/#bivacchi">Bivacchi</a>
            <a href="/#paesi">Paesi di montagna</a>
            <a href="/#atlante/trekking">Alte Vie e Sentiero Italia</a>
            <a href="/#pianifica">Pianifica un percorso</a>
            <button type="button" className="site-footer-link" aria-haspopup="dialog" onClick={() => setCoverageOpen(true)}>Cosa c'è nella mappa</button>
          </div>
          <div>
            <h3>Cima Becco</h3>
            <a href="/#community">Il progetto</a>
            <a href="/#atlante/rifugi">Atlante completo</a>
            <a href="/#statistiche">Statistiche del laboratorio</a>
            <a href="/fonti-e-crediti/">Fonti e crediti</a>
            <a href="/#privacy">Privacy</a>
            <a href="/#contact">Contatti</a>
          </div>
          <div>
            <h3>Un sentiero in più</h3>
            <a href="/#import" onClick={openImportHere}>Importa un GPX</a>
            <button type="button" className="site-footer-link" onClick={requestAddPlace}>Segnala una cima mancante</button>
            <a href="/#terms">Contributi e licenze</a>
          </div>
        </div>
        <div className="site-footer-base">
          <span>© Cima Becco · Ogni cima, un nuovo percorso.</span>
          <span>Un progetto sperimentale. <a href="/fonti-e-crediti/">Fonti, attribuzioni e licenze</a></span>
          <div className="cb-footer-egg" data-awake={beccoClicks > 0}>
            <button type="button" className="cb-footer-egg-trigger" onClick={() => setBeccoClicks(n => n + 1)}
              aria-label="Stuzzica lo stambecco. Sblocca una battuta." title="Sì, il logo si può stuzzicare.">
              <Mark size={32} />
            </button>
            <span className="cb-footer-egg-copy" aria-live="polite">
              {beccoClicks > 0 ? beccoLines[(beccoClicks - 1) % beccoLines.length] : 'Non stuzzicare lo stambecco.'}
            </span>
          </div>
        </div>
      </div>
      {coverageOpen && <FooterCoverage onClose={() => setCoverageOpen(false)} />}
    </footer>
  );
}

/** "What's mapped", opened from the footer; the numbers load only once it is asked for. */
function FooterCoverage({ onClose }: { onClose: () => void }) {
  const coverage = useCoverage();
  return coverage ? <CoverageModal coverage={coverage} onClose={onClose} /> : null;
}
