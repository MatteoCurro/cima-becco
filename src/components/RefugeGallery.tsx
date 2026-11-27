import { useMemo, useState } from 'react';
import type { AlpinePlace } from '../lib/alpinePlaces';
import { authorizedAtlasMedia } from '../lib/atlasDossier';
import { AlpinePlaceVisual } from './AlpinePlaceVisual';
import { FaIcon } from './FaIcon';
import type { AtlasMedia } from '../lib/atlasDossier';

interface GalleryItem {
  url: string;
  sourceUrl: string;
  author?: string;
  license: string;
  caption?: string;
  capturedAt?: string;
  historical?: boolean;
}
export function refugeGalleryItems(place: AlpinePlace): GalleryItem[] {
  const authorized = authorizedAtlasMedia(place.media)
    .filter((item:AtlasMedia)=>item.kind==='photo'||item.kind==='historical_photo');
  const items:GalleryItem[] = authorized.map(item=>({
    url:item.url, sourceUrl:item.sourceUrl, author:item.author,
    license:item.licence, caption:item.caption, capturedAt:item.capturedAt,
    historical:item.kind==='historical_photo',
  }));
  if(place.photo?.url && place.photo.sourceUrl && place.photo.license && !items.some(item=>item.url===place.photo?.url)){
    items.unshift({...place.photo,caption:undefined,historical:false});
  }
  const unique=new Map<string,GalleryItem>();
  for(const item of items){
    if(!/^https:\/\//.test(item.url)||!/^https:\/\//.test(item.sourceUrl))continue;
    if(!unique.has(item.url))unique.set(item.url,item);
  }
  return [...unique.values()];
}

/** Slideshow manuale: nessun autoplay, niente immagini inventate né dipendenze di carousel. */
export function RefugeGallery({place}:{place:AlpinePlace}){
  const gallery=useMemo(()=>refugeGalleryItems(place),[place]);
  const [index,setIndex]=useState(0);
  const [failed,setFailed]=useState<string[]>([]);
  const valid=gallery.filter(item=>!failed.includes(item.url));
  const currentIndex=Math.min(index,Math.max(0,valid.length-1));
  const selected=valid[currentIndex];
  const go=(next:number)=>setIndex((next+valid.length)%valid.length);
  return <figure className="cb-refuge-gallery" aria-label={'Fotografie di '+place.name}>
    {selected ? <div className="cb-refuge-gallery-stage"
      role={valid.length>1?'region':undefined} aria-roledescription={valid.length>1?'carosello':undefined}
      aria-label={valid.length>1?'Galleria fotografica della struttura':undefined}
      onKeyDown={event=>{
        if(valid.length<2)return;
        if(event.key==='ArrowRight'){event.preventDefault();go(currentIndex+1)}
        if(event.key==='ArrowLeft'){event.preventDefault();go(currentIndex-1)}
      }}>
      <img key={selected.url} src={selected.url}
        alt={(selected.historical?'Fotografia storica di ':'Fotografia di ')+place.name+(selected.caption?' — '+selected.caption:'')}
        loading={currentIndex===0?'eager':'lazy'} decoding="async"
        onError={()=>setFailed(old=>[...old,selected.url])}/>
      {valid.length>1&&<>
        <button type="button" className="cb-refuge-gallery-prev" aria-label="Fotografia precedente"
          onClick={()=>go(currentIndex-1)}><FaIcon name="chevron-left" size={16}/></button>
        <button type="button" className="cb-refuge-gallery-next" aria-label="Fotografia successiva"
          onClick={()=>go(currentIndex+1)}><FaIcon name="chevron-right" size={16}/></button>
        <span className="cb-refuge-gallery-count" aria-live="polite">{currentIndex+1} / {valid.length}</span>
      </>}
      {selected.historical&&<span className="cb-refuge-gallery-historical">FOTO STORICA</span>}
    </div> : <AlpinePlaceVisual place={place}/>}
    {selected&&<figcaption className="cb-refuge-gallery-caption">
      <span>{selected.caption || (selected.historical?'Immagine storica del luogo':'La struttura in fotografia')}
        {selected.capturedAt?' · '+selected.capturedAt:''}</span>

    </figcaption>}
    {valid.length>1&&<div className="cb-refuge-gallery-thumbs" role="group" aria-label="Scegli una fotografia">
      {valid.map((item,i)=><button key={item.url} type="button"
        aria-label={'Mostra fotografia '+(i+1)+' di '+valid.length}
        aria-pressed={i===currentIndex}
        className={i===currentIndex?'is-active':undefined} onClick={()=>setIndex(i)}>
        <img src={item.url} alt="" loading="lazy" decoding="async"/>
      </button>)}
    </div>}
  </figure>;
}
