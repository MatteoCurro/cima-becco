import type { Venue } from '../types';
import { AlpineAtlasMap } from './AlpineAtlasMap';
import type { AlpinePlace } from '../lib/alpinePlaces';

/** Stesso motore MapLibre, stesso punto selezionato, nessun renderer duplicato per le cime. */
const NO_PLACES: AlpinePlace[] = [];
export function MiniMap({venue}:{venue:Venue}){
  return <div className="mini-map">
    <AlpineAtlasMap places={NO_PLACES} kind="borgo"
      selectedPoint={{lat:venue.lat,lng:venue.lng,name:venue.name}}
      caption={venue.name} height="100%"/>
  </div>;
}
