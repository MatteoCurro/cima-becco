import './atlasNearby.css';
import { alpinePlaceLink } from '../lib/alpinePlaces';
import type { NearbyAtlasPlace } from '../lib/nearbyAtlas';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';
import { DetailSectionHeading } from './DetailPrimitives';

export function NearbyAtlasPlaces({ items, embedded=false }: { items: readonly NearbyAtlasPlace[]; embedded?:boolean }) {
  if (!items.length) return null;
  return <section id={embedded?undefined:"cb-place-nearby"}
    className={"cb-nearby-entities"+(embedded?" cb-nearby-entities--embedded":" cb-location-section cb-detail-group")}
    aria-label={embedded?"Luoghi geograficamente vicini":undefined}
    aria-labelledby={embedded?undefined:"cb-place-nearby-title"}>
    {!embedded&&<DetailSectionHeading kicker="ATLANTE / LUOGHI COLLEGATI" title="ALTRI LUOGHI NEI DINTORNI."
      id="cb-place-nearby-title" description="Distanze geografiche in linea d’aria. Vicinanza non significa accessibilità, collegamento diretto o percorso verificato."/>}
    <div className="cb-nearby-entities-grid">
      {items.map(({ place, distanceKm })=><a key={place.kind+':'+place.slug}
        className="cb-nearby-entity" href={alpinePlaceLink(place)}>
        <span className="cb-nearby-entity-icon"><AlpinePlaceIcon kind={place.kind} size={23}/></span>
        <span className="cb-nearby-entity-content">
          <small>{place.kind === 'rifugio' ? 'Rifugio' : place.kind === 'bivacco' ? 'Bivacco' : 'Località'} · {distanceKm.toLocaleString('it-IT',{maximumFractionDigits:1})} km</small>
          <strong>{place.name}</strong>
          <span>{place.elevationM != null ? place.elevationM.toLocaleString('it-IT') + ' m di quota' : 'Quota non indicata'}</span>
        </span>
        <span className="cb-nearby-entity-open" aria-hidden="true">↗</span>
      </a>)}
    </div>
  </section>;
}
