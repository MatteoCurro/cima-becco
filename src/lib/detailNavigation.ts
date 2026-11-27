/** La navigazione interna non usa hash: # è riservato al router SPA.
 * Cerca lo scroll container corretto (la pagina o l'overlay della cima)
 * e calcola la vera altezza dell'header sticky, senza costanti per device. */
export function scrollToDetailSection(id:string,behavior?:ScrollBehavior):boolean {
  const target=document.getElementById(id);
  if(!target)return false;
  const reduceMotion=window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const mode=behavior??(reduceMotion?'auto':'smooth');

  // La mappa è già visibile a destra sul desktop: navigare significa focalizzarla.
  if(window.innerWidth>900 && (id.endsWith('-map')||id.endsWith('-map-pane'))){
    target.focus({preventScroll:true});
    return true;
  }
  let element=target.parentElement;
  let scroller:HTMLElement|null=null;
  while(element && element!==document.documentElement){
    const style=getComputedStyle(element);
    if(/^(auto|scroll)$/.test(style.overflowY)&&element.scrollHeight>element.clientHeight+2){
      scroller=element;
      break;
    }
    element=element.parentElement;
  }
  const viewportTop=scroller?.getBoundingClientRect().top??0;
  const stickySelector='.site-header.sticky, .map-top, .venue-detail > .site-header';
  const sticky=(scroller??document).querySelector<HTMLElement>(stickySelector);
  const rect=sticky?.getBoundingClientRect();
  const stickyOffset=rect && rect.bottom>viewportTop && rect.top<=viewportTop+1
    ? rect.bottom-viewportTop : 0;
  const delta=target.getBoundingClientRect().top-viewportTop-stickyOffset-14;
  if(scroller){
    scroller.scrollTo({top:Math.max(0,scroller.scrollTop+delta),behavior:mode});
  }else{
    window.scrollTo({top:Math.max(0,window.scrollY+delta),behavior:mode});
  }
  return true;
}
