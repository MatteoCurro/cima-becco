import { REFUGE_AMENITIES, refugeFact, refugeServiceFacts } from './refugeEditorial.js';

/** Campi aggiuntivi del registro canonico bivacchi. Solo valori booleani documentati. */
export const BIVOUAC_AMENITIES=Object.freeze([
  {key:'mattressAvailableReported',label:'Materassi'},
  {key:'blanketAvailableReported',label:'Coperte'},
  {key:'stoveAvailableReported',label:'Stufa'},
  {key:'firewoodAvailableReported',label:'Legna per la stufa'},
  {key:'gasAvailableReported',label:'Gas'},
  {key:'toiletAvailableReported',label:'Servizi igienici'},
]);

export const HUT_SERVICE_CHAPTERS={
  rifugio:[
    {id:'ristoro',title:'Ristoro e pernottamento',keys:['meals','kitchen','showers','hotWater','sleepingBagLiner']},
    {id:'energia',title:'Energia e connettività',keys:['wifi','cardPayments','electricity','mobileSignal','solarPower','hydropower','generatorPower']},
    {id:'essenziali',title:'Acqua e servizi essenziali',keys:['waterAvailableReported','drinkingWater','outsideWater','pets','accessibility','defibrillator','accessibleToilets']},
  ],
  bivacco:[
    {id:'riposo',title:'Riposo e dotazioni interne',keys:['mattressAvailableReported','blanketAvailableReported','sleepingBagLiner','showers','hotWater']},
    {id:'calore',title:'Cucina e riscaldamento',keys:['stoveAvailableReported','firewoodAvailableReported','gasAvailableReported','kitchen','meals']},
    {id:'essenziali',title:'Acqua e servizi essenziali',keys:['waterAvailableReported','drinkingWater','outsideWater','toiletAvailableReported','accessibleToilets','pets','accessibility','defibrillator']},
    {id:'energia',title:'Energia e comunicazioni',keys:['electricity','solarPower','generatorPower','hydropower','mobileSignal','wifi','cardPayments']},
  ],
};

/** False è un'assenza esplicita. Null / campi non attribuiti sono ignoti e non vengono mostrati. */
export function hutServiceFacts(place) {
  const base=refugeServiceFacts(place);
  if(place?.kind!=='bivacco') return base;
  const extras=BIVOUAC_AMENITIES.map(item=>({...item,value:refugeFact(place,item.key)}))
    .filter(item=>item.value===true||item.value===false);
  return [...base,...extras];
}
export function hutServiceChapters(place) {
  const items=hutServiceFacts(place);
  const def=HUT_SERVICE_CHAPTERS[place?.kind==='bivacco'?'bivacco':'rifugio'];
  return def.map(chapter=>({...chapter,items:items.filter(item=>chapter.keys.includes(item.key))}))
    .filter(chapter=>chapter.items.length);
}

/** Alias distinti dal nome principale, con lingua/storicità mantenute. */
export function hutAliases(place) {
  const stored=place?.facts?.aliases;
  const raw=(stored?.sourceId||stored?.sourceUrl)?stored.value:null;
  const fromFact=typeof raw==='string'?raw.split(/[;|]/).map(value=>({value:value.trim()})):
    Array.isArray(raw)?raw.filter(value=>typeof value==='string').map(value=>({value})):[]; 
  const names=[...(place?.aliases||[]),...(place?.localNames||[]),...fromFact];
  const seen=new Set([String(place?.name||'').normalize('NFKD').toLocaleLowerCase('it-IT').trim()]);
  return names.filter(item=>{
    const val=String(item?.value||'').trim();
    if(!val)return false;
    const key=val.normalize('NFKD').toLocaleLowerCase('it-IT').trim();
    if(seen.has(key))return false;
    seen.add(key);return true;
  });
}
export function shelterOverview(place) {
  const kind=place?.shelterTypeLabel || 'Bivacco alpino';
  const elevation=refugeFact(place,'elevationM') ??
    (Number.isFinite(place?.elevationM)?place.elevationM:null);
  const beds=refugeFact(place,'bedsTotal') ??
    (Number.isFinite(place?.capacity)?place.capacity:null);
  return kind+(typeof elevation==='number'&&elevation>0
    ? ' a '+elevation.toLocaleString('it-IT')+' metri di quota':'')+
    (typeof beds==='number'&&beds>0?', con '+beds+' posti indicati':'')+
    '. Consultane posizione, caratteristiche e itinerari nei dintorni.';
}
export function shelterSeoDescription(place) {
  const copy=place?.description?.trim() || shelterOverview(place);
  return copy.length>275 ? copy.slice(0,272).replace(/\s+\S*$/,'')+'…':copy;
}
/** Etichette dei gruppi dai registry, per i dettagli tecnici espandibili. */
export const HUT_FACT_GROUP_LABELS=Object.freeze({
  geography:'Geografia e coordinate',management:'Gestione e manutenzione',
  capacity:'Pernottamento e ricovero',services:'Dotazioni aggiuntive',
  safety:'Sicurezza e verifiche',rules:'Regole di utilizzo',
  contact:'Contatti e riferimenti',access:'Accesso e sentieri',
  history:'Storia',identity:'Identità',entity_type:'Tipologia',
  quality:'Qualità dei dati',provenance:'Dati di catalogo',
  name:'Denominazione',names:'Varianti del nome',content:'Descrizione',
});
