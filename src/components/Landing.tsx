import { useEffect, useMemo, useRef, useState } from 'react';
import type { Route } from '../types';
import { SiteSearch } from './SearchBar';
import { loadDataset, type Dataset } from '../lib/venues';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { mixByDifficulty, routeHasElevation } from '../lib/routes';
import { trailTitle, trailMood, trailArea } from '../lib/routeEditorial';
import { ChevronLeftIcon, ChevronRightIcon } from './icons';
import { RouteThumb } from './RouteThumb';
import { ActivityTag } from './ActivityIcon';
import { routeActivity } from '../lib/routeAnalysis';
import { errorText } from '../lib/api';
import { TrailHero } from './TrailHero';
import { RouteBookmarkButton } from './RouteBookmarkButton';
import { useUnits } from './UnitsContext';
import { HomeEditorial } from './HomeEditorial';

const ROUTES_LINK = '#routes';

/**
 * The landing is now an editorial entrance to G2-rich atlas entities,
 * not a second world-peak index. The operational routes carousel remains.
 */
export function Landing() {
  const [dataset,setDataset]=useState<Dataset|null>(null);
  const [loadError,setLoadError]=useState<string|null>(null);
  const [featuredRoutes,setFeaturedRoutes]=useState<Route[]|null>(null);
  useEffect(()=>{
    let active=true;
    void loadDataset().then(d=>{if(active)setDataset(d);})
      .catch((error:unknown)=>{if(active)setLoadError(errorText(error));});
    void fetch(import.meta.env.BASE_URL+'data/featured-routes.json')
      .then(response=>response.ok?response.json() as Promise<{routes:Route[]}>:null)
      .then(doc=>{if(active)setFeaturedRoutes(Array.isArray(doc?.routes)?doc.routes:[]);})
      .catch(()=>{if(active)setFeaturedRoutes([]);});
    return()=>{active=false;};
  },[]);
  const routes=useMemo(()=>featuredRoutes
    ? mixByDifficulty(featuredRoutes.length?featuredRoutes:dataset?.routes??[])
    : dataset?.routes?mixByDifficulty(dataset.routes):null,[dataset,featuredRoutes]);
  return <div className="home">
    <SiteHeader sticky center={<SiteSearch/>}/>
    <TrailHero/>
    <main className="home-shell home-main">
      <HomeEditorial routes={featuredRoutes??dataset?.routes??[]}/>
      {loadError&&<section className="home-load-error" role="alert">
        <h2>La mappa si prende una pausa. Non ci piace nemmeno a noi.</h2>
        <p>{loadError}</p>
        <button type="button" className="btn btn-light" onClick={()=>window.location.reload()}>Riprova</button>
      </section>}
      <Row title="Pessime idee per il weekend" link={ROUTES_LINK} loading={!routes}>
        {routes?.map((route,i)=><RouteTile key={route.slug} route={route} index={i}/>)}
      </Row>
      <div className="home-more">
        <a className="btn btn-light" href="#map">Esplora la mappa delle montagne</a>
      </div>
    </main>
    <SiteFooter/>
  </div>;
}

/** Keep the existing accessible and keyboard-scrollable route carousel. */
function Row({title,link,loading,children}:{
  title:string;link:string;loading:boolean;children:React.ReactNode;
}) {
  const trackRef=useRef<HTMLDivElement>(null);
  const [edges,setEdges]=useState({start:true,end:false});
  const update=()=>{
    const el=trackRef.current;
    if(!el)return;
    setEdges({start:el.scrollLeft<4,end:el.scrollLeft+el.clientWidth>=el.scrollWidth-4});
  };
  useEffect(update,[loading,children]);
  useEffect(()=>{
    const el=trackRef.current;
    if(!el)return;
    const onWheel=(event:WheelEvent)=>{
      if(!event.shiftKey||Math.abs(event.deltaY)<=Math.abs(event.deltaX)||
        el.scrollWidth<=el.clientWidth+2)return;
      event.preventDefault();
      el.scrollLeft+=event.deltaY;
    };
    el.addEventListener('wheel',onWheel,{passive:false});
    return()=>el.removeEventListener('wheel',onWheel);
  },[]);
  return <section className="home-row">
    <header className="home-row-head">
      <h2 className="home-row-heading">
        <a className="home-row-title" href={link}>{title}<ChevronRightIcon size={14}/></a>
      </h2>
      <div className="home-row-nav">
        <button type="button" aria-label="Scorri a sinistra" disabled={edges.start}
          onClick={()=>trackRef.current?.scrollBy({left:-trackRef.current.clientWidth*.9,behavior:'smooth'})}>
          <ChevronLeftIcon size={12}/>
        </button>
        <button type="button" aria-label="Scorri a destra" disabled={edges.end}
          onClick={()=>trackRef.current?.scrollBy({left:trackRef.current.clientWidth*.9,behavior:'smooth'})}>
          <ChevronRightIcon size={12}/>
        </button>
      </div>
    </header>
    <div className="home-row-track" ref={trackRef} onScroll={update} tabIndex={0}
      role="region" aria-label={'Esplora: '+title}>
      {loading?Array.from({length:7},(_,i)=><div key={i} className="tile skeleton-card"
        aria-hidden="true"><span className="sk-thumb"/><span className="sk-line"/>
        <span className="sk-line"/></div>):<>
        {children}
        <a className="tile tile-see-all" href={link} aria-label={'Vedi tutte: '+title}>
          <span className="tile-media"><span className="see-all-card">
            <span className="see-all-arrow" aria-hidden="true"><ChevronRightIcon size={20}/></span>
            <span className="see-all-label">VEDI TUTTO</span>
          </span></span>
        </a>
      </>}
    </div>
  </section>;
}
function RouteTile({route,index}:{route:Route;index:number}) {
  const units=useUnits(),region=trailArea(route),mood=trailMood(route);
  return <div className="tile-wrap">
    <a href={import.meta.env.BASE_URL+'route/'+encodeURIComponent(route.slug)+'/'}
      className="tile" style={{'--i':index} as React.CSSProperties}>
      <span className="tile-media">
        <RouteThumb route={route}/>
        {mood.quip&&<span className={'tile-badge cb-tile-slang cb-tile-slang--'+mood.level}
          title={mood.label}>{mood.quip}</span>}
      </span>
      <span className="tile-top">
        <span className="tile-name">{trailTitle(route)}</span>
        <ActivityTag activity={routeActivity(route)}/>
      </span>
      <span className="tile-meta">{[region,route.loop?'Anello':'Percorso lineare'].filter(Boolean).join(' · ')}</span>
      <span className="tile-meta">
        <strong>{units.distance(route.distanceM)}</strong> · <strong>
          {routeHasElevation(route)?units.height(route.gainM)+' di salita':'Dislivello da stimare'}
        </strong>
      </span>
    </a>
    <RouteBookmarkButton route={route} variant="card"/>
  </div>;
}
