import { describe, expect, it } from 'vitest';
import { atlasMatchesFacet, availableLocalFacets, LOCAL_ATLAS_FACETS } from './atlasFacets';
import type { AlpinePlace } from './alpinePlaces';
const base: AlpinePlace={slug:'a',name:'Rifugio prova',kind:'rifugio',lat:46,lng:12,osmUrl:'https://openstreetmap.org'};
describe('faccette: valori documentati, non campi nominali',()=>{
  it('attiva Wi-Fi solo con fatto positivo e fonte',()=>{
    const wifi=LOCAL_ATLAS_FACETS.find(f=>f.id==='wifi')!;
    expect(atlasMatchesFacet({...base,facts:{wifi_service:{value:true}}},wifi)).toBe(false);
    expect(atlasMatchesFacet({...base,facts:{wifi_service:{value:false,sourceId:'CAI'}}},wifi)).toBe(false);
    expect(atlasMatchesFacet({...base,facts:{wifi_service:{value:true,sourceId:'CAI'}}},wifi)).toBe(true);
    expect(availableLocalFacets([base],'rifugio')).toHaveLength(0);
  });
  it('non inventa webcam da un nome e non le marca live',()=>{
    const withWebcam={...base,webcams:[{id:'camera',name:'Vista',officialUrl:'https://example.org/cam',operator:'Ente'}]};
    expect(availableLocalFacets([withWebcam],'rifugio').map(f=>f.id)).toContain('webcam');
    expect(availableLocalFacets([{...base,webcams:[{id:'x',name:'Vista',officialUrl:'',operator:'Ente'}]}],'rifugio')).toEqual([]);
  });
});
