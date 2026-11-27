import { describe, expect, it } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { AlpinePlace } from '../lib/alpinePlaces';
import { refugeFact, refugeOverview, refugeSeoDescription, refugeServiceFacts } from '../lib/refugeEditorial';
import { RefugeGallery, refugeGalleryItems } from '../components/RefugeGallery';

const base: AlpinePlace = {
  slug:'cai-123',name:'Rifugio Campione',kind:'rifugio',lat:46.42,lng:11.86,
  osmUrl:'https://www.openstreetmap.org/#map=14/46.42/11.86',
};
const fact=(value:string|boolean|number)=>({
  value,sourceId:'cai:shelter:123',sourceUrl:'https://rifugi.cai.it/shelters/123',method:'reported' as const,
});
describe('profilo rifugio CAI',()=>{
  it('compone un testo specifico senza inventare orari, prezzi o apertura',()=>{
    const place:AlpinePlace={...base,facts:{
      elevationM:fact(2180),bedsTotal:fact(32),bedsWinter:fact(6),
      wifi:fact(true),showers:fact(false),waterAvailableReported:fact(true),
    }};
    const copy=refugeOverview(place);
    expect(copy.replaceAll('.', '')).toContain('2180 metri');
    expect(copy).toContain('32 posti letto');
    expect(copy).toContain('6 invernali');
    expect(copy).toContain('Wi-Fi');
    expect(copy).not.toMatch(/apert[oa]|potabile|tariffa|prenotabile/);
    expect(refugeSeoDescription(place)).toContain('Cima Becco');
    expect(refugeServiceFacts(place)).toEqual(expect.arrayContaining([
      expect.objectContaining({key:'wifi',value:true}),
      expect.objectContaining({key:'showers',value:false}),
    ]));
  });
  it('non trasforma null in no e non pubblica fatti privi di fonte',()=>{
    const place:AlpinePlace={...base,facts:{
      wifi:fact(null as unknown as string),showers:{value:false},
      pets:fact(false),drinkingWater:fact(true),
    }};
    const services=refugeServiceFacts(place);
    expect(services.map(s=>s.key)).toEqual(['pets','drinkingWater']);
    expect(refugeFact(place,'wifi')).toBeNull();
    expect(refugeFact(place,'showers')).toBeNull();
  });
  it('galleria senza duplicati, in ordine e solo con media documentati',()=>{
    const photo={
      id:'cai:1',kind:'photo' as const,
      url:'https://cdn.example.com/a.jpg',sourceUrl:'https://rifugi.cai.it/shelters/123',
      licence:'Licenza CAI',author:'Archivio CAI',subjectVerified:true,reuseAllowed:true,
    };
    const place:AlpinePlace={...base,
      photo:{url:photo.url,sourceUrl:photo.sourceUrl,license:photo.licence,author:photo.author},
      media:[photo,{...photo,id:'cai:2',url:'https://cdn.example.com/b.jpg',caption:'Vista estiva'},
        {...photo,id:'cai:3',url:'https://cdn.example.com/no.jpg',reuseAllowed:false}],
    };
    expect(refugeGalleryItems(place)).toHaveLength(2);
    const html=renderToStaticMarkup(createElement(RefugeGallery,{place}));
    expect(html).toContain('Fotografia precedente');
    expect(html).toContain('Mostra fotografia 2 di 2');
    expect(html).toContain('Fonte e crediti');
    expect(html).not.toContain('no.jpg');
  });
  it('con zero immagini mostra un fallback dichiarato, non una foto di repertorio',()=>{
    const html=renderToStaticMarkup(createElement(RefugeGallery,{place:base}));
    expect(html).toContain('ILLUSTRAZIONE TOPOGRAFICA');
    expect(html).not.toContain('Fotografia precedente');
  });
});
