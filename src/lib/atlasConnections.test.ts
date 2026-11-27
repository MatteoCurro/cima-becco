import { describe, expect, it } from 'vitest';
import type { AlpinePlace } from './alpinePlaces';
import { atlasCanonicalPath, canonicalAtlasSlug, atlasSlugPart } from './placePermalinks';
import { resolveRefugeTerritory, relatedAtlasPlaces } from './atlasConnections';

const place=(name:string,slug:string,kind:AlpinePlace['kind'],lat:number,lng:number):AlpinePlace=>
  ({name,slug,kind,lat,lng,osmUrl:'https://www.openstreetmap.org/#map=14/46/11'});

describe('permalink parlanti e legami territoriali dell’Atlante',()=>{
  it('mantiene le identità interne, ma rende leggibile il permalink CAI',()=>{
    const ref={...place('Rifugio Boé – Piz Boè','osm-w-100','rifugio',46.5,11.8),sourceIds:{cai:'921800106',osm:'way/100'}};
    expect(canonicalAtlasSlug(ref)).toBe('rifugio-boe-piz-boe-cai-921800106');
    expect(atlasCanonicalPath(ref)).toBe('/rifugi/rifugio-boe-piz-boe-cai-921800106/');
    expect(ref.slug).toBe('osm-w-100'); // route.stops resta valido
    const cai=place('Rifugio alle Torri','cai-1234','rifugio',46,11);
    expect(atlasCanonicalPath(cai)).toBe('/rifugi/rifugio-alle-torri-cai-1234/');
  });
  it('non cambia gli URL delle altre tipologie durante questo rilascio',()=>{
    expect(atlasCanonicalPath(place('Canazei','osm-n-999','borgo',46.4,11.7))).toBe('/borghi/osm-n-999/');
    expect(atlasCanonicalPath(place('Bivacco rosso','osm-w-22','bivacco',46.4,11.7))).toBe('/bivacchi/osm-w-22/');
    expect(atlasSlugPart('Rifugio Àlpë ß')).toBe('rifugio-alpe-ss');
  });
  const refuge:AlpinePlace={...place('Rifugio Lagorai','cai-98','rifugio',46.30,11.60),
    facts:{
      municipalityNameReported:{value:'Cavalese',sourceId:'cai:shelter:98'},
      localityNameReported:{value:'Tesero',sourceId:'cai:shelter:98'},
    }};
  it('collega un paese solo se nome esatto e coordinate compatibili individuano un unico luogo',()=>{
    const atlas=[
      place('Cavalese','osm-n-1','borgo',46.29,11.47),
      place('Tesero','osm-n-2','borgo',46.29,11.51),
      place('Cavalese','osm-n-3','borgo',45.55,11.60), // omonimo lontano
    ];
    const links=resolveRefugeTerritory(refuge,atlas);
    expect(links.find(x=>x.name==='Cavalese')?.href).toBe('/borghi/osm-n-1/');
    expect(links.find(x=>x.name==='Tesero')?.href).toBe('/borghi/osm-n-2/');
  });
  it('blocca omonimi vicini, candidati remoti e nomi privi di fonte',()=>{
    const atlas=[
      place('Cavalese','osm-n-1','borgo',46.28,11.56),
      place('Cavalese','osm-n-4','borgo',46.27,11.59),
      place('Tesero','osm-n-2','borgo',44.50,11.60),
    ];
    const links=resolveRefugeTerritory(refuge,atlas);
    expect(links.every(link=>link.href===null)).toBe(true);
    expect(resolveRefugeTerritory({...refuge,facts:{
      municipalityNameReported:{value:'Cavalese'},
    }},atlas)).toHaveLength(0);
  });
  it('suggerisce altre pagine solo con posizioni documentate e distanza esplicita',()=>{
    const near=place('Rifugio vicino','osm-n-55','rifugio',46.30,11.61);
    const distant=place('Rifugio lontano','osm-n-56','rifugio',45.0,10.0);
    expect(relatedAtlasPlaces(refuge,[near,distant],8,5).map(x=>x.place.slug)).toEqual(['osm-n-55']);
  });
});
