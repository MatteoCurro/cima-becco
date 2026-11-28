/**
 * Catalogue telemetry. Snapshot = facts in the published JSON, NEVER browser
 * usage. History is appended only after a workflow has passed all release gates.
 * A missing earlier point does not mean there were zero records previously.
 */
import {existsSync,readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join,dirname} from 'node:path';
import {fileURLToPath} from 'node:url';

const ROOT=join(dirname(fileURLToPath(import.meta.url)),'..');
const DATA=join(ROOT,'public','data');
const HISTORY=type=>join(DATA,'atlas','import-history-'+type+'-v1.json');
const read=(path)=>existsSync(path)?JSON.parse(readFileSync(path,'utf8')):null;
const file=(name)=>read(join(DATA,name));
const countFacts=(e)=>Object.values(e?.facts||{}).filter(f=>f && f.value!==null&&f.value!==undefined).length;
const countMedia=(es)=>es.reduce((n,e)=>n+(e.media||[]).filter(m=>
    (m.kind==='photo'||m.kind==='historical_photo'||m.kind==='logo') &&
    m.reuseAllowed && m.subjectVerified && m.sourceUrl && m.licence).length,0);
const fact=(e,k)=>e?.facts?.[k]?.value;
const available=(e,k)=>fact(e,k)!==null&&fact(e,k)!==undefined;
const coverage=(es,predicate)=>es.filter(predicate).length;

export function summarizeImportCatalog(){
  const municipalities=file('atlas/municipalities-v1.json');
  const refuges=file('atlas/refuges-v1.json');
  const shelters=file('atlas/shelters-v1.json');
  const places=file('alpine-places.json');
  const routes=file('routes-manifest.json');
  const people=file('atlas/people-v1.json');
  const peopleEntities=people?.entities||[];
  const mun=municipalities?.entities||[];
  const ref=refuges?.entities||[];
  const she=shelters?.entities||[];
  const osm=places?.places||[];
  const all=[...ref,...she];
  const mcover={
    'Quota documentata':coverage(mun,e=>available(e,'quotaCentroM')||available(e,'elevationReportedM')),
    'Altimetria del territorio':coverage(mun,e=>available(e,'altitudineTerritorioMinM')||available(e,'altitudineTerritorioMediaM')||available(e,'altitudineTerritorioMaxM')),
    'Superficie':coverage(mun,e=>available(e,'superficieKm2')),
    'Popolazione ISTAT datata':coverage(mun,e=>available(e,'popolazione')&&available(e,'populationReferenceDate')),
    'Sindaco (DAIT)':coverage(mun,e=>available(e,'sindacoNome')),
    'Sito istituzionale':coverage(mun,e=>available(e,'sitoUfficiale')),
    'Foto attribuita':coverage(mun,e=>(e.media||[]).some(m=>m.kind==='photo'&&m.reuseAllowed&&m.subjectVerified&&m.author&&m.licence)),
    'Testo documentato':coverage(mun,e=>Boolean(e.textSources?.length)),
    'Relazioni territoriali':coverage(mun,e=>(e.relations||[]).length>0),
    'Stemma':coverage(mun,e=>(e.media||[]).some(m=>m.kind==='logo'&&m.reuseAllowed&&m.subjectVerified)),
    'Personaggi documentati':coverage(mun,e=>(e.connectedPeople||[]).some(p=>p.verified)),
    'Figure di montagna':coverage(mun,e=>(e.connectedPeople||[]).some(p=>p.verified&&p.category==='montagna')),
  };
  const sources=[
    {id:'comuni',name:'Comuni ISTAT / DAIT',count:mun.length,
      facts:mun.reduce((s,e)=>s+countFacts(e),0),
      media:countMedia(mun),relations:mun.reduce((s,e)=>s+(e.relations||[]).length,0),
      checkedAt:municipalities?.retrievedAt||null,
      coverage:mcover,denominator:mun.length},
    {id:'rifugi',name:'Rifugi CAI / OSM',count:ref.length,
      facts:ref.reduce((s,e)=>s+countFacts(e),0),media:countMedia(ref),
      relations:ref.reduce((s,e)=>s+(e.relations||[]).length,0),checkedAt:refuges?.generatedAt||refuges?.retrievedAt||null,
      coverage:{'Quota':coverage(ref,e=>available(e,'elevationM')),
                'Posti letto':coverage(ref,e=>available(e,'bedsTotal')),
                'Fotografie':coverage(ref,e=>(e.media||[]).some(m=>m.kind==='photo'&&m.reuseAllowed&&m.subjectVerified))},
      denominator:ref.length},
    {id:'ricoveri',name:'Bivacchi e ricoveri CAI / OSM',count:she.length,
      facts:she.reduce((s,e)=>s+countFacts(e),0),media:countMedia(she),
      relations:she.reduce((s,e)=>s+(e.relations||[]).length,0),checkedAt:shelters?.generatedAt||shelters?.retrievedAt||null,
      coverage:{'Quota':coverage(she,e=>available(e,'elevationM')),
                'Posti dichiarati':coverage(she,e=>available(e,'bedsTotal')),
                'Fotografie':coverage(she,e=>(e.media||[]).some(m=>m.kind==='photo'&&m.reuseAllowed&&m.subjectVerified))},
      denominator:she.length},
    {id:'luoghi',name:'Località OSM (archivio)',count:osm.length,
      facts:0,media:osm.filter(e=>e.photo?.sourceUrl&&e.photo?.license).length,
      relations:0,checkedAt:places?.generatedAt||null,coverage:{},denominator:osm.length},
    {id:'persone',name:'Persone nel grafo (G1)',count:peopleEntities.length,
      facts:0,media:0,relations:peopleEntities.reduce((s,e)=>s+(e.relations||[]).length,0),
      checkedAt:people?.generatedAt||null,
      coverage:{'Con relazione documentata':coverage(peopleEntities,e=>(e.relations||[]).some(r=>r.verified))},
      denominator:peopleEntities.length},
    {id:'sentieri',name:'Sentieri GPX (manifest)',count:Number(routes?.routeCount)||0,
      facts:0,media:0,relations:0,checkedAt:routes?.generatedAt||null,
      coverage:{},denominator:Number(routes?.routeCount)||0},
  ];
  const totalFacts=sources.reduce((sum,s)=>sum+s.facts,0);
  return {
    schemaVersion:'1.0',generatedAt:new Date().toISOString(),
    semantics:'published_catalogue_not_visitor_analytics',
    sources,total:{
      publicEntities:mun.length+ref.length+she.length,
      municipalities:mun.length,refuges:ref.length,shelters:she.length,
      peopleInGraph:peopleEntities.length,
      municipalityPersonRelations:mun.reduce((s,e)=>s+(e.connectedPeople||[]).filter(p=>p.verified).length,0),
      osmPlaces:osm.length,routes:Number(routes?.routeCount)||0,
      sourcedFacts:totalFacts,attributedMedia:countMedia([...mun,...all]),
      documentedRelations:sources.reduce((sum,s)=>sum+s.relations,0)},
    quality:{
      municipalitiesG2:mun.filter(e=>e.quality?.gate==='G2').length,
      missingMunicipalElevation:mun.filter(e=>!(
        available(e,'quotaCentroM')||available(e,'elevationReportedM')||
        available(e,'altitudineTerritorioMinM')||available(e,'altitudineTerritorioMediaM')||
        available(e,'altitudineTerritorioMaxM'))).length,
      missingMunicipalPopulation:mun.filter(e=>!(
        available(e,'popolazione')&&available(e,'populationReferenceDate'))).length,
    }
  };
}
export function importHistory(pipeline){
  const pipelines=pipeline?[pipeline]:['comuni','rifugi-ricoveri'];
  const sources=pipelines.map(p=>read(HISTORY(p)));
  const events=sources.flatMap(doc=>doc?.schemaVersion==='1.0'&&Array.isArray(doc.events)?doc.events:[]);
  events.sort((a,b)=>String(a.recordedAt||'').localeCompare(String(b.recordedAt||'')));
  return {schemaVersion:'1.0',description:'Verified successful import snapshots, no invented history',events};
}
export function appendSuccessfulImport(pipeline,runId,{report=null,sourceSha=null}={}){
  if(!['comuni','rifugi-ricoveri'].includes(pipeline))throw Error('Pipeline sconosciuta');
  if(!runId||!/^[0-9]+$/.test(String(runId)))throw Error('GitHub Actions run ID obbligatorio');
  const snapshot=summarizeImportCatalog();
  const history=importHistory(pipeline);
  if(history.events.some(e=>e.pipeline===pipeline&&e.runId===String(runId)))return history;
  const sourceIds=pipeline==='comuni'?['comuni','persone']:['rifugi','ricoveri'];
  const sources=snapshot.sources.filter(s=>sourceIds.includes(s.id));
  const event={
    runId:String(runId),pipeline,status:'success',recordedAt:new Date().toISOString(),
    sourceSha:sourceSha||null,
    sources:Object.fromEntries(sources.map(s=>[s.id,{count:s.count,facts:s.facts,
      media:s.media,relations:s.relations,coverage:s.coverage,denominator:s.denominator}])),
    report:report&&typeof report==='object'?Object.fromEntries(
      Object.entries(report).filter(([k,v])=>
        ['municipalities','mayorsMatched','daitRowsOfficialCrosswalkRejected',
         'newG2','newMedia','newWikiText','selectedCandidates','publishedG2',
         'metricsAdded','matched','failuresCount',
         'municipalityPeopleLinks','peopleCatalogued','mountainLinks','otherNotableLinks','sourceAltimetryMatched'].includes(k) &&
        (typeof v==='number'||typeof v==='string'))):{},
  };
  // Delta on equivalent source key only. Baseline is null, never "0 new".
  const previous=[...history.events].reverse().find(e=>e.pipeline===pipeline);
  event.delta=Object.fromEntries(sourceIds.map(id=>[id,previous?.sources?.[id]?
    event.sources[id].count-previous.sources[id].count:null]));
  history.events.push(event);
  history.events=history.events.slice(-240);
  const filename=HISTORY(pipeline);
  mkdirSync(dirname(filename),{recursive:true});
  writeFileSync(filename,JSON.stringify(history,null,2)+'\n');
  return history;
}

if(process.argv[1]&&fileURLToPath(import.meta.url)===process.argv[1]){
  const pipeline=process.argv[2],runId=process.argv[3];
  const reportPath=process.argv[4];
  const report=reportPath?read(reportPath):null;
  if(pipeline&&runId) {
    const h=appendSuccessfulImport(pipeline,runId,{report,sourceSha:process.env.GITHUB_SHA||null});
    console.log('Telemetry:',pipeline,'events',h.events.length);
  }else console.log(JSON.stringify(summarizeImportCatalog()));
}
