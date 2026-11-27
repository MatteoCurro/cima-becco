import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { loadAlpinePlaces, alpinePlaceLink, atlasCategory, placeBounds, type AlpinePlace, type AlpinePlacesDataset } from '../lib/alpinePlaces';
import { loadRoutesInBounds } from '../lib/routeTiles';
import { routesNear } from '../lib/routes';
import { trailMood, trailTitle } from '../lib/routeEditorial';
import { usePageTitle } from '../lib/pageTitle';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { AlpinePlaceVisual } from './AlpinePlaceVisual';
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
  // Permalink progetto trekking oppure vecchio link dell'Atlante.
  if(!hash){
    const base=import.meta.env.BASE_URL;
    if(window.location.pathname.startsWith(base)){
      const parts=window.location.pathname.slice(base.length).split('/').filter(Boolean);
      if(parts[0]==='trekking'&&parts[1])return {section:'trekking',slug:parts[1]};
    }
  }
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
      return <a key={route.slug} href={`${import.meta.env.BASE_URL}route/${encodeURIComponent(route.slug)}/`}>
        <strong>{trailTitle(route)}</strong>
        <span>{(route.distanceM/1000).toLocaleString('it-IT',{maximumFractionDigits:1})} km · {mood.quip}
          <small> · {mood.label}</small>
        </span>
      </a>;
    })}</div>
  </section>;
}

export function PlaceDetail({ place, onBack, places }: { place: AlpinePlace; onBack: string; places: AlpinePlace[] }) {
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
  return <article className="cb-location-profile">
    <a className="cb-location-back" href={onBack}>← Esplora {place.kind==='rifugio'?'i rifugi':place.kind==='bivacco'?'i bivacchi':'i paesi'}</a>


    <div className="cb-location-body">
      <div className="cb-location-content">
    <header className="cb-location-hero">
      <div className="cb-location-hero-copy">
        <div className="cb-location-avatar">{place.logo?<img src={place.logo.url} alt={'Logo ufficiale di '+place.name}/>:<AlpinePlaceIcon kind={place.kind} size={39}/>}</div>
        <PlaceBadge place={place}/>
        <h1>{place.name}</h1>
        <p className="cb-location-lead">{placeLine}</p>
        {place.description&&<p className="cb-location-story">{place.description}</p>}
        <div className="cb-location-metrics" aria-label="Informazioni principali">
          <div><strong>{place.elevationM!=null?place.elevationM.toLocaleString('it-IT')+' m':'n.d.'}</strong><span>Altitudine{place.elevationSource==='dem'?' stimata':''}</span></div>
          {place.capacity!=null&&<div><strong>{place.capacity}</strong><span>{place.kind==='bivacco'?'Posti indicati':'Posti letto'}</span></div>}
          <div><strong>{loading?'…':nearby.length}</strong><span>Sentieri vicini</span></div>
        </div>
        {place.fee&&<div className="cb-location-cost">
          <span>PREZZI / ACCESSO</span>
          {/^\s*(yes|no)\s*$/i.test(place.fee)?<strong>{place.fee.toLowerCase()==='no'?'Accesso indicato gratuito':'Tariffa presente, importo da verificare'}</strong>:
            <><strong>{place.fee}</strong>{/\d/.test(place.fee)&&<span className="cb-location-dobloni" title="Indicazione giocosa basata su una tariffa dichiarata; non è un rating">🪙🪙 <small>Tariffa da verificare</small></span>}</>}
        </div>}
        <div className="cb-location-actions">
          <button type="button" className="cb-location-action-primary" onClick={()=>document.getElementById('cb-place-map')?.scrollIntoView({behavior:'smooth',block:'start'})}>ESPLORA SULLA MAPPA <span aria-hidden="true">↗</span></button>
          {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')}>CHIAMA IL RIFUGIO</a>}
          {place.email&&<a href={'mailto:'+place.email}>SCRIVI</a>}
        </div>
        {place.kind==='bivacco'&&<p className="cb-location-alert">Bivacco non custodito: verifica accesso, dotazioni e condizioni prima di partire. La capienza indicata non garantisce posto disponibile.</p>}
      </div>
      <figure className="cb-location-hero-media">
        <AlpinePlaceVisual key={place.slug} place={place}/>
        <figcaption>{place.photo?'Foto del luogo · attribuzione e licenza in fondo alla pagina':'Rappresentazione topografica: fotografia del luogo non disponibile'}</figcaption>
      </figure>
    </header>
        <section className="cb-location-section cb-location-dossier" aria-labelledby="cb-location-info-heading">
          <div className="cb-location-section-heading">
            <span>01 / DATI ESSENZIALI</span>
            <h2 id="cb-location-info-heading">PRIMA DI PARTIRE.</h2>
            <p>Informazioni disponibili nelle fonti cartografiche, da verificare con la struttura quando necessario.</p>
          </div>
          <dl className="cb-location-dl">{detailRows.map(row=><div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>)}</dl>
          {place.kind==='rifugio'&&!place.phone&&!place.email&&<p className="cb-location-muted-note">Non abbiamo ancora recapiti verificati per questa struttura: dato mancante non significa che sia chiusa.</p>}
        </section>

        <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>

        <section className="cb-location-section cb-location-itineraries" aria-label="Sentieri vicini">
          <div className="cb-location-section-heading">
            <span>03 / ESCURSIONI E ACCESSI</span>
            <h2>SENTIERI NEI DINTORNI.</h2>
            <p>Tracce disponibili in zona: la vicinanza geometrica al percorso non certifica un accesso diretto.</p>
          </div>
          {loading?<p className="cb-atlas-loading">Recupero i sentieri cartografati…</p>:<>
            <RouteGroup title="PARTONO DA QUI" items={departures}/>
            <RouteGroup title="ARRIVANO QUI" items={arrivals}/>
            <RouteGroup title="PASSANO VICINO" items={passes}/>
            <RouteGroup title="ALTRI ITINERARI IN ZONA" items={around}/>
            {!nearby.length&&<p className="cb-location-muted-note">Non sono state trovate tracce indicizzate nelle immediate vicinanze. Non implica che non esistano sentieri.</p>}
          </>}
        </section>

        {water.length>0&&<section className="cb-location-section cb-location-water">
          <div className="cb-location-section-heading"><span>04 / RISORSE IN ZONA</span>
            <h2>ACQUA NEI DINTORNI.</h2>
            <p>Fonti mappate entro circa 1,8 km in linea d'aria. La potabilità, l'accessibilità e la disponibilità vanno verificate sul posto.</p>
          </div>
          <div className="cb-location-water-grid">{water.slice(0,8).map(w=><div key={w.slug}>
            <AlpinePlaceIcon kind="acqua" size={22}/><div><strong>{w.name}</strong><small>{w.kind} · {potabilityLabel(w.potable)}{w.seasonal?' · stagionale':''}</small></div>
          </div>)}</div>
        </section>}

        {place.kind==='rifugio'&&<section className="cb-location-community">
          <div className="cb-location-section-heading"><span>05 / COMUNITÀ</span><h2>PARLA CON CHI CONOSCE IL POSTO.</h2></div>
          <p>Domande ai gestori verificati e recensioni moderate sono previste, ma non ancora disponibili. Non vengono mostrati giudizi o risposte fittizi.</p>
          <HutClaimRequest place={place}/>
        </section>}
        <footer className="cb-location-credits">
          Dati del luogo: <a href={place.osmUrl} target="_blank" rel="noopener noreferrer">OpenStreetMap · ODbL</a>.
          {place.photo&&<> Immagine: {place.photo.author}, {place.photo.license} · <a href={place.photo.sourceUrl} target="_blank" rel="noopener noreferrer">licenza e attribuzione</a>.</>}
          {place.wikidata&&<> <a href={'https://www.wikidata.org/wiki/'+place.wikidata} target="_blank" rel="noopener noreferrer">Wikidata</a>.</>}
          {' '}Meteo da modello, dati e condizioni del territorio possono cambiare.
        </footer>
      </div>

      <aside className="cb-location-sidebar" aria-label="Posizione e contatti">
        <section id="cb-place-map" className="cb-location-side-map">
          <div className="cb-location-sidebar-heading"><span>POSIZIONE</span><strong>DOVE SI TROVA.</strong></div>
          <AlpineAtlasMap places={places} kind={place.kind} selected={place} routes={nearby} water={water.map(w=>({lng:w.lng,lat:w.lat,potable:w.potable==='yes'}))} height="100%"/>
          <p>Coordinate: {place.lat.toFixed(5)}, {place.lng.toFixed(5)} · Mappa TOPO / satellite</p>
        </section>
        <section className="cb-location-contact-card">
          <div className="cb-location-sidebar-heading"><span>INFO OPERATIVE</span><strong>CONTATTI &amp; ACCESSO.</strong></div>
          {place.operator&&<div className="cb-location-contact-row"><small>Gestore / ente</small><strong>{place.operator}</strong></div>}
          {place.openingHours&&<div className="cb-location-contact-row"><small>Orari dichiarati</small><strong>{place.openingHours}</strong></div>}
          {place.phone&&<a className="cb-location-contact-link" href={'tel:'+place.phone.replace(/[^+\d]/g,'')}>☎ {place.phone}</a>}
          {place.email&&<a className="cb-location-contact-link" href={'mailto:'+place.email}>✉ {place.email}</a>}
          {place.website&&<a className="cb-location-contact-link cb-location-site-link" href={place.website} target="_blank" rel="noopener noreferrer">Sito della struttura ↗</a>}
          {!place.phone&&!place.email&&!place.website&&<p className="cb-location-muted-note">Contatti non ancora presenti nei dati disponibili.</p>}
        </section>
        <div className="cb-location-safety"><strong>IN MONTAGNA SERVE LA TESTA.</strong><p>Posizione, meteo e sentieri sono indicativi. Prima di partire verifica apertura, condizioni, eventuali chiusure e bollettino valanghe.</p></div>
      </aside>
    </div>
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
          {stage.routeSlugs.map(slug => <a href={`${import.meta.env.BASE_URL}route/${encodeURIComponent(slug)}/`} key={slug}>Apri il segmento {slug} ↗</a>)}
        </div>)}</div>
    </section>}
    {trek.routeSlugs.length>0 && <section className="cb-atlas-nearby"><h2>SEGMENTI COLLEGATI</h2>
      <div className="cb-atlas-routes">{trek.routeSlugs.slice(0,80).map(slug =>
        <a key={slug} href={`${import.meta.env.BASE_URL}route/${encodeURIComponent(slug)}/`}>Apri il segmento cartografico ↗ <small>{slug}</small></a>)}</div>
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
          </> : <div className="cb-atlas-grid">{treks.projects.map(t=><a key={t.slug} className="cb-atlas-card cb-atlas-trek" href={`${import.meta.env.BASE_URL}trekking/${encodeURIComponent(t.slug)}/`}>
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
