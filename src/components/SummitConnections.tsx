import { useEffect, useMemo, useState } from 'react';
import type { Route, Venue } from '../types';
import { loadRoutesInBounds } from '../lib/routeTiles';
import { radiusBounds } from '../lib/routes';
import { loadAlpinePlaces, alpinePlaceLink, type AlpinePlace } from '../lib/alpinePlaces';
import { routeDetailHref } from '../lib/navigation';
import { trailMood, trailTitle } from '../lib/routeEditorial';
import { routePresentationCategory } from '../lib/routeClassification';
import { summitRoutes, summitSupportPlaces, type SummitRouteConnection, type SummitSupportPlace } from '../lib/summitApproach';
import './summitProfile.css';

interface SummitConnectionsProps {
  venue: Venue;
  connectedRoutes: Route[];
}

/** Nearby GPX geometry is never proof of a verified summit ascent. */
export function SummitConnections({ venue, connectedRoutes }: SummitConnectionsProps) {
  const [mapped, setMapped] = useState<Route[]>([]);
  const [places, setPlaces] = useState<AlpinePlace[]>([]);
  const [routeState, setRouteState] = useState<'loading'|'ready'|'unavailable'>('loading');
  const [placeState, setPlaceState] = useState<'loading'|'ready'|'unavailable'>('loading');
  useEffect(() => {
    let active=true;
    setRouteState('loading');
    setPlaceState('loading');
    setMapped([]);
    setPlaces([]);
    void loadRoutesInBounds(radiusBounds(venue.lng,venue.lat,4500))
      .then(routes=>{if(active){setMapped(routes);setRouteState('ready');}})
      .catch(()=>{if(active)setRouteState('unavailable');});
    void loadAlpinePlaces()
      .then(data=>{if(active){setPlaces(data.places);setPlaceState('ready');}})
      .catch(()=>{if(active)setPlaceState('unavailable');});
    return ()=>{active=false;};
  },[venue.slug,venue.lng,venue.lat]);

  const linked=useMemo(()=>{
    // Do not overwrite an already related route with a tile copy whose
    // metadata may omit its documented summit relation.
    const unique=new Map(mapped.map(route=>[route.slug,route]));
    for(const route of connectedRoutes)unique.set(route.slug,route);
    return summitRoutes(venue,[...unique.values()]);
  },[venue,mapped,connectedRoutes]);
  const support=useMemo(()=>summitSupportPlaces(venue,places,linked),[venue,places,linked]);
  const documented=linked.filter(item=>item.relation==='documented');
  const ferrate=linked.filter(item=>item.relation!=='documented'&&item.ferrata);
  const endpoints=linked.filter(item=>item.relation==='endpoint_near'&&!item.ferrata);
  const passes=linked.filter(item=>item.relation==='passes_near'&&!item.ferrata);

  return <>
    <section className="venue-detail-section cb-detail-group cb-summit-section" id="cb-summit-access">
      <p className="cb-summit-kicker">ITINERARI, FERRATE E ACCESSI</p>
      <h2>Come si arriva lassù?</h2>
      <p className="cb-summit-lead">Le tracce sono associate alla cima attraverso la loro geometria, non per somiglianza del nome.
        Una linea GPX nei pressi della vetta non certifica che un sentiero sia praticabile o che raggiunga esattamente la cima.</p>
      {routeState==='loading'&&<p className="cb-summit-status" role="status">Cerco i tracciati cartografati attorno alla cima…</p>}
      {routeState==='unavailable'&&<p className="cb-summit-status" role="status">Catalogo dei tracciati temporaneamente non disponibile. I collegamenti già noti restano consultabili.</p>}
      {linked.length>0 ? <>
        <SummitRouteGroup title="Accessi documentati" caption="Solo collegamenti esplicitamente verificati nelle fonti." items={documented}/>
        <SummitRouteGroup title="Ferrate e percorsi attrezzati" caption="Tipologia e difficoltà tecnica possono richiedere verifica. La vicinanza non prova un collegamento alla vetta." items={ferrate} technical/>
        <SummitRouteGroup title="Tracce con un’estremità vicino alla cima" caption="Il punto iniziale oppure finale è entro 100 metri dalle coordinate della cima; non è un accesso confermato." items={endpoints}/>
        <SummitRouteGroup title="Sentieri che passano nei pressi" caption="La traccia transita entro circa 160 metri dalla cima. Non è necessariamente una via di salita." items={passes}/>
      </> : routeState!=='loading' ? <p className="cb-summit-status">Nessun tracciato collegabile con sufficiente evidenza nei dati attualmente disponibili. Non significa che la cima non abbia vie di salita.</p> : null}
      <p className="cb-summit-method">I tracciati OSM o GPX non sono relazioni tecniche di ascensione e non indicano lo stato di attrezzature, nevai, esposizione o chiusure.</p>
    </section>
    <section className="venue-detail-section cb-detail-group cb-summit-section" id="cb-summit-support">
      <p className="cb-summit-kicker">LOGISTICA IN MONTAGNA</p>
      <h2>Rifugi e bivacchi nei dintorni.</h2>
      <p className="cb-summit-lead">Possibili riferimenti per organizzare un’escursione, non punti di partenza o appoggio certificati. Le distanze indicate sono sempre in linea d’aria.</p>
      {placeState==='loading'&&<p className="cb-summit-status" role="status">Individuo rifugi e bivacchi censiti nella zona…</p>}
      {placeState==='unavailable'&&<p className="cb-summit-status">Archivio delle strutture temporaneamente non disponibile.</p>}
      {support.length>0&&<div className="cb-summit-support-list">
        {support.map(item=><SummitSupportRow key={item.place.slug} item={item}/>)}
      </div>}
      {placeState==='ready'&&!support.length&&<p className="cb-summit-status">Non risultano strutture censite entro 9 km; la copertura degli archivi è ancora in espansione.</p>}
      <p className="cb-summit-method">La presenza di una struttura lungo o vicino a una traccia non garantisce accessibilità, disponibilità di posti, apertura né un itinerario sicuro fino alla cima.</p>
    </section>
  </>;
}

function SummitRouteGroup({title,caption,items,technical=false}:{
  title:string;caption:string;items:SummitRouteConnection[];technical?:boolean;
}){
  if(!items.length)return null;
  return <div className="cb-summit-route-group">
    <h3>{title} <span>{items.length}</span></h3>
    <p className="cb-summit-group-note">{caption}</p>
    <div className="cb-summit-route-list">
      {items.map(item=>{
        const category=routePresentationCategory(item.route);
        const mood=trailMood(item.route);
        const length=item.route.distanceM>0
          ? (item.route.distanceM/1000).toLocaleString('it-IT',{maximumFractionDigits:1})+' km'
          : 'Lunghezza non disponibile';
        const elevation=item.route.elevationAvailable!==false&&item.route.gainM>0?
          ' · +'+Math.round(item.route.gainM)+' m':'';
        const status=item.relation==='documented'?'Relazione verificata':
          item.relation==='endpoint_near'?'Estremità nei pressi della cima':
          item.relation==='passes_near'?'Passa vicino alla cima':
          (category.kind==='attrezzato'?'Percorso attrezzato nell’area':'Possibile ferrata nell’area')+
            ' · '+item.distanceM+' m dalla cima';
        return <a key={item.route.slug}
          className={technical?'cb-summit-route cb-summit-route--technical':'cb-summit-route'}
          href={routeDetailHref(item.route.slug,item.route.source)}>
          <span className="cb-summit-route-main">
            <strong>{trailTitle(item.route)}</strong>
            <small>{category.label} · {length}{elevation}</small>
          </span>
          <span className="cb-summit-route-extra">
            {technical&&<b className="cb-summit-technical-tag">{category.evidence==='inferred'?'TIPOLOGIA DA VERIFICARE':category.kind==='ferrata'?'FERRATA CENSITA':'PERCORSO ATTREZZATO'}</b>}
            <em>{mood.quip}</em>
            <small>{status}</small>
          </span>
        </a>;
      })}
    </div>
  </div>;
}

function SummitSupportRow({item}:{item:SummitSupportPlace}){
  const place=item.place;
  return <a href={alpinePlaceLink(place)} className="cb-summit-support-row">
    <span className="cb-summit-support-main">
      <strong>{place.name}</strong>
      <small>{place.kind==='bivacco'?'Bivacco':'Rifugio'}{place.elevationM?' · '+Math.round(place.elevationM).toLocaleString('it-IT')+' m':''}</small>
    </span>
    <span className="cb-summit-support-extra">
      <strong>{item.straightLineKm.toLocaleString('it-IT',{maximumFractionDigits:1})} km</strong>
      <small>{item.relation==='documented'?'Relazione d’accesso verificata':item.relation==='mapped_route'?'Segnalato presso una traccia mappata':'Distanza in linea d’aria'}</small>
    </span>
  </a>;
}
