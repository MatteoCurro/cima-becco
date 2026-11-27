/** Indice contestuale compatto, sempre nella colonna dei contenuti, non sopra la mappa. */
export interface DetailJumpItem { id:string; label:string; }
export function DetailJumpNav({items}:{items:readonly DetailJumpItem[]}) {
  return <nav className="cb-detail-jump" aria-label="Naviga questa scheda">
    <span className="cb-detail-jump-heading">Vai a</span>
    {items.map(item=><a key={item.id} href={'#'+item.id}>{item.label}</a>)}
  </nav>;
}
