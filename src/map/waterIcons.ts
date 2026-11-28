import type { Map as MlMap } from 'maplibre-gl';
import { WATER_KINDS } from '../lib/waterPresentation';

/** Sprite raster condivisi, generati una sola volta per mappa, senza marker DOM per migliaia di punti. */
export function registerWaterMapIcons(map:MlMap):void{
  for(const [kind,mark] of Object.entries(WATER_KINDS)){
    const id='cb-water-'+kind;
    if(map.hasImage(id))continue;
    const canvas=document.createElement('canvas');
    canvas.width=56;canvas.height=56;
    const context=canvas.getContext('2d');
    if(!context)continue;
    context.scale(56/28,56/28);
    context.beginPath();context.arc(14,14,12.2,0,2*Math.PI);
    context.fillStyle=mark.color;context.fill();
    context.strokeStyle='#fff';context.lineWidth=2.2;context.stroke();
    context.strokeStyle='#fff';context.lineWidth=1.75;
    context.lineCap='round';context.lineJoin='round';
    context.save();context.translate(2,2);
    for(const d of mark.paths)context.stroke(new Path2D(d));
    context.restore();
    map.addImage(id,context.getImageData(0,0,56,56),{pixelRatio:2});
  }
}
