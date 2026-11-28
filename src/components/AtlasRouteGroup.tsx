import type { Route } from '../types';
import { trailMood, trailTitle } from '../lib/routeEditorial';

/** La stessa riga di sentiero per paesi generici e comuni G2. */
export function AtlasRouteGroup({title,items}:{title:string;items:Route[]}) {
  if(!items.length)return null;
  return <section className="cb-atlas-nearby">
    <h3>{title} <span>{items.length}</span></h3>
    <div className="cb-atlas-routes">{items.map(route=>{
      const mood=trailMood(route);
      return <a key={route.slug} href={import.meta.env.BASE_URL+'route/'+encodeURIComponent(route.slug)+'/'}>
        <strong>{trailTitle(route)}</strong>
        <span>{(route.distanceM/1000).toLocaleString('it-IT',{maximumFractionDigits:1})} km · {mood.quip}
          <small> · {mood.label}</small>
        </span>
      </a>;
    })}</div>
  </section>;
}
