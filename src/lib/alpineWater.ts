import { DATA_BASE } from './venues';
export type Potability='yes'|'no'|'unknown';
export interface AlpineWaterPoint {
 slug:string;name:string;kind:'fontanella'|'sorgente'|'rubinetto';
 potable:Potability;lat:number;lng:number;osmUrl:string;seasonal?:boolean;
}
export interface AlpineWaterDataset { generatedAt:string|null;coverage:string;source:string;sources:AlpineWaterPoint[] }
let cache:Promise<AlpineWaterDataset>|null=null;
export function loadAlpineWater():Promise<AlpineWaterDataset>{
  cache??=fetch(`${DATA_BASE}/alpine-water.json`)
    .then(async r=>{if(!r.ok)throw new Error('Punti acqua non disponibili');return await r.json() as AlpineWaterDataset;})
    .catch(()=>{cache=null;return {generatedAt:null,coverage:'',source:'OpenStreetMap',sources:[]};});
  return cache;
}
export function potabilityLabel(value:Potability):string{
 return value==='yes'?'Potabile secondo OSM':value==='no'?'Segnalata non potabile':'Potabilità NON verificata';
}
export function alpineWaterNear(points:AlpineWaterPoint[],lng:number,lat:number,radiusM=1600,limit=16):AlpineWaterPoint[]{
  const kx=Math.cos(lat*Math.PI/180)*111320;
  return points.map(p=>({p,d:Math.hypot((p.lng-lng)*kx,(p.lat-lat)*111195)}))
   .filter(x=>x.d<=radiusM).sort((a,b)=>a.d-b.d).slice(0,limit).map(x=>x.p);
}
