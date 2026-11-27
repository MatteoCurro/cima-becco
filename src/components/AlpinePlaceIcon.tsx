import { FaIcon } from './FaIcon';

/** Iconografia di categoria in SVG Font Awesome Free, uniforme su ogni browser. */
export function AlpinePlaceIcon({kind,size=24}:{kind:'rifugio'|'bivacco'|'borgo'|'acqua';size?:number}) {
  const name=kind==='rifugio'?'house':kind==='bivacco'?'tent':kind==='acqua'?'water':'mountain';
  return <FaIcon name={name} size={size} className={'cb-alpine-icon--'+kind}/>;
}
