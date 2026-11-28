import {useEffect,useMemo,useState} from 'react';
import type {Route} from '../types';
import type {AlpinePlace} from '../lib/alpinePlaces';
import {placeBounds} from '../lib/alpinePlaces';
import {loadNaturalLakes,naturalLakeHref,naturalLakeLabel,type NaturalLake,type NaturalLakeDataset} from '../lib/naturalLakeRelease';
import {loadLakeSourceCensus,lakeSourceLabel,lakeSourceClass,lakeSourceProvider,lakeSourcePreviewHref,type LakeSourceCensus,type LakeSourceCensusRecord} from '../lib/naturalLakeCensus';
import {loadIdentifiedLakePoints,lakeIdentifiedHref,lakeIdentifiedDisplayName,type LakeIdentifiedG1,type LakeIdentifiedG1Dataset} from '../lib/naturalLakePointsG1';
import {loadRoutesInBounds} from '../lib/routeTiles';
import {routesNear} from '../lib/routes';
import {loadAlpineWater,alpineWaterNear,type AlpineWaterPoint} from '../lib/alpineWater';
import {SiteFooter,SiteHeader} from './SiteChrome';
import {ExploreNavigation} from './ExploreNavigation';
import {DetailLayout,DetailFacts,DetailMetrics,DetailSectionHeading} from './DetailPrimitives';
import {AlpineAtlasMap,type NaturalWaterPolygon} from './AlpineAtlasMap';
import {AlpineWeatherPanel} from './AlpineWeatherPanel';
import {AtlasRouteGroup} from './AtlasRouteGroup';
import {DetailJumpNav} from './DetailJumpNav';
import {MapContextLabel} from './MapContextLabel';
import {WaterNearbyList} from './WaterNearbyList';
import {scrollToDetailSection} from '../lib/detailNavigation';
import {usePageTitle} from '../lib/pageTitle';
import {track} from '../lib/analytics';
import '../alpineAtlas.css';
import '../alpineExplore.css';
import '../locationProfile.css';

const NO_PLACES:AlpinePlace[]=[];
const EMPTY:NaturalLakeDataset={generatedAt:null,features:[]};
const fmt=(v:number,digits=1)=>v.toLocaleString('it-IT',{maximumFractionDigits:digits});
const meters=(v:number)=>fmt(v)+' m';
const mappedSurface=(km2:number)=>
  km2<1?fmt(km2*100,1)+' ha · cartografia OSM':
    fmt(km2,2)+' km² · cartografia OSM';
const lakePolygon=(feature:NaturalLake):NaturalWaterPolygon=>({
  slug:feature.slug,name:feature.name,subtype:feature.subtype,
  lat:feature.geo.point.lat,lng:feature.geo.point.lng,
  geometry:feature.geo.area,
});
function routeSlug():string|null{
  const matched=/^#laghi(?:\/([a-z0-9-]+))?$/.exec(window.location.hash);
  if(matched)return matched[1]||null;
  const base=import.meta.env.BASE_URL;
  if(!window.location.pathname.startsWith(base))return null;
  const parts=window.location.pathname.slice(base.length).split('/').filter(Boolean);
  return parts[0]==='laghi'&&parts.length===2&&/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(parts[1])
    ?parts[1]:null;
}
function LakeDetail({feature}:{feature:NaturalLake}){
  const [routes,setRoutes]=useState<Route[]>([]);
  const [loadingRoutes,setLoadingRoutes]=useState(true);
  const [water,setWater]=useState<AlpineWaterPoint[]>([]);
  const [waterSlug,setWaterSlug]=useState<string|null>(null);
  const point=feature.geo.point;
  const mapped=feature.facts.osmMappedWaterSurfaceKm2;
  const reported=feature.facts.elevationM;
  const wikipedia=feature.textSources?.find(t=>t.sourceId.startsWith('wikipedia:it:'))?.text||feature.description;
  const photo=feature.media.find(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed);
  const polygon=useMemo(()=>[lakePolygon(feature)],[feature]);
  const linked=useMemo(()=>[...(feature.relations||[])].filter(r=>
    r.type==='near'&&r.target?.name&&typeof r.straightLineKm==='number')
    .sort((a,b)=>(a.straightLineKm??0)-(b.straightLineKm??0)).slice(0,8),[feature]);
  useEffect(()=>{
    let active=true;setRoutes([]);setLoadingRoutes(true);
    void loadRoutesInBounds(placeBounds({lat:point.lat,lng:point.lng},4))
      .then(found=>{if(active)setRoutes(routesNear(found,point.lng,point.lat,2000,16));})
      .catch(()=>{if(active)setRoutes([]);})
      .finally(()=>{if(active)setLoadingRoutes(false);});
    return ()=>{active=false;};
  },[point.lat,point.lng]);
  useEffect(()=>{
    let active=true;setWater([]);setWaterSlug(null);
    void loadAlpineWater().then(found=>{
      if(active)setWater(alpineWaterNear(found.sources,point.lng,point.lat,1800,14));
    });
    return ()=>{active=false;};
  },[point.lat,point.lng]);
  useEffect(()=>{track('atlas_lake_view',feature.slug);},[feature.slug]);
  const alternativeElevation=feature.facts.wikidataElevationReportedM;
  const wikiAlt=feature.factsAlternatives?.find(x=>x.key==='elevationM'&&
    typeof x.fact.value==='number'&&x.fact.value!==reported.value);
  return <DetailLayout
    backHref={import.meta.env.BASE_URL+'laghi/'}
    backLabel="Tutti i laghi"
    sidebarLabel={'Perimetro e mappa del '+feature.name}
    sidebar={<section id="cb-lake-map" tabIndex={-1} className="cb-location-side-map">
      <MapContextLabel kicker="CARTOGRAFIA · PERIMETRO VERIFICATO" title={feature.name}/>
      <AlpineAtlasMap places={NO_PLACES} kind="borgo"
        selectedPoint={{...point,name:feature.name,icon:'≈'}}
        naturalPolygons={polygon}
        routes={routes} water={water}
        selectedWaterSlug={waterSlug} onWaterSelect={setWaterSlug}
        height="100%" caption={'Perimetro cartografico di '+feature.name}/>
    </section>}>
    <header className="cb-location-hero">
      <div className="cb-location-hero-copy">
        <span className="cb-atlas-kind">{naturalLakeLabel(feature).toUpperCase()}</span>
        <h1>{feature.name}</h1>
        {Boolean(feature.localNames?.length)&&<p className="cb-location-muted-note">
          Noto anche come {feature.localNames!.slice(0,4).map(x=>x.value).join(' · ')}
        </p>}
        <p className="cb-location-lead">{feature.shortSummary||wikipedia.slice(0,180)}</p>
        <DetailMetrics label="Dati essenziali dello specchio d'acqua" items={[
          {label:reported.method==='estimated'?'Quota · stima DEM GeoNames':'Quota · GeoNames',
            value:meters(Number(reported.value))},
          {label:'Superficie mappata · non ufficiale',value:mappedSurface(Number(mapped.value))},
          {label:'Sentieri cartografati vicini',value:loadingRoutes?'…':routes.length},
        ]}/>
        <div className="cb-location-actions">
          <button type="button" className="cb-location-action-primary"
            onClick={()=>scrollToDetailSection('cb-lake-map')}>ESPLORA IL PERIMETRO</button>
        </div>
      </div>
      <figure className="cb-location-hero-media">
        {photo?.url&&<img src={photo.url} loading="eager" decoding="async"
          alt={'Fotografia documentata associata a '+feature.name}/>}
        <figcaption>{photo?.caption||'Fotografia associata al lago tramite Wikidata'}</figcaption>
      </figure>
    </header>
    <DetailJumpNav items={[
      {id:'cb-lake-data',label:'Dati',icon:'compass'},
      {id:'cb-lake-about',label:'Il lago',icon:'mountain'},
      {id:'cb-lake-nearby',label:'Dintorni',icon:'location-dot'},
      {id:'cb-lake-routes',label:'Sentieri',icon:'route'},
      ...(water.length?[{id:'cb-lake-water',label:'Fonti',icon:'water' as const}]:[]),
      {id:'cb-lake-weather',label:'Meteo',icon:'compass'},
      {id:'cb-lake-map',label:'Mappa',icon:'map'},
    ]}/>
    <section id="cb-lake-data" className="cb-detail-group cb-detail-group--first cb-location-section">
      <DetailSectionHeading kicker="01 / DATI DOCUMENTATI" title="LA GEOGRAFIA, SENZA INVENTARE."
        description="Quota GeoNames e superficie derivata dalla geometria OSM sono grandezze diverse, con metodi e fonti separati."/>
      <DetailFacts rows={[
        {label:'Tipo di bacino',value:naturalLakeLabel(feature)},
        {label:'Quota GeoNames',value:meters(Number(reported.value))+
          (reported.method==='estimated'?' · stimata DEM':' · riportata')},
        {label:'Superficie perimetrata in OSM',value:mappedSurface(Number(mapped.value))},
        {label:'Coordinate del punto GeoNames',value:point.lat.toFixed(5)+', '+point.lng.toFixed(5)},
        ...(typeof alternativeElevation?.value==='number'&&alternativeElevation.value!==reported.value
          ?[{label:'Quota alternativa Wikidata',value:meters(alternativeElevation.value)}]:[]),
        ...(wikiAlt&&typeof wikiAlt.fact.value==='number'
          ?[{label:'Quota nella voce enciclopedica',value:meters(wikiAlt.fact.value)}]:[]),
      ]}/>
    </section>
    <section id="cb-lake-about" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="02 / PAESAGGIO" title="DENTRO IL PAESAGGIO."/>
      <p className="cb-location-story">{wikipedia}</p>
    </section>
    {linked.length>0&&<section id="cb-lake-nearby" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="03 / RELAZIONI TERRITORIALI" title="LUOGHI NEI DINTORNI."
        description="Distanze in linea d'aria, non attraversamenti, sentieri di accesso o rive raggiungibili."/>
      <div className="cb-atlas-grid">
        {linked.map(rel=><div className="cb-atlas-card" key={rel.type+':'+rel.target.id}>
          <strong>{rel.target.name}</strong>
          <span>{fmt(Number(rel.straightLineKm))} km in linea d'aria</span>
        </div>)}
      </div>
    </section>}
    <section id="cb-lake-routes" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="04 / ESCURSIONI" title="SENTIERI NELLA ZONA."
        description="Tracce geometricamente vicine al punto GeoNames: non attestano un accesso al lago né la percorribilità della riva."/>
      {loadingRoutes?<p className="cb-atlas-loading">Verifico i sentieri cartografati…</p>:
        routes.length?<AtlasRouteGroup title="TRACCE DISPONIBILI IN ZONA" items={routes}/>:
          <p className="cb-location-muted-note">Nessuna traccia indicizzata nelle immediate vicinanze. Non significa che non esistano sentieri.</p>}
    </section>
    {water.length>0&&<section id="cb-lake-water" className="cb-detail-group cb-location-section cb-location-water">
      <DetailSectionHeading kicker="05 / FONTI E FONTANELLE" title="ACQUA NEI DINTORNI."
        description="Catalogo delle fonti potabili e non potabili separato dai laghi. Prossimità non significa disponibilità, accesso o potabilità."/>
      <WaterNearbyList points={water} selectedSlug={waterSlug}
        onSelect={slug=>{setWaterSlug(slug);scrollToDetailSection('cb-lake-map');}}/>
    </section>}
    <section id="cb-lake-weather" className="cb-detail-group cb-location-section">
      <AlpineWeatherPanel lat={point.lat} lng={point.lng} name={feature.name}/>
    </section>
    <footer className="cb-location-credits">
      La geometria visualizzata rappresenta il contorno mappato in OpenStreetMap e non certifica superficie ufficiale, balneabilità, accesso alle rive, qualità dell'acqua o condizioni di sicurezza.
    </footer>
  </DetailLayout>;
}

const sourcePolygon=(r:LakeSourceCensusRecord):NaturalWaterPolygon=>({
  slug:r.sourceKey,name:lakeSourceLabel(r),subtype:'unspecified',
  sourceKey:r.sourceKey,quality:'G0',
  // No invented centroid: location and selection come from the real outline.
  geometry:r.geom,
});
const sourceType=(r:LakeSourceCensusRecord):'lake'|'reservoir'|'other'|'unclassified'=>
  r.provider!=='arpav_water_surfaces'?'unclassified':
    r.rawClass==='Lago'?'lake':
    r.rawClass==='Invaso'||r.rawClass==='Bacino artificiale'?'reservoir':'other';
const sourceSearch=(r:LakeSourceCensusRecord,q:string)=>
  [r.name||'',r.sourceFeatureId,...r.names.map(x=>x.name)]
    .some(x=>x.toLocaleLowerCase('it').includes(q));
const viewSurface=(r:LakeSourceCensusRecord)=>
  r.agencyReportedAreaM2!==null
    ?fmt(r.agencyReportedAreaM2/10000,2)+' ha · dato ente'
    :fmt(r.derivedMappedKm2*100,2)+' ha · dal perimetro';
function sourceProfileSlug():string|null{
  const base=import.meta.env.BASE_URL;
  if(!window.location.pathname.startsWith(base))return null;
  const path=window.location.pathname.slice(base.length);
  const result=/^laghi\/censiti\/([a-z0-9-]+)\/?$/.exec(path);
  return result?.[1]||null;
}
function AgencyLakeSourceDetail({source}:{source:LakeSourceCensusRecord}){
  const factItems=[
    {label:source.agencyReportedAreaM2!==null?'Superficie dichiarata dall’ente':'Superficie derivata WFS',
      value:viewSurface(source)},
    ...(source.agencyReportedElevationM!==null?
      [{label:'Quota · valore dell’ente',value:meters(source.agencyReportedElevationM)}]:[]),
    ...(source.agencyReportedVolumeM3!==null&&source.agencyReportedVolumeM3>0?
      [{label:'Volume · valore dell’ente',value:fmt(source.agencyReportedVolumeM3,0)+' m³'}]:[]),
    ...(source.agencyReportedWidthM!==null&&source.agencyReportedWidthM>0?
      [{label:'Larghezza · valore dell’ente',value:meters(source.agencyReportedWidthM)}]:[]),
    ...(source.agencyReportedLengthM!==null&&source.agencyReportedLengthM>0?
      [{label:'Lunghezza · valore dell’ente',value:meters(source.agencyReportedLengthM)}]:[]),
  ];
  const aliases=source.names.filter(n=>n.name!==source.name);
  const poly=useMemo(()=>[sourcePolygon(source)],[source]);
  useEffect(()=>{track('atlas_lake_source_preview',source.provider);},[source.provider,source.sourceFeatureId]);
  return <DetailLayout
    backHref={import.meta.env.BASE_URL+'laghi/'}
    backLabel="Torna all’atlante dei laghi"
    sidebarLabel={'Perimetro documentato dalla fonte di '+lakeSourceLabel(source)}
    sidebar={<section id="cb-lake-source-map" className="cb-location-side-map" tabIndex={-1}>
      <MapContextLabel kicker="PERIMETRO WFS · CENSIMENTO" title={lakeSourceLabel(source)}/>
      <AlpineAtlasMap places={NO_PLACES} kind="borgo"
        naturalPolygons={poly} selectedPolygonSlug={source.sourceKey}
        height="100%" caption={'Perimetro WFS di '+lakeSourceLabel(source)}/>
    </section>}>
    <header className="cb-location-hero cb-lake-preview-hero">
      <div className="cb-location-hero-copy">
        <span className="cb-atlas-kind">SCHEDA DI CENSIMENTO · G0 / NON INDICIZZATA</span>
        <h1>{lakeSourceLabel(source)}</h1>
        {aliases.length>0&&<p className="cb-location-muted-note">
          {aliases.map(n=>n.name+' ('+n.lang+')').join(' · ')}
        </p>}
        <p className="cb-location-lead">
          {lakeSourceProvider(source.provider)}
          {source.municipalityReported?' · Comune riportato: '+source.municipalityReported:''}.
          {' '}Informazioni e perimetro cartografico disponibili; l’identità fra archivi è ancora in verifica.
        </p>
        <DetailMetrics label="Dati ufficiali e cartografici disponibili" items={factItems}/>
        <div className="cb-location-actions">
          <button type="button" className="cb-location-action-primary"
            onClick={()=>scrollToDetailSection('cb-lake-source-map')}>ESPLORA IL CONTORNO</button>
        </div>
      </div>
      <div className="cb-lake-preview-topo" aria-label="Fotografia non ancora verificata">
        <span aria-hidden="true">≈</span>
        <strong>PAESAGGIO IN VERIFICA.</strong>
        <small>Una fotografia appare soltanto dopo una verifica del soggetto e della licenza.</small>
      </div>
    </header>
    <section id="cb-lake-source-facts" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="INVENTARIO · DATO SORGENTE" title="Quello che sappiamo."/>
      <div className="cb-lake-source-fact-list">
        <div><strong>Ente censitore</strong><span>{lakeSourceProvider(source.provider)}</span></div>
        {source.municipalityReported&&
          <div><strong>Comune riportato</strong><span>{source.municipalityReported}</span></div>}
        {source.sourceDescriptionName&&source.sourceDescriptionName!==source.name&&
          <div><strong>Denominazione descrittiva dell’ente</strong><span>{source.sourceDescriptionName}</span></div>}
        {source.rawClass&&
          <div><strong>Tipologia nel catalogo di origine</strong><span>{source.rawClass} · da verificare prima della riconciliazione</span></div>}
        <div><strong>Identificativo originario</strong><span>{source.sourceFeatureId}</span></div>
      </div>
    </section>
    <section className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="QUALITÀ · IN ARRICCHIMENTO" title="Le informazioni ancora da collegare."/>
      <p>Questa scheda descrive un singolo record geografico ufficiale. La verifica con GeoNames, Wikidata e OpenStreetMap, l’eventuale classificazione naturale o artificiale e le fotografie del soggetto sono ancora in corso. Non rappresenta un dossier G2 e non è nella sitemap.</p>
      <p>Il perimetro WFS rappresenta l’estensione cartografata, non il punto di accesso, la percorribilità della riva, la potabilità o l’idoneità alla balneazione.</p>
    </section>
  </DetailLayout>;
}
function SourceRow({row,active,onLocate}:{row:LakeSourceCensusRecord;active:boolean;onLocate:()=>void}){
  const cells=<>
    <span className="cb-lake-source-name">{lakeSourceLabel(row)}</span>
    <span className="cb-lake-source-kind">{row.rawClass||'Classe non attestata'}</span>
    <span className="cb-lake-source-place">{lakeSourceProvider(row.provider)}</span>
    <span className="cb-lake-source-surface">{viewSurface(row)}</span>
    <span className="cb-lake-source-action" aria-hidden="true">↗</span>
  </>;
  const className='cb-lake-source-row'+(active?' is-active':'');
  const href=lakeSourcePreviewHref(row);
  return href?<a className={className} href={href}>{cells}</a>:
    <button className={className} type="button" onClick={onLocate}>{cells}</button>;
}

const NO_POINT_G1:LakeIdentifiedG1Dataset={
  entities:[],counts:{profiles:0,pointOnly:0,withOsmGeometry:0,withVerifiedP18:0,withVerifiedItwiki:0},
  sourceG1Candidates:0,excludedCanonicalG2:0,
};
function identifiedLakeSlug():string|null{
  const base=import.meta.env.BASE_URL;
  if(!window.location.pathname.startsWith(base))return null;
  return /^laghi\/identificati\/([a-z0-9-]+)\/?$/
    .exec(window.location.pathname.slice(base.length))?.[1]||null;
}
function identifiedAsPolygon(item:LakeIdentifiedG1):NaturalWaterPolygon[]{
  return item.geo.area?[{
    slug:'g1:'+item.slug,name:lakeIdentifiedDisplayName(item),
    subtype:'lake',quality:'G1',geometry:item.geo.area,
  }]:[];
}
function IdentifiedLakeDetail({feature}:{feature:LakeIdentifiedG1}){
  const display=lakeIdentifiedDisplayName(feature);
  const area=feature.facts.osmMappedWaterSurfaceKm2;
  const alt=feature.facts.elevationM;
  const poly=useMemo(()=>identifiedAsPolygon(feature),[feature]);
  const photo=feature.media.find(m=>m.kind==='photo'&&m.reuseAllowed&&m.subjectVerified);
  const summary=feature.textSources?.[0]?.text;
  const altNames=[
    ...feature.localNames.map(x=>x.value),
    feature.name,...feature.aliases.map(x=>x.value),
  ].filter((x,i,a)=>x!==display&&a.indexOf(x)===i).slice(0,5);
  const facts=[
    ...(alt&&typeof alt.value==='number'?
      [{label:alt.method==='estimated'?'Quota · stima GeoNames/DEM':'Quota · GeoNames',
        value:meters(alt.value)}]:[]),
    ...(area&&typeof area.value==='number'?
      [{label:'Superficie · perimetro OSM verificato',value:mappedSurface(area.value)}]:[]),
    {label:'Geometria disponibile',
      value:feature.geo.area?'Perimetro OSM':'Posizione GeoNames'},
  ];
  useEffect(()=>{track('atlas_lake_identified_view',feature.slug);},[feature.slug]);
  return <DetailLayout
    backHref={import.meta.env.BASE_URL+'laghi/'}
    backLabel="Torna all’atlante dei laghi"
    sidebarLabel={feature.geo.area?'Perimetro verificato del '+display:'Posizione verificata del '+display}
    sidebar={<section id="cb-lake-g1-map" tabIndex={-1} className="cb-location-side-map">
      <MapContextLabel kicker={feature.geo.area?'PERIMETRO OSM · IDENTITÀ G1':'POSIZIONE GEONAMES · IDENTITÀ G1'}
        title={display}/>
      <AlpineAtlasMap places={NO_PLACES} kind="borgo"
        selectedPoint={{...feature.geo.point,name:display,icon:'≈'}}
        naturalPolygons={poly}
        height="100%"
        caption={feature.geo.area?'Perimetro OSM associato con identità verificata':
          'Punto geografico verificato GeoNames e Wikidata; contorno non disponibile'}/>
    </section>}>
    <header className="cb-location-hero cb-lake-preview-hero">
      <div className="cb-location-hero-copy">
        <span className="cb-atlas-kind">LAGO IDENTIFICATO · G1 / NON INDICIZZATO</span>
        <h1>{display}</h1>
        {altNames.length>0&&<p className="cb-location-muted-note">
          Noto anche come {altNames.join(' · ')}
        </p>}
        <p className="cb-location-lead">{summary?.slice(0,240)||
          'Il lago ha un’identità geografica verificata tramite GeoNames e Wikidata. La scheda si arricchisce con informazioni ulteriori quando documentate.'}</p>
        <DetailMetrics label="Dati geografici verificati" items={facts}/>
        <div className="cb-location-actions">
          <button className="cb-location-action-primary" type="button"
            onClick={()=>scrollToDetailSection('cb-lake-g1-map')}>
            {feature.geo.area?'ESPLORA IL PERIMETRO':'VEDI LA POSIZIONE'}
          </button>
        </div>
      </div>
      {photo?
        <figure className="cb-location-hero-media">
          <img src={photo.url} alt={'Fotografia documentata associata a '+display}
            loading="eager" decoding="async"/>
          <figcaption>{photo.caption||'Fotografia associata all’identità Wikidata del lago'}</figcaption>
        </figure>:
        <div className="cb-lake-preview-topo" aria-label="Fotografia del soggetto non ancora verificata">
          <span aria-hidden="true">≈</span>
          <strong>UN LAGO. NON UNA FOTO A CASO.</strong>
          <small>Le immagini vengono aggiunte solo dopo la verifica del soggetto e dei diritti.</small>
        </div>}
    </header>
    {summary&&<section className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="TERRITORIO / TESTO DOCUMENTATO" title="Paesaggio e territorio."/>
      <p>{summary}</p>
    </section>}
    <section className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="GEOREFERENZIAZIONE / IDENTITÀ" title="I dati che possiamo confermare."/>
      <div className="cb-lake-source-fact-list">
        <div><strong>Identità</strong><span>GeoNames e Wikidata, proprietà P1566 e P625</span></div>
        <div><strong>Coordinate GeoNames</strong><span>
          {fmt(feature.geo.point.lat,5)}° N · {fmt(feature.geo.point.lng,5)}° E
        </span></div>
        <div><strong>Contorno dello specchio d’acqua</strong><span>
          {feature.geo.area?'Perimetro OSM associato tramite identificativi verificati':
            'Non ancora disponibile: la mappa mostra solo il punto geografico'}
        </span></div>
        {feature.facts.wikidataElevationReportedM&&
          <div><strong>Quota riportata da Wikidata</strong>
            <span>{meters(Number(feature.facts.wikidataElevationReportedM.value))}</span>
          </div>}
      </div>
    </section>
    <section className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="QUALITÀ / STATO DEI DATI" title="Una scheda in arricchimento."/>
      <p>Identità verificata, contenuti pubblicati solo se documentati. Il perimetro, quando presente, è cartografia OSM e non una misura ufficiale della superficie. Un punto GeoNames non rappresenta un punto di partenza, una riva né un accesso. Balneabilità, potabilità e percorribilità richiedono fonti specifiche.</p>
    </section>
  </DetailLayout>;
}

const INITIAL_PAGE=36;

export function NaturalLakePage(){
  const [slug,setSlug]=useState(routeSlug);
  const [sourceSlug,setSourceSlug]=useState(sourceProfileSlug);
  const [identifiedSlug,setIdentifiedSlug]=useState(identifiedLakeSlug);
  const [identified,setIdentified]=useState<LakeIdentifiedG1Dataset>(NO_POINT_G1);
  const [loadingIdentified,setLoadingIdentified]=useState(true);
  const [dataset,setDataset]=useState<NaturalLakeDataset>(EMPTY);
  const [loading,setLoading]=useState(true);
  const [census,setCensus]=useState<LakeSourceCensus|null>(null);
  const [loadingCensus,setLoadingCensus]=useState(true);
  const [query,setQuery]=useState('');
  const [sort,setSort]=useState<'name'|'height'|'surface'>('name');
  const [providerFilter,setProviderFilter]=useState<'all'|'bolzano_lakes'|'arpav_water_surfaces'>('all');
  const [typeFilter,setTypeFilter]=useState<'all'|'lake'|'reservoir'|'other'|'unclassified'>('all');
  const [visibleLimit,setVisibleLimit]=useState(INITIAL_PAGE);
  const [selectedSourceKey,setSelectedSourceKey]=useState<string|null>(null);

  useEffect(()=>{
    let active=true;
    void loadNaturalLakes().then(doc=>{
      if(active){setDataset(doc);setLoading(false);}
    });
    return ()=>{active=false;};
  },[]);
  useEffect(()=>{
    let active=true;
    void loadIdentifiedLakePoints().then(doc=>{
      if(active){setIdentified(doc);setLoadingIdentified(false);}
    });
    return ()=>{active=false;};
  },[]);
  useEffect(()=>{
    if(slug||identifiedSlug)return;
    let active=true;
    void loadLakeSourceCensus().then(doc=>{
      if(active){setCensus(doc);setLoadingCensus(false);}
    });
    return ()=>{active=false;};
  },[slug,identifiedSlug]);
  useEffect(()=>{
    const change=()=>{
      setSlug(routeSlug());setSourceSlug(sourceProfileSlug());
      setIdentifiedSlug(identifiedLakeSlug());
      setQuery('');setSelectedSourceKey(null);
      setVisibleLimit(INITIAL_PAGE);window.scrollTo({top:0});
    };
    window.addEventListener('hashchange',change);
    return ()=>window.removeEventListener('hashchange',change);
  },[]);

  const features=dataset.features;
  const current=slug?features.find(f=>f.slug===slug):null;
  const preview=sourceSlug?census?.records.find(x=>x.previewSlug===sourceSlug):null;
  const g1Detail=identifiedSlug?identified.entities.find(x=>x.slug===identifiedSlug):null;
  const allSources=census?.records||[];
  const q=query.trim().toLocaleLowerCase('it');
  const shown=useMemo(()=>features.filter(x=>
    [x.name,...(x.aliases||[]).map(a=>a.value),...(x.localNames||[]).map(a=>a.value)]
      .some(name=>name.toLocaleLowerCase('it').includes(q)))
    .sort((a,b)=>sort==='height'
      ?Number(b.facts.elevationM.value)-Number(a.facts.elevationM.value)
      :sort==='surface'
      ?Number(b.facts.osmMappedWaterSurfaceKm2.value)-Number(a.facts.osmMappedWaterSurfaceKm2.value)
      :a.name.localeCompare(b.name,'it')),[features,q,sort]);
  const shownG1=useMemo(()=>identified.entities.filter(x=>
    [x.name,...x.localNames.map(n=>n.value),...x.aliases.map(n=>n.value)]
      .some(n=>n.toLocaleLowerCase('it').includes(q)))
    .sort((a,b)=>lakeIdentifiedDisplayName(a).localeCompare(lakeIdentifiedDisplayName(b),'it')),
    [identified.entities,q]);
  const shownSource=useMemo(()=>allSources.filter(r=>
    (providerFilter==='all'||r.provider===providerFilter)&&
    (typeFilter==='all'||sourceType(r)===typeFilter)&&
    sourceSearch(r,q))
    .sort((a,b)=>{
      if(sort==='height')
        return (b.agencyReportedElevationM??-1)-(a.agencyReportedElevationM??-1)||
          lakeSourceLabel(a).localeCompare(lakeSourceLabel(b),'it');
      if(sort==='surface')
        return (b.agencyReportedAreaM2??b.derivedMappedKm2*1000000)-
          (a.agencyReportedAreaM2??a.derivedMappedKm2*1000000);
      return lakeSourceLabel(a).localeCompare(lakeSourceLabel(b),'it');
    }),[allSources,providerFilter,typeFilter,q,sort]);
  const polygons=useMemo(()=>[
    ...shownSource.map(sourcePolygon),
    ...shownG1.flatMap(identifiedAsPolygon),
    ...shown.map(lake=>({...lakePolygon(lake),quality:'G2' as const})),
  ],[shownSource,shownG1,shown]);
  const selectedSource=useMemo(()=>
    allSources.find(r=>r.sourceKey===selectedSourceKey)||null,
    [allSources,selectedSourceKey]);
  const namedCount=census?Object.values(census.sourceCounts)
    .reduce((sum,p)=>sum+p.namedSourceRecords,0):0;
  usePageTitle((current?current.name:g1Detail?lakeIdentifiedDisplayName(g1Detail):
    preview?lakeSourceLabel(preview)+' · Censimento':'Laghi e invasi alpini')+' · Cima Becco');
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <ExploreNavigation active="laghi"/>
    <main className={slug||identifiedSlug||sourceSlug?'cb-atlas-shell cb-atlas-shell--detail':'cb-atlas-shell'}>
      {current?<LakeDetail feature={current}/>:
       identifiedSlug?(g1Detail?<IdentifiedLakeDetail feature={g1Detail}/>:
         loadingIdentified?<div className="cb-atlas-loading">Caricamento della scheda…</div>:
         <div className="cb-atlas-empty"><h1>Lago identificato non disponibile.</h1>
           <a href={import.meta.env.BASE_URL+'laghi/'}>Torna all’elenco dei laghi</a>
         </div>):
       sourceSlug?(preview?<AgencyLakeSourceDetail source={preview}/>:
         loadingCensus?<div className="cb-atlas-loading">Caricamento della scheda…</div>:
         <div className="cb-atlas-empty"><h1>Scheda di censimento non disponibile.</h1>
           <p>La voce potrebbe non avere ancora un nome verificabile o un perimetro cartografico valido.</p>
           <a href={import.meta.env.BASE_URL+'laghi/'}>Torna all’elenco dei laghi</a>
         </div>):
       slug?<div className="cb-atlas-empty"><h1>Questa scheda non è ancora disponibile.</h1>
         <p>Il lago non ha ancora superato la verifica di perimetro, identità e contenuti.</p>
         <a href={import.meta.env.BASE_URL+'laghi/'}>Torna ai laghi documentati</a></div>:
       <>
         <div className="cb-atlas-overline">CIMA BECCO / LUOGHI / LAGHI</div>
         <div className="cb-atlas-intro">
           <div><span className="cb-atlas-eyebrow">SPECCHI D'ACQUA / DOLOMITI / ALPI</span>
             <h1>LAGHI. SENZA SPONDE INVENTATE.</h1>
             <p>Una mappa, tre livelli di conoscenza: censimenti regionali, laghi identificati mediante GeoNames e Wikidata e dossier approfonditi. Senza inventare rive, foto o collegamenti.</p>
           </div>
           <div className="cb-atlas-intro-symbol" aria-hidden="true">≈</div>
         </div>
         <div className="cb-lake-census-stats" aria-label="Stato del censimento">
           <span><strong>{loadingCensus?'…':census?.shownPolygons||0}</strong> perimetri di fonte</span>
           <span><strong>{loadingCensus?'…':namedCount}</strong> con nome censito</span>
           <span><strong>{loadingCensus?'…':census?.geometryPendingReview||0}</strong> geometrie in revisione</span>
           <span><strong>{loading?'…':features.length}</strong> dossier completi</span>
           <span><strong>{loadingIdentified?'…':identified.counts.profiles}</strong> laghi identificati G1</span>
         </div>
         <div className="cb-atlas-toolbar cb-lake-census-toolbar">
           <label htmlFor="cb-lake-query">CERCA</label>
           <input id="cb-lake-query" type="search" value={query}
             onChange={e=>{setQuery(e.target.value);setVisibleLimit(INITIAL_PAGE);setSelectedSourceKey(null);}}
             placeholder="Nome del lago o codice ufficiale…" />
           <label htmlFor="cb-lake-provider">TERRITORIO</label>
           <select id="cb-lake-provider" value={providerFilter}
             onChange={e=>{setProviderFilter(e.target.value as typeof providerFilter);setVisibleLimit(INITIAL_PAGE);setSelectedSourceKey(null);}}>
             <option value="all">Tutte le fonti</option>
             <option value="bolzano_lakes">Alto Adige</option>
             <option value="arpav_water_surfaces">Veneto</option>
           </select>
           <label htmlFor="cb-lake-type">TIPO FONTE</label>
           <select id="cb-lake-type" value={typeFilter}
             onChange={e=>{setTypeFilter(e.target.value as typeof typeFilter);setVisibleLimit(INITIAL_PAGE);setSelectedSourceKey(null);}}>
             <option value="all">Tutti</option>
             <option value="lake">Lago (ARPAV)</option>
             <option value="reservoir">Invaso / bacino (ARPAV)</option>
             <option value="other">Altri specchi d'acqua (ARPAV)</option>
             <option value="unclassified">Non classificati (Bolzano)</option>
           </select>
           <label htmlFor="cb-lake-sort">ORDINA</label>
           <select id="cb-lake-sort" value={sort}
             onChange={e=>{setSort(e.target.value as typeof sort);setVisibleLimit(INITIAL_PAGE);}}>
             <option value="name">Nome</option>
             <option value="height">Quota riportata</option>
             <option value="surface">Superficie</option>
           </select>
           <span>{shownSource.length} record di fonte · {shown.length} dossier</span>
         </div>
         <section className="cb-atlas-list-map" aria-label="Mappa dei corpi idrici censiti">
           <div className="cb-atlas-section-top"><span>ATLANTE / CARTOGRAFIA</span>
             <h2>PERIMETRI, NON IPOTESI.</h2>
             <p>I contorni chiari sono record ufficiali G0; i punti e i perimetri intermedi sono laghi G1 identificati; i contorni marcati sono dossier G2. Una sovrapposizione fra fonti non ne dimostra automaticamente l’identità.</p>
           </div>
           <div className="cb-lake-map-key" aria-label="Legenda livello dei dati">
             <span><i className="cb-lake-key-g0" aria-hidden="true"/>Censimento · G0</span>
             <span><i className="cb-lake-key-g1" aria-hidden="true"/>Identificato · G1</span>
             <span><i className="cb-lake-key-g2" aria-hidden="true"/>Dossier · G2</span>
           </div>
           {polygons.length>0?
             <AlpineAtlasMap places={NO_PLACES} kind="borgo"
               naturalPoints={shownG1.map(x=>({
                 slug:x.slug,name:lakeIdentifiedDisplayName(x),
                 lat:x.geo.point.lat,lng:x.geo.point.lng,subtype:x.subtype,
               }))}
               onNaturalSelect={p=>{
                 const item=identified.entities.find(x=>x.slug===p.slug);
                 if(item)window.location.assign(lakeIdentifiedHref(item));
               }}
               naturalPolygons={polygons}
               selectedPolygonSlug={selectedSourceKey}
               onNaturalPolygonSelect={p=>{
                 if(p.quality==='G0'){setSelectedSourceKey(p.sourceKey||null);return;}
                 if(p.quality==='G1'){
                   const item=identified.entities.find(x=>'g1:'+x.slug===p.slug);
                   if(item)window.location.assign(lakeIdentifiedHref(item));
                   return;
                 }
                 window.location.assign(naturalLakeHref(p.slug));
               }}
               height={430} caption="Perimetri WFS G0, punti e poligoni G1 e dossier documentati G2"/>:
             <p className="cb-atlas-loading">{loadingCensus?'Caricamento dei perimetri…':'Nessun perimetro corrisponde ai filtri.'}</p>}
           {selectedSource&&<div className="cb-lake-source-selected" id="cb-lake-source-selected" aria-live="polite">
             <div><span className="cb-atlas-eyebrow">RECORD CARTOGRAFICO · G0</span>
               <h3>{lakeSourceLabel(selectedSource)}</h3>
               <p>{lakeSourceProvider(selectedSource.provider)} · {lakeSourceClass(selectedSource)}</p>
               <p>{viewSurface(selectedSource)}
                 {selectedSource.agencyReportedElevationM!==null?' · Quota ente '+meters(selectedSource.agencyReportedElevationM):''}</p>
               {lakeSourcePreviewHref(selectedSource)&&<p><a className="cb-lake-profile-link" href={lakeSourcePreviewHref(selectedSource)!}>APRI LA SCHEDA DI CENSIMENTO ↗</a></p>}
               <small>ID della fonte: {selectedSource.sourceFeatureId}. Identità fra archivi non ancora accertata; nessuna indicazione di accessibilità o balneabilità.</small>
             </div>
             <button type="button" onClick={()=>setSelectedSourceKey(null)}>Chiudi dettagli</button>
           </div>}
         </section>

         <section className="cb-lake-complete-section" aria-label="Schede verificate">
           <div className="cb-atlas-section-top"><span>LETTURE / DOSSIER G2</span>
             <h2>QUELLI CHE CONOSCIAMO DAVVERO.</h2>
             <p>Fotografie, narrativa, provenienza, geometrie e collegamenti verificati. Queste sono le sole schede con URL individuale indicizzabile.</p>
           </div>
           {shown.length>0?<div className="cb-atlas-grid">
             {shown.map((lake,i)=><a href={naturalLakeHref(lake.slug)}
               key={lake.id} className="cb-atlas-card">
               <span className="cb-atlas-card-count">{String(i+1).padStart(2,'0')}</span>
               <span className="cb-atlas-kind">{naturalLakeLabel(lake).toUpperCase()}</span>
               {lake.media[0]?.url&&<img className="cb-atlas-card-photo"
                 src={lake.media[0].url} alt="" loading="lazy"/>}
               <h2>{lake.name}</h2>
               <strong>{meters(Number(lake.facts.elevationM.value))}</strong>
               <span>{mappedSurface(Number(lake.facts.osmMappedWaterSurfaceKm2.value))}</span>
               <span className="cb-atlas-card-go">SCOPRI IL LAGO ↗</span>
             </a>)}
           </div>:<p className="cb-atlas-loading">{loading?'Caricamento delle schede…':'Nessun dossier con questo nome.'}</p>}
         </section>

         <section className="cb-lake-complete-section" aria-label="Laghi identificati anche senza perimetro">
           <div className="cb-atlas-section-top"><span>IDENTITÀ / GEOREFERENZIAZIONE G1</span>
             <h2>UN NOME, UNA POSIZIONE, UNA STORIA DA COMPLETARE.</h2>
             <p>Laghi già collegati a GeoNames e Wikidata tramite identificativi e coordinate verificati. Le schede sono consultabili ma non indicizzate. Il punto geografico non dimostra l’accesso e i contorni mancanti non sono simulati.</p>
           </div>
           {shownG1.length>0?<div className="cb-atlas-grid cb-lake-g1-grid">
             {shownG1.map(x=><a href={lakeIdentifiedHref(x)} key={x.id} className="cb-atlas-card">
               <span className="cb-atlas-kind">IDENTIFICATO · G1</span>
               {x.media[0]?.url?
                 <img className="cb-atlas-card-photo" src={x.media[0].url}
                   alt="" loading="lazy"/>:
                 <span className="cb-lake-g1-card-placeholder" aria-hidden="true">≈</span>}
               <h2>{lakeIdentifiedDisplayName(x)}</h2>
               {typeof x.facts.elevationM?.value==='number'&&
                 <strong>{meters(x.facts.elevationM.value)}</strong>}
               <span>{x.geo.area?'Perimetro OSM verificato':'Posizione GeoNames · contorno assente'}</span>
               <span className="cb-atlas-card-go">APRI LA SCHEDA ↗</span>
             </a>)}
           </div>:<p className="cb-atlas-loading">
             {loadingIdentified?'Caricamento dei laghi identificati…':
               q?'Nessun lago G1 corrisponde alla ricerca.':'Nessun lago G1 aggiuntivo rispetto ai dossier completi.'}
           </p>}
         </section>
         <section className="cb-lake-census-list" aria-label="Elenco dei record regionali">
           <div className="cb-atlas-section-top"><span>INVENTARIO / FONTI REGIONALI</span>
             <h2>ALTRI SPECCHI D'ACQUA CENSITI.</h2>
             <p>Ogni riga è un identificativo di origine, non ancora un lago unico nel grafo. Apri le schede di censimento con nome documentato; i record senza un nome affidabile restano selezionabili sulla mappa. Le geometrie non validate non vengono rappresentate.</p>
           </div>
           {shownSource.length>0?<div className="cb-lake-source-rows">
             {shownSource.slice(0,visibleLimit).map(r=><SourceRow key={r.sourceKey}
               row={r} active={selectedSourceKey===r.sourceKey}
               onLocate={()=>{
                 setSelectedSourceKey(r.sourceKey);
                 document.querySelector('.cb-atlas-list-map')?.scrollIntoView({behavior:'smooth',block:'start'});
               }}/>)}
           </div>:<p className="cb-atlas-loading">
             {loadingCensus?'Caricamento dell’inventario…':
               q||providerFilter!=='all'||typeFilter!=='all'?'Nessun record per questi filtri.':'Inventario in aggiornamento.'}
           </p>}
           {visibleLimit<shownSource.length&&<button type="button" className="cb-atlas-more"
             onClick={()=>setVisibleLimit(n=>n+INITIAL_PAGE)}>
             MOSTRA ALTRI · {shownSource.length-visibleLimit} RIMASTI
           </button>}
           <p className="cb-lake-source-caveat">I {census?.geometryPendingReview||0} record con geometria in revisione non compaiono sulla mappa. Le fonti originali, le licenze e gli aggiornamenti sono documentati in <a href={import.meta.env.BASE_URL+'fonti-e-crediti/'}>Fonti e crediti</a>. Nessun contorno certifica accesso alle rive, potabilità o balneabilità.</p>
         </section>
       </>}
    </main>
    <SiteFooter/>
  </div>;
}
