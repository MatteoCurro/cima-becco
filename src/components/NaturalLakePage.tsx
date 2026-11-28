import {useEffect,useMemo,useState} from 'react';
import type {Route} from '../types';
import type {AlpinePlace} from '../lib/alpinePlaces';
import {placeBounds} from '../lib/alpinePlaces';
import {loadNaturalLakes,naturalLakeHref,naturalLakeLabel,type NaturalLake,type NaturalLakeDataset} from '../lib/naturalLakeRelease';
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

export function NaturalLakePage(){
  const [slug,setSlug]=useState(routeSlug);
  const [dataset,setDataset]=useState<NaturalLakeDataset>(EMPTY);
  const [loading,setLoading]=useState(true);
  const [query,setQuery]=useState('');
  const [sort,setSort]=useState<'name'|'height'|'surface'>('name');
  useEffect(()=>{
    let active=true;
    void loadNaturalLakes().then(doc=>{if(active){setDataset(doc);setLoading(false);}});
    return ()=>{active=false;};
  },[]);
  useEffect(()=>{
    const change=()=>{setSlug(routeSlug());setQuery('');window.scrollTo({top:0});};
    window.addEventListener('hashchange',change);
    return ()=>window.removeEventListener('hashchange',change);
  },[]);
  const features=dataset.features;
  const polygons=useMemo(()=>features.map(lakePolygon),[features]);
  const current=slug?features.find(f=>f.slug===slug):null;
  const shown=useMemo(()=>features.filter(x=>
    [x.name,...(x.aliases||[]).map(a=>a.value),...(x.localNames||[]).map(a=>a.value)]
      .some(name=>name.toLocaleLowerCase('it').includes(query.trim().toLocaleLowerCase('it'))))
    .sort((a,b)=>sort==='height'
      ?Number(b.facts.elevationM.value)-Number(a.facts.elevationM.value)
      :sort==='surface'
      ?Number(b.facts.osmMappedWaterSurfaceKm2.value)-Number(a.facts.osmMappedWaterSurfaceKm2.value)
      :a.name.localeCompare(b.name,'it')),[features,query,sort]);
  usePageTitle((current?current.name:'Laghi e invasi alpini')+' · Cima Becco');
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <ExploreNavigation active="laghi"/>
    <main className={slug?'cb-atlas-shell cb-atlas-shell--detail':'cb-atlas-shell'}>
      {current?<LakeDetail feature={current}/>:
       slug?<div className="cb-atlas-empty"><h1>Questa scheda non è ancora disponibile.</h1>
         <p>Il lago non ha ancora superato la verifica di perimetro, identità e contenuti.</p>
         <a href={import.meta.env.BASE_URL+'laghi/'}>Torna ai laghi documentati</a></div>:
       <>
         <div className="cb-atlas-overline">CIMA BECCO / LUOGHI / LAGHI</div>
         <div className="cb-atlas-intro">
           <div><span className="cb-atlas-eyebrow">SPECCHI D'ACQUA / DOLOMITI / ALPI</span>
             <h1>LAGHI. SENZA SPONDE INVENTATE.</h1>
             <p>Paesaggi lacustri con perimetri OSM e identità verificate. La vicinanza dei sentieri non attesta un accesso alle rive; balneabilità e potabilità non sono dedotte.</p>
           </div>
           <div className="cb-atlas-intro-symbol" aria-hidden="true">≈</div>
         </div>
         {features.length>0&&<section className="cb-atlas-list-map">
           <div className="cb-atlas-section-top"><span>GEOMETRIE DOCUMENTATE</span>
             <h2>I LAGHI SULLA MAPPA.</h2></div>
           <AlpineAtlasMap places={NO_PLACES} kind="borgo"
             naturalPolygons={polygons} height={350} caption="Laghi e invasi con perimetro verificato"/>
         </section>}
         <div className="cb-atlas-toolbar">
           <label htmlFor="cb-lake-query">CERCA UN LAGO</label>
           <input id="cb-lake-query" type="search" value={query}
             onChange={e=>setQuery(e.target.value)} placeholder="Nome italiano, tedesco o ladino…"/>
           <label htmlFor="cb-lake-sort">ORDINA</label>
           <select id="cb-lake-sort" value={sort}
             onChange={e=>setSort(e.target.value as 'name'|'height'|'surface')}>
             <option value="name">Nome</option>
             <option value="height">Quota più alta</option>
             <option value="surface">Superficie OSM maggiore</option>
           </select>
           <span>{shown.length} laghi documentati</span>
         </div>
         {shown.length>0?<div className="cb-atlas-grid">
           {shown.map((lake,i)=><a href={naturalLakeHref(lake.slug)}
             key={lake.id} className="cb-atlas-card">
             <span className="cb-atlas-card-count">{String(i+1).padStart(2,'0')}</span>
             <span className="cb-atlas-kind">{naturalLakeLabel(lake).toUpperCase()}</span>
             {lake.media[0]?.url&&<img className="cb-atlas-card-photo" src={lake.media[0].url}
               alt="" loading="lazy"/>}
             <h2>{lake.name}</h2>
             <strong>{meters(Number(lake.facts.elevationM.value))}</strong>
             <span>{mappedSurface(Number(lake.facts.osmMappedWaterSurfaceKm2.value))}</span>
             <span className="cb-atlas-card-go">SCOPRI IL LAGO ↗</span>
           </a>)}
         </div>:<div className="cb-atlas-empty">
           <h2>{loading?'Caricamento dei laghi…':
             query?'Nessun lago con questo nome.':'L’archivio dei laghi è in verifica.'}</h2>
           <p>Mostriamo soltanto identità, perimetri e immagini che superano il gate editoriale.</p>
         </div>}
       </>}
    </main>
    <SiteFooter/>
  </div>;
}
