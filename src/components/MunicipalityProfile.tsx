import type { Route } from '../types';
import type { AlpinePlace } from '../lib/alpinePlaces';
import type { NearbyAtlasPlace } from '../lib/nearbyAtlas';
import type { AlpineWaterPoint } from '../lib/alpineWater';
import type { AtlasPersonConnection } from '../lib/atlasDossier';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { AlpinePlaceVisual } from './AlpinePlaceVisual';
import { AlpineWeatherPanel } from './AlpineWeatherPanel';
import { AtlasRouteGroup } from './AtlasRouteGroup';
import { DetailFacts,DetailMetrics,DetailSectionHeading } from './DetailPrimitives';
import { DetailJumpNav } from './DetailJumpNav';
import { NearbyAtlasPlaces } from './NearbyAtlasPlaces';
import { WaterNearbyList } from './WaterNearbyList';
import { FaIcon } from './FaIcon';
import { scrollToDetailSection } from '../lib/detailNavigation';
import { municipalityArchiveFacts,municipalityNumber,municipalityText,municipalityDisplayDate } from '../lib/municipalityPresentation';
import './municipalityProfile.css';

type RouteGroups={departures:Route[];arrivals:Route[];passes:Route[];around:Route[]};
interface Props {
  place:AlpinePlace;
  routeGroups:RouteGroups;
  loadingRoutes:boolean;
  nearbyPlaces:readonly NearbyAtlasPlace[];
  water:AlpineWaterPoint[];
  selectedWaterSlug:string|null;
  onWaterSelect:(slug:string)=>void;
}
function PersonCards({people,title}:{people:AtlasPersonConnection[];title:string}){
  if(!people.length)return null;
  return <div className="cb-municipality-people-group">
    <h3>{title} <span>{people.length}</span></h3>
    <div className="cb-person-grid">{people.map(person=><article
      className="cb-person-card" key={person.personId+':'+person.relationType}>
      <div className="cb-person-card-top">
        <span>{person.category==='montagna'?'ALPINISMO E MONTAGNA':'CULTURA E RICERCA'}</span>
        <span>{person.relationType==='birthplace_of'?'NATA/O QUI':
          person.relationType==='historical_residence_of'?'RESIDENZA STORICA':'ATTIVITÀ DOCUMENTATA'}</span>
      </div>
      {person.portrait?.url&&person.portrait.portraitCandidate&&person.portrait.subjectVerified&&
        person.portrait.reuseAllowed&&<img className="cb-person-portrait" src={person.portrait.url}
          alt={'Immagine attribuita a '+person.name} loading="lazy" decoding="async"/>}
      <h4>{person.name}</h4>
      <p className="cb-person-role">{person.role}</p>
      {(person.birthDate||person.deathDate)&&<p className="cb-person-dates">
        {person.birthDate?.slice(0,4)||'—'}{person.deathDate?' – '+person.deathDate.slice(0,4):''}
      </p>}
      {(person.biography||person.description)&&<p>{(person.biography||person.description)?.slice(0,320)}</p>}
      {person.wikipediaUrl?.startsWith('https://')&&<a href={person.wikipediaUrl}
        target="_blank" rel="noopener noreferrer">Approfondimento biografico ↗</a>}
    </article>)}</div>
  </div>;
}
export function MunicipalityProfile({place,routeGroups,loadingRoutes,nearbyPlaces,water,
  selectedWaterSlug,onWaterSelect}:Props){
  const n=(key:string)=>municipalityNumber(place,key);
  const t=(key:string)=>municipalityText(place,key);
  const region=place.administrativeHierarchy?.region;
  const province=place.administrativeHierarchy?.province;
  const centre=n('quotaCentroM');
  const reported=n('elevationReportedM');
  const minimum=n('altitudineTerritorioMinM');
  const maximum=n('altitudineTerritorioMaxM');
  const average=n('altitudineTerritorioMediaM');
  const surface=n('superficieKm2');
  const population=n('popolazione');
  const populationReference=t('populationReferenceDate');
  const mayor=t('sindacoNome');
  const mandate=t('mandatoInizio');
  const election=t('dataElezione');
  const website=place.website?.startsWith('https://')?place.website:null;
  const hasAdministration=Boolean(mayor||election||mandate||website);
  const people=(place.connectedPeople||[]).filter(p=>p.verified&&p.personId&&p.name);
  const mountainPeople=people.filter(p=>p.category==='montagna');
  const culturalPeople=people.filter(p=>p.category==='cultura_e_ricerca');
  const historicalMedia=(place.media||[]).filter(m=>m.kind==='historical_photo'&&
    m.subjectVerified&&m.reuseAllowed&&m.licence&&m.sourceUrl&&m.url);
  const aliases=(place.aliases||[]).filter(a=>a.value&&a.value!==place.name);
  const archive=municipalityArchiveFacts(place);
  const hasArchive=Object.keys(archive).length>0||Boolean(place.factsAlternatives?.length);
  const territoryRows=[
    ...(region?[{label:'Regione',value:region}]:[]),
    ...(province?[{label:'Provincia',value:province}]:[]),
    ...(centre!==null?[{label:'Quota del centro abitato (fonte dichiarata)',value:centre.toLocaleString('it-IT')+' m'}]:[]),
    ...(reported!==null?[{label:'Quota riportata da Wikidata',value:reported.toLocaleString('it-IT')+' m'}]:[]),
    ...(minimum!==null?[{label:'Quota minima del territorio (DEM 2021)',value:minimum.toLocaleString('it-IT')+' m'}]:[]),
    ...(average!==null?[{label:'Quota media del territorio (DEM 2021)',value:average.toLocaleString('it-IT')+' m'}]:[]),
    ...(maximum!==null?[{label:'Quota massima del territorio (DEM 2021)',value:maximum.toLocaleString('it-IT')+' m'}]:[]),
    ...(surface!==null?[{label:'Superficie comunale',value:surface.toLocaleString('it-IT',{maximumFractionDigits:2})+' km²'}]:[]),
    ...(population!==null&&populationReference?[{label:'Popolazione ('+populationReference+')',
      value:population.toLocaleString('it-IT')}]:[]),
  ];
  const hasRoutes=Object.values(routeGroups).some(group=>group.length);
  const hasRelations=Boolean(place.relations?.some(r=>r.target?.kind!=='person'&&r.target?.name));
  const synopsis=place.description?.trim()||place.shortSummary?.trim()||
    place.name+' è un comune delle Alpi italiane. Esplora il territorio e le relazioni documentate.';

  return <div className="cb-municipality-profile">
    <header className="cb-location-hero cb-municipality-hero">
      <div className="cb-location-hero-copy">
        <span className="cb-municipality-eyebrow"><AlpinePlaceIcon kind="borgo" size={16}/> COMUNE ITALIANO
          {province?' · '+province:''}</span>
        <h1>{place.name}</h1>
        {aliases.length>0&&<p className="cb-municipality-aliases">
          Conosciuto anche come <strong>{aliases.map(a=>a.value).join(' · ')}</strong>
        </p>}
        <p className="cb-municipality-intro">{synopsis}</p>
        <AtlasDossierBlocks record={place} placement="alerts"/>
        <DetailMetrics label="Il comune in sintesi" items={[
          ...(centre!==null?[{label:'Quota del centro',value:centre.toLocaleString('it-IT')+' m'}]:
            reported!==null?[{label:'Quota riportata',value:reported.toLocaleString('it-IT')+' m'}]:[]),
          ...(surface!==null?[{label:'Superficie',value:surface.toLocaleString('it-IT',{maximumFractionDigits:1})+' km²'}]:[]),
          ...(maximum!==null?[{label:'Quota massima del territorio',value:maximum.toLocaleString('it-IT')+' m'}]:[]),
          ...(population!==null&&populationReference?[{label:'Residenti ('+populationReference+')',value:population.toLocaleString('it-IT')}]:[]),
        ]}/>
        <div className="cb-location-actions">
          <button className="cb-location-action-primary cb-icon-link" type="button"
            onClick={()=>scrollToDetailSection('cb-place-map')}><FaIcon name="map" size={14}/> ESPLORA LA MAPPA</button>
          {website&&<a className="cb-icon-link" href={website} target="_blank" rel="noopener noreferrer">
            <FaIcon name="arrow-up-right-from-square" size={12}/> Sito istituzionale</a>}
        </div>
      </div>
      <figure className="cb-location-hero-media">
        <AlpinePlaceVisual key={place.slug} place={place}/>
        <div className="cb-location-avatar">{place.logo?
          <img src={place.logo.url} alt={'Stemma di '+place.name}/>:
          <AlpinePlaceIcon kind="borgo" size={39}/>}</div>
        <figcaption>{place.photo?'Fotografia documentata del territorio':
          'Rappresentazione topografica: fotografia non disponibile'}</figcaption>
      </figure>
    </header>

    <DetailJumpNav items={[
      {id:'cb-municipality-territory',label:'Territorio',icon:'mountain'},
      ...(hasAdministration?[{id:'cb-municipality-admin',label:'Comune',icon:'house' as const}]:[]),
      ...(people.length?[{id:'cb-municipality-people',label:'Persone',icon:'person-hiking' as const}]:[]),
      {id:'cb-place-itineraries',label:'Sentieri',icon:'route'},
      ...(water.length?[{id:'cb-place-water',label:'Acqua',icon:'water' as const}]:[]),
      {id:'cb-place-weather',label:'Meteo',icon:'compass'},
      ...(nearbyPlaces.length||hasRelations?[{id:'cb-municipality-nearby',label:'Dintorni',icon:'location-dot' as const}]:[]),
      ...(historicalMedia.length?[{id:'cb-municipality-archive-photos',label:'Archivio',icon:'images' as const}]:[]),
      {id:'cb-place-map',label:'Mappa',icon:'map'},
    ]}/>

    <section id="cb-municipality-territory" className="cb-detail-group cb-detail-group--first cb-location-section cb-municipality-territory">
      <DetailSectionHeading kicker="01 / GEOGRAFIA" title="Il territorio in cifre"
        description="La quota del centro e le quote minime e massime del territorio comunale sono misure distinte."/>
      {minimum!==null&&maximum!==null&&<div className="cb-municipality-altitude">
        <div><span>MINIMO TERRITORIALE</span><strong>{minimum.toLocaleString('it-IT')} <small>m</small></strong></div>
        <div className="cb-municipality-altitude-track" aria-hidden="true"><span/></div>
        <div><span>MASSIMO TERRITORIALE</span><strong>{maximum.toLocaleString('it-IT')} <small>m</small></strong></div>
      </div>}
      <DetailFacts rows={territoryRows}/>
      {(minimum!==null||maximum!==null||average!==null)&&
        <p className="cb-municipality-data-note">Le quote territoriali derivano da un modello altimetrico con riferimento 2021: non rappresentano le altitudini del municipio o del centro abitato.</p>}
    </section>
    {hasAdministration&&<section id="cb-municipality-admin" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="02 / AMMINISTRAZIONE" title="Il Comune"
        description="Dati istituzionali documentati; le cariche e gli incarichi non sono aggiornamenti in tempo reale."/>
      <div className="cb-municipality-administration">
        {mayor&&<div className="cb-municipality-mayor">
          <span>{t('carica')||'Sindaco'} riportato dal DAIT</span><strong>{mayor}</strong>
          {mandate&&<small>Incarico dal {municipalityDisplayDate(mandate)}</small>}
        </div>}
        <DetailFacts rows={[
          ...(election?[{label:'Data dell’elezione',value:municipalityDisplayDate(election)||election}]:[]),
          ...(mandate&&!mayor?[{label:'Mandato dal',value:municipalityDisplayDate(mandate)||mandate}]:[]),
          ...(t('mandatoFine')?[{label:'Mandato fino al',value:municipalityDisplayDate(t('mandatoFine'))||''}]:[]),
        ]}/>
        {website&&<a className="cb-municipality-official" href={website} target="_blank" rel="noopener noreferrer">
          <FaIcon name="arrow-up-right-from-square" size={14}/> Visita il sito istituzionale</a>}
      </div>
    </section>}
    {people.length>0&&<section id="cb-municipality-people" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="03 / PERSONE E MEMORIA" title="Vite legate alla montagna"
        description="Sono distinti il luogo di nascita, la residenza storica e l’attività documentata. Nessun legame è dedotto dalla sola vicinanza."/>
      <PersonCards people={mountainPeople} title="Alpinismo e montagna"/>
      <PersonCards people={culturalPeople} title="Altre figure del territorio"/>
    </section>}
    <section id="cb-place-itineraries" className="cb-detail-group cb-location-section cb-location-itineraries">
      <DetailSectionHeading kicker="04 / DA QUI ALLA MONTAGNA" title="Sentieri e itinerari"
        description="I collegamenti geometrici indicano vicinanza alle tracce, non necessariamente un accesso percorribile."/>
      {loadingRoutes?<p className="cb-atlas-loading">Recupero i percorsi cartografati…</p>:<>
        <AtlasRouteGroup title="Partono da qui" items={routeGroups.departures}/>
        <AtlasRouteGroup title="Arrivano qui" items={routeGroups.arrivals}/>
        <AtlasRouteGroup title="Passano nelle vicinanze" items={routeGroups.passes}/>
        <AtlasRouteGroup title="Altri itinerari nella zona" items={routeGroups.around}/>
        {!hasRoutes&&<p className="cb-location-muted-note">Nessuna traccia indicizzata nelle immediate vicinanze. Non significa che non esistano sentieri.</p>}
      </>}
    </section>
    {(nearbyPlaces.length>0||hasRelations)&&<section id="cb-municipality-nearby" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="05 / ATLANTE RELAZIONALE" title="Luoghi e collegamenti"
        description="Rifugi, bivacchi e località vicini o con una relazione documentata; la distanza in linea d'aria non descrive un itinerario."/>
      <NearbyAtlasPlaces items={nearbyPlaces}/>
      <AtlasDossierBlocks record={place} placement="connections"/>
    </section>}
    {water.length>0&&<section id="cb-place-water" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="06 / RISORSE CARTOGRAFATE" title="Punti acqua nei dintorni"
        description="Fontanelle, sorgenti e rubinetti entro circa 1,8 km, identificati sulla mappa dallo stesso numero."/>
      <WaterNearbyList points={water} selectedSlug={selectedWaterSlug} onSelect={onWaterSelect}/>
    </section>}
    <section id="cb-place-weather" className="cb-detail-group cb-location-section">
      <AlpineWeatherPanel lat={place.lat} lng={place.lng} name={place.name}/>
    </section>
    {historicalMedia.length>0&&<section id="cb-municipality-archive-photos" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="MEMORIA DEL TERRITORIO" title="Fotografie storiche"/>
      <div className="cb-municipality-historical-gallery">{historicalMedia.map(m=><figure key={m.id}>
        <img src={m.url} alt={m.caption||'Fotografia storica di '+place.name} loading="lazy"/>
        <figcaption>{m.caption||'Immagine storica'}{m.capturedAt?' · '+m.capturedAt:''}</figcaption>
      </figure>)}</div>
    </section>}
    {hasArchive&&<section className="cb-detail-group cb-location-section cb-municipality-archive">
      <details>
        <summary><span>Altre informazioni</span><small>Codici ISTAT, classificazioni e cronologia amministrativa</small></summary>
        <AtlasDossierBlocks placement="core" record={{...place,facts:archive,
          administrativeHierarchy:undefined,aliases:[],localNames:[],history:undefined}}/>
      </details>
    </section>}
    <AtlasDossierBlocks record={{...place,media:[]}} placement="media"/>
    <footer className="cb-location-credits">Dati e immagini conservano provenienza e aggiornamenti nel registro centralizzato delle fonti.</footer>
  </div>;
}
