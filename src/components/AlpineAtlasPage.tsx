import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { loadAlpinePlaces, alpinePlaceLink, atlasCategory, placeBounds, type AlpinePlace, type AlpinePlacesDataset } from '../lib/alpinePlaces';
import { loadRoutesInBounds } from '../lib/routeTiles';
import { routesNear } from '../lib/routes';
import { trailMood, trailTitle } from '../lib/routeEditorial';
import { usePageTitle } from '../lib/pageTitle';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { AlpineAtlasMap } from './AlpineAtlasMap';
import { AlpineWeatherPanel } from './AlpineWeatherPanel';
import { HutClaimRequest } from './HutClaimRequest';
import { loadAlpineWater, alpineWaterNear, potabilityLabel, type AlpineWaterPoint } from '../lib/alpineWater';
import { track } from '../lib/analytics';
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
type Section = 'rifugi' | 'bivacchi' | 'borghi' | 'trekking';

function parseAtlas(hash: string): { section: Section; slug: string | null } {
  // The initial part is a section name, not an empty prefix.
  const path = hash.replace(/^#atlante\/?/, '').split('/').filter(Boolean);
  const section = path[0] === 'borghi' || path[0] === 'bivacchi' || path[0] === 'trekking' ? path[0] : 'rifugi';
  return { section, slug: path[1] ?? null };
}

const sectionLabels: Record<Section,string> = { rifugi:'RIFUGI',bivacchi:'BIVACCHI',borghi:'PAESI',trekking:'TREKKING A TAPPE' };

function AtlasHeader({ section }: { section: Section }) {
  return <div className="cb-atlas-tabs" role="navigation" aria-label="Esplora atlante">
    {(['rifugi','bivacchi','borghi','trekking'] as Section[]).map(key =>
      <a key={key} className={section === key ? 'active' : ''} href={`#atlante/${key}`}>{sectionLabels[key]}</a>)}
  </div>;
}

function PlaceBadge({ place }: { place: AlpinePlace }) {
  return <span className={`cb-atlas-kind cb-atlas-kind--${place.kind}`}>
    <AlpinePlaceIcon kind={place.kind} size={19}/>
    {place.kind === 'rifugio' ? 'RIFUGIO' : place.kind === 'bivacco' ? 'BIVACCO' : 'PAESE'}{place.elevationM ? ` · ${place.elevationM.toLocaleString('it-IT')} m` : ''}
  </span>;
}

function RouteGroup({title,items}:{title:string;items:Route[]}) {
  if(!items.length)return null;
  return <section className="cb-atlas-nearby">
    <h2>{title} <span>{items.length}</span></h2>
    <div className="cb-atlas-routes">{items.map(route=>{
      const mood=trailMood(route);
      return <a key={route.slug} href={`#route/${route.slug}`}>
        <strong>{trailTitle(route)}</strong>
        <span>{(route.distanceM/1000).toLocaleString('it-IT',{maximumFractionDigits:1})} km · {mood.quip}
          <small> · {mood.label}</small>
        </span>
      </a>;
    })}</div>
  </section>;
}

function PlaceDetail({ place, onBack, places }: { place: AlpinePlace; onBack: string; places: AlpinePlace[] }) {
  const [nearby,setNearby]=useState<Route[]>([]);
  const [loading,setLoading]=useState(true);
  const [water,setWater]=useState<AlpineWaterPoint[]>([]);
  useEffect(()=>{
    let active=true;
    setLoading(true);setNearby([]);
    void loadRoutesInBounds(placeBounds(place,4))
      .then(routes=>{if(active)setNearby(routesNear(routes,place.lng,place.lat,place.kind==='borgo'?1600:1100,22));})
      .catch(()=>{if(active)setNearby([]);})
      .finally(()=>{if(active)setLoading(false);});
    return ()=>{active=false;};
  },[place]);
  useEffect(()=>{
    let active=true;setWater([]);
    void loadAlpineWater().then(data=>{if(active)setWater(alpineWaterNear(data.sources,place.lng,place.lat,1800,14));});
    return ()=>{active=false;};
  },[place]);
  useEffect(()=>{track('atlas_place_view',place.slug);},[place.slug]);

  const tagged=nearby.filter(route=>(route.stops??[]).some(stop=>stop.slug===place.slug));
  const departures=tagged.filter(route=>(route.stops??[]).some(stop=>stop.slug===place.slug&&stop.relation==='partenza'));
  const arrivals=tagged.filter(route=>!departures.includes(route)&&(route.stops??[]).some(stop=>stop.slug===place.slug&&stop.relation==='arrivo'));
  const passes=tagged.filter(route=>!departures.includes(route)&&!arrivals.includes(route));
  const around=nearby.filter(route=>!tagged.includes(route));
  const kindLabel=place.kind==='rifugio'?'rifugio alpino':place.kind==='bivacco'?'bivacco':'località montana';
  const placeLine=place.kind==='borgo'
    ? `${place.name} è una località di montagna censita nelle Dolomiti.`
    : `${place.name} è un ${kindLabel} censito nelle Dolomiti.`;
  const detailRows: { label:string; value:string }[]=[
    ...(place.operator?[{label:'Gestore o ente indicato',value:place.operator}]:[]),
    ...(place.capacity!=null?[{label:place.kind==='bivacco'?'Capienza indicata':'Posti letto indicati',value:String(place.capacity)}]:[]),
    ...(place.openingHours?[{label:'Orari dichiarati',value:place.openingHours}]:[]),
    ...(place.seasonal?[{label:'Stagionalità',value:place.seasonal}]:[]),
    ...(place.access?[{label:'Accesso dichiarato in OSM',value:place.access}]:[]),
    ...(place.fee?[{label:'Indicazione tariffa',value:place.fee}]:[]),
    ...(place.winterRoom?[{label:'Locale invernale',value:place.winterRoom}]:[]),
    ...(place.address?[{label:'Indirizzo',value:place.address}]:[]),
    {label:'Coordinate WGS84',value:`${place.lat.toFixed(5)}, ${place.lng.toFixed(5)}`},
    ...(place.elevationSource?[{label:'Fonte della quota',value:place.elevationSource==='dem'?'Stima del modello altimetrico DEM':'Quota registrata in OpenStreetMap'}]:[]),
  ];
  return <article className="cb-atlas-detail cb-atlas-detail-wide cb-place-detail">
    <a className="cb-atlas-back" href={onBack}>← Torna a {place.kind==='rifugio'?'rifugi':place.kind==='bivacco'?'bivacchi':'paesi'}</a>
    <header className="cb-place-hero">
      <PlaceBadge place={place}/>
      <h1>{place.name}</h1>
      <p className="cb-atlas-lead">{place.description || placeLine}</p>
      <div className="cb-place-facts" aria-label="Dati essenziali">
        <div><strong>{place.elevationM!=null?`${place.elevationM.toLocaleString('it-IT')} m`:'n.d.'}</strong><span>Altitudine{place.elevationSource==='dem'?' stimata':''}</span></div>
        {place.capacity!=null&&<div><strong>{place.capacity}</strong><span>{place.kind==='bivacco'?'Posti indicati':'Posti letto'}</span></div>}
        <div><strong>{nearby.length || (loading?'…':'0')}</strong><span>Sentieri nei dintorni</span></div>
      </div>
      <div className="cb-place-contact-actions">
        {place.phone&&<a className="cb-atlas-primary" href={`tel:${place.phone.replace(/[^+\d]/g,'')}`}>CHIAMA LA STRUTTURA</a>}
        {place.email&&<a className={place.phone?'cb-place-secondary':'cb-atlas-primary'} href={`mailto:${place.email}`}>SCRIVI UNA EMAIL</a>}
        <button type="button" className={place.phone||place.email?'cb-place-secondary':'cb-atlas-primary'} onClick={()=>document.getElementById('cb-place-map')?.scrollIntoView({behavior:'smooth',block:'start'})}>VEDI SULLA MAPPA ↓</button>
      </div>
      {place.kind==='bivacco'&&<p className="cb-place-alert">Bivacco non equivale a rifugio custodito: verifica accessibilità, eventuale chiusura e dotazioni. Non fare affidamento sulla disponibilità di posti.</p>}
      {place.kind==='rifugio'&&!place.phone&&!place.email&&<p className="cb-place-note">Recapiti non ancora verificati: non interpretiamo l'assenza del dato come indisponibilità della struttura.</p>}
    </header>

    {place.photo&&<figure className="cb-atlas-cover cb-place-cover">
      <img src={place.photo.url} alt={`Fotografia documentata di ${place.name}`} loading="lazy"/>
      <figcaption>Foto: {place.photo.author} · {place.photo.license}</figcaption>
    </figure>}

    <section className="cb-place-information" aria-label="Informazioni dettagliate">
      <div className="cb-atlas-section-top"><span>INFORMAZIONI UTILI</span><h2>DATI DEL LUOGO.</h2>
        <p>Informazioni strutturate riportate dalle fonti disponibili, non conferme di apertura in tempo reale.</p>
      </div>
      <dl className="cb-place-details">{detailRows.map(row=><div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl>
      {(place.phone||place.email||place.website)&&<div className="cb-place-recapiti">
        <h3>CONTATTI E RIFERIMENTI</h3>
        {place.phone&&<a href={`tel:${place.phone.replace(/[^+\d]/g,'')}`}>Telefono: {place.phone}</a>}
        {place.email&&<a href={`mailto:${place.email}`}>Email: {place.email}</a>}
        {place.website&&<a href={place.website} target="_blank" rel="noopener noreferrer">Sito della struttura ↗</a>}
      </div>}
    </section>

    <section id="cb-place-map" className="cb-place-map-section">
      <div className="cb-atlas-section-top"><span>DOVE SI TROVA</span><h2>LA MAPPA DELLA ZONA.</h2>
        <p>Il luogo e i sentieri vicini. Attiva separatamente i punti acqua; la vicinanza non dimostra l'accesso diretto.</p>
      </div>
      <AlpineAtlasMap places={places} kind={place.kind} selected={place} routes={nearby} water={water.map(w=>({lng:w.lng,lat:w.lat,potable:w.potable==='yes'}))} height={380}/>
    </section>

    {loading?<p className="cb-atlas-loading">Sto recuperando i sentieri nei dintorni…</p>:<>
      <RouteGroup title="PERCORSI CHE PARTONO DA QUI" items={departures}/>
      <RouteGroup title="PERCORSI CHE ARRIVANO QUI" items={arrivals}/>
      <RouteGroup title="PERCORSI DI PASSAGGIO" items={passes}/>
      <RouteGroup title="ALTRI SENTIERI NELLA ZONA" items={around}/>
      {!nearby.length&&<p className="cb-place-note">Non ci sono tracce già indicizzate vicino al punto: non significa che non esistano sentieri.</p>}
    </>}

    <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>

    {water.length>0&&<section className="cb-local-water">
      <h2><AlpinePlaceIcon kind="acqua" size={24}/> ACQUA NEI DINTORNI</h2>
      <p>Fonti entro circa 1,8 km in linea d'aria. Potabilità, disponibilità e accesso non garantiti.</p>
      <div className="cb-local-water-grid">{water.slice(0,8).map(w=><div key={w.slug}>
        <strong>{w.name}</strong><small>{w.kind} · {potabilityLabel(w.potable)}{w.seasonal?' · stagionale':''}</small>
      </div>)}</div>
    </section>}

    {place.kind==='rifugio'&&<HutClaimRequest place={place}/>}
    {place.kind==='rifugio'&&<section className="cb-place-community">
      <div className="cb-atlas-section-top"><span>LA VOCE DEI CAMMINATORI</span><h2>DOMANDE E RECENSIONI.</h2></div>
      <p>Stiamo predisponendo le domande sulla struttura e le risposte del gestore verificato, insieme alle recensioni moderate. Non sono ancora aperte alle pubblicazioni: niente messaggi senza una gestione affidabile.</p>
    </section>}
    <footer className="cb-atlas-sourcing">Dati geografici: <a href={place.osmUrl} target="_blank" rel="noopener noreferrer">OpenStreetMap · ODbL</a>.
      {place.photo&&<> Immagine: {place.photo.license} · <a href={place.photo.sourceUrl} target="_blank" rel="noopener noreferrer">attribuzione completa</a>.</>}
      {place.wikidata&&<> Scheda: <a href={`https://www.wikidata.org/wiki/${place.wikidata}`} target="_blank" rel="noopener noreferrer">Wikidata</a>.</>}
      {' '}Verifica sempre itinerari, accessi e condizioni prima di partire.</footer>
  </article>;
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
  usePageTitle(sectionLabels[section] + ' · Cima Becco');
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
  const allSectionPlaces=useMemo(()=>data.places.filter(place=>atlasCategory(place.kind)===section),[data,section]);
  const places=useMemo(()=>allSectionPlaces.filter(place=>place.name.toLocaleLowerCase('it').includes(query.trim().toLocaleLowerCase('it'))),[allSectionPlaces,query]);
  const place=slug?data.places.find(p=>p.slug===slug && atlasCategory(p.kind)===section):null;
  const trek=slug?treks.projects.find(p=>p.slug===slug):null;
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <main className="cb-atlas-shell">
      <div className="cb-atlas-overline">CIMA BECCO / ESPLORA</div>
      <AtlasHeader section={section}/>
      {place ? <PlaceDetail place={place} onBack={`#atlante/${section}`} places={allSectionPlaces}/>
        : trek ? <TrekDetail trek={trek} onBack="#atlante/trekking"/>
        : slug ? <div className="cb-atlas-empty"><h1>Questa tappa ci sfugge.</h1><p>Il dato non è ancora disponibile in questo atlante.</p><a href={`#atlante/${section}`}>Vai all'elenco</a></div>
        : <>
          <div className="cb-atlas-intro">
            <div>
              <span className="cb-atlas-eyebrow">{section==='trekking'?'TANTE TAPPE, UNA SOLA FOLLIA':'FUORI DALLA SOLITA ROTTA'}</span>
              <h1>{section==='rifugi'?'RIFUGI.\nPOI SI VEDE.':section==='bivacchi'?'BIVACCHI.\nPOCHE SCUSE.':section==='borghi'?'PAESI PICCOLI.\nGITE GROSSE.':'CAMMINI LUNGHI.\nSCUSE CORTE.'}</h1>
              <p>{section==='rifugi'?'Dove fermarti, ricaricare le gambe e scegliere la prossima salita. Rifugi veri, collegati ai sentieri mappati.'
                :section==='bivacchi'?'Ripari essenziali in quota, non strutture custodite: mappe e dati verificabili per pianificare con prudenza.'
                :section==='borghi'?'Località montane da cui partire, con sentieri, cartografia e meteo della zona.'
                  :'Alte Vie e Sentiero Italia: segmenti reali, tappe quando esistono, niente GPX inventati per riempire i buchi.'}</p>
            </div>
            <div className="cb-atlas-intro-symbol" aria-hidden="true">{section==='rifugi'?'⌂':section==='bivacchi'?'△':section==='borghi'?'↟':'↯'}</div>
          </div>
          {section!=='trekking' ? <>
            {allSectionPlaces.length>0&&<section className="cb-atlas-list-map">
              <div className="cb-atlas-section-top"><span>{section==='rifugi'?'I RIFUGI IN QUOTA':section==='bivacchi'?'I RIPARI IN QUOTA':'PAESI DA CUI PARTIRE'}</span>
                <h2>TUTTI SULLA MAPPA.</h2></div>
              <AlpineAtlasMap places={allSectionPlaces} kind={section==='rifugi'?'rifugio':section==='bivacchi'?'bivacco':'borgo'} height={350}/>
            </section>}
            <div className="cb-atlas-toolbar"><label htmlFor="cb-atlas-query">CERCA UN {section==='rifugi'?'RIFUGIO':section==='bivacchi'?'BIVACCO':'PAESE'}</label>
              <input id="cb-atlas-query" type="search" value={query} onChange={e=>{setQuery(e.target.value);setVisible(36);}} placeholder="Scrivi il nome…" />
              <span>{places.length} luoghi presenti</span>
            </div>
            {places.length>0 ? <div className="cb-atlas-grid">{places.slice(0,visible).map((item,index)=>
              <a key={item.slug} className="cb-atlas-card" href={alpinePlaceLink(item)}>
                <span className="cb-atlas-card-count">{String(index+1).padStart(2,'0')}</span>
                <PlaceBadge place={item}/>
                {item.photo&&<img className="cb-atlas-card-photo" src={item.photo.url} alt="" loading="lazy"/>}
                <h2>{item.name}</h2>
                <span className="cb-atlas-card-go">ESPLORA ↗</span>
              </a>)}</div>
            : <div className="cb-atlas-empty"><h2>{query?'Non c’è questo nome in archivio.':'Il catalogo di questa categoria non è ancora disponibile.'}</h2>
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
