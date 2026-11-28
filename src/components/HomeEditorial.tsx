import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import { DATA_BASE } from '../lib/venues';
import { boundsToHash } from '../lib/regions';
import { RouteThumb } from './RouteThumb';
import { homeDiscoveryForDay, homeTerritoryForDay, romeDay, validHomeEditorialFeed,
  type HomeEditorialFeed, type HomeEditorialKind, type HomeEditorialPlace } from '../lib/homeEditorial';
import './homeEditorial.css';

const NAMES:Record<HomeEditorialKind,string>={
  town:'Paesi e comunità',refuge:'Rifugi',bivacco:'Bivacchi',summit:'Cime documentate',
};
const LABELS:Record<HomeEditorialKind,string>={
  town:'PAESE NEL TERRITORIO',refuge:'RIFUGIO NELLA ZONA',
  bivacco:'BIVACCO NELLA ZONA',summit:'CIMA DOCUMENTATA',
};
function link(path:string) {
  return import.meta.env.BASE_URL.replace(/\/$/,'') + path;
}
function height(place:HomeEditorialPlace) {
  return place.elevationM != null && Number.isFinite(place.elevationM)
    ? Math.round(place.elevationM).toLocaleString('it-IT')+' m' : null;
}
function relationship(place:HomeEditorialPlace) {
  if(place.relation==='mapped_route')return 'Presso una traccia mappata';
  return place.distanceToRouteKm!=null
    ? place.distanceToRouteKm.toLocaleString('it-IT',{maximumFractionDigits:1})+
      ' km in linea d’aria dalla traccia'
    : null;
}
function PlaceFeature({place,variant}:{place:HomeEditorialPlace;variant:string}) {
  return <a className={'cb-home-focus-card cb-home-focus-'+variant} href={link(place.href)}>
    <span className="cb-home-focus-media">
      {place.cover && <img src={place.cover.url} alt={'Fotografia documentata di '+place.name}
        loading={variant==='lead'?'eager':'lazy'} decoding="async"/>}
    </span>
    <span className="cb-home-focus-shade"/>
    <span className="cb-home-focus-copy">
      <small className="cb-home-focus-overline">{LABELS[place.kind]}</small>
      <strong>{place.name}</strong>
      {variant==='lead' && place.text && <span className="cb-home-focus-description">{place.text}</span>}
      <span className="cb-home-focus-meta">
        {[height(place),relationship(place)].filter(Boolean).join(' · ')}
      </span>
    </span>
    <span className="cb-home-focus-arrow" aria-hidden="true">↗</span>
  </a>;
}
function TerritoryRoute({route,full}:{route:HomeEditorialFeed['territories'][number]['route'];full?:Route}) {
  return <a className="cb-home-focus-card cb-home-focus-route" href={link(route.href)}>
    <span className="cb-home-route-art" aria-hidden="true">
      {full ? <RouteThumb route={full} animate={false}/> :
        <span className="cb-home-route-line">╱╲╱╲╱</span>}
    </span>
    <span className="cb-home-focus-copy">
      <small className="cb-home-focus-overline">UNA TRACCIA DA ESPLORARE</small>
      <strong>{route.name}</strong>
      <span className="cb-home-focus-meta">
        {route.distanceKm.toLocaleString('it-IT',{maximumFractionDigits:1})} km
        {route.gainM!=null?' · +'+route.gainM.toLocaleString('it-IT')+' m':''}
        {route.difficulty?' · '+route.difficulty:''}
      </span>
    </span>
    <span className="cb-home-focus-arrow" aria-hidden="true">↗</span>
  </a>;
}
function TerritoryPerson({person}:{person:NonNullable<HomeEditorialFeed['territories'][number]['person']>}) {
  const relation=person.relation==='birthplace_of'?'Nata/o nel comune':
    person.relation==='historical_residence_of'?'Residenza storica documentata':'Attività documentata nel comune';
  return <a className="cb-home-focus-card cb-home-focus-person" href={link(person.href)}>
    {person.portrait ? <img src={person.portrait} loading="lazy" decoding="async"
      alt={'Ritratto documentato di '+person.name} className="cb-home-person-portrait"/> : null}
    <span className="cb-home-focus-copy">
      <small className="cb-home-focus-overline">PERSONE DI MONTAGNA</small>
      <strong>{person.name}</strong>
      <span className="cb-home-focus-meta">{person.role} · {relation}</span>
      <span className="cb-home-person-footnote">Nel dossier di {person.placeName}</span>
    </span>
    <span className="cb-home-focus-arrow" aria-hidden="true">↗</span>
  </a>;
}
function HomeCategoryCard({place}:{place:HomeEditorialPlace}) {
  return <a href={link(place.href)} className="cb-home-category-entry">
    <span className="cb-home-category-photo">
      {place.cover && <img src={place.cover.url} loading="lazy" decoding="async"
        alt={'Fotografia documentata di '+place.name}/>}
    </span>
    <span className="cb-home-category-text">
      <strong>{place.name}</strong>
      <small>{[height(place),place.text].filter(Boolean).join(' · ')}</small>
    </span>
    <span className="cb-home-category-arrow" aria-hidden="true">↗</span>
  </a>;
}
function focusBounds(items:HomeEditorialPlace[],center:{lat:number;lng:number}) {
  const pts=[center,...items.filter(Boolean)];
  const lat=Math.max(0.14,(Math.max(...pts.map(p=>p.lat))-Math.min(...pts.map(p=>p.lat)))/2+0.055);
  const lng=Math.max(0.19,(Math.max(...pts.map(p=>p.lng))-Math.min(...pts.map(p=>p.lng)))/2+0.075);
  const midLat=(Math.max(...pts.map(p=>p.lat))+Math.min(...pts.map(p=>p.lat)))/2;
  const midLng=(Math.max(...pts.map(p=>p.lng))+Math.min(...pts.map(p=>p.lng)))/2;
  return boundsToHash({west:midLng-lng,south:midLat-lat,east:midLng+lng,north:midLat+lat});
}
export function HomeEditorial({routes}:{routes:Route[]}) {
  const [feed,setFeed]=useState<HomeEditorialFeed|null>(null);
  const [loaded,setLoaded]=useState(false);
  useEffect(()=>{
    let active=true;
    void fetch(DATA_BASE+'/home-editorial-v1.json')
      .then(r=>r.ok?r.json():null)
      .then(raw=>{if(active)setFeed(validHomeEditorialFeed(raw)?raw:null);})
      .catch(()=>{if(active)setFeed(null);})
      .finally(()=>{if(active)setLoaded(true);});
    return()=>{active=false;};
  },[]);
  // Fixed to Europe's calendar day, not Math.random() or each refresh.
  const date=useMemo(()=>new Date(),[]);
  const today=romeDay(date);
  const territory=feed?homeTerritoryForDay(feed,date):null;
  const groups=feed?homeDiscoveryForDay(feed,date,territory):[];
  const featured=routes.find(route=>route.slug===territory?.route.slug);
  const localPlaces=territory?[territory.town,territory.refuge,
    territory.bivacco,territory.summit].filter((x):x is HomeEditorialPlace=>Boolean(x)):[];
  const mapHref=territory?focusBounds(localPlaces,territory.center):'#map';
  return <div className="cb-home-editorial" id="cb-home-editorial">
    {!loaded ? <div className="cb-home-editorial-pending" role="status">
      <span className="cb-home-editorial-kicker">IL TERRITORIO DI OGGI</span>
      <h2>STIAMO SCEGLIENDO UNA BELLA ZONA.</h2>
    </div> : null}
    {territory && <section className="cb-home-daily" aria-labelledby="cb-home-daily-title">
      <header className="cb-home-editorial-heading">
        <div>
          <span className="cb-home-editorial-kicker">OGNI GIORNO, UN PEZZO DI MONTAGNA · <time dateTime={today.key}>{today.label}</time></span>
          <h2 id="cb-home-daily-title">{territory.title}<span>.</span></h2>
          <p>Un paese, una traccia e altri luoghi dello stesso territorio. Le connessioni vere si raccontano; le distanze si dichiarano.</p>
        </div>
        <a className="cb-home-editorial-all" href={mapHref}>ESPLORA L’AREA <span aria-hidden="true">↗</span></a>
      </header>
      <div className="cb-home-focus-grid">
        <PlaceFeature place={territory.town} variant="lead"/>
        <TerritoryRoute route={territory.route} full={featured}/>
        <PlaceFeature place={territory.refuge} variant="refuge"/>
        {territory.bivacco && <PlaceFeature place={territory.bivacco} variant="bivacco"/>}
        {territory.summit && <PlaceFeature place={territory.summit} variant="summit"/>}
        {territory.person ? <TerritoryPerson person={territory.person}/> :
          <a className="cb-home-focus-card cb-home-focus-note" href={mapHref}>
            <span className="cb-home-focus-overline">IL BELLO DI CAMBIARE PROSPETTIVA</span>
            <strong>NON È UNA LISTA. È UN TERRITORIO.</strong>
            <span>Apri la mappa, trova le relazioni e scegli tu come esplorarlo.</span>
            <span className="cb-home-focus-arrow" aria-hidden="true">↗</span>
          </a>}
      </div>
      <p className="cb-home-editorial-caution">Le distanze indicate sono geografiche e non dimostrano percorribilità, accessi alla vetta o continuità tra sentieri, rifugi e bivacchi. Verifica sempre condizioni e itinerari.</p>
    </section>}
    {loaded && groups.length>0 && <section className="cb-home-discovery" aria-labelledby="cb-home-discovery-title">
      <header className="cb-home-editorial-heading">
        <div>
          <span className="cb-home-editorial-kicker">DENTRO L’ATLANTE / SCHEDE DOCUMENTATE</span>
          <h2 id="cb-home-discovery-title">ALTRE COSE DA SCOPRIRE<span>.</span></h2>
          <p>Non soltanto cime. Storie, luoghi e punti di riferimento che hanno già qualcosa da raccontare.</p>
        </div>
      </header>
      <div className="cb-home-category-grid">
        {groups.map(group=><section className={'cb-home-category cb-home-category--'+group.kind} key={group.kind}>
          <h3>{NAMES[group.kind]}</h3>
          <div>{group.items.map(p=><HomeCategoryCard place={p} key={p.href}/>)}</div>
        </section>)}
      </div>
    </section>}
    {loaded && !territory && groups.length===0 &&
      <div className="cb-home-editorial-empty">
        <span className="cb-home-editorial-kicker">L’ATLANTE SI ARRICCHISCE</span>
        <h2>LA MONTAGNA NON FINISCE QUI.</h2>
        <p>Stiamo selezionando schede con identità, fotografie e informazioni verificabili. Nel frattempo, i percorsi restano consultabili.</p>
        <a className="cb-home-editorial-all" href="#routes">Esplora i sentieri ↗</a>
      </div>}
  </div>;
}
