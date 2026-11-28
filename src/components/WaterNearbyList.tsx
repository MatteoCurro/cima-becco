import type { AlpineWaterPoint } from '../lib/alpineWater';
import { potabilityLabel } from '../lib/alpineWater';
import { waterDisplayName, waterKindLabel } from '../lib/waterPresentation';
import { WaterPointIcon } from './WaterPointIcon';
import './waterPoints.css';

/** I numeri corrispondono ai marker visibili; nessun hover necessario, anche su mobile. */
export function WaterNearbyList({points,onSelect,selectedSlug}:{
  points:readonly AlpineWaterPoint[];
  onSelect:(slug:string)=>void;
  selectedSlug?:string|null;
}){
  return <div className="cb-water-nearby">
    <div className="cb-water-legend" aria-label="Tipi di punti acqua">
      {(['fontanella','sorgente','rubinetto'] as const).map(kind=>
        <span key={kind}><WaterPointIcon kind={kind} size={17}/>{waterKindLabel(kind)}</span>)}
      <small>Il simbolo identifica la tipologia, non la potabilità.</small>
    </div>
    <div className="cb-water-nearby-grid">
      {points.map((point,index)=><button key={point.slug} type="button"
        className={'cb-water-nearby-item'+(selectedSlug===point.slug?' is-selected':'')}
        onClick={()=>onSelect(point.slug)}
        aria-label={'Mostra sulla mappa il punto '+(index+1)+': '+waterDisplayName(point,index+1)+', '+potabilityLabel(point.potable)}
        aria-pressed={selectedSlug===point.slug}>
        <span className="cb-water-marker-index">{index+1}</span>
        <span className={'cb-water-kind-symbol cb-water-kind-symbol--'+point.kind}>
          <WaterPointIcon kind={point.kind}/>
        </span>
        <span className="cb-water-nearby-info">
          <strong>{waterDisplayName(point,index+1)}</strong>
          <small>{waterKindLabel(point.kind)} · {potabilityLabel(point.potable)}{point.seasonal?' · stagionale':''}</small>
        </span>
        <span className="cb-water-map-action" aria-hidden="true">Mappa ↗</span>
      </button>)}
    </div>
    <p className="cb-water-caution">Posizione e presenza in OpenStreetMap non garantiscono che l'acqua sia accessibile, disponibile o potabile. Verifica sempre sul posto.</p>
  </div>;
}
