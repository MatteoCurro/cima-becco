import { openMapWith } from '../lib/mapIntent';
import { LocateIcon, SearchIcon } from './icons';
import { focusSiteSearch } from './SearchBar';
import '../homeHeroV2.css';

/** Una promessa, un'azione primaria, tre scorciatoie. Nessuna timeline decorativa. */
export function TrailHero(){
  return <section className="cb-hero-v2" aria-labelledby="cb-hero-title">
    <div className="cb-hero-v2-grid">
      <div className="cb-hero-v2-content">
        <span className="cb-hero-v2-eyebrow"><span aria-hidden="true">↗</span> CIMA BECCO / VAI IN MONTAGNA</span>
        <h1 id="cb-hero-title">TROVA LA TUA <em>PROSSIMA SALITA.</em></h1>
        <p>Sentieri, cime e posti in cui fermarti. Scegli dove andare, guarda la mappa e parti con le informazioni giuste.</p>
        <div className="cb-hero-v2-actions">
          <a className="cb-hero-v2-main-link" href="#routes">ESPLORA I SENTIERI <span aria-hidden="true">↗</span></a>
          <button type="button" className="cb-hero-v2-near" onClick={()=>openMapWith({kind:'near-me'})}><LocateIcon size={17}/> VICINO A ME</button>
        </div>
        <div className="cb-hero-v2-search">
          <span>HAI GIÀ UN POSTO IN MENTE?</span>
          <button type="button" onClick={()=>{window.scrollTo({top:0,behavior:'smooth'});focusSiteSearch();}}><SearchIcon size={17}/> Cerca per nome nella barra in alto <span aria-hidden="true">↗</span></button>
        </div>
      </div>
      <div className="cb-hero-v2-landscape" role="img" aria-label="Illustrazione astratta delle Dolomiti: montagne, creste e un sentiero">
        <svg viewBox="0 0 650 600" preserveAspectRatio="xMidYMid slice" aria-hidden="true" focusable="false">
          <defs><linearGradient id="cb-hg" x1="0" y1="0" x2="1" y2="1"><stop stopColor="#cae7ce"/><stop offset="1" stopColor="#7fb199"/></linearGradient></defs>
          <rect width="650" height="600" fill="url(#cb-hg)"/>
          <circle cx="445" cy="125" r="80" fill="#f8ebbc" opacity=".95"/>
          <path d="M-30 480 124 225 231 348 355 109 531 372 613 249 720 511v100H-30Z" fill="#b3d2b4"/>
          <path d="m288 224 67-115 75 116-39-12-36 31-32-17Z" fill="#edf9ef"/>
          <path d="M-20 540 189 330l80 100 133-238 165 283 96-127 55 243v120H-20Z" fill="#416b58"/>
          <path d="m349 283 53-91 67 116-41-23-26 17-25-17Z" fill="#f0f6e4"/>
          <g stroke="#d6efd8" fill="none" strokeWidth="2" opacity=".45">
            <path d="M-30 465Q160 310 254 462T680 379"/>
            <path d="M-30 493Q160 338 254 490T680 407"/>
            <path d="M-30 521Q160 366 254 518T680 435"/>
            <path d="M-30 549Q160 394 254 546T680 463"/>
            <path d="M-30 577Q160 422 254 574T680 491"/>
          </g>
          <path d="M115 640Q187 538 290 516T434 391" fill="none" stroke="#f8f1d9" strokeWidth="17" strokeLinecap="round" strokeDasharray="2 25"/>
          <circle cx="433" cy="391" r="17" fill="#fa2775" stroke="#fff" strokeWidth="8"/>
        </svg>
        <div className="cb-hero-v2-image-stamp"><strong>ALTA QUOTA</strong><span>BASSE SCUSE.</span></div>
        <div className="cb-hero-v2-image-caption">LE DOLOMITI NON SI GIRANO DA SOLE.</div>
      </div>
    </div>
    <nav className="cb-hero-v2-links" aria-label="Esplora per categoria">
      <a href="#map">Cime <span>↗</span></a><a href="#rifugi">Rifugi <span>↗</span></a>
      <a href="#bivacchi">Bivacchi <span>↗</span></a><a href="#paesi">Paesi <span>↗</span></a>
    </nav>
  </section>;
}