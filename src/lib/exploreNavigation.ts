import { homeHref } from './navigation';

/** Sorgente unica delle categorie: menu, tab, URL e future estensioni. */
export type ExploreKind = 'routes'|'peaks'|'passi'|'rifugi'|'bivacchi'|'paesi'|'trekking'|'falesie'|'palestre';
export const EXPLORE_CATEGORIES: ReadonlyArray<{
  id:ExploreKind;label:string;menuLabel:string;hash:string;enabled:boolean;group:'Percorsi'|'Luoghi'|'Arrampicata';
}> = [
  {id:'routes',label:'Sentieri',menuLabel:'Sentieri e ferrate',hash:'routes',enabled:true,group:'Percorsi'},
  {id:'trekking',label:'Trekking',menuLabel:'Trekking e Alte Vie',hash:'atlante/trekking',enabled:true,group:'Percorsi'},
  {id:'peaks',label:'Cime',menuLabel:'Cime e montagne',hash:'map',enabled:true,group:'Luoghi'},
  {id:'passi',label:'Passi',menuLabel:'Passi e valichi',hash:'passi',enabled:true,group:'Luoghi'},
  {id:'rifugi',label:'Rifugi',menuLabel:'Rifugi',hash:'rifugi',enabled:true,group:'Luoghi'},
  {id:'bivacchi',label:'Bivacchi',menuLabel:'Bivacchi',hash:'bivacchi',enabled:true,group:'Luoghi'},
  {id:'paesi',label:'Paesi',menuLabel:'Paesi di montagna',hash:'paesi',enabled:true,group:'Luoghi'},
  {id:'falesie',label:'Falesie',menuLabel:'Falesie',hash:'falesie',enabled:false,group:'Arrampicata'},
  {id:'palestre',label:'Palestre',menuLabel:'Palestre di arrampicata',hash:'palestre',enabled:false,group:'Arrampicata'},
];
export const exploreGroups = (['Percorsi','Luoghi','Arrampicata'] as const).map(title=>({
  title,items:EXPLORE_CATEGORIES.filter(category=>category.group===title).map(category=>({
    label:category.menuLabel,href:category.enabled?homeHref(category.hash):null,
  })),
}));
