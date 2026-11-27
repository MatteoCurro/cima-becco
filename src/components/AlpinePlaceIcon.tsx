/** Segni vettoriali Cima Becco: tetti geometrici, spigoli fucsia, zero clipart. */
export function AlpinePlaceIcon({kind,size=24}:{kind:'rifugio'|'borgo'|'acqua';size?:number}) {
  if(kind==='acqua')return <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M24 4C19 12 9 25 9 32a15 15 0 0030 0C39 25 29 12 24 4Z" fill="#36a9d3" stroke="#123b2c" strokeWidth="3"/>
    <path d="M17 32c0 5 3 8 8 9" stroke="#e9fff7" strokeWidth="3" strokeLinecap="round"/>
  </svg>;
  if(kind==='rifugio')return <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M5 23 24 6l19 17" stroke="#f71970" strokeWidth="6" strokeLinejoin="bevel" strokeLinecap="square"/>
    <path d="M10 23h28v20H10Z" fill="#dff4c5" stroke="#143d2f" strokeWidth="3"/>
    <path d="M21 43V29h8v14" fill="#f71970" stroke="#143d2f" strokeWidth="2.5"/>
    <path d="M13 29h5v6h-5Zm18 0h5v6h-5Z" fill="#143d2f"/>
  </svg>;
  return <svg width={size} height={size} viewBox="0 0 48 48" fill="none" aria-hidden="true">
    <path d="M3 23 15 12l12 11v20H3Z" fill="#e7ffd0" stroke="#143d2f" strokeWidth="2.7"/>
    <path d="M20 17 33 5l12 12v26H20Z" fill="#f71970" stroke="#143d2f" strokeWidth="2.7"/>
    <path d="M2 23 15 11l12 12M19 18 33 5l13 13" stroke="#143d2f" strokeWidth="3" strokeLinecap="round"/>
    <path d="M29 43V28h7v15M8 28h7v7H8Z" fill="#e7ffd0" stroke="#143d2f" strokeWidth="2"/>
  </svg>;
}
