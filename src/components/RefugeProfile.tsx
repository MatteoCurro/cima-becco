import type { ReactNode } from 'react';
import type { Route } from '../types';
import type { AlpinePlace } from '../lib/alpinePlaces';
import type { NearbyAtlasPlace } from '../lib/nearbyAtlas';
import type { AlpineWaterPoint } from '../lib/alpineWater';
import { potabilityLabel } from '../lib/alpineWater';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { AlpineWeatherPanel } from './AlpineWeatherPanel';
import { DetailJumpNav, type DetailJumpItem } from './DetailJumpNav';
import { DetailMetrics } from './DetailPrimitives';
import { FaIcon, type FaIconName } from './FaIcon';
import { RefugeGallery } from './RefugeGallery';
import { NearbyAtlasPlaces } from './NearbyAtlasPlaces';
import { HutClaimRequest } from './HutClaimRequest';
import { scrollToDetailSection } from '../lib/detailNavigation';
import { formatAtlasFact, type AtlasFact } from '../lib/atlasDossier';
import { REFUGE_AMENITIES, refugeFact, refugeOverview, refugeServiceFacts } from '../lib/refugeEditorial';
import { trailTitle, trailMood } from '../lib/routeEditorial';
import './refugeProfile.css';

interface RefugeProfileProps {
  place: AlpinePlace;
  routes: Route[];
  loadingRoutes: boolean;
  nearbyPlaces: readonly NearbyAtlasPlace[];
  water: AlpineWaterPoint[];
}

const AMENITY_ICONS:Record<string,FaIconName>={
  meals:'utensils',wifi:'wifi',showers:'shower',cardPayments:'credit-card',
  electricity:'bolt',kitchen:'utensils',pets:'paw',accessibility:'wheelchair',
  defibrillator:'heart-pulse',waterAvailableReported:'glass-water',drinkingWater:'glass-water',
  hotWater:'shower',mobileSignal:'signal',accessibleToilets:'toilet',
  outsideWater:'water',sleepingBagLiner:'bed',solarPower:'leaf',
  hydropower:'water',generatorPower:'bolt',
};
const FACT_LABELS:Record<string,string>={
  bedsTotal:'Posti letto totali',capacityReported:'Capienza dichiarata',
  bedsWinter:'Posti letto invernali',winterShelter:'Ricovero invernale',
  dormitories:'Camerate',largeDormitoriesAvailableReported:'Camerate con più di 4 posti',
  managerBeds:'Posti riservati al gestore',
  openingStatus:'Stato di apertura dichiarato (non in tempo reale)',
  openingHoursReported:'Orari dichiarati',openingHours:'Orari',seasonality:'Periodo di apertura',
  winterRoom:'Locale invernale',accessRules:'Condizioni di accesso',
  owner:'Proprietà',owningSection:'Sezione proprietaria',manager:'Gestione',
  operatorReported:'Gestore dichiarato',selfManaged:'Autogestione',
  nightlyPrice:'Pernottamento',halfBoardPrice:'Mezza pensione',
  memberDiscount:'Agevolazioni soci',priceValidUntil:'Prezzi validi fino a',
  yearBuilt:'Anno di costruzione',yearRebuilt:'Anno di ricostruzione',
  yearOpened:'Anno di apertura',dedication:'Intitolazione',
  mountainGroupId:'Gruppo montuoso indicato',municipalityId:'Comune indicato',
  localityId:'Località indicata',
  mountainGroupNameReported:'Gruppo montuoso dichiarato',
  municipalityNameReported:'Comune dichiarato',localityNameReported:'Località dichiarata',
  valleyName:'Valle',protectedAreaName:'Area protetta',
  regionReported:'Regione indicata',provinceReported:'Provincia indicata',
  hospitalityRegistrationId:'Identificativo ricettivo',
  iso14001:'Certificazione ISO 14001',waterCertification:'Certificazione delle acque',
  caiCategory:'Classificazione nel catalogo CAI',
  caiCatalogueStatus:'Stato nel catalogo CAI (non stato di apertura)',
  elevationM:'Altitudine',
};
const STAY=['bedsTotal','capacityReported','bedsWinter','winterRoom','winterShelter','dormitories','largeDormitoriesAvailableReported','managerBeds'];
const OPEN=['openingHoursReported','openingHours','seasonality','openingStatus','accessRules'];
const MANAGEMENT=['manager','operatorReported','owner','owningSection','selfManaged'];
const PRICES=['nightlyPrice','halfBoardPrice','memberDiscount','priceValidUntil'];
const TERRITORY=['mountainGroupNameReported','municipalityNameReported','localityNameReported',
  'mountainGroupId','municipalityId','localityId','valleyName','protectedAreaName','regionReported','provinceReported'];
const HISTORY=['yearBuilt','yearRebuilt','yearOpened','dedication'];
const SPECIAL=['hospitalityRegistrationId','iso14001','waterCertification','caiCategory','caiCatalogueStatus'];
const COVERED=new Set([
  ...STAY,...OPEN,...MANAGEMENT,...PRICES,...TERRITORY,...HISTORY,...SPECIAL,
  ...REFUGE_AMENITIES.map(s=>s.key), 'elevationM','phone','email','website',
  'description','address','bookingUrl',
]);

function value(place:AlpinePlace,key:string):AtlasFact|null{
  const fact=place.facts?.[key];
  if(fact && fact.value!==null && fact.value!==undefined && fact.value!=='')return fact;
  const legacy:Record<string,string|number|undefined>={
    winterRoom:place.winterRoom,seasonality:place.seasonal,accessRules:place.access,
    openingHours:place.openingHours,address:place.address,
    bedsTotal:place.capacity,manager:place.operator,
  };
  const val=legacy[key];
  return val===undefined||val===null||val===''?null:{value:val,method:'reported'};
}
function FactLines({place,keys}:{place:AlpinePlace;keys:readonly string[]}){
  const facts=keys.map(key=>({key,fact:value(place,key)})).filter((entry):entry is {key:string;fact:AtlasFact}=>entry.fact!==null);
  return facts.length?<dl className="cb-refuge-fact-list">
    {facts.map(({key,fact})=><div key={key}>
      <dt>{FACT_LABELS[key]||fact.label||key}</dt>
      <dd>{formatAtlasFact(fact)}
        {(fact.sourceUpdatedAt||fact.validUntil||fact.method==='estimated')&&<small>
          {[fact.method==='estimated'?'Stima':null,fact.sourceUpdatedAt?'Fonte aggiornata: '+fact.sourceUpdatedAt:null,
          fact.validUntil?'Valido fino al: '+fact.validUntil:null].filter(Boolean).join(' · ')}</small>}
        {fact.sourceUrl&&/^https:\/\//.test(fact.sourceUrl)&&<a href={fact.sourceUrl}
          target="_blank" rel="noopener noreferrer" aria-label={'Fonte per '+(FACT_LABELS[key]||key)}>
          <FaIcon name="arrow-up-right-from-square" size={10}/> Fonte</a>}
      </dd>
    </div>)}
  </dl>:null;
}
function RefugeBlock({id,kicker,title,icon,children}:{id:string;kicker:string;title:string;icon:FaIconName;children:ReactNode}){
  return <section id={id} className="cb-refuge-block cb-detail-group" aria-labelledby={id+'-title'}>
    <div className="cb-refuge-block-heading">
      <span className="cb-refuge-block-icon"><FaIcon name={icon} size={20}/></span>
      <div><span>{kicker}</span><h2 id={id+'-title'}>{title}</h2></div>
    </div>
    {children}
  </section>;
}
function RouteLine({route}:{route:Route}){
  const mood=trailMood(route);
  return <a className="cb-refuge-route" href={`${import.meta.env.BASE_URL}route/${encodeURIComponent(route.slug)}/`}>
    <FaIcon name="route" size={17}/>
    <span><strong>{trailTitle(route)}</strong><small>{(route.distanceM/1000).toLocaleString('it-IT',{maximumFractionDigits:1})} km · {mood.label}</small></span>
    <FaIcon name="arrow-right" size={13}/>
  </a>;
}
function SourceLink({url,children}:{url?:string;children:ReactNode}){
  return url && /^https:\/\//.test(url)?<a href={url} target="_blank" rel="noopener noreferrer">{children}</a>:null;
}

export function RefugeProfile({place,routes,loadingRoutes,nearbyPlaces,water}:RefugeProfileProps){
  const facts=place.facts??{};
  const knownServices=refugeServiceFacts(place);
  const arrival=routes.filter(route=>(route.stops??[]).some(stop=>
    stop.slug===place.slug && ['arrivo','partenza'].includes(stop.relation)));
  const pass=routes.filter(route=>!arrival.includes(route) && (route.stops??[]).some(stop=>stop.slug===place.slug));
  const inArea=routes.filter(route=>!arrival.includes(route)&&!pass.includes(route));
  const booking=refugeFact(place,'bookingUrl');
  const bookingHref=typeof booking==='string'&&/^https:\/\//.test(booking)?booking:null;
  const hasStay=STAY.some(key=>value(place,key)!==null);
  const hasOpen=OPEN.some(key=>value(place,key)!==null);
  const hasManager=MANAGEMENT.some(key=>value(place,key)!==null);
  const hasPrice=PRICES.some(key=>value(place,key)!==null)||Boolean(place.fee);
  const hasTerritory=TERRITORY.some(key=>value(place,key)!==null);
  const hasHistory=HISTORY.some(key=>value(place,key)!==null)||Boolean(place.history&&place.historySourceUrl);
  const hasContact=Boolean(place.phone||place.email||place.website||bookingHref);
  const hasSpecial=SPECIAL.some(key=>value(place,key)!==null);
  const others=Object.fromEntries(Object.entries(facts).filter(([key,entry])=>!COVERED.has(key)&&entry?.value!==null&&entry?.value!==undefined));
  const extraRecord={...place,facts:others,history:undefined,historySourceUrl:undefined};
  const galleryLogo=place.media?.find(m=>m.kind==='logo'&&m.reuseAllowed&&m.subjectVerified&&m.url&&m.sourceUrl&&m.licence);
  const logo=place.logo?.url||galleryLogo?.url;
  const official=place.officialUrl||(place.sourceIds?.cai?'https://rifugi.cai.it/shelters/'+place.sourceIds.cai:undefined);
  const items:DetailJumpItem[]=[
    {id:'cb-refuge-stay',label:'Ospitalità',icon:'bed'},
    ...(knownServices.length?[{id:'cb-refuge-services',label:'Servizi',icon:'wifi' as const}]:[]),
    {id:'cb-refuge-access',label:'Sentieri',icon:'route'},
    ...(place.description||hasHistory||hasTerritory?[{id:'cb-refuge-story',label:'Il rifugio',icon:'book-open' as const}]:[]),
    {id:'cb-refuge-weather',label:'Meteo',icon:'compass'},
    ...(nearbyPlaces.length?[{id:'cb-place-nearby',label:'Dintorni',icon:'location-dot' as const}]:[]),
    {id:'cb-place-map',label:'Mappa',icon:'map'},
  ];
  const beds=refugeFact(place,'bedsTotal')??place.capacity;
  const elevation=refugeFact(place,'elevationM')??place.elevationM;

  return <div className="cb-refuge-profile">
    <header className="cb-refuge-hero">
      <div className="cb-refuge-hero-media">
        <RefugeGallery key={place.slug} place={place}/>
        <div className="cb-refuge-avatar">{logo?<img src={logo} alt={'Logo di '+place.name}/>:<AlpinePlaceIcon kind="rifugio" size={33}/>}</div>
      </div>
      <div className="cb-refuge-hero-info">
        <div className="cb-refuge-kicker"><AlpinePlaceIcon kind="rifugio" size={16}/> RIFUGIO ALPINO
          {place.sourceIds?.cai&&<span> · SCHEDA CAI</span>}</div>
        <h1>{place.name}</h1>
        <p className="cb-refuge-intro">{refugeOverview(place)}</p>
        <DetailMetrics label="Riepilogo del rifugio" items={[
          ...(typeof elevation==='number'&&elevation>0?[{label:'Quota dichiarata',value:elevation.toLocaleString('it-IT')+' m'}]:[]),
          ...(typeof beds==='number'&&beds>0?[{label:'Posti letto indicati',value:beds}]:[]),
          ...(typeof refugeFact(place,'bedsWinter')==='number'&&Number(refugeFact(place,'bedsWinter'))>0
            ?[{label:'Posti invernali',value:Number(refugeFact(place,'bedsWinter'))}]:[]),
        ]}/>
        <div className="cb-refuge-actions">
          {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')} className="cb-refuge-action-primary"><FaIcon name="phone" size={15}/> Chiama</a>}
          {bookingHref&&<a href={bookingHref} target="_blank" rel="noopener noreferrer" className="cb-refuge-action-primary"><FaIcon name="calendar-days" size={15}/> Prenota</a>}
          {place.website&&/^https:\/\//.test(place.website)&&<a href={place.website} target="_blank" rel="noopener noreferrer"><FaIcon name="globe" size={15}/> Sito ufficiale</a>}
          <button type="button" onClick={()=>scrollToDetailSection('cb-place-map')}><FaIcon name="map" size={15}/> Mappa</button>
        </div>
        {(place.sourceIds?.cai||place.checkedAt)&&<p className="cb-refuge-source-label">
          {place.sourceIds?.cai?'Dati del rifugio integrati dal catalogo CAI. ':''}
          {place.checkedAt?'Ultima verifica indicata: '+place.checkedAt: 'Apertura, disponibilità e condizioni vanno verificate prima della visita.'}
        </p>}
      </div>
    </header>
    <AtlasDossierBlocks record={place} placement="alerts"/>
    <DetailJumpNav items={items}/>
    <RefugeBlock id="cb-refuge-stay" kicker="PRIMA DI SALIRE" title="Ospitalità e informazioni pratiche" icon="bed">
      {hasOpen&&<div className="cb-refuge-subsection"><h3><FaIcon name="clock" size={14}/> Apertura dichiarata</h3>
        <FactLines place={place} keys={OPEN}/><p className="cb-refuge-disclaimer">La presenza di orari nel catalogo non certifica che il rifugio sia aperto oggi.</p></div>}
      {hasStay&&<div className="cb-refuge-subsection"><h3><FaIcon name="bed" size={14}/> Pernottamento e capienza</h3>
        <FactLines place={place} keys={STAY}/></div>}
      {hasPrice&&<div className="cb-refuge-subsection"><h3><FaIcon name="coins" size={14}/> Tariffe dichiarate</h3>
        <FactLines place={place} keys={PRICES}/>
        {place.fee&&!PRICES.some(key=>value(place,key)!==null)&&<p>Indicazione tariffaria OSM: {place.fee}</p>}
        <p className="cb-refuge-disclaimer">Verifica importi, disponibilità e validità con il gestore prima di prenotare.</p></div>}
      {(hasContact||hasManager)&&<div className="cb-refuge-subsection"><h3><FaIcon name="phone" size={14}/> Contatti e gestione</h3>
        {hasContact&&<div className="cb-refuge-contact-links">
          {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')}><FaIcon name="phone" size={13}/>{place.phone}</a>}
          {place.email&&<a href={'mailto:'+place.email}><FaIcon name="envelope" size={13}/>{place.email}</a>}
          {place.website&&/^https:\/\//.test(place.website)&&<a href={place.website} target="_blank" rel="noopener noreferrer"><FaIcon name="globe" size={13}/>Sito web</a>}
          {bookingHref&&<a href={bookingHref} target="_blank" rel="noopener noreferrer"><FaIcon name="calendar-days" size={13}/>Prenotazione ufficiale</a>}
        </div>}
        {hasManager&&<FactLines place={place} keys={MANAGEMENT}/>}</div>}
      {!hasStay&&!hasOpen&&!hasContact&&!hasManager&&!hasPrice&&
        <p className="cb-refuge-disclaimer">Le informazioni pratiche non sono ancora documentate. Consulta la scheda della fonte o contatta direttamente la struttura prima di partire.</p>}
      <SourceLink url={official}>Consulta la scheda del rifugio nel catalogo CAI</SourceLink>
    </RefugeBlock>
    {knownServices.length>0&&<RefugeBlock id="cb-refuge-services" kicker="DOTAZIONI DICHIARATE" title="Servizi disponibili" icon="utensils">
      <p className="cb-refuge-section-intro">Le dotazioni riportano il valore comunicato dalla fonte, non una verifica effettuata oggi. I servizi senza dato non vengono considerati assenti.</p>
      <div className="cb-refuge-service-grid">
        {knownServices.map(item=><div key={item.key} className={'cb-refuge-service '+(item.value?'is-yes':'is-no')}>
          <span className="cb-refuge-service-icon"><FaIcon name={AMENITY_ICONS[item.key]||'circle-question'} size={19}/></span>
          <span><strong>{item.label}</strong><small>{item.value?'Dichiarato presente':'Dichiarato non presente'}</small></span>
          <FaIcon name={item.value?'circle-check':'circle-xmark'} size={14}/>
        </div>)}
      </div>
      <p className="cb-refuge-disclaimer">Acqua disponibile non equivale ad acqua potabile: la potabilità richiede un'informazione specifica.</p>
    </RefugeBlock>}
    <RefugeBlock id="cb-refuge-access" kicker="NEL TERRITORIO" title="Come arrivare e sentieri" icon="person-hiking">
      {place.access&&<p className="cb-refuge-section-intro"><strong>Accesso riportato dalla fonte:</strong> {place.access}</p>}
      {arrival.length>0&&<div className="cb-refuge-route-list"><h3>Itinerari con relazione di partenza o arrivo</h3>{arrival.slice(0,12).map(route=><RouteLine key={route.slug} route={route}/>)}</div>}
      {pass.length>0&&<div className="cb-refuge-route-list"><h3>Altri itinerari collegati al luogo</h3>{pass.slice(0,8).map(route=><RouteLine key={route.slug} route={route}/>)}</div>}
      {inArea.length>0&&<details className="cb-refuge-more"><summary>Tracce vicine (non accessi verificati) · {inArea.length}</summary>
        <div className="cb-refuge-route-list">{inArea.slice(0,14).map(route=><RouteLine key={route.slug} route={route}/>)}</div></details>}
      {loadingRoutes&&<p className="cb-refuge-disclaimer">Caricamento dei percorsi cartografati…</p>}
      {!loadingRoutes&&!routes.length&&<p className="cb-refuge-disclaimer">Nessuna traccia indicizzata nelle immediate vicinanze; questo non significa che non esistano sentieri di accesso.</p>}
      <p className="cb-refuge-disclaimer">La vicinanza a una traccia GPX non certifica che il sentiero conduca al rifugio né che sia percorribile.</p>
      <button type="button" className="cb-refuge-map-link" onClick={()=>scrollToDetailSection('cb-place-map')}><FaIcon name="map" size={14}/> Vedi il rifugio sulla mappa</button>
    </RefugeBlock>
    {(place.description||hasTerritory||hasHistory)&&<RefugeBlock id="cb-refuge-story" kicker="IDENTITÀ E TERRITORIO" title="Il rifugio, la storia e il paesaggio" icon="book-open">
      {place.description&&<p className="cb-refuge-editorial">{place.description}</p>}
      {hasTerritory&&<FactLines place={place} keys={TERRITORY}/>}
      {hasHistory&&<div className="cb-refuge-subsection"><h3>Storia documentata</h3>
        <FactLines place={place} keys={HISTORY}/>
        {place.history&&place.historySourceUrl&&<><p className="cb-refuge-editorial">{place.history}</p>
          <SourceLink url={place.historySourceUrl}>Fonte dell'approfondimento storico</SourceLink></>}</div>}
    </RefugeBlock>}
    <RefugeBlock id="cb-refuge-weather" kicker="CONDIZIONI DEL TERRITORIO" title="Meteo e montagna" icon="compass">
      <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>
    </RefugeBlock>
    {water.length>0&&<RefugeBlock id="cb-refuge-water" kicker="PUNTI CARTOGRAFATI" title="Acqua nei dintorni" icon="water">
      <div className="cb-refuge-water-list">{water.slice(0,8).map(item=><div key={item.slug}>
        <FaIcon name="water" size={17}/><span><strong>{item.name}</strong><small>{item.kind} · {potabilityLabel(item.potable)}{item.seasonal?' · stagionale':''}</small></span>
      </div>)}</div>
      <p className="cb-refuge-disclaimer">Distanze e presenza sulla mappa non garantiscono accessibilità, disponibilità o potabilità.</p>
    </RefugeBlock>}
    <NearbyAtlasPlaces items={nearbyPlaces}/>
    <AtlasDossierBlocks record={place} placement="connections"/>
    {(hasSpecial||Object.keys(others).length>0||place.climate?.length||place.aliases?.length||place.administrativeHierarchy)&&
      <RefugeBlock id="cb-refuge-archive" kicker="ATLANTE / DATI E PROVENIENZA" title="Altri dati documentati" icon="book-open">
        {hasSpecial&&<FactLines place={place} keys={SPECIAL}/>}
        <AtlasDossierBlocks record={extraRecord} placement="core"/>
      </RefugeBlock>}
    <AtlasDossierBlocks record={place} placement="media" excludeImages/>
    <RefugeBlock id="cb-refuge-community" kicker="CIMA BECCO / COMMUNITY" title="Conosci questo rifugio?" icon="house">
      <p>Se rappresenti la struttura, puoi richiedere la gestione della scheda e proporre informazioni aggiornate. Non mostriamo recensioni o valutazioni inventate.</p>
      <HutClaimRequest place={place}/>
    </RefugeBlock>
    <div className="cb-refuge-credits">
      <AtlasDossierBlocks record={place} placement="credits"/>
      {place.sourceIds?.cai&&<p>Archivio CAI · <SourceLink url={official}>Unico Rifugi</SourceLink></p>}
      {place.sourceIds?.osm&&<p>Informazioni OpenStreetMap · <SourceLink url={place.osmUrl}>ODbL</SourceLink></p>}
      <p>La scheda riporta informazioni raccolte da fonti documentate. Apertura, condizioni del terreno e disponibilità possono cambiare.</p>
    </div>
  </div>;
}
