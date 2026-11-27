import { useEffect, useState } from 'react';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { localInsights, summarizeInsights } from '../lib/analytics';
import { loadAlpinePlaces } from '../lib/alpinePlaces';
import { loadRouteManifest } from '../lib/routeTiles';
import { usePageTitle } from '../lib/pageTitle';
import '../alpineAtlas.css';

function Rank({title,data}:{title:string;data:{name:string;total:number}[]}) {
  const peak=Math.max(1,...data.map(x=>x.total));
  return <section className="cb-insights-rank"><h2>{title}</h2>{data.length
    ?<div className="cb-insights-bars">{data.map((row,i)=><div key={row.name} className="cb-insights-row">
      <span>{i+1}. {row.name}</span><strong>{row.total}</strong>
      <div className="cb-insights-track"><span style={{width:`${row.total/peak*100}%`}}/></div>
    </div>)}</div>
    :<p>Niente dati ancora da questo browser.</p>}
  </section>;
}

export function SiteInsightsPage(){
  usePageTitle('Statistiche Cima Becco · Laboratorio');
  const [snapshot,setSnapshot]=useState(()=>summarizeInsights(localInsights()));
  const [catalog,setCatalog]=useState({routes:0,rifugi:0,borghi:0});
  useEffect(()=>{
    void Promise.all([loadAlpinePlaces(),loadRouteManifest()]).then(([places,routes])=>{
      setCatalog({routes:routes?.routeCount||0,
        rifugi:places.places.filter(p=>p.kind==='rifugio').length,
        borghi:places.places.filter(p=>p.kind==='borgo').length});
    }).catch(()=>undefined);
  },[]);
  return <div className="cb-atlas-page"><SiteHeader sticky/><main className="cb-atlas-shell cb-insights-page">
    <div className="cb-atlas-overline">CIMA BECCO / LABORATORIO DATI</div>
    <h1>NON BASTA CAMMINARE. CONTIAMO ANCHE.</h1>
    <p className="cb-atlas-lead">Un primo cruscotto con dati reali del catalogo e interazioni raccolte <strong>solo in questo browser</strong>.
      Le classifiche globali arriveranno con il database dedicato e la raccolta eventi protetta da limiti e permessi.</p>
    <div className="cb-insights-totals">
      {[['SENTIERI INDICIZZATI',catalog.routes],['RIFUGI',catalog.rifugi],['LOCALITÀ',catalog.borghi],
      ['EVENTI IN QUESTO BROWSER',snapshot.total]].map(([label,value])=>
        <div key={label}><strong>{Number(value).toLocaleString('it-IT')}</strong><span>{label}</span></div>)}
    </div>
    <div className="cb-insights-grid">
      <Rank title="Ricerche più fatte" data={snapshot.searches}/>
      <Rank title="Percorsi più aperti" data={snapshot.routes}/>
      <Rank title="Rifugi e borghi più consultati" data={snapshot.places}/>
      <Rank title="GPX più scaricati" data={snapshot.downloads}/>
      <Rank title="Percorsi salvati" data={snapshot.bookmarks}/>
    </div>
    <p className="cb-insights-note">Le statistiche locali sono conservate in localStorage, senza identificare le persone e senza inviarle a un server.
      Non rappresentano visitatori globali; cancellando i dati del browser si azzerano.</p>
    <button type="button" className="cb-atlas-more" onClick={()=>setSnapshot(summarizeInsights(localInsights()))}>AGGIORNA IL CRUSCOTTO ↺</button>
  </main><SiteFooter/></div>;
}
