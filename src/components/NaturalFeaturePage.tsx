import { useEffect, useMemo, useState } from 'react';
import type { Route } from '../types';
import type { AlpinePlace } from '../lib/alpinePlaces';
import { placeBounds } from '../lib/alpinePlaces';
import { loadNaturalPasses, naturalPassUrl, naturalPassLabel, type NaturalPass, type NaturalPassDataset } from '../lib/naturalPassRelease';
import { loadRoutesInBounds } from '../lib/routeTiles';
import { routesNear } from '../lib/routes';
import { loadAlpineWater, alpineWaterNear, type AlpineWaterPoint } from '../lib/alpineWater';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { ExploreNavigation } from './ExploreNavigation';
import { DetailLayout, DetailFacts, DetailMetrics, DetailSectionHeading } from './DetailPrimitives';
import { AlpineAtlasMap } from './AlpineAtlasMap';
import { AlpineWeatherPanel } from './AlpineWeatherPanel';
import { AtlasRouteGroup } from './AtlasRouteGroup';
import { DetailJumpNav } from './DetailJumpNav';
import { MapContextLabel } from './MapContextLabel';
import { WaterNearbyList } from './WaterNearbyList';
import { scrollToDetailSection } from '../lib/detailNavigation';
import { usePageTitle } from '../lib/pageTitle';
import { track } from '../lib/analytics';
import '../alpineAtlas.css';
import '../alpineExplore.css';
import '../locationProfile.css';

const NO_ALPINE_PLACES:AlpinePlace[]=[];
const DATA_EMPTY:NaturalPassDataset={generatedAt:null,features:[]};

function routeSlug():string|null{
  const hash=/^#passi(?:\/([a-z0-9-]+))?$/.exec(window.location.hash);
  if(hash)return hash[1]||null;
  const base=import.meta.env.BASE_URL;
  if(!window.location.pathname.startsWith(base))return null;
  const parts=window.location.pathname.slice(base.length).split('/').filter(Boolean);
  if(parts[0]!=='passi'||parts.length!==2)return null;
  return /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(parts[1])?parts[1]:null;
}
const alt=(value:number)=>value.toLocaleString('it-IT',{maximumFractionDigits:1})+' m';
const coordinate=(value:number)=>value.toFixed(5);
const relationUrl=(target:{kind:string;slug?:string}):string|null=>{
  if(!target.slug || !/^[a-z0-9-]+$/.test(target.slug))return null;
  const folder=target.kind==='refuge'?'rifugi':
    target.kind==='bivouac'?'bivacchi':
    target.kind==='settlement'?'borghi':
    target.kind==='summit'?'cime':null;
  return folder?import.meta.env.BASE_URL+folder+'/'+encodeURIComponent(target.slug)+'/':null;
};

function PassDetail({feature}: {feature:NaturalPass}){
  const [routes,setRoutes]=useState<Route[]>([]);
  const [routesPending,setRoutesPending]=useState(true);
  const [water,setWater]=useState<AlpineWaterPoint[]>([]);
  const [waterSlug,setWaterSlug]=useState<string|null>(null);
  const point=feature.geo.point;
  useEffect(()=>{
    let active=true;setRoutes([]);setRoutesPending(true);
    void loadRoutesInBounds(placeBounds({lat:point.lat,lng:point.lng},4))
      .then(results=>{if(active)setRoutes(routesNear(results,point.lng,point.lat,1600,14));})
      .catch(()=>{if(active)setRoutes([]);})
      .finally(()=>{if(active)setRoutesPending(false);});
    return ()=>{active=false;};
  },[point.lat,point.lng]);
  useEffect(()=>{
    let active=true;setWater([]);setWaterSlug(null);
    void loadAlpineWater().then(doc=>{
      if(active)setWater(alpineWaterNear(doc.sources,point.lng,point.lat,1800,16));
    });
    return ()=>{active=false;};
  },[point.lat,point.lng]);
  useEffect(()=>{track('atlas_pass_view',feature.slug);},[feature.slug]);
  const lead=feature.textSources?.find(x=>x.sourceId.startsWith('wikipedia:it:'))?.text ||
    feature.description;
  const photo=feature.media.find(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed);
  const elevation=feature.facts.elevationM;
  const otherElevation=feature.facts.wikidataElevationReportedM;
  const alternative=feature.factsAlternatives?.find(x=>x.key==='elevationM'&&
    typeof x.fact.value==='number'&&x.fact.value!==elevation.value);
  const linked=(feature.relations||[]).filter(r=>r.type==='near'&&r.target?.name&&
    typeof r.straightLineKm==='number').sort((a,b)=>(a.straightLineKm??0)-(b.straightLineKm??0));
  const metrics=[
    {label:elevation.method==='estimated'?'Quota GeoNames · stima DEM':'Quota GeoNames · registrata',
     value:alt(Number(elevation.value))},
    {label:'Tracce cartografiche vicine',value:routesPending?'…':routes.length},
    {label:'Risorse idriche nella zona',value:water.length},
  ];
  const detailRows=[
    {label:'Tipologia',value:naturalPassLabel(feature)},
    {label:'Coordinate WGS84',value:coordinate(point.lat)+', '+coordinate(point.lng)},
    ...(typeof otherElevation?.value==='number'&&otherElevation.value!==elevation.value
       ?[{label:'Quota riportata da Wikidata',value:alt(otherElevation.value)}]:[]),
    ...(alternative&&typeof alternative.fact.value==='number'
       ?[{label:'Quota nella voce enciclopedica',value:alt(alternative.fact.value)}]:[]),
    ...(feature.localNames?.length?[{label:'Altri toponimi documentati',
       value:feature.localNames.slice(0,8).map(a=>a.value).join(' · ')}]:[]),
  ];
  return <DetailLayout
    backHref={import.meta.env.BASE_URL+'passi/'}
    backLabel="Tutti i passi"
    sidebarLabel={'Mappa del valico '+feature.name}
    sidebar={<section id="cb-pass-map" tabIndex={-1} className="cb-location-side-map">
      <MapContextLabel kicker="CARTOGRAFIA ALPINA" title={feature.name}/>
      <AlpineAtlasMap places={NO_ALPINE_PLACES} kind="borgo"
        selectedPoint={{...point,name:feature.name,icon:'◇'}}
        water={water} selectedWaterSlug={waterSlug} onWaterSelect={setWaterSlug}
        routes={routes} height="100%" caption={feature.name}/>
    </section>}
  >
    <header className="cb-location-hero">
      <div className="cb-location-hero-copy">
        <span className="cb-atlas-kind">{naturalPassLabel(feature).toUpperCase()}</span>
        <h1>{feature.name}</h1>
        {Boolean(feature.localNames?.length)&&<p className="cb-location-muted-note">
          Noto anche come {feature.localNames?.slice(0,4).map(a=>a.value).join(' · ')}
        </p>}
        <p className="cb-location-lead">{feature.shortSummary||lead.slice(0,200)}</p>
        <DetailMetrics label="Dati essenziali del valico" items={metrics}/>
        <div className="cb-location-actions">
          <button type="button" className="cb-location-action-primary"
            onClick={()=>scrollToDetailSection('cb-pass-map')}>ESPLORA SULLA MAPPA</button>
        </div>
      </div>
      <figure className="cb-location-hero-media">
        {photo?.url?<img src={photo.url} alt={'Immagine documentata associata a '+feature.name}
          loading="eager" decoding="async"/>:null}
        <figcaption>{photo?.caption||'Immagine documentata del territorio'}</figcaption>
      </figure>
    </header>
    <DetailJumpNav items={[
      {id:'cb-pass-essential',label:'Dati',icon:'compass'},
      {id:'cb-pass-about',label:'Il luogo',icon:'mountain'},
      {id:'cb-pass-nearby',label:'Dintorni',icon:'location-dot'},
      {id:'cb-pass-routes',label:'Sentieri',icon:'route'},
      ...(water.length?[{id:'cb-pass-water',label:'Acqua',icon:'water' as const}]:[]),
      {id:'cb-pass-weather',label:'Meteo',icon:'compass'},
      {id:'cb-pass-map',label:'Mappa',icon:'map'},
    ]}/>
    <section id="cb-pass-essential" className="cb-detail-group cb-detail-group--first cb-location-section">
      <DetailSectionHeading kicker="01 / DATI ESSENZIALI" title="IL VALICO IN CIFRE."
        description="Quote e denominazioni mantengono distinta la fonte registrata dalla stima DEM e dalle informazioni enciclopediche."/>
      <DetailFacts rows={detailRows}/>
    </section>
    <section id="cb-pass-about" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="02 / TERRITORIO" title="FRA DUE VERSANTI."/>
      <p className="cb-location-story">{lead}</p>
    </section>
    {linked.length>0&&<section id="cb-pass-nearby" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="03 / LUOGHI COLLEGATI" title="NEI DINTORNI."
        description="Relazioni geografiche basate sulla distanza in linea d’aria: non attestano un passaggio o un accesso."/>
      <div className="cb-atlas-grid">
        {linked.slice(0,8).map(r=><div className="cb-atlas-card" key={r.target.id+':'+r.type}>
          <strong>{r.target.name}</strong>
          <span>{r.straightLineKm?.toLocaleString('it-IT',{maximumFractionDigits:1})} km in linea d'aria</span>
          {relationUrl(r.target)&&<a href={relationUrl(r.target)!}>Apri scheda del luogo</a>}
        </div>)}
      </div>
    </section>}
    <section id="cb-pass-routes" className="cb-detail-group cb-location-section">
      <DetailSectionHeading kicker="04 / CARTOGRAFIA ESCURSIONISTICA" title="SENTIERI NELLA ZONA."
        description="Tracce GPX vicine alla posizione cartografata: non confermano attraversamento, apertura del passo o accessibilità."/>
      {routesPending?<p className="cb-atlas-loading">Ricerco le tracce disponibili nella zona…</p>:
        routes.length?<AtlasRouteGroup title="TRACCE CARTOGRAFICHE VICINE" items={routes}/>:
        <p className="cb-location-muted-note">Nessuna traccia indicizzata nelle immediate vicinanze; non significa che non esistano percorsi.</p>}
    </section>
    {water.length>0&&<section id="cb-pass-water" className="cb-detail-group cb-location-section cb-location-water">
      <DetailSectionHeading kicker="05 / PUNTI D’ACQUA" title="ACQUA NEI DINTORNI."
        description="Le sorgenti e fontane provengono dal catalogo acqua esistente. La prossimità non prova accessibilità o disponibilità; la potabilità è un dato distinto."/>
      <WaterNearbyList points={water} selectedSlug={waterSlug}
        onSelect={slug=>{setWaterSlug(slug);scrollToDetailSection('cb-pass-map');}}/>
    </section>}
    <section id="cb-pass-weather" className="cb-detail-group cb-location-section">
      <AlpineWeatherPanel lat={point.lat} lng={point.lng} name={feature.name}/>
    </section>
    <footer className="cb-location-credits">
      I dati sono indicativi e documentati per fonte; verificare segnaletica, condizioni locali e avvisi ufficiali prima di intraprendere un percorso.
    </footer>
  </DetailLayout>;
}

export function NaturalFeaturePage(){
  const [slug,setSlug]=useState(routeSlug);
  const [dataset,setDataset]=useState<NaturalPassDataset>(DATA_EMPTY);
  const [loaded,setLoaded]=useState(false);
  const [query,setQuery]=useState('');
  const [order,setOrder]=useState<'name'|'height'>('name');
  useEffect(()=>{
    let active=true;
    void loadNaturalPasses().then(data=>{if(active){setDataset(data);setLoaded(true);}});
    return ()=>{active=false;};
  },[]);
  useEffect(()=>{
    const onHash=()=>{setSlug(routeSlug());setQuery('');window.scrollTo({top:0});};
    window.addEventListener('hashchange',onHash);
    return ()=>window.removeEventListener('hashchange',onHash);
  },[]);
  const features=dataset.features;
  const current=slug?features.find(f=>f.slug===slug):null;
  const shown=useMemo(()=>features.filter(f=>
    [f.name,...(f.aliases||[]).map(x=>x.value),...(f.localNames||[]).map(x=>x.value)]
      .some(name=>name.toLocaleLowerCase('it').includes(query.toLocaleLowerCase('it'))))
    .sort((a,b)=>order==='height'
      ?Number(b.facts.elevationM.value)-Number(a.facts.elevationM.value)
      :a.name.localeCompare(b.name,'it')),[features,query,order]);
  usePageTitle((current?current.name:'Passi di montagna')+' · Cima Becco');
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <ExploreNavigation active="passi"/>
    <main className={slug?'cb-atlas-shell cb-atlas-shell--detail':'cb-atlas-shell'}>
      {current?<PassDetail feature={current}/>:
       slug?<div className="cb-atlas-empty"><h1>Valico non disponibile.</h1>
           <p>Questa scheda non ha ancora superato i controlli di qualità dell'Atlante.</p>
           <a href={import.meta.env.BASE_URL+'passi/'}>Vai ai passi verificati</a>
         </div>:
       <>
         <div className="cb-atlas-overline">CIMA BECCO / LUOGHI / PASSI</div>
         <div className="cb-atlas-intro">
           <div><span className="cb-atlas-eyebrow">VALICHI / FORCELLE / TERRITORIO</span>
             <h1>DA UN VERSANTE ALL'ALTRO.</h1>
             <p>Passi documentati, quote confrontate e luoghi connessi. La mappa non sostituisce informazioni aggiornate su viabilità, sentieri e divieti.</p>
           </div>
           <div className="cb-atlas-intro-symbol" aria-hidden="true">◇</div>
         </div>
         {features.length>0&&<section className="cb-atlas-list-map">
           <div className="cb-atlas-section-top"><span>VALICHI DOCUMENTATI</span>
             <h2>UNA MAPPA, MOLTI PASSAGGI.</h2></div>
           <AlpineAtlasMap places={NO_ALPINE_PLACES} kind="borgo"
             naturalPoints={features.map(f=>({slug:f.slug,name:f.name,
               lat:f.geo.point.lat,lng:f.geo.point.lng,subtype:f.subtype}))}
             height={350} caption="Passi e valichi alpini"/>
         </section>}
         <div className="cb-atlas-toolbar">
           <label htmlFor="cb-pass-query">CERCA UN PASSO</label>
           <input id="cb-pass-query" type="search" value={query}
             onChange={e=>setQuery(e.target.value)} placeholder="Nome italiano, tedesco o ladino…"/>
           <label htmlFor="cb-pass-sort">ORDINA</label>
           <select id="cb-pass-sort" value={order} onChange={e=>setOrder(e.target.value as 'name'|'height')}>
             <option value="name">Nome</option>
             <option value="height">Quota più alta</option>
           </select>
           <span>{shown.length} valichi verificati</span>
         </div>
         {shown.length>0?<div className="cb-atlas-grid">
           {shown.map((feature,i)=><a className="cb-atlas-card" key={feature.id}
             href={naturalPassUrl(feature.slug)}>
             <span className="cb-atlas-card-count">{String(i+1).padStart(2,'0')}</span>
             <span className="cb-atlas-kind">{naturalPassLabel(feature).toUpperCase()}</span>
             {feature.media[0]?.url&&<img className="cb-atlas-card-photo"
               src={feature.media[0].url} alt="" loading="lazy"/>}
             <h2>{feature.name}</h2>
             <strong>{alt(Number(feature.facts.elevationM.value))}</strong>
             <span className="cb-atlas-card-go">SCOPRI IL VALICO ↗</span>
           </a>)}
         </div>:<div className="cb-atlas-empty">
           <h2>{!loaded?'Caricamento dei passi…':query?'Nessun passo con questo nome.':'L’archivio dei passi è in fase di verifica.'}</h2>
           <p>Mostriamo solo i dossier che hanno superato i controlli su identità, fotografia e provenienza.</p>
         </div>}
       </>}
    </main>
    <SiteFooter/>
  </div>;
}
