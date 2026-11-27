import { useEffect, useMemo, useState } from 'react';
import { AlpineAtlasMap } from './AlpineAtlasMap';
import { AlpinePlaceVisual } from './AlpinePlaceVisual';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { PlaceDetail } from './AlpineAtlasPage';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { loadAlpinePlaces, type AlpinePlace } from '../lib/alpinePlaces';
import { usePageTitle } from '../lib/pageTitle';
import '../alpineExplore.css';

type Section = 'rifugi' | 'bivacchi' | 'paesi';
type Sort = 'richness' | 'altitude' | 'name';
const CONFIG: Record<Section,{kind:AlpinePlace['kind'];title:string;lead:string;kicker:string;singular:string}> = {
  rifugi:{kind:'rifugio',title:'RIFUGI.',lead:'Un tetto sopra la testa, qualche metro sotto i piedi. Cerca una struttura e scopri dove si trova davvero.',kicker:'RIPARO · SOSTA · ACCESSI',singular:'rifugio'},
  bivacchi:{kind:'bivacco',title:'BIVACCHI.',lead:'Pochi comfort e molta montagna. Posizione, accesso dichiarato e sentieri: le informazioni che contano.',kicker:'RIPARI LIBERI · QUOTA',singular:'bivacco'},
  paesi:{kind:'borgo',title:'PAESI.',lead:'Le avventure partono da un posto preciso. Trova la località da cui esplorare i sentieri della zona.',kicker:'LOCALITÀ · PUNTI DI PARTENZA',singular:'paese'},
};
const SECTIONS:Section[]=['rifugi','bivacchi','paesi'];
function fromHash(){
  const match=/^#(rifugi|bivacchi|paesi)(?:\/([^/?]+))?/.exec(window.location.hash);
  if(match)return {section:match[1] as Section,slug:match[2]||null};
  const base=import.meta.env.BASE_URL;
  if(window.location.pathname.startsWith(base)){
    const parts=window.location.pathname.slice(base.length).split('/').filter(Boolean);
    const section=parts[0]==='borghi'?'paesi':parts[0];
    if(parts.length===2&&(section==='rifugi'||section==='bivacchi'||section==='paesi'))
      return {section:section as Section,slug:parts[1]};
  }
  return {section:'rifugi' as Section,slug:null};
}
function score(p:AlpinePlace){
  return Number(Boolean(p.photo))*110+Number(Boolean(p.description))*20+Number(Boolean(p.phone||p.email))*14+
    Number(Boolean(p.website))*10+Number(Boolean(p.operator))*6+Number(p.elevationM!=null)*4;
}
function hasContact(p:AlpinePlace){return Boolean(p.phone||p.email);}

/** Esplorazione coerente con #routes: risultati fotografici, filtri e una mappa dedicata alla sola categoria. */
export function AlpineExplorePage(){
  const [nav,setNav]=useState(fromHash);
  const [data,setData]=useState<AlpinePlace[]>([]);
  const [loaded,setLoaded]=useState(false);
  const [query,setQuery]=useState('');
  const [sort,setSort]=useState<Sort>('richness');
  const [onlyPhoto,setOnlyPhoto]=useState(false);
  const [onlyContacts,setOnlyContacts]=useState(false);
  const [limit,setLimit]=useState(24);
  const [selected,setSelected]=useState<string|null>(null);
  const [mobileTab,setMobileTab]=useState<'list'|'map'>('list');
  const config=CONFIG[nav.section];
  usePageTitle(config.title.replace('.','')+' · Esplora · Cima Becco');
  useEffect(()=>{
    const sync=()=>{setNav(fromHash());window.scrollTo({top:0});};
    window.addEventListener('hashchange',sync);
    return ()=>window.removeEventListener('hashchange',sync);
  },[]);
  useEffect(()=>{let active=true;void loadAlpinePlaces().then(result=>{if(active){setData(result.places);setLoaded(true);}});return()=>{active=false};},[]);
  useEffect(()=>{
    setQuery('');setOnlyPhoto(false);setOnlyContacts(false);setSort('richness');
    setSelected(null);setLimit(24);setMobileTab('list');
  },[nav.section]);
  const places=useMemo(()=>data.filter(p=>p.kind===config.kind),[data,config.kind]);
  const selectedPlace=useMemo(()=>places.find(p=>p.slug===selected)||null,[places,selected]);
  const detail=nav.slug?places.find(p=>p.slug===nav.slug):null;
  const filtered=useMemo(()=>{
    const needle=query.trim().toLocaleLowerCase('it');
    const candidates=places.filter(p=>(!needle||p.name.toLocaleLowerCase('it').includes(needle))&&
      (!onlyPhoto||Boolean(p.photo))&&(!onlyContacts||hasContact(p)));
    return candidates.sort((a,b)=>sort==='name'?a.name.localeCompare(b.name,'it'):
      sort==='altitude'?(b.elevationM??-1)-(a.elevationM??-1)||a.name.localeCompare(b.name,'it'):
      score(b)-score(a)||a.name.localeCompare(b.name,'it'));
  },[places,query,onlyPhoto,onlyContacts,sort]);
  const mapPlaces=useMemo(()=>filtered,[filtered]);
  useEffect(()=>{setLimit(24);setSelected(null);},[query,sort,onlyPhoto,onlyContacts]);
  const onSelect=(p:AlpinePlace)=>{setSelected(p.slug);setMobileTab('map');};
  const count=filtered.length.toLocaleString('it-IT');
  const detailHref=(p:AlpinePlace)=>import.meta.env.BASE_URL+(nav.section==='paesi'?'borghi':nav.section)+'/'+encodeURIComponent(p.slug)+'/';
  return <div className="cb-explore-page">
    {nav.slug ? <>
      <SiteHeader sticky/>
      <main className="cb-explore-detail-shell">
      {detail?<PlaceDetail place={detail} onBack={import.meta.env.BASE_URL+'#'+nav.section} places={places}/>:
      <div className="cb-explore-no-data"><h1>{loaded?'Luogo non trovato':'Caricamento in corso…'}</h1><a href={'#'+nav.section}>Torna all'elenco</a></div>}
      </main>
    </> : <div className="cb-explore-screen">
      <SiteHeader sticky/>
      <div className="cb-explore-overview">
        <div className="cb-explore-overview-inner">
          <div className="cb-explore-heading">
            <h1>{config.title}</h1>
            <p>{config.lead}</p>
          </div>
          <div className="cb-explore-count"><strong>{loaded?places.length.toLocaleString('it-IT'):'…'}</strong><span>LUOGHI IN ARCHIVIO</span></div>
        </div>
        <nav className="cb-explore-categories" aria-label="Categorie da esplorare">
          <a href="#routes">Sentieri</a><a href="#map">Cime</a>
          {SECTIONS.map(key=><a key={key} href={'#'+key} aria-current={nav.section===key?'page':undefined}><AlpinePlaceIcon kind={CONFIG[key].kind} size={18}/>{key==='paesi'?'Paesi':key==='rifugi'?'Rifugi':'Bivacchi'}</a>)}
        </nav>
      </div>
      <main className={'cb-explore-workspace cb-explore-mobile-'+mobileTab}>
        <section className="cb-explore-list" aria-label="Elenco dei luoghi">
          <div className="cb-explore-list-head">
            <label className="cb-explore-search"><span>Cerca per nome</span>
              <input type="search" placeholder={'Cerca un '+config.singular+'…'} value={query} onChange={e=>setQuery(e.target.value)} />
            </label>
            <div className="cb-explore-filters">
              <button type="button" className={onlyPhoto?'active':''} aria-pressed={onlyPhoto} onClick={()=>setOnlyPhoto(v=>!v)}>Con foto</button>
              {nav.section==='rifugi'&&<button type="button" className={onlyContacts?'active':''} aria-pressed={onlyContacts} onClick={()=>setOnlyContacts(v=>!v)}>Con recapiti</button>}
              <label>Ordina <select value={sort} onChange={e=>setSort(e.target.value as Sort)}>
                <option value="richness">Più documentati</option><option value="altitude">Quota più alta</option><option value="name">Nome A–Z</option>
              </select></label>
            </div>
          </div>
          <div className="cb-explore-result-header"><h2>{loaded?count:'…'} {nav.section} <span>in elenco</span></h2>
            <p>Seleziona una scheda per individuarla sulla mappa, poi apri il dettaglio.</p>
          </div>
          {loaded&&!filtered.length&&<div className="cb-explore-empty"><strong>Nessun risultato con questi filtri.</strong><p>Prova a rimuovere il filtro sulle fotografie o a cercare un'altra località.</p><button type="button" onClick={()=>{setOnlyPhoto(false);setOnlyContacts(false);setQuery('');}}>Mostra tutti</button></div>}
          <ul className="cb-explore-grid">
            {filtered.slice(0,limit).map(place=><li key={place.slug} className={selected===place.slug?'cb-explore-card is-selected':'cb-explore-card'}>
              <button type="button" className="cb-explore-card-select" onClick={()=>onSelect(place)} aria-label={'Localizza '+place.name+' sulla mappa'}>
                <AlpinePlaceVisual key={place.slug} place={place} compact/>
                <span className="cb-explore-card-body">
                  <span className="cb-explore-card-kicker"><AlpinePlaceIcon kind={place.kind} size={17}/>{place.kind==='borgo'?'PAESE':place.kind==='bivacco'?'BIVACCO':'RIFUGIO'}</span>
                  <strong className="cb-explore-card-name">{place.name}</strong>
                  <span className="cb-explore-card-meta">{place.operator||'Dolomiti · dati OpenStreetMap'}</span>
                  <span className="cb-explore-card-facts">
                    <span><strong>{place.elevationM!=null?place.elevationM.toLocaleString('it-IT')+' m':'n.d.'}</strong><small>Quota</small></span>
                    {place.capacity!=null&&<span><strong>{place.capacity}</strong><small>Posti indicati</small></span>}
                  </span>
                </span>
              </button>
              <a className="cb-explore-card-detail" href={detailHref(place)}>Apri scheda <span aria-hidden="true">↗</span></a>
            </li>)}
          </ul>
          {filtered.length>limit&&<button type="button" className="cb-explore-more" onClick={()=>setLimit(v=>v+24)}>Mostra altri {Math.min(24,filtered.length-limit)} luoghi ↓</button>}
          <p className="cb-explore-source">Schede basate su dati OpenStreetMap e fonti dichiarate. Le foto vengono mostrate solo se attribuite al luogo e riutilizzabili.</p>
        </section>
        <section className="cb-explore-map-panel" aria-label="Mappa della categoria selezionata">
          <div className="cb-explore-map-topline"><AlpinePlaceIcon kind={config.kind} size={17}/> MAPPA {nav.section.toUpperCase()} <span>{count} RISULTATI</span></div>
          <AlpineAtlasMap places={mapPlaces} kind={config.kind} selected={selectedPlace} height="100%" onSelect={onSelect}/>
          {selectedPlace&&<aside className="cb-explore-map-preview" aria-label={'Selezionato: '+selectedPlace.name}>
            <button type="button" className="cb-explore-preview-close" onClick={()=>setSelected(null)} aria-label="Chiudi anteprima">×</button>
            <AlpinePlaceVisual key={selectedPlace.slug} place={selectedPlace} compact/>
            <div><small>{config.singular.toUpperCase()} · {selectedPlace.elevationM!=null?selectedPlace.elevationM.toLocaleString('it-IT')+' m':'QUOTA N.D.'}</small>
              <strong>{selectedPlace.name}</strong>
              <a href={detailHref(selectedPlace)}>Apri scheda completa ↗</a>
            </div>
          </aside>}
        </section>
        <div className="cb-explore-mobile-switch" role="group" aria-label="Visualizzazione">
          <button type="button" aria-pressed={mobileTab==='list'} onClick={()=>setMobileTab('list')}>Elenco</button>
          <button type="button" aria-pressed={mobileTab==='map'} onClick={()=>setMobileTab('map')}>Mappa</button>
        </div>
      </main>
    </div>}
    <SiteFooter/>
  </div>;
}
