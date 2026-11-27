import { useState } from 'react';
import type { AlpinePlace } from '../lib/alpinePlaces';
import { AlpinePlaceIcon } from './AlpinePlaceIcon';

type Props = { place: AlpinePlace; compact?: boolean; className?: string };

const TEXT = {rifugio:'RIFUGIO ALPINO',bivacco:'BIVACCO',borgo:'PAESE DI MONTAGNA'};

/** La foto è reale e documentata oppure si vede un'illustrazione dichiarata, mai un'immagine inventata. */
export function AlpinePlaceVisual({place,compact=false,className=''}:Props) {
  const [failed,setFailed]=useState(false);
  return <div className={'cb-place-visual cb-place-visual--'+place.kind+' '+className}>
    {place.photo && !failed ? <img src={place.photo.url} alt={'Vista di '+place.name} loading="lazy" onError={()=>setFailed(true)} /> :
      <div className="cb-place-visual-art" aria-label={'Illustrazione topografica, fotografia non disponibile per '+place.name}>
        <svg viewBox="0 0 600 390" preserveAspectRatio="xMidYMid slice" aria-hidden="true">
          <path className="cb-visual-mountain-far" d="M0 320 112 180l80 86 105-167 122 174 95-127 92 169v75H0Z"/>
          <path className="cb-visual-mountain-near" d="M-20 390 107 274l85 47 137-157 166 201 103-100 50 125Z"/>
          <g className="cb-visual-contours" fill="none">
            <path d="M-20 324C150 100 220 405 400 196S650 244 670 84"/>
            <path d="M-20 347C150 123 220 428 400 219S650 267 670 107"/>
            <path d="M-20 370C150 146 220 451 400 242S650 290 670 130"/>
            <path d="M-20 393C150 169 220 474 400 265S650 313 670 153"/>
            <path d="M-20 416C150 192 220 497 400 288S650 336 670 176"/>
          </g>
          <circle cx="434" cy="105" r="48" className="cb-visual-sun"/>
          <path d="m328 164 40-55 22 34 25-27 37 48" fill="none" stroke="#fff" strokeOpacity=".7" strokeWidth="4" />
        </svg>
        <div className="cb-visual-symbol"><AlpinePlaceIcon kind={place.kind} size={compact?39:55}/></div>
        {!compact&&<span className="cb-visual-caption">ILLUSTRAZIONE TOPOGRAFICA / FOTO DA DOCUMENTARE</span>}
      </div>}
    {!compact&&<span className="cb-place-visual-label">{TEXT[place.kind]}</span>}
  </div>;
}
