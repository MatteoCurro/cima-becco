import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { ExploreNavigation } from './ExploreNavigation';
import { homeHref } from '../lib/navigation';
import { loadAlpinePlaces, alpinePlaceLink, atlasCategory, placeBounds, type AlpinePlace, type AlpinePlacesDataset } from '../lib/alpinePlaces';
import { loadRouteBySlug, loadRoutesInBounds } from '../lib/routeTiles';
import { routesNear } from '../lib/routes';
import { trailMood, trailTitle } from '../lib/routeEditorial';
import { usePageTitle } from '../lib/pageTitle';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { AlpinePlaceVisual } from './AlpinePlaceVisual';
import { AlpineAtlasMap } from './AlpineAtlasMap';
import { MapContextLabel } from './MapContextLabel';
import { AlpineWeatherPanel } from './AlpineWeatherPanel';
import { HutClaimRequest } from './HutClaimRequest';
import { DetailFacts, DetailLayout, DetailMetrics, DetailSectionHeading } from './DetailPrimitives';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';
import { DetailJumpNav } from './DetailJumpNav';
import { NearbyAtlasPlaces } from './NearbyAtlasPlaces';
import { nearbyAtlasPlaces } from '../lib/nearbyAtlas';
import type { AtlasEntityMetadata } from '../lib/atlasDossier';
import { loadAlpineWater, alpineWaterNear, potabilityLabel, type AlpineWaterPoint } from '../lib/alpineWater';
import { track } from '../lib/analytics';
import '../alpineAtlas.css';
import '../locationProfile.css';
import '../alpineExplore.css';

interface TrekProject {
  slug: string;
  title: string;
  slogan: string;
  description: string;
  routeSlugs: string[];
  stages: { number: number; routeSlugs: string[] }[];
  /** Schema editoriale opzionale; le tappe legacy rimangono distinte. */
  atlas?: AtlasEntityMetadata;
}
type TreksDataset = { generatedAt: string | null; projects: TrekProject[] };
const EMPTY: AlpinePlacesDataset = { generatedAt: null, source: 'OpenStreetMap · ODbL 1.0', coverage: 'Dolomiti', places: [] };
const EMPTY_TREKS: TreksDataset = { generatedAt: null, projects: [] };
const EMPTY_PLACES: AlpinePlace[] = [];
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

export function PlaceDetail({ place, onBack }: { place: AlpinePlace; onBack: string }) {
  const [nearby,setNearby]=useState<Route[]>([]);
  const [loading,setLoading]=useState(true);
  const [water,setWater]=useState<AlpineWaterPoint[]>([]);
  const [localAtlas,setLocalAtlas]=useState<AlpinePlace[]>([]);
  const mapPlaces=useMemo(()=>[place],[place]);
  const nearbyPlaces=useMemo(()=>nearbyAtlasPlaces(place,localAtlas,{maxKm:8,limit:8}),[place,localAtlas]);
  useEffect(()=>{
    let alive=true;
    void loadAlpinePlaces().then(dataset=>{if(alive)setLocalAtlas(dataset.places);});
    return ()=>{alive=false;};
  },[]);
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
  const wiki=place.wikipedia?.match(/^([a-z]{2,3}):(.+)$/);
  const wikiUrl=wiki?`https://${wiki[1]}.wikipedia.org/wiki/${encodeURIComponent(wiki[2].replace(/ /g,'_'))}`:null;
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
  return <DetailLayout
    backHref={onBack}
    backLabel={`Esplora ${place.kind==='rifugio'?'i rifugi':place.kind==='bivacco'?'i bivacchi':'i paesi'}`}
    sidebarLabel="Posizione e contatti"
    sidebar={<section id="cb-place-map" className="cb-location-side-map">
      <MapContextLabel kicker="CARTOGRAFIA DEL LUOGO" title={place.name}/>
      <AlpineAtlasMap places={mapPlaces} kind={place.kind} selected={place} routes={nearby}
        water={water.map(w=>({lng:w.lng,lat:w.lat,name:w.name,kind:w.kind,potable:w.potable}))}
        height="100%" caption={place.name}/>
    </section>}
  >
    <header className="cb-location-hero">
      <div className="cb-location-hero-copy">
        <PlaceBadge place={place}/>
        <h1>{place.name}</h1>
        <p className="cb-location-lead">{place.shortSummary || placeLine}</p>
        {place.description&&<p className="cb-location-story">{place.description}</p>}
        {wikiUrl&&<a className="cb-location-wiki" href={wikiUrl} target="_blank" rel="noopener noreferrer">Storia e approfondimenti enciclopedici ↗</a>}
        <AtlasDossierBlocks record={place} placement="alerts"/>
        <DetailMetrics label="Informazioni principali" items={[
          { label: 'Altitudine' + (place.elevationSource === 'dem' ? ' stimata' : ''), value: place.elevationM != null ? place.elevationM.toLocaleString('it-IT') + ' m' : 'n.d.' },
          ...(place.capacity != null ? [{ label: place.kind === 'bivacco' ? 'Posti indicati' : 'Posti letto', value: place.capacity }] : []),
          { label: 'Sentieri vicini', value: loading ? '…' : nearby.length },
        ]}/>
        {place.kind!=='borgo'&&place.fee&&<div className="cb-location-cost">
          <span>PREZZI / ACCESSO</span>
          {/^\s*(yes|no)\s*$/i.test(place.fee)?<strong>{place.fee.toLowerCase()==='no'?'Accesso indicato gratuito':'Tariffa presente, importo da verificare'}</strong>:
            <><strong>{place.fee}</strong>{/\d/.test(place.fee)&&<span className="cb-location-dobloni" title="Indicazione giocosa basata su una tariffa dichiarata; non è un rating">🪙 <small>Importo dichiarato · verifica con il gestore</small></span>}</>}
        </div>}
        <div className="cb-location-actions">
          <button type="button" className="cb-location-action-primary" onClick={()=>document.getElementById('cb-place-map')?.scrollIntoView({behavior:'smooth',block:'start'})}>ESPLORA SULLA MAPPA <span aria-hidden="true">↗</span></button>
          {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')}>{place.kind==='rifugio'?'CHIAMA IL RIFUGIO':place.kind==='bivacco'?'CHIAMA IL REFERENTE':'CHIAMA'}</a>}
          {place.email&&<a href={'mailto:'+place.email}>SCRIVI</a>}
        </div>
        {place.kind==='bivacco'&&<p className="cb-location-alert">Bivacco non custodito: verifica accesso, dotazioni e condizioni prima di partire. La capienza indicata non garantisce posto disponibile.</p>}
      </div>
      <figure className="cb-location-hero-media">
        <AlpinePlaceVisual key={place.slug} place={place}/>
        <div className="cb-location-avatar">{place.logo?<img src={place.logo.url} alt={'Logo ufficiale di '+place.name}/>:<AlpinePlaceIcon kind={place.kind} size={39}/>}</div>
        <figcaption>{place.photo?<><span>Foto: {place.photo.author} · {place.photo.license}</span> · <a href={place.photo.sourceUrl} target="_blank" rel="noopener noreferrer">Fonte e licenza ↗</a></>:'Rappresentazione topografica: fotografia del luogo non disponibile'}</figcaption>
      </figure>
    </header>
    <DetailJumpNav items={[
      {id:"cb-location-info-heading",label:"Informazioni"},
      {id:"cb-location-contact-title",label:"Contatti"},
      {id:"cb-place-itineraries",label:"Sentieri"},
      ...(nearbyPlaces.length?[{id:"cb-place-nearby",label:"Dintorni"}]:[]),
      {id:"cb-place-map",label:"Mappa"},
    ]}/>
        <section className="cb-location-section cb-location-dossier" aria-labelledby="cb-location-info-heading">
          <DetailSectionHeading kicker="01 / DATI ESSENZIALI" title="PRIMA DI PARTIRE." id="cb-location-info-heading" description="Informazioni disponibili nelle fonti cartografiche, da verificare con la struttura quando necessario."/>
          <DetailFacts rows={detailRows}/>
          {place.kind==='rifugio'&&!place.phone&&!place.email&&<p className="cb-location-muted-note">Non abbiamo ancora recapiti verificati per questa struttura: dato mancante non significa che sia chiusa.</p>}
        </section>
        <AtlasDossierBlocks record={place} placement="core"/>
        <section className="cb-location-section cb-location-contact-card" aria-labelledby="cb-location-contact-title">
          <DetailSectionHeading kicker="02 / INFO PRATICHE" id="cb-location-contact-title" title="CONTATTI E ACCESSO."/>
          {place.operator&&<p><strong>Gestore o ente: </strong>{place.operator}</p>}
          {place.openingHours&&<p><strong>Orari dichiarati: </strong>{place.openingHours}</p>}
          <div className="cb-location-contact-links">
            {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')}>☎ {place.phone}</a>}
            {place.email&&<a href={'mailto:'+place.email}>✉ {place.email}</a>}
            {place.website&&<a href={place.website} target="_blank" rel="noopener noreferrer">Sito ufficiale ↗</a>}
          </div>
          {!place.phone&&!place.email&&!place.website&&<p className="cb-location-muted-note">Recapiti non disponibili nelle fonti: non significa che la struttura sia chiusa.</p>}
        </section>
        <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>

        <section id="cb-place-itineraries" className="cb-location-section cb-location-itineraries" aria-label="Sentieri vicini">
          <DetailSectionHeading kicker="03 / ESCURSIONI E ACCESSI" title="SENTIERI NEI DINTORNI." description="Tracce disponibili in zona: la vicinanza geometrica al percorso non certifica un accesso diretto."/>
          {loading?<p className="cb-atlas-loading">Recupero i sentieri cartografati…</p>:<>
            <RouteGroup title="PARTONO DA QUI" items={departures}/>
            <RouteGroup title="ARRIVANO QUI" items={arrivals}/>
            <RouteGroup title="PASSANO VICINO" items={passes}/>
            <RouteGroup title="ALTRI ITINERARI IN ZONA" items={around}/>
            {!nearby.length&&<p className="cb-location-muted-note">Non sono state trovate tracce indicizzate nelle immediate vicinanze. Non implica che non esistano sentieri.</p>}
          </>}
        </section>

        {water.length>0&&<section className="cb-location-section cb-location-water">
          <DetailSectionHeading kicker="04 / RISORSE IN ZONA" title="ACQUA NEI DINTORNI." description="Fonti mappate entro circa 1,8 km in linea d'aria. La potabilità, l'accessibilità e la disponibilità vanno verificate sul posto."/>
          <div className="cb-location-water-grid">{water.slice(0,8).map(w=><div key={w.slug}>
            <AlpinePlaceIcon kind="acqua" size={22}/><div><strong>{w.name}</strong><small>{w.kind} · {potabilityLabel(w.potable)}{w.seasonal?' · stagionale':''}</small></div>
          </div>)}</div>
        </section>}

        <NearbyAtlasPlaces items={nearbyPlaces}/>
        <AtlasDossierBlocks record={place} placement="connections"/>
        <AtlasDossierBlocks record={place} placement="media"/>
        {place.kind==='rifugio'&&<section className="cb-location-community">
          <DetailSectionHeading kicker="05 / COMUNITÀ" title="PARLA CON CHI CONOSCE IL POSTO."/>
          <p>Domande ai gestori verificati e recensioni moderate sono previste, ma non ancora disponibili. Non vengono mostrati giudizi o risposte fittizi.</p>
          <HutClaimRequest place={place}/>
        </section>}
        <footer className="cb-location-credits">
          <AtlasDossierBlocks record={place} placement="credits"/>
          Dati del luogo: <a href={place.osmUrl} target="_blank" rel="noopener noreferrer">OpenStreetMap · ODbL</a>.
          {place.photo&&<> Immagine: {place.photo.author}, {place.photo.license} · <a href={place.photo.sourceUrl} target="_blank" rel="noopener noreferrer">licenza e attribuzione</a>.</>}
          {place.wikidata&&<> <a href={'https://www.wikidata.org/wiki/'+place.wikidata} target="_blank" rel="noopener noreferrer">Wikidata</a>.</>}
          {' '}Meteo da modello, dati e condizioni del territorio possono cambiare.
        </footer>
        <p className="cb-location-safety"><strong>IN MONTAGNA SERVE LA TESTA.</strong> Posizione, meteo, apertura e condizioni possono cambiare. Verifica con le fonti ufficiali prima di partire.</p>
  </DetailLayout>;
}

function TrekDetail({ trek, onBack }: { trek: TrekProject; onBack: string }) {
  const [previewRoutes, setPreviewRoutes] = useState<Route[]>([]);
  const [loading, setLoading] = useState(true);
  useEffect(() => {
    let active = true;
    setPreviewRoutes([]);
    setLoading(true);
    // Anteprima di pochi segmenti reali: non si inventano collegamenti tra tracce.
    const candidates = trek.stages.length ? trek.stages.flatMap(stage => stage.routeSlugs) : trek.routeSlugs;
    const slugs = [...new Set(candidates)].slice(0, 3);
    void Promise.allSettled(slugs.map(loadRouteBySlug)).then(results => {
      if (!active) return;
      setPreviewRoutes(results.flatMap(result => result.status === 'fulfilled' && result.value ? [result.value] : []));
      setLoading(false);
    });
    return () => { active = false; };
  }, [trek]);

  return <DetailLayout
    backHref={onBack}
    backLabel="Tutti i trekking"
    sidebarLabel="Cartografia del trekking"
    className="cb-trek-profile"
    sidebar={<section id="cb-place-map" className="cb-location-side-map">
      <MapContextLabel kicker="TAPPE DEL TREKKING" title={trek.title}/>
      {previewRoutes.length?<AlpineAtlasMap places={EMPTY_PLACES} kind="borgo" routes={previewRoutes}
        caption="ANTEPRIMA TAPPE" height="100%"/>:
        <div className="cb-trek-empty-map">{loading?'Caricamento delle tracce…':'Nessuna traccia disponibile per questa anteprima.'}</div>}
    </section>}
  >
        <header className="cb-location-hero">
          <figure className="cb-trek-hero-art" aria-label="Illustrazione topografica; fotografia del trekking non disponibile"><span>ALTE VIE / TREKKING</span></figure>
          <div className="cb-location-hero-copy">
            <span className="cb-atlas-kind cb-atlas-kind--trek">TREKKING A TAPPE</span>
            <h1>{trek.title}</h1>
            <p className="cb-location-lead">{trek.slogan}</p>
            <p className="cb-location-story">{trek.description}</p>
            <AtlasDossierBlocks record={trek.atlas ?? {}} placement="alerts"/>
            <DetailMetrics label="Dati del trekking" items={[
              { label: 'Segmenti identificati', value: trek.routeSlugs.length },
              { label: 'Tappe esplicite', value: trek.stages.length },
              { label: 'Segmenti in anteprima', value: loading ? '…' : previewRoutes.length },
            ]}/>
            <p className="cb-location-alert">Il tracciato completo non è verificato: i segmenti cartografici non dimostrano da soli continuità, accessibilità o percorribilità.</p>
          </div>
        </header>
        {trek.stages.length > 0 && <section className="cb-location-section cb-location-dossier">
          <DetailSectionHeading kicker="01 / PERCORSO" title="TAPPE IDENTIFICATE." description="Tappe esplicitamente associate nei dati, senza inferire collegamenti mancanti."/>
          <div className="cb-atlas-routes">{trek.stages.map(stage =>
            <div key={stage.number}><strong>TAPPA {stage.number}</strong>
              {stage.routeSlugs.map(slug => <a href={`${import.meta.env.BASE_URL}route/${encodeURIComponent(slug)}/`} key={slug}>Apri il segmento {slug} ↗</a>)}
            </div>)}</div>
        </section>}
        {trek.routeSlugs.length > 0 && <section className="cb-location-section cb-location-itineraries">
          <DetailSectionHeading kicker="02 / DATI CARTOGRAFICI" title="SEGMENTI COLLEGATI." description="Elementi realmente censiti, consultabili singolarmente sulla mappa."/>
          <div className="cb-atlas-routes">{trek.routeSlugs.slice(0, 80).map(slug =>
            <a key={slug} href={`${import.meta.env.BASE_URL}route/${encodeURIComponent(slug)}/`}>Apri il segmento cartografico ↗ <small>{slug}</small></a>)}</div>
        </section>}
        <AtlasDossierBlocks record={trek.atlas ?? {}} placement="core"/>
        <AtlasDossierBlocks record={trek.atlas ?? {}} placement="connections"/>
        <AtlasDossierBlocks record={trek.atlas ?? {}} placement="media"/>
        <footer className="cb-location-credits"><AtlasDossierBlocks record={trek.atlas ?? {}} placement="credits"/>Dati escursionistici e geometrie dei singoli segmenti: verifica sempre fonti, segnaletica e condizioni prima della partenza.</footer>
  </DetailLayout>;
}

export function AlpineAtlasPage() {
  const [hash,setHash] = useState(() => window.location.hash);
  const [data,setData] = useState<AlpinePlacesDataset>(EMPTY);
  const [treks,setTreks] = useState<TreksDataset>(EMPTY_TREKS);
  const [query,setQuery] = useState('');
  const [visible,setVisible] = useState(36);
  const {section,slug}=parseAtlas(hash);
  usePageTitle(sectionLabels[section] + ' · Cima Becco');
  useEffect(()=>{
    if(section==='trekking')return;
    if(slug){
      const kind=section==='rifugi'?'rifugio':section==='bivacchi'?'bivacco':'borgo';
      window.location.replace(alpinePlaceLink({kind,slug}));
    }else window.location.replace(homeHref(section==='borghi'?'paesi':section));
  },[section,slug]);
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
    {!slug && <ExploreNavigation active={section==='trekking'?'trekking':section==='borghi'?'paesi':section}/>}
    <main className={slug ? 'cb-atlas-shell cb-atlas-shell--detail' : 'cb-atlas-shell'}>
      {!slug && <div className="cb-atlas-overline">CIMA BECCO / ESPLORA</div>} 
      {place ? <PlaceDetail place={place} onBack={`#atlante/${section}`}/>
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
