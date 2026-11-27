import { useState, type ReactNode } from 'react';
import { openImportHere, requestAddPlace } from '../lib/contribute';
import { AccountMenu } from './AccountMenu';
import { SUPABASE_CONFIGURED } from '../lib/api';
import { HeaderControls } from './HeaderControls';
import { CoverageModal, useCoverage } from './Coverage';
import { Mark } from './icons';
import { exploreGroups } from '../lib/exploreNavigation';
import { SiteSearch } from './SearchBar';

/** Identità Cima Becco: cresta e becco stilizzati, tipografia dal carattere editoriale. */
export function Wordmark({ size = 36, href = '/#' }: { size?: number; href?: string }) {
  return (
    <a className="wordmark" href={href} aria-label="Cima Becco — home">
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
  return (
    <header className={`site-header${sticky ? ' sticky' : ''}`}>
      <div className="site-header-row">
        <div className="site-header-left">
          <Wordmark />
        </div>
        <div className="site-header-center">{center}</div>
        <div className="site-header-right">
          <button type="button" className="site-header-cta cb-explore-trigger" aria-expanded={exploreOpen} onClick={() => setExploreOpen(v => !v)}>Esplora</button>
          <a className="site-header-cta cb-plan-link" href="/#pianifica" aria-label="Pianifica un percorso">Pianifica</a>
          <a className="site-header-cta" href="/#import" onClick={openImportHere} aria-label="Carica GPX" data-tip="Carica GPX">
            <svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" aria-hidden="true">
              <path d="M8 3v10M3 8h10" />
            </svg>
            <span className="site-header-cta-label" aria-hidden="true">Carica GPX</span>
          </a>
          <HeaderControls />
          {SUPABASE_CONFIGURED && <AccountMenu />}
        </div>
      </div>
      {exploreOpen && <nav className="cb-explore-menu" aria-label="Esplora Cima Becco">{exploreGroups.map(group => <section key={group.title}><strong>{group.title}</strong>{group.items.map(item => item.href ? <a key={item.label} href={item.href} onClick={() => setExploreOpen(false)}>{item.label}</a> : <span key={item.label}>{item.label} · prossimamente</span>)}</section>)}<section><strong>Strumenti</strong><a href="/#pianifica" onClick={() => setExploreOpen(false)}>Pianifica un percorso</a></section></nav>}
    </header>
  );
}

/**
 * The same footer on every page. On the map it sits at the end of the list,
 * so it only shows once you have scrolled past the results.
 */
export function SiteFooter({ openSourcePill = false }: { openSourcePill?: boolean }) {
  const [coverageOpen, setCoverageOpen] = useState(false);
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
            <a href="/#data">Fonti e crediti</a>
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
          <span>Un progetto sperimentale. <a href="/#data">Fonti, attribuzioni e licenze</a></span>
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
