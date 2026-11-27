import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { loadAlpinePlaces, alpinePlaceLink, atlasCategory, placeBounds, type AlpinePlace, type AlpinePlacesDataset } from '../lib/alpinePlaces';
import { boundsToHash } from '../lib/regions';
import { loadRoutesInBounds } from '../lib/routeTiles';
import { routesNear } from '../lib/routes';
import { trailMood, trailTitle } from '../lib/routeEditorial';
import { usePageTitle } from '../lib/pageTitle';
import '../alpineAtlas.css';

interface TrekProject {
  slug: string;
  title: string;
  slogan: string;
  description: string;
  routeSlugs: string[];
  stages: { number: number; routeSlugs: string[] }[];
}
type TreksDataset = { generatedAt: string | null; projects: TrekProject[] };
const EMPTY: AlpinePlacesDataset = { generatedAt: null, source: 'OpenStreetMap · ODbL 1.0', coverage: 'Dolomiti', places: [] };
const EMPTY_TREKS: TreksDataset = { generatedAt: null, projects: [] };
type Section = 'rifugi' | 'borghi' | 'trekking';

function parseAtlas(hash: string): { section: Section; slug: string | null } {
  const [, category, slug] = hash.replace(/^#atlante\/?/, '').split('/');
  // The initial part is a section name, not an empty prefix.
  const path = hash.replace(/^#atlante\/?/, '').split('/').filter(Boolean);
  const section = path[0] === 'borghi' || path[0] === 'trekking' ? path[0] : 'rifugi';
  return { section, slug: path[1] ?? null };
}

const sectionLabels: Record<Section,string> = { rifugi:'RIFUGI',borghi:'PAESI DI MONTAGNA',trekking:'CAMMINI XXL' };

function AtlasHeader({ section }: { section: Section }) {
  return <div className="cb-atlas-tabs" role="navigation" aria-label="Esplora atlante">
    {(['rifugi','borghi','trekking'] as Section[]).map(key =>
      <a key={key} className={section === key ? 'active' : ''} href={`#atlante/${key}`}>{sectionLabels[key]}</a>)}
  </div>;
}

function PlaceBadge({ place }: { place: AlpinePlace }) {
  return <span className={`cb-atlas-kind cb-atlas-kind--${place.kind}`}>
    {place.kind === 'rifugio' ? '⌂ RIFUGIO' : '◈ BORGO'}{place.elevationM ? ` · ${place.elevationM.toLocaleString('it-IT')} m` : ''}
  </span>;
}

function PlaceDetail({ place, onBack }: { place: AlpinePlace; onBack: string }) {
  const [nearby, setNearby] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setLoading(true);
    const box = placeBounds(place, 4);
    void loadRoutesInBounds(box)
      .then((routes) => {
        if (active) setNearby(routesNear(routes,place.lng,place.lat,place.kind==='rifugio'?850:1400,12));
      })
      .catch(() => { if(active)setNearby([]); })
      .finally(() => {if(active)setLoading(false);});
    return () => {active=false;};
  },[place]);
  return <div className="cb-atlas-detail">
    <a className="cb-atlas-back" href={onBack}>← Torna all'atlante</a>
    <PlaceBadge place={place}/>
    <h1>{place.name}</h1>
    <p className="cb-atlas-lead">{place.kind==='rifugio'
      ? 'Un punto d’appoggio in quota. Prima di partire controlla apertura, accesso e disponibilità direttamente con il gestore.'
      : 'Una base per puntare alle montagne, non soltanto un posto sulla cartina. Guarda cosa si muove nei dintorni.'}</p>
    <div className="cb-atlas-facts">
      <span><strong>{place.lat.toFixed(4)}, {place.lng.toFixed(4)}</strong>Coordinate</span>
      {place.elevationM!=null && <span><strong>{place.elevationM.toLocaleString('it-IT')} m</strong>Quota OSM</span>}
      {place.operator && <span><strong>{place.operator}</strong>Gestore indicato</span>}
    </div>
    <div className="cb-atlas-actions">
      <a className="cb-atlas-primary" href={boundsToHash(placeBounds(place,3))}>VEDI SULLA MAPPA ↗</a>
      {place.website && <a href={place.website} target="_blank" rel="noopener noreferrer">Sito indicato nei dati OSM</a>}
    </div>
    <section className="cb-atlas-nearby">
      <h2>SENTIERI NEI DINTORNI <span>{nearby.length || ''}</span></h2>
      {loading ? <p>Sto cercando i tracciati vicini…</p>
        : nearby.length
          ? <div className="cb-atlas-routes">{nearby.map(route => {
              const mood=trailMood(route);
              return <a key={route.slug} href={`#route/${route.slug}`}><strong>{trailTitle(route)}</strong>
                <span>{(route.distanceM/1000).toLocaleString('it-IT',{maximumFractionDigits:1})} km · {mood.quip} <small>{mood.label}</small></span></a>;
            })}</div>
          : <p>Nessun sentiero già indicizzato nei pressi di questo punto. Non significa che non esistano sentieri.</p>}
    </section>
    <p className="cb-atlas-sourcing">Dati geografici: <a href={place.osmUrl} target="_blank" rel="noopener noreferrer">OpenStreetMap</a>. Il collegamento a un percorso non garantisce accessibilità.</p>
  </div>;
}

function TrekDetail({ trek, onBack }: { trek: TrekProject; onBack: string }) {
  return <div className="cb-atlas-detail">
    <a className="cb-atlas-back" href={onBack}>← Tutti i trekking</a>
    <span className="cb-atlas-kind cb-atlas-kind--trek">PROGETTO A TAPPE</span>
    <h1>{trek.title}</h1>
    <strong className="cb-atlas-trek-slogan">{trek.slogan}</strong>
    <p className="cb-atlas-lead">{trek.description}</p>
    <div className="cb-atlas-facts">
      <span><strong>{trek.routeSlugs.length}</strong>segmenti identificati</span>
      <span><strong>{trek.stages.length}</strong>tappe esplicite nei dati</span>
    </div>
    {trek.stages.length > 0 && <section className="cb-atlas-nearby"><h2>TAPPE IDENTIFICATE</h2>
      <div className="cb-atlas-routes">{trek.stages.map(stage =>
        <div key={stage.number}><strong>TAPPA {stage.number}</strong>
          {stage.routeSlugs.map(slug => <a href={`#route/${slug}`} key={slug}>Apri il segmento {slug} ↗</a>)}
        </div>)}</div>
    </section>}
    {trek.routeSlugs.length>0 && <section className="cb-atlas-nearby"><h2>SEGMENTI COLLEGATI</h2>
      <div className="cb-atlas-routes">{trek.routeSlugs.slice(0,80).map(slug =>
        <a key={slug} href={`#route/${slug}`}>Apri il segmento cartografico ↗ <small>{slug}</small></a>)}</div>
    </section>}
    <p className="cb-atlas-warning">Non è ancora un trekking composto e percorribile end-to-end. Il collegamento in tappe richiede ordine, continuità geometrica e verifica delle condizioni.</p>
  </div>;
}

export function AlpineAtlasPage() {
  const [hash,setHash] = useState(() => window.location.hash);
  const [data,setData] = useState<AlpinePlacesDataset>(EMPTY);
  const [treks,setTreks] = useState<TreksDataset>(EMPTY_TREKS);
  const [query,setQuery] = useState('');
  const [visible,setVisible] = useState(36);
  const {section,slug}=parseAtlas(hash);
  usePageTitle('Atlante · Rifugi, borghi e trekking');
  useEffect(() => {
    const change = () => {setHash(window.location.hash);setQuery('');setVisible(36);window.scrollTo({top:0});};
    window.addEventListener('hashchange',change);
    return ()=>window.removeEventListener('hashchange',change);
  },[]);
  useEffect(() => {
    void loadAlpinePlaces().then(setData);
    void fetch(`${import.meta.env.BASE_URL}data/trekking-projects.json`)
      .then(r=>r.ok?r.json():EMPTY_TREKS).then((result:TreksDataset)=>{if(Array.isArray(result.projects))setTreks(result);})
      .catch(()=>undefined);
  },[]);
  const places=useMemo(()=>data.places.filter(place=>atlasCategory(place.kind)===section && place.name.toLocaleLowerCase('it').includes(query.trim().toLocaleLowerCase('it'))),[data,section,query]);
  const place=slug?data.places.find(p=>p.slug===slug && atlasCategory(p.kind)===section):null;
  const trek=slug?treks.projects.find(p=>p.slug===slug):null;
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <main className="cb-atlas-shell">
      <div className="cb-atlas-overline">CIMA BECCO / ATLANTE IN PROGRESS</div>
      <AtlasHeader section={section}/>
      {place ? <PlaceDetail place={place} onBack={`#atlante/${section}`}/>
        : trek ? <TrekDetail trek={trek} onBack="#atlante/trekking"/>
        : slug ? <div className="cb-atlas-empty"><h1>Questa tappa ci sfugge.</h1><p>Il dato non è ancora disponibile in questo atlante.</p><a href={`#atlante/${section}`}>Vai all'elenco</a></div>
        : <>
          <div className="cb-atlas-intro">
            <div>
              <span className="cb-atlas-eyebrow">{section==='trekking'?'TANTE TAPPE, UNA SOLA FOLLIA':'FUORI DALLA SOLITA ROTTA'}</span>
              <h1>{section==='rifugi'?'RIFUGI.\nPOI SI VEDE.':section==='borghi'?'BORGHI PICCOLI.\nGITE GROSSE.':'CAMMINI LUNGHI.\nSCUSE CORTE.'}</h1>
              <p>{section==='rifugi'?'Dove fermarti, ricaricare le gambe e scegliere la prossima salita. Rifugi veri, collegati ai sentieri mappati.'
                :section==='borghi'?'Paesini di montagna da cui partire, non cartoline da mettere sul frigo.'
                  :'Alte Vie e Sentiero Italia: segmenti reali, tappe quando esistono, niente GPX inventati per riempire i buchi.'}</p>
            </div>
            <div className="cb-atlas-intro-symbol" aria-hidden="true">{section==='rifugi'?'⌂':section==='borghi'?'↟':'↯'}</div>
          </div>
          {section!=='trekking' ? <>
            <div className="cb-atlas-toolbar"><label htmlFor="cb-atlas-query">CERCA UN {section==='rifugi'?'RIFUGIO':'PAESE'}</label>
              <input id="cb-atlas-query" type="search" value={query} onChange={e=>{setQuery(e.target.value);setVisible(36);}} placeholder="Scrivi il nome…" />
              <span>{places.length} luoghi presenti</span>
            </div>
            {places.length>0 ? <div className="cb-atlas-grid">{places.slice(0,visible).map((item,index)=>
              <a key={item.slug} className="cb-atlas-card" href={alpinePlaceLink(item)}>
                <span className="cb-atlas-card-count">{String(index+1).padStart(2,'0')}</span>
                <PlaceBadge place={item}/>
                <h2>{item.name}</h2>
                <span className="cb-atlas-card-go">ESPLORA ↗</span>
              </a>)}</div>
            : <div className="cb-atlas-empty"><h2>{query?'Non c’è questo nome in archivio.':'Stiamo importando i primi rifugi e borghi dalle Dolomiti.'}</h2>
                <p>Il catalogo usa località reali di OpenStreetMap; non mostriamo località inventate.</p><a href="#map">Intanto, esplora la mappa ↗</a></div>}
            {places.length>visible && <button type="button" className="cb-atlas-more" onClick={()=>setVisible(n=>n+36)}>ALTRI {Math.min(36,places.length-visible)} LUOGHI ↓</button>}
          </> : <div className="cb-atlas-grid">{treks.projects.map(t=><a key={t.slug} className="cb-atlas-card cb-atlas-trek" href={`#atlante/trekking/${t.slug}`}>
            <span className="cb-atlas-kind cb-atlas-kind--trek">TREKKING A TAPPE</span>
            <h2>{t.title}</h2>
            <strong>{t.slogan}</strong>
            <p>{t.description}</p><span className="cb-atlas-card-go">{t.routeSlugs.length} SEGMENTI MAPPATI ↗</span>
          </a>)}</div>}
        </>}
    </main>
    <SiteFooter/>
  </div>;
}
