import type { AlpineWaterPoint } from '../lib/alpineWater';
import { WATER_KINDS } from '../lib/waterPresentation';

export function WaterPointIcon({kind,size=23}:{kind:AlpineWaterPoint['kind'];size?:number}) {
  const mark=WATER_KINDS[kind];
  return <svg className={'cb-water-kind-icon cb-water-kind-icon--'+kind} width={size} height={size}
    viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
    {mark.paths.map((path,i)=><path key={i} d={path}/>)}
  </svg>;
}
