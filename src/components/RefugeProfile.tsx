import type { ReactNode } from 'react';
import type { Route } from '../types';
import type { AlpinePlace } from '../lib/alpinePlaces';
import type { NearbyAtlasPlace } from '../lib/nearbyAtlas';
import type { AlpineWaterPoint } from '../lib/alpineWater';
import { WaterNearbyList } from './WaterNearbyList';
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
import { REFUGE_AMENITIES, refugeFact, refugeOverview } from '../lib/refugeEditorial';
import { BIVOUAC_AMENITIES, HUT_FACT_GROUP_LABELS, hutAliases, hutServiceFacts, shelterOverview } from '../lib/hutEditorial';
import { HutServices } from './HutServices';
import { trailTitle, trailMood } from '../lib/routeEditorial';
import { resolveRefugeTerritory } from '../lib/atlasConnections';
import './refugeProfile.css';

interface RefugeProfileProps {
  place: AlpinePlace;
  routes: Route[];
  loadingRoutes: boolean;
  nearbyPlaces: readonly NearbyAtlasPlace[];
  allPlaces: readonly AlpinePlace[];
  water: AlpineWaterPoint[];
  onWaterSelect:(slug:string)=>void;
}

const FACT_LABELS:Record<string,string>={
  bedsTotal:'Posti letto totali',capacityReported:'Capienza dichiarata',
  mattressAvailableReported:'Materassi',blanketAvailableReported:'Coperte',
  stoveAvailableReported:'Stufa',firewoodAvailableReported:'Legna',
  gasAvailableReported:'Gas',toiletAvailableReported:'Servizi igienici',
  heatingTypeReported:'Tipo di riscaldamento',waterSourceTypeReported:'Approvisionnement idrico',
  winterRoomReported:'Locale invernale',maintenanceProvider:'Ente manutentore',
  maintenanceCheckedAt:'Ultima manutenzione indicata',lastInspectionAt:'Ultimo controllo indicato',
  accessRestrictions:'Limitazioni d’accesso',reservationsRequired:'Prenotazione richiesta',
  usageRules:'Regole d’uso',keysRequired:'Chiavi necessarie',
  emergencyUseOnly:'Solo utilizzo d’emergenza',currentOpenStatus:'Stato attuale dichiarato',
  accessTrailRef:'Segnavia d’accesso',accessDifficultyOfficial:'Difficoltà d’accesso',
  accessDurationOfficial:'Tempo d’accesso',
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
  regionReported:'Regione indicata',provinceReported:'Provincia indicata',address:'Indirizzo censito',
  hospitalityRegistrationId:'Identificativo ricettivo',
  waterCertification:'Informazione sulle acque',
  caiCategory:'Classificazione nel catalogo CAI',
  caiCatalogueStatus:'Stato nel catalogo CAI (non stato di apertura)',
  elevationM:'Altitudine',
};
const STAY=['bedsTotal','capacityReported','bedsWinter','winterRoom','winterShelter','dormitories','largeDormitoriesAvailableReported','managerBeds'];
const OPEN=['openingHoursReported','openingHours','seasonality','openingStatus','accessRules'];
const SHELTER_STAY=['bedsTotal','capacityReported','bedsWinter','winterRoomReported','winterRoom','winterShelter'];
const SHELTER_RULES=['keysRequired','emergencyUseOnly','reservationsRequired','usageRules',
  'accessRestrictions','accessRules','openingHoursReported','openingHours','seasonality','openingStatus','currentOpenStatus'];
const SHELTER_MANAGER=['owner','owningSection','manager','operatorReported','selfManaged',
  'maintenanceProvider','maintenanceCheckedAt','lastInspectionAt'];
const MANAGEMENT=['manager','operatorReported','owner','owningSection','selfManaged'];
const PRICES=['nightlyPrice','halfBoardPrice','memberDiscount','priceValidUntil'];
const TERRITORY=['mountainGroupNameReported','municipalityNameReported','localityNameReported',
  'mountainGroupId','municipalityId','localityId','valleyName','protectedAreaName','regionReported','provinceReported','address'];
const HISTORY=['yearBuilt','yearRebuilt','yearOpened','dedication'];
const SPECIAL=['hospitalityRegistrationId','waterCertification','caiCategory','caiCatalogueStatus'];
const COVERED=new Set([
  ...STAY,...OPEN,...MANAGEMENT,...PRICES,...TERRITORY,...HISTORY,...SPECIAL,
  ...SHELTER_STAY,...SHELTER_RULES,...SHELTER_MANAGER,
  ...REFUGE_AMENITIES.map(s=>s.key),...BIVOUAC_AMENITIES.map(s=>s.key),
  'elevationM','phone','email','website','accessTrailRef','accessDifficultyOfficial',
  'accessDurationOfficial','description','address','bookingUrl','iso14001','aliases',
  'heatingTypeReported','waterSourceTypeReported',
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
const PROMINENT_FACTS=new Set(['bedsTotal','bedsWinter','capacityReported','nightlyPrice','halfBoardPrice']);
function FactLines({place,keys}:{place:AlpinePlace;keys:readonly string[]}){
  const facts=keys.map(key=>({key,fact:value(place,key)}))
    .filter((entry):entry is {key:string;fact:AtlasFact}=>entry.fact!==null);
  return facts.length?<dl className="cb-refuge-fact-list">
    {facts.map(({key,fact})=><div key={key}
      className={'cb-refuge-fact'+(PROMINENT_FACTS.has(key)&&typeof fact.value==='number'?' is-prominent':'')}>
      <dt>{FACT_LABELS[key]||fact.label||key}</dt>
      <dd>{formatAtlasFact(fact)}</dd>
    </div>)}
  </dl>:null;
}
function RefugeBlock({id,kicker,title,icon,children}:{id:string;kicker:string;title:string;icon?:FaIconName;children:ReactNode}){
  return <section id={id} className="cb-refuge-block cb-detail-group" aria-labelledby={id+'-title'}>
    <div className="cb-refuge-block-heading">
      {icon&&<span className="cb-refuge-block-icon"><FaIcon name={icon} size={20}/></span>}
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
export function RefugeProfile({place,routes,loadingRoutes,nearbyPlaces,allPlaces,water,onWaterSelect}:RefugeProfileProps){
  const isShelter=place.kind==='bivacco';
  const isRuralSupportPoint=isShelter&&place.subtype==='support_point';
  const facts=place.facts??{};
  const knownServices=hutServiceFacts(place);
  const territoryLinks=resolveRefugeTerritory(place,allPlaces);
  const aliases=hutAliases(place);
  const fullDescription=place.description?.trim();
  const displayKind=isShelter?(place.shelterTypeLabel||'Bivacco alpino'):'Rifugio alpino';
  const arrival=routes.filter(route=>(route.stops??[]).some(stop=>
    stop.slug===place.slug && ['arrivo','partenza'].includes(stop.relation)));
  const pass=routes.filter(route=>!arrival.includes(route) && (route.stops??[]).some(stop=>stop.slug===place.slug));
  const inArea=routes.filter(route=>!arrival.includes(route)&&!pass.includes(route));
  const booking=refugeFact(place,'bookingUrl');
  const bookingHref=typeof booking==='string'&&/^https:\/\//.test(booking)?booking:null;
  const hasStay=(isShelter?SHELTER_STAY:STAY).some(key=>value(place,key)!==null);
  const hasOpen=OPEN.some(key=>value(place,key)!==null);
  const hasRules=isShelter&&SHELTER_RULES.some(key=>value(place,key)!==null);
  const hasManager=(isShelter?SHELTER_MANAGER:MANAGEMENT).some(key=>value(place,key)!==null);
  const hasPrice=PRICES.some(key=>value(place,key)!==null)||Boolean(place.fee);
  const hasAccessDetails=isShelter&&['accessTrailRef','accessDifficultyOfficial','accessDurationOfficial'].some(key=>value(place,key)!==null);
  const hasTerritory=TERRITORY.some(key=>value(place,key)!==null);
  const hasHistory=HISTORY.some(key=>value(place,key)!==null)||Boolean(place.history&&place.historySourceUrl);
  const hasContact=Boolean(place.phone||place.email||place.website||bookingHref);
  const hasSpecial=SPECIAL.some(key=>value(place,key)!==null);
  const others=Object.fromEntries(Object.entries(facts)
    .filter(([key,entry])=>!COVERED.has(key)&&!/^iso\d+/i.test(key)&&entry?.value!==null&&entry?.value!==undefined)
    .map(([key,entry])=>[key,{...entry,label:FACT_LABELS[key]||entry.label,
      group:HUT_FACT_GROUP_LABELS[entry.group||'']||entry.group||'Ulteriori caratteristiche'}]));
  const extraRecord={...place,facts:others,aliases:[],localNames:[],history:undefined,historySourceUrl:undefined};
  const hasArchive=Boolean(hasSpecial||Object.keys(others).length||place.climate?.length||
    Object.values(place.administrativeHierarchy||{}).some(Boolean)||
    place.factsAlternatives?.length||place.technical||place.pitches?.length);
  const galleryLogo=place.media?.find(m=>m.kind==='logo'&&m.reuseAllowed&&m.subjectVerified&&m.url&&m.sourceUrl&&m.licence);
  const logo=place.logo?.url||galleryLogo?.url;
  const items:DetailJumpItem[]=[
    {id:'cb-refuge-stay',label:isShelter?'Utilizzo':'Ospitalità',icon:'bed'},
    ...(knownServices.length?[{id:'cb-refuge-services',label:'Servizi',icon:'wifi' as const}]:[]),
    ...(water.length?[{id:'cb-refuge-water',label:'Acqua',icon:'water' as const}]:[]),
    {id:'cb-refuge-access',label:'Sentieri',icon:'route'},
    ...(hasHistory||hasTerritory?[{id:'cb-refuge-story',label:isShelter?'Il luogo':'Il rifugio',icon:'book-open' as const}]:[]),
    {id:'cb-refuge-weather',label:'Meteo',icon:'compass'},
    ...(nearbyPlaces.length?[{id:'cb-place-nearby',label:'Dintorni',icon:'location-dot' as const}]:[]),
    {id:'cb-place-map',label:'Mappa',icon:'map'},
  ];
  const beds=refugeFact(place,'bedsTotal')??place.capacity;
  const elevation=refugeFact(place,'elevationM')??place.elevationM;

  return <div className={'cb-refuge-profile'+(isShelter?' cb-refuge-profile--bivacco':'')}>
    <header className="cb-refuge-hero">
      <div className="cb-refuge-hero-media">
        <RefugeGallery key={place.slug} place={place}/>
        <div className="cb-refuge-avatar">{logo?<img src={logo} alt={'Logo di '+place.name}/>:<AlpinePlaceIcon kind={place.kind} size={33}/>}</div>
      </div>
      <div className="cb-refuge-hero-info">
        <div className="cb-refuge-kicker"><AlpinePlaceIcon kind={place.kind} size={16}/> {displayKind.toLocaleUpperCase('it-IT')}</div>
        <h1>{place.name}</h1>
        {aliases.length>0&&<div className="cb-hut-aliases">
          <span>Conosciuto anche come</span>
          <p>{aliases.slice(0,3).map((item,i)=><span key={item.value}>
            {i>0?' · ':''}<strong>{item.value}</strong>
            {item.historical&&<em> nome storico</em>}
            {item.language&&<em> {item.language}</em>}
          </span>)}</p>
          {aliases.length>3&&<details><summary>Altre denominazioni ({aliases.length-3})</summary>
            <p>{aliases.slice(3).map(item=>item.value).join(' · ')}</p>
          </details>}
        </div>}
        <p className="cb-refuge-intro">{fullDescription||(isShelter?(place.shortSummary||shelterOverview(place)):refugeOverview(place))}</p>
        {isShelter&&<p className="cb-hut-safety-notice">{isRuralSupportPoint?
          "Malga e punto di ristoro, non struttura per il pernottamento ordinario. L'eventuale ricovero d'emergenza e i servizi stagionali non sono garantiti: verifica apertura e condizioni prima della salita.":
          "Ricovero non necessariamente custodito: accesso, dotazioni e utilizzabilità possono cambiare. Verifica prima della salita."}</p>}
        <DetailMetrics label="Riepilogo della struttura" items={[
          ...(typeof elevation==='number'&&elevation>0?[{label:'Quota dichiarata',value:elevation.toLocaleString('it-IT')+' m'}]:[]),
          ...(typeof beds==='number'&&beds>0?[{label:isShelter?'Posti indicati':'Posti letto indicati',value:beds}]:[]),
          ...(typeof refugeFact(place,'bedsWinter')==='number'&&Number(refugeFact(place,'bedsWinter'))>0
            ?[{label:'Posti invernali',value:Number(refugeFact(place,'bedsWinter'))}]:[]),
        ]}/>
        <div className="cb-refuge-actions">
          {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')} className="cb-refuge-action-primary"><FaIcon name="phone" size={15}/> Chiama</a>}
          {!isShelter&&bookingHref&&<a href={bookingHref} target="_blank" rel="noopener noreferrer" className="cb-refuge-action-primary"><FaIcon name="calendar-days" size={15}/> Prenota</a>}
          {place.website&&/^https:\/\//.test(place.website)&&<a href={place.website} target="_blank" rel="noopener noreferrer"><FaIcon name="globe" size={15}/> Sito ufficiale</a>}
          <button type="button" onClick={()=>scrollToDetailSection('cb-place-map')}><FaIcon name="map" size={15}/> Mappa</button>
        </div>

      </div>
    </header>
    <AtlasDossierBlocks record={place} placement="alerts"/>
    <DetailJumpNav items={items}/>
    <RefugeBlock id="cb-refuge-stay" kicker="PRIMA DI SALIRE"
      title={isRuralSupportPoint?'Malga: accesso, ristoro e uso d’emergenza':isShelter?'Accesso, capienza e regole d’uso':'Ospitalità e informazioni pratiche'} icon={isShelter?'tent':'bed'}>
      {isRuralSupportPoint&&<p className="cb-refuge-disclaimer">Ristoro stagionale documentato, ma operatività attuale non verificata. Non utilizzare questa scheda per programmare un pernottamento o presumere la disponibilità di un ricovero.</p>}
      {isShelter&&hasRules&&<div className="cb-refuge-subsection"><h3>Regole e accesso</h3>
        <FactLines place={place} keys={SHELTER_RULES}/></div>}
      {!isShelter&&hasOpen&&<div className="cb-refuge-subsection"><h3><FaIcon name="clock" size={14}/> Apertura dichiarata</h3>
        <FactLines place={place} keys={OPEN}/><p className="cb-refuge-disclaimer">Gli orari pubblicati non indicano l'apertura in tempo reale.</p></div>}
      {hasStay&&<div className="cb-refuge-subsection"><h3><FaIcon name="bed" size={14}/> {isShelter?'Posti e ricovero':'Pernottamento e capienza'}</h3>
        <FactLines place={place} keys={isShelter?SHELTER_STAY:STAY}/></div>}
      {hasPrice&&<div className="cb-refuge-subsection"><h3><FaIcon name="coins" size={14}/> Tariffe</h3>
        <FactLines place={place} keys={PRICES}/>
        {place.fee&&!PRICES.some(key=>value(place,key)!==null)&&<p>Tariffa indicata: {place.fee}</p>}
        <p className="cb-refuge-disclaimer">Verifica importi e disponibilità prima di prenotare.</p></div>}
      {(hasContact||hasManager)&&<div className="cb-refuge-subsection"><h3><FaIcon name="phone" size={14}/> {isShelter?'Riferimenti e manutenzione':'Contatti e gestione'}</h3>
        {hasContact&&<div className="cb-refuge-contact-links">
          {place.phone&&<a href={'tel:'+place.phone.replace(/[^+\d]/g,'')}><FaIcon name="phone" size={13}/>{place.phone}</a>}
          {place.email&&<a href={'mailto:'+place.email}><FaIcon name="envelope" size={13}/>{place.email}</a>}
          {place.website&&/^https:\/\//.test(place.website)&&<a href={place.website} target="_blank" rel="noopener noreferrer"><FaIcon name="globe" size={13}/>Sito web</a>}
          {!isShelter&&bookingHref&&<a href={bookingHref} target="_blank" rel="noopener noreferrer"><FaIcon name="calendar-days" size={13}/>Prenotazione ufficiale</a>}
        </div>}
        {hasManager&&<FactLines place={place} keys={isShelter?SHELTER_MANAGER:MANAGEMENT}/>}</div>}
      {!hasStay&&!hasOpen&&!hasRules&&!hasContact&&!hasManager&&!hasPrice&&
        <p className="cb-refuge-disclaimer">Informazioni pratiche non ancora disponibili. Verifica accesso e condizioni prima di salire.</p>}
    </RefugeBlock>
    {knownServices.length>0&&<RefugeBlock id="cb-refuge-services" kicker={isShelter?'DENTRO IL RICOVERO':'VITA IN RIFUGIO'}
      title={isShelter?'Dotazioni del bivacco':'Cosa trovi una volta arrivato'}>
      <HutServices place={place}/>
      {isShelter&&['heatingTypeReported','waterSourceTypeReported'].some(key=>value(place,key)!==null)&&
        <div className="cb-hut-extra-features"><h3>Caratteristiche delle dotazioni</h3>
          <FactLines place={place} keys={['heatingTypeReported','waterSourceTypeReported']}/>
        </div>}
    </RefugeBlock>}
    <RefugeBlock id="cb-refuge-access" kicker="NEL TERRITORIO" title="Come arrivare e sentieri" icon="person-hiking">
      {place.access&&<p className="cb-refuge-section-intro"><strong>Accesso:</strong> {place.access}</p>}
      {hasAccessDetails&&<FactLines place={place} keys={['accessTrailRef','accessDifficultyOfficial','accessDurationOfficial']}/>}
      {arrival.length>0&&<div className="cb-refuge-route-list"><h3>Itinerari con relazione di partenza o arrivo</h3>{arrival.slice(0,12).map(route=><RouteLine key={route.slug} route={route}/>)}</div>}
      {pass.length>0&&<div className="cb-refuge-route-list"><h3>Altri itinerari collegati al luogo</h3>{pass.slice(0,8).map(route=><RouteLine key={route.slug} route={route}/>)}</div>}
      {inArea.length>0&&<details className="cb-refuge-more"><summary>Tracce vicine (non accessi verificati) · {inArea.length}</summary>
        <div className="cb-refuge-route-list">{inArea.slice(0,14).map(route=><RouteLine key={route.slug} route={route}/>)}</div></details>}
      {loadingRoutes&&<p className="cb-refuge-disclaimer">Caricamento dei percorsi cartografati…</p>}
      {!loadingRoutes&&!routes.length&&<p className="cb-refuge-disclaimer">Nessuna traccia indicizzata nelle immediate vicinanze; questo non significa che non esistano sentieri di accesso.</p>}
      <p className="cb-refuge-disclaimer">La vicinanza al tracciato non dimostra un accesso diretto né la percorribilità.</p>
      <button type="button" className="cb-refuge-map-link" onClick={()=>scrollToDetailSection('cb-place-map')}><FaIcon name="map" size={14}/> Vedi sulla mappa</button>
    </RefugeBlock>
    {(hasTerritory||hasHistory)&&<RefugeBlock id="cb-refuge-story" kicker="LUOGHI, NOMI E MEMORIA"
      title={isShelter?'Il bivacco e il suo territorio':'Un rifugio, un territorio'}>
      {territoryLinks.length>0&&<aside className="cb-refuge-territory-feature">
        <span>{isShelter?'IL BIVACCO E I LUOGHI INTORNO':'IL RIFUGIO E I LUOGHI INTORNO'}</span>
        <p>{territoryLinks.map((item,index)=><span key={item.key}>
          {index>0?' · ':''}{item.label}: {item.href?
            <a href={item.href}>{item.name} <FaIcon name="arrow-up-right-from-square" size={11}/></a>:
            <strong>{item.name}</strong>}
        </span>)}</p>
      </aside>}
      {hasTerritory&&<div className="cb-refuge-territory-details">
        <h3>Geografia e toponimi</h3>
        <FactLines place={place} keys={TERRITORY.filter(key=>!territoryLinks.some(item=>item.key===key))}/>
      </div>}
      {hasHistory&&<div className="cb-refuge-history-feature">
        {value(place,'yearBuilt')&&<div className="cb-refuge-history-date"><small>ANNO DI COSTRUZIONE DICHIARATO</small>
          <strong>{formatAtlasFact(value(place,'yearBuilt')!)}</strong></div>}
        <div><h3>Storia documentata</h3>
          <FactLines place={place} keys={HISTORY.filter(key=>key!=='yearBuilt'||!value(place,'yearBuilt'))}/>
          {place.history&&place.historySourceUrl&&<><p className="cb-refuge-editorial">{place.history}</p></>}
        </div>
      </div>}
    </RefugeBlock>}
    <RefugeBlock id="cb-refuge-weather" kicker="CONDIZIONI DEL TERRITORIO" title="Meteo e montagna">
      <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>
    </RefugeBlock>
    {water.length>0&&<RefugeBlock id="cb-refuge-water" kicker="PUNTI CARTOGRAFATI" title="Acqua nei dintorni">
      <WaterNearbyList points={water} onSelect={onWaterSelect}/>
    </RefugeBlock>}
    <NearbyAtlasPlaces items={nearbyPlaces}/>
    <AtlasDossierBlocks record={place} placement="connections"/>
    {hasArchive&&<section id="cb-refuge-archive" className="cb-refuge-archive cb-detail-group">
      <details>
        <summary><span>Altre informazioni</span><small>Geografia, caratteristiche tecniche e dati aggiuntivi</small></summary>
        <div className="cb-hut-archive-contents">
          {hasSpecial&&<section className="cb-hut-archive-category"><h3>Codici e classificazioni</h3>
            <FactLines place={place} keys={SPECIAL}/></section>}
          <AtlasDossierBlocks record={extraRecord} placement="core"/>
        </div>
      </details>
    </section>}
    <AtlasDossierBlocks record={place} placement="media" excludeImages/>
    {!isShelter&&<RefugeBlock id="cb-refuge-community" kicker="CIMA BECCO / COMMUNITY" title="Conosci questo rifugio?">
      <p>Se rappresenti la struttura, puoi richiedere la gestione della scheda e proporre aggiornamenti.</p>
      <HutClaimRequest place={place}/>
    </RefugeBlock>}
    <div className="cb-refuge-credits">
      <p>Informazioni documentate e soggette ad aggiornamento. Apertura, disponibilità e condizioni dei sentieri vanno verificate prima di partire.</p>
      <a href={import.meta.env.BASE_URL+'fonti-e-crediti/'}>Fonti e crediti del progetto</a>
    </div>
  </div>;
}
