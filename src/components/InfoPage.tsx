import { useEffect } from 'react';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { SiteSearch } from './SearchBar';
import { usePageTitle } from '../lib/pageTitle';
import { ContactForm } from './ContactForm';
import { CONTACT_EMAIL } from '../lib/contribute';

export type InfoPageId = 'privacy' | 'terms' | 'community' | 'data' | 'contact';
const TABS: { id: InfoPageId; label: string }[] = [
  { id: 'community', label: 'Il progetto' },
  { id: 'data', label: 'Fonti e crediti' },
  { id: 'privacy', label: 'Privacy' },
  { id: 'terms', label: 'Contributi' },
  { id: 'contact', label: 'Contatti' },
];

function DataSources() {
  return <>
    <h1>Fonti e crediti</h1>
    <p className="info-lead">Dietro ogni sentiero ci sono cartografi, volontari, escursionisti e tanti dati aperti. Qui trovi le fonti usate da Cima Becco, senza trasformare la mappa in una pagina di note a piè di pagina.</p>
    <h2>Sentieri e geografia</h2>
    <p>Le tracce escursionistiche importate automaticamente provengono da <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">OpenStreetMap</a> e dai suoi contributori, con licenza <a href="https://opendatacommons.org/licenses/odbl/" target="_blank" rel="noopener noreferrer">ODbL 1.0</a>. Le schede mantengono il collegamento alla relazione di provenienza. Geometrie, classificazioni e quote possono essere incomplete o obsolete.</p>
    <p>I dati del catasto sentieristico <a href="https://www.cai.it/sentieri-e-rifugi/infomont/" target="_blank" rel="noopener noreferrer">CAI INFOMONT</a> e quelli della <a href="https://www.sat.tn.it/sentieri/mappa-sentieri/" target="_blank" rel="noopener noreferrer">SAT</a> sono considerati per la successiva integrazione diretta. Se una classificazione CAI è già presente nella relazione OSM viene indicata come tale; non equivale a una verifica sul campo.</p>
    <p>Toponimi e cime sono arricchiti da <a href="https://www.geonames.org" target="_blank" rel="noopener noreferrer">GeoNames</a> (CC BY 4.0), <a href="https://www.wikidata.org" target="_blank" rel="noopener noreferrer">Wikidata</a> e, quando presente, <a href="https://it.wikipedia.org" target="_blank" rel="noopener noreferrer">Wikipedia</a>.</p>
    <h2>Mappe, quote e immagini</h2>
    <p>La cartografia visualizzata utilizza servizi e dati di <a href="https://openfreemap.org" target="_blank" rel="noopener noreferrer">OpenFreeMap</a> e OpenStreetMap. Le quote stimate possono utilizzare <a href="https://registry.opendata.aws/terrain-tiles/" target="_blank" rel="noopener noreferrer">AWS Terrain Tiles</a>; non sono misure topografiche certificate.</p>
    <p>Le fotografie reperite da <a href="https://commons.wikimedia.org" target="_blank" rel="noopener noreferrer">Wikimedia Commons</a> restano attribuite al rispettivo autore e alla licenza della singola immagine. Il collegamento alla pagina originale è disponibile quando una foto viene mostrata; non tutte le fotografie rappresentano esattamente il punto indicato dal GPS.</p>
    <h2>Software</h2>
    <p>Cima Becco riutilizza codice del progetto open source <a href="https://github.com/StarlightsJourney/HillGPX" target="_blank" rel="noopener noreferrer">HillGPX</a>, distribuito con licenza MIT, mantenendone gli avvisi di copyright. <a href="https://github.com/MatteoCurro/cima-becco/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">Leggi la licenza e gli avvisi originali.</a></p>
    <p className="cima-info-note">Un percorso o un GPX non certifica condizioni, percorribilità e sicurezza della montagna. Prima di partire consulta indicazioni ufficiali, meteo e informazioni aggiornate.</p>
  </>;
}
function Community() {
  return <>
    <h1>Cima Becco</h1>
    <p className="info-lead">Ogni cima, un nuovo percorso. Un atlante escursionistico italiano per trovare una gita, capire dove porta un sentiero e portarsi a casa una traccia GPX.</p>
    <h2>Cosa c'è già</h2>
    <p>Una mappa delle cime, una raccolta di escursioni e ferrate importate da fonti aperte, un pianificatore e schede dedicate agli itinerari. La raccolta si amplia automaticamente per area geografica.</p>
    <h2>Cosa stiamo migliorando</h2>
    <p>Descrizioni comprensibili, dislivelli affidabili, collegamenti ai rifugi, fotografie verificate e informazioni CAI/SAT. I tag scherzosi danno carattere al progetto, ma non sostituiscono mai la classificazione tecnica del sentiero.</p>
    <p>Il progetto è in fase sperimentale. La presenza di una traccia non garantisce che un passaggio sia accessibile o sicuro.</p>
  </>;
}
function Privacy() {
  return <>
    <h1>Privacy</h1>
    <p className="info-lead">Il catalogo di Cima Becco è consultabile anche senza account.</p>
    <p>Il sito statico è distribuito attraverso GitHub Pages. Il browser contatta anche fornitori esterni per mappe, quote, immagini e caratteri, che ricevono i dati tecnici necessari alla connessione. I preferiti possono essere salvati nel browser.</p>
    <p>L'accesso tramite account e le funzioni collaborative sono in fase di configurazione. Non viene richiesto un account per consultare gli itinerari pubblici.</p>
    <p>Per dettagli o richieste puoi usare la pagina <a href="#contact">Contatti</a>.</p>
  </>;
}
function Terms() {
  return <>
    <h1>Contributi</h1>
    <p className="info-lead">GPX, fotografie e segnalazioni possono provenire da fonti diverse: ciò che è pubblicamente accessibile non è automaticamente riutilizzabile senza condizioni.</p>
    <p>Le tracce OSM sono soggette alla licenza ODbL. I contenuti condivisi dalle persone mantengono le condizioni e le attribuzioni dichiarate dai rispettivi autori. Per le fotografie rispettiamo la licenza specifica del file.</p>
    <p>Una traccia può contenere errori: la valutazione delle condizioni e dell'attrezzatura necessaria spetta a chi percorre l'itinerario.</p>
  </>;
}
function Contact() {
  return <>
    <h1>Contatti e correzioni</h1>
    <p className="info-lead">Hai trovato una cima sbagliata, un'immagine fuori luogo o un sentiero da rivedere? Puoi segnalarlo.</p>
    {CONTACT_EMAIL && <p>Scrivici a <a href={`mailto:${CONTACT_EMAIL}`}>{CONTACT_EMAIL}</a>.</p>}
    <ContactForm />
  </>;
}

export function InfoPage({ page }: { page: InfoPageId }) {
  useEffect(() => { window.scrollTo({ top: 0 }); }, [page]);
  usePageTitle(TABS.find((tab) => tab.id === page)?.label ?? 'Informazioni');
  return <div className="info-page">
    <SiteHeader sticky center={<SiteSearch />} />
    <main className="info-page-body">
      <nav className="info-tabs" aria-label="Informazioni Cima Becco">
        {TABS.map((tab) => <a key={tab.id} href={`#${tab.id}`} aria-current={tab.id === page ? 'page' : undefined}>{tab.label}</a>)}
      </nav>
      <article className="info-article">
        {page === 'data' ? <DataSources /> : page === 'community' ? <Community /> : page === 'privacy' ? <Privacy /> : page === 'terms' ? <Terms /> : <Contact />}
      </article>
    </main>
    <SiteFooter />
  </div>;
}
