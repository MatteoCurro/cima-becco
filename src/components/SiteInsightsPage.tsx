import { useEffect, useMemo, useState } from 'react';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { localInsights, summarizeInsights } from '../lib/analytics';
import { usePageTitle } from '../lib/pageTitle';
import '../alpineAtlas.css';
import './siteInsightsImport.css';

type SourceStats={
  id:string;name:string;count:number;facts:number;media:number;relations:number;
  checkedAt:string|null;coverage:Record<string,number>;denominator:number;
};
type ImportEvent={
  runId:string;pipeline:string;status:string;recordedAt:string;
  sources:Record<string,Pick<SourceStats,'count'|'facts'|'media'|'relations'|'coverage'|'denominator'>>;
  delta?:Record<string,number|null>;report?:Record<string,string|number>;
};
type ImportStats={
  schemaVersion:string;generatedAt:string;sources:SourceStats[];history:ImportEvent[];
  total:{publicEntities:number;municipalities:number;refuges:number;shelters:number;
    routes:number;osmPlaces:number;sourcedFacts:number;attributedMedia:number;documentedRelations:number;
    peopleInGraph:number;municipalityPersonRelations:number};
  quality:{municipalitiesG2:number;missingMunicipalElevation:number;missingMunicipalPopulation:number};
};
type Metric='count'|'facts'|'media'|'relations';
const nf=(n:number)=>n.toLocaleString('it-IT');
const fmtDate=(v:string|null|undefined)=>v&&Number.isFinite(Date.parse(v))
  ?new Intl.DateTimeFormat('it-IT',{day:'2-digit',month:'short',year:'numeric'}).format(new Date(v))
  :'Data non disponibile';
const metricLabels:Record<Metric,string>={
  count:'Schede',facts:'Fatti documentati',media:'Media attribuiti',relations:'Relazioni'};
const sourceHref:Record<string,string>={
  comuni:'/comuni/',rifugi:'/rifugi/',ricoveri:'/bivacchi/',luoghi:'/borghi/',sentieri:'/#routes',persone:'/comuni/'};
const fmtDelta=(v:number|null|undefined)=>v==null?'—':(v>0?'+':'')+nf(v);

function Rank({title,data}:{title:string;data:{name:string;total:number}[]}) {
  const peak=Math.max(1,...data.map(x=>x.total));
  return <section className="cb-insights-rank"><h2>{title}</h2>{data.length
    ?<div className="cb-insights-bars">{data.map((r,i)=><div key={r.name} className="cb-insights-row">
      <span>{i+1}. {r.name}</span><strong>{r.total}</strong>
      <div className="cb-insights-track"><span style={{width:(r.total/peak*100)+'%'}}/></div>
    </div>)}</div>
    :<p>Nessuna attività registrata in questo browser.</p>}
  </section>;
}
function CoverageBars({data,denominator}:{data:Record<string,number>;denominator:number}) {
  return <div className="cb-import-coverage">
    {Object.entries(data).map(([label,count])=>{
      const percent=denominator?Math.round(count/denominator*100):0;
      return <div className="cb-import-coverage-row" key={label}>
        <div><span>{label}</span><strong>{nf(count)}/{nf(denominator)} · {percent}%</strong></div>
        <div className="cb-import-track"><span style={{width:percent+'%'}}/></div>
      </div>;
    })}
  </div>;
}
function TrendPlot({events,pipeline,metric}:{events:ImportEvent[];pipeline:string;metric:Metric}) {
  const key=pipeline==='comuni'?'comuni':'rifugi';
  const points=events.filter(x=>x.pipeline===pipeline&&x.status==='success'&&x.sources?.[key])
    .slice(-48).map(e=>({date:e.recordedAt,value:e.sources[key][metric],run:e.runId}));
  if(points.length<2)return <div className="cb-import-empty-plot">
    <strong>Storico in costruzione</strong>
    <p>{points.length===1?'Il primo snapshot verificato è registrato. Il grafico mostrerà i cambiamenti dai prossimi import.':
      'Non esistono ancora snapshot per questa pipeline. Nessun dato precedente viene inventato.'}</p>
  </div>;
  const max=Math.max(1,...points.map(p=>p.value));
  const min=Math.max(0,Math.min(...points.map(p=>p.value))-(max-Math.min(...points.map(p=>p.value)))*.15);
  const top=max===min?max+1:max+(max-min)*.10;
  const x=(i:number)=>44+i*(666/Math.max(1,points.length-1));
  const y=(value:number)=>185-(value-min)/(top-min)*153;
  const line=points.map((p,i)=>x(i)+','+y(p.value)).join(' ');
  return <div className="cb-import-plot">
    <svg viewBox="0 0 760 225" role="img" aria-label={'Andamento '+metricLabels[metric]+' in '+pipeline+' su '+points.length+' import verificati'}>
      {[0,1,2,3].map(i=>{
        const value=min+(top-min)*(3-i)/3;
        return <g key={i}>
          <line x1="43" x2="716" y1={32+i*51} y2={32+i*51} stroke="#dbe8dc" strokeDasharray="4 5"/>
          <text x="37" y={36+i*51} textAnchor="end" fontSize="11" fill="#657e68">{nf(Math.round(value))}</text>
        </g>;
      })}
      <polyline fill="none" stroke="#c90958" strokeWidth="3.5" strokeLinecap="round" strokeLinejoin="round" points={line}/>
      {points.map((p,i)=><circle key={p.run} cx={x(i)} cy={y(p.value)} r="3.5" fill="#c90958">
        <title>{fmtDate(p.date)+': '+nf(p.value)+' '+metricLabels[metric].toLowerCase()}</title>
      </circle>)}
      <text x="45" y="212" fill="#576c5d" fontSize="11">{fmtDate(points[0].date)}</text>
      <text x="714" y="212" textAnchor="end" fill="#576c5d" fontSize="11">{fmtDate(points[points.length-1].date)}</text>
    </svg>
  </div>;
}
function SourceMix({sources,metric}:{sources:SourceStats[];metric:Metric}) {
  const subset=sources.filter(s=>s.count>0);
  const max=Math.max(1,...subset.map(s=>s[metric]));
  return <div className="cb-import-source-bars">{subset.map(s=>
    <div key={s.id} className="cb-import-source-row">
      <span>{s.name}</span>
      <div className="cb-import-track"><span style={{width:Math.max(0,s[metric]/max*100)+'%'}}/></div>
      <strong>{nf(s[metric])}</strong>
    </div>)}</div>;
}
function LocalUsage(){
  const [snapshot,setSnapshot]=useState(()=>summarizeInsights(localInsights()));
  return <>
    <p className="cb-atlas-lead">Questi conteggi riguardano soltanto questo dispositivo e non rappresentano le visite globali al portale.</p>
    <div className="cb-insights-totals"><div><strong>{nf(snapshot.total)}</strong><span>EVENTI NEL BROWSER</span></div></div>
    <div className="cb-insights-grid">
      <Rank title="Ricerche più frequenti" data={snapshot.searches}/>
      <Rank title="Percorsi più aperti" data={snapshot.routes}/>
      <Rank title="Rifugi e luoghi consultati" data={snapshot.places}/>
      <Rank title="GPX scaricati" data={snapshot.downloads}/>
      <Rank title="Percorsi salvati" data={snapshot.bookmarks}/>
    </div>
    <p className="cb-insights-note">Lo storico locale è conservato nel browser (localStorage) e non identifica visitatori.</p>
    <button type="button" className="cb-atlas-more" onClick={()=>setSnapshot(summarizeInsights(localInsights()))}>
      AGGIORNA I DATI LOCALI ↺
    </button>
  </>;
}
export function SiteInsightsPage(){
  usePageTitle('Statistiche e importatori · Cima Becco');
  const [tab,setTab]=useState<'imports'|'browser'>('imports');
  const [stats,setStats]=useState<ImportStats|null>(null);
  const [error,setError]=useState(false);
  const [pipeline,setPipeline]=useState<'comuni'|'rifugi-ricoveri'>('comuni');
  const [metric,setMetric]=useState<Metric>('count');
  const [sourceMetric,setSourceMetric]=useState<Metric>('count');
  const [selectedSource,setSelectedSource]=useState('comuni');
  useEffect(()=>{
    let active=true;
    void fetch(import.meta.env.BASE_URL+'data/atlas/import-insights-v1.json')
      .then(r=>{if(!r.ok)throw Error('telemetria assente');return r.json() as Promise<ImportStats>;})
      .then(data=>{if(active&&data?.schemaVersion==='1.0'&&Array.isArray(data.sources))setStats(data);})
      .catch(()=>{if(active)setError(true);});
    return ()=>{active=false;};
  },[]);
  const source=useMemo(()=>stats?.sources.find(s=>s.id===selectedSource),[stats,selectedSource]);
  const log=useMemo(()=>(stats?.history||[]).filter(e=>e.status==='success')
    .slice().sort((a,b)=>b.recordedAt.localeCompare(a.recordedAt)).slice(0,12),[stats]);
  const latestComuni=useMemo(()=>(stats?.history||[]).slice().reverse()
    .find(e=>e.pipeline==='comuni'),[stats]);
  return <div className="cb-atlas-page">
    <SiteHeader sticky/>
    <main className="cb-atlas-shell cb-insights-page">
      <div className="cb-atlas-overline">CIMA BECCO / OSSERVATORIO DATI</div>
      <h1>I DATI CRESCONO. LI TENIAMO D'OCCHIO.</h1>
      <p className="cb-atlas-lead">Catalogo, qualità delle schede, provenienza e avanzamento degli importatori. Tutti gli indicatori pubblici sono calcolati dai dataset realmente pubblicati, senza ricostruzioni arbitrarie.</p>
      <div className="cb-import-tabs" role="group" aria-label="Sezione statistiche">
        <button type="button" aria-pressed={tab==='imports'} onClick={()=>setTab('imports')}>Importatori e qualità</button>
        <button type="button" aria-pressed={tab==='browser'} onClick={()=>setTab('browser')}>Attività del browser</button>
      </div>
      {tab==='browser'?<LocalUsage/>:!stats?<section className="cb-import-empty-plot">
        <strong>{error?'Dati di monitoraggio temporaneamente non disponibili':'Caricamento osservatorio…'}</strong>
        <p>{error?'Il catalogo rimane disponibile; nessuna statistica viene simulata.':'Lettura dello snapshot pubblico dei dati.'}</p>
      </section>:<>
        <div className="cb-insights-totals cb-import-totals">
          {[
            ['SCHEDE STRUTTURE + COMUNI',stats.total.publicEntities],
            ['SENTIERI MAPPATI',stats.total.routes],
            ['FATTI CON VALORE',stats.total.sourcedFacts],
            ['MEDIA ATTRIBUITI',stats.total.attributedMedia],
            ['RELAZIONI',stats.total.documentedRelations],
            ['COMUNI G2',stats.quality.municipalitiesG2],
            ['PERSONE NEL GRAFO (G1)',stats.total.peopleInGraph||0],
            ['LEGAMI PERSONA-COMUNE',stats.total.municipalityPersonRelations||0]
          ].map(([label,value])=><div key={label}><strong>{nf(Number(value))}</strong><span>{label}</span></div>)}
        </div>
        <div className="cb-import-section-heading"><div>
          <span>01 / COPERTURA E CATALOGHI</span>
          <h2>Quanto abbiamo importato.</h2>
          <p>Le categorie non sono sommabili senza rischi di doppio conteggio: i luoghi OSM sono l'archivio di base e i dossier CAI/ISTAT hanno identità riconciliate.</p>
        </div><small>Snapshot {fmtDate(stats.generatedAt)}</small></div>
        <div className="cb-insights-grid">
          <section className="cb-insights-rank">
            <h2>Composizione degli archivi</h2>
            <div className="cb-import-chart-controls">
              <label htmlFor="cb-import-mix-metric">Indicatore</label>
              <select id="cb-import-mix-metric" value={sourceMetric} onChange={e=>setSourceMetric(e.target.value as Metric)}>
                {(Object.keys(metricLabels) as Metric[]).map(k=><option key={k} value={k}>{metricLabels[k]}</option>)}
              </select>
            </div>
            <SourceMix sources={stats.sources} metric={sourceMetric}/>
            <p className="cb-insights-note">I campi non applicabili a un dataset compaiono a zero, non sono stimati.</p>
          </section>
          <section className="cb-insights-rank">
            <h2>Qualità per tipologia</h2>
            <div className="cb-import-chart-controls">
              <label htmlFor="cb-import-source">Archivio</label>
              <select id="cb-import-source" value={selectedSource} onChange={e=>setSelectedSource(e.target.value)}>
                {stats.sources.filter(s=>Object.keys(s.coverage).length).map(s=><option key={s.id} value={s.id}>{s.name}</option>)}
              </select>
            </div>
            {source&&Object.keys(source.coverage).length?<CoverageBars data={source.coverage} denominator={source.denominator}/>:
              <p>Copertura analitica non disponibile per questo archivio.</p>}
            <p className="cb-insights-note">Percentuali sulle schede pubblicate, non sulla copertura nazionale.</p>
          </section>
        </div>
        <div className="cb-import-section-heading"><div>
          <span>02 / ANDAMENTO IMPORTATORI</span>
          <h2>Come cambiano i dati.</h2>
          <p>Ogni punto deriva da un'importazione effettiva e superata. Gli snapshot precedenti all'avvio di questo registro non vengono ricostruiti.</p>
        </div></div>
        <section className="cb-insights-rank cb-import-wide">
          <div className="cb-import-chart-controls">
            <label htmlFor="cb-import-pipeline">Importatore</label>
            <select id="cb-import-pipeline" value={pipeline} onChange={e=>setPipeline(e.target.value as 'comuni'|'rifugi-ricoveri')}>
              <option value="comuni">Comuni ISTAT / DAIT / Wikimedia</option>
              <option value="rifugi-ricoveri">Rifugi e bivacchi CAI / OSM</option>
            </select>
            <label htmlFor="cb-import-metric">Misura</label>
            <select id="cb-import-metric" value={metric} onChange={e=>setMetric(e.target.value as Metric)}>
              {(Object.keys(metricLabels) as Metric[]).map(k=><option key={k} value={k}>{metricLabels[k]}</option>)}
            </select>
          </div>
          <TrendPlot events={stats.history||[]} pipeline={pipeline} metric={metric}/>
        </section>
        <div className="cb-insights-grid">
          <section className="cb-insights-rank">
            <h2>Completezza dei Comuni</h2>
            <p className="cb-import-big-number">{nf(stats.total.municipalities)} <small>schede G2 pubblicate</small></p>
            {latestComuni?.report?.municipalities!=null&&<p>Su {nf(Number(latestComuni.report.municipalities))} comuni presenti nell'ultimo snapshot ISTAT.</p>}
            <p>{nf(stats.quality.missingMunicipalElevation)} schede senza quota documentata;
              {' '}{nf(stats.quality.missingMunicipalPopulation)} senza popolazione ISTAT datata.</p>
            <p>{nf(stats.total.peopleInGraph||0)} profili persona G1 e {nf(stats.total.municipalityPersonRelations||0)} relazioni documentate persona–comune. Non equivalgono a biografie G2 indicizzate.</p>
            <p className="cb-insights-note">I livelli G0/G1 non diventano automaticamente pagine indicizzate. I dati DEM 2021 misurano il territorio, non il centro comunale.</p>
          </section>
          <section className="cb-insights-rank">
            <h2>Ultimo lotto comunale</h2>
            {latestComuni?<div className="cb-import-last-run">
              <strong>{fmtDate(latestComuni.recordedAt)}</strong>
              <span>Nuovi G2: {latestComuni.report?.newG2!=null?nf(Number(latestComuni.report.newG2)):'n.d.'}</span>
              <span>Nuovi media: {latestComuni.report?.newMedia!=null?nf(Number(latestComuni.report.newMedia)):'n.d.'}</span>
              <span>DAIT da revisione: {latestComuni.report?.daitRowsOfficialCrosswalkRejected!=null?nf(Number(latestComuni.report.daitRowsOfficialCrosswalkRejected)):'n.d.'}</span>
              <span>Relazioni con personaggi: {latestComuni.report?.municipalityPeopleLinks!=null?nf(Number(latestComuni.report.municipalityPeopleLinks)):'n.d.'}</span>
              <span>Quote territoriali associate: {latestComuni.report?.sourceAltimetryMatched!=null?nf(Number(latestComuni.report.sourceAltimetryMatched)):'n.d.'}</span>
              <a href={'https://github.com/MatteoCurro/cima-becco/actions/runs/'+latestComuni.runId} target="_blank" rel="noopener noreferrer">Apri esecuzione GitHub Actions ↗</a>
            </div>:<p>Il primo registro degli importatori sarà alimentato dal prossimo rilascio verificato.</p>}
          </section>
        </div>
        <div className="cb-import-section-heading"><div><span>03 / REGISTRO</span><h2>Ultime acquisizioni con esito positivo.</h2></div></div>
        <section className="cb-insights-rank cb-import-wide">
          {log.length?<div className="cb-import-log-wrap"><table className="cb-import-log">
            <thead><tr><th>Data</th><th>Importatore</th><th>Schede</th><th>Variazione netta</th><th>CI</th></tr></thead>
            <tbody>{log.map(e=>{
              const sourceId=e.pipeline==='comuni'?'comuni':'rifugi';
              const source=e.sources?.[sourceId];
              return <tr key={e.pipeline+e.runId}>
                <td>{fmtDate(e.recordedAt)}</td><td>{e.pipeline==='comuni'?'Comuni':'Rifugi / ricoveri'}</td>
                <td>{source?nf(source.count):'—'}</td><td>{fmtDelta(e.delta?.[sourceId])}</td>
                <td><a href={'https://github.com/MatteoCurro/cima-becco/actions/runs/'+e.runId} target="_blank" rel="noopener noreferrer">Verifica ↗</a></td>
              </tr>;
            })}</tbody>
          </table></div>:<p>Lo storico degli import parte dal primo workflow instrumentato; nessun andamento precedente è inventato.</p>}
        </section>
        <div className="cb-import-section-heading"><div><span>04 / ESPLORA GLI ARCHIVI</span><h2>Dai numeri alle schede.</h2></div></div>
        <div className="cb-import-source-links">{stats.sources.map(s=><a key={s.id} href={sourceHref[s.id]}>
          <strong>{s.name}</strong><span>{nf(s.count)} record nella vista</span>
          <small>Ultimo aggiornamento: {fmtDate(s.checkedAt)}</small>
        </a>)}</div>
        <p className="cb-insights-note">Dati tecnici: gli import riusciti sono tracciati nei JSON pubblici dopo i quality gate. Gli errori di esecuzione (job non conclusi o falliti) si verificano su GitHub Actions; non sono conteggiati come successi. Le visite al portale non sono incluse in queste statistiche.</p>
      </>}
    </main>
    <SiteFooter/>
  </div>;
}
