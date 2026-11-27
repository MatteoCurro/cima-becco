import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { loadAlpinePlaces, alpinePlaceLink, atlasCategory, placeBounds, type AlpinePlace, type AlpinePlacesDataset } from '../lib/alpinePlaces';
import { boundsToHash } from '../lib/regions';
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
type Section = 'rifugi' | 'borghi' | 'trekking';

function parseAtlas(hash: string): { section: Section; slug: string | null } {
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
    <AlpinePlaceIcon kind={place.kind} size={19}/>
    {place.kind === 'rifugio' ? 'RIFUGIO' : 'BORGO'}{place.elevationM ? ` · ${place.elevationM.toLocaleString('it-IT')} m` : ''}
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
      .then(routes=>{if(active)setNearby(routesNear(routes,place.lng,place.lat,place.kind==='rifugio'?1100:1600,22));})
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
  const placeLine=place.kind==='rifugio'
    ? `${place.name} è un rifugio mappato nel settore dolomitico${place.elevationM ? `, a circa ${place.elevationM} metri di quota` : ''}.`
    : `${place.name} è una località montana identificata nei dati OpenStreetMap${place.elevationM ? `, a ${place.elevationM} metri di quota` : ''}.`;

  return <div className="cb-atlas-detail cb-atlas-detail-wide">
    <a className="cb-atlas-back" href={onBack}>← Torna all'atlante</a>
    <PlaceBadge place={place}/>
    <h1>{place.name}</h1>
    <p className="cb-atlas-lead">{place.description || placeLine} {place.kind==='rifugio'
      ? 'Controlla apertura, accessi e disponibilità prima di organizzare una sosta.'
      : 'Una base per muoversi tra i sentieri e le montagne della zona.'}</p>
    {place.photo && <figure className="cb-atlas-cover">
      <a href={place.photo.sourceUrl} target="_blank" rel="noopener noreferrer"><img src={place.photo.url} alt={`Fotografia collegata a ${place.name}`} loading="lazy"/></a>
    </figure>}
    <div className="cb-atlas-facts">
      <span><strong>{place.lat.toFixed(4)}, {place.lng.toFixed(4)}</strong>Coordinate</span>
      {place.elevationM!=null && <span><strong>{place.elevationM.toLocaleString('it-IT')} m</strong>{place.elevationSource==='dem'?'Quota DEM stimata':'Quota indicata in OSM'}</span>}
      {place.operator&&<span><strong>{place.operator}</strong>Gestore</span>}
      {place.capacity!=null&&<span><strong>{place.capacity}</strong>Posti letto dichiarati OSM</span>}
      {place.openingHours&&<span><strong>{place.openingHours}</strong>Orari indicati OSM</span>}
      {place.address&&<span><strong>{place.address}</strong>Indirizzo indicato OSM</span>}
      {place.phone&&<span><strong>{place.phone}</strong>Telefono</span>}
    </div>
    <div className="cb-atlas-actions">
      <a className="cb-atlas-primary" href={boundsToHash(placeBounds(place,3))}>ESPLORA LA ZONA ↗</a>
      {place.website&&<a href={place.website} target="_blank" rel="noopener noreferrer">Sito ufficiale indicato nei dati ↗</a>}
      {place.wikidata&&<a href={`https://www.wikidata.org/wiki/${place.wikidata}`} target="_blank" rel="noopener noreferrer">Dati enciclopedici ↗</a>}
    </div>
    <div className="cb-atlas-section-top"><span>CARTOGRAFIA DEDICATA</span><h2>LA MAPPA NON MENTE. (QUASI.)</h2>
      <p>Rifugi e località mappati, sentieri vicini e punti acqua. TOPO per leggere il terreno, SAT per guardarlo.</p>
    </div>
    <AlpineAtlasMap places={places} kind={place.kind} selected={place} routes={nearby} water={water.map(w=>({lng:w.lng,lat:w.lat,potable:w.potable==='yes'}))} height={360}/>
    {loading ? <p className="cb-atlas-loading">Sto incrociando i tracciati cartografici nei dintorni…</p> : <>
      <RouteGroup title="SI PARTE DA QUI" items={departures}/>
      <RouteGroup title="QUI SI ARRIVA" items={arrivals}/>
      <RouteGroup title="CI PASSANO VICINO DAVVERO" items={passes}/>
      <RouteGroup title="ALTRI SENTIERI NEI DINTORNI" items={around}/>
      {!nearby.length&&<div className="cb-atlas-empty"><p>Nessun tracciato già indicizzato vicino a questa posizione. Non significa che non ci siano sentieri.</p></div>}
    </>}
    {water.length>0&&<section className="cb-local-water">
      <h2><AlpinePlaceIcon kind="acqua" size={27}/> L'ACQUA NON VIENE CON L'ABBONAMENTO.</h2>
      <p>Fonti registrate entro circa 1,8 km dalla località. La distanza è in linea d’aria: non garantisce raggiungibilità.</p>
      <div className="cb-local-water-grid">{water.slice(0,8).map(w=><a key={w.slug} href={w.osmUrl} target="_blank" rel="noopener noreferrer">
        <strong>{w.name}</strong><small>{w.kind} · {potabilityLabel(w.potable)}{w.seasonal?' · stagionale':''}</small></a>)}</div>
    </section>}
    <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>
    {place.kind==='rifugio'&&<HutClaimRequest place={place}/>}
    <p className="cb-atlas-sourcing">Dati cartografici: <a href={place.osmUrl} target="_blank" rel="noopener noreferrer">OpenStreetMap · ODbL</a>.
      {place.photo&&<> Foto: {place.photo.author}, {place.photo.license} · <a href={place.photo.sourceUrl} target="_blank" rel="noopener noreferrer">Wikimedia Commons</a>.</>}
      {' '}Quote, condizioni meteo, fonti d’acqua e sentieri richiedono verifica sul posto.</p>
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
  const allSectionPlaces=useMemo(()=>data.places.filter(place=>atlasCategory(place.kind)===section),[data,section]);
  const places=useMemo(()=>allSectionPlaces.filter(place=>place.name.toLocaleLowerCase('it').includes(query.trim().toLocaleLowerCase('it'))),[allSectionPlaces,query]);
  const place=slug?data.places.find(p=>p.slug===slug && atlasCategory(p.kind)===section):null;
  const trek=slug?treks.projects.find(p=>p.slug===slug):null;
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <main className="cb-atlas-shell">
      <div className="cb-atlas-overline">CIMA BECCO / ATLANTE IN PROGRESS</div>
      <AtlasHeader section={section}/>
      {place ? <PlaceDetail place={place} onBack={`#atlante/${section}`} places={allSectionPlaces}/>
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
            {allSectionPlaces.length>0&&<section className="cb-atlas-list-map">
              <div className="cb-atlas-section-top"><span>{section==='rifugi'?'I TETTI AD ALTA QUOTA':'BORGHI DA CUI PARTIRE'}</span>
                <h2>TUTTI SULLA MAPPA.</h2></div>
              <AlpineAtlasMap places={allSectionPlaces} kind={section==='rifugi'?'rifugio':'borgo'} height={350}/>
            </section>}
            <div className="cb-atlas-toolbar"><label htmlFor="cb-atlas-query">CERCA UN {section==='rifugi'?'RIFUGIO':'PAESE'}</label>
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
