import type { ReactNode, MouseEvent } from 'react';
import { homeHref } from '../lib/navigation';
import { EXPLORE_CATEGORIES, type ExploreKind } from '../lib/exploreNavigation';

/** Un solo selettore per l'Atlante, la mappa avanzata e tutte le categorie future.
 * Il livello inferiore accetta gli stessi filtri contestuali già sviluppati. */
export function ExploreNavigation({active,children,onModeChange}:{
  active:ExploreKind;children?:ReactNode;onModeChange?:(value:'routes'|'peaks')=>void
}){
  const activate=(event:MouseEvent<HTMLAnchorElement>,kind:ExploreKind)=>{
    if(onModeChange && (kind==='routes'||kind==='peaks')){
      event.preventDefault();
      onModeChange(kind);
      window.history.replaceState(null,'',homeHref(kind==='routes'?'routes':'map'));
    }
  };
  return <nav className="cb-browse-bar" aria-label="Esplora e filtra le risorse">
    <div className="cb-browse-tabs" role="tablist" aria-label="Tipo di risorsa">
      {EXPLORE_CATEGORIES.map(category=>category.enabled?
        <a key={category.id} className={active===category.id?'is-active':''}
          role="tab" aria-selected={active===category.id} href={homeHref(category.hash)}
          onClick={event=>activate(event,category.id)}>{category.label}</a>:
        <span key={category.id} className="is-upcoming" title="Categoria prevista, dati non ancora disponibili">{category.label}<small>presto</small></span>)}
    </div>
    {children&&<div className="cb-browse-facets" aria-label="Filtri contestuali">{children}</div>}
  </nav>;
}
