import {describe,it,expect} from 'vitest';
import {romeDay,homeTerritoryForDay,homeDiscoveryForDay,validHomeEditorialFeed,
  type HomeEditorialFeed,type HomeEditorialPlace,type HomeEditorialTerritory} from './homeEditorial';
const place=(kind:HomeEditorialPlace['kind'],name:string):HomeEditorialPlace=>({
  kind,id:name,slug:name,href:'/'+kind+'/'+name+'/',name,
  lat:46.5,lng:12.2,cover:{url:'https://example.org/'+name+'.jpg',
    sourceUrl:'https://example.org/'+name,licence:'CC BY',author:'Autore',sourceId:'file:1'},
  text:'Una descrizione documentata',elevationM:1890,factsCount:7,sourceIds:{},
});
const territory=(key:string):HomeEditorialTerritory=>({
  key,title:key,location:key,center:{lat:46.5,lng:12.2},
  town:place('town',key),refuge:place('refuge','rifugio-'+key),
  bivacco:place('bivacco','bivacco-'+key),summit:place('summit','cima-'+key),
  person:null,score:20,
  route:{kind:'route',name:'Sentiero '+key,slug:key,href:'/route/'+key+'/',
    distanceKm:9,gainM:720,difficulty:'E',activity:'hike',trailRef:'12'},
});
const feed:HomeEditorialFeed={
  schemaVersion:'1.0',generatedAt:'2026-11-28T00:00:00Z',
  policy:'published-source-only',territories:['a','b','c'].map(territory),
  discovery:{town:[place('town','a'),place('town','paese-extra')],
    refuge:[place('refuge','rifugio-a'),place('refuge','rifugio-extra')],
    bivacco:[place('bivacco','bivacco-a'),place('bivacco','bivacco-extra')],
    summit:[place('summit','cima-a'),place('summit','cima-extra')]},
};
describe('Home editoriale giornaliera',()=>{
  it('cambia alla mezzanotte di Roma, non a UTC né a ogni refresh',()=>{
    const before=romeDay(new Date('2026-11-28T22:30:00Z'));
    const after=romeDay(new Date('2026-11-28T23:30:00Z'));
    expect(before.key).toBe('2026-11-28');
    expect(after.key).toBe('2026-11-29');
    expect(after.ordinal-before.ordinal).toBe(1);
  });
  it('un giorno ha un solo territorio e il successivo ruota',()=>{
    const day=new Date('2026-11-28T12:00:00Z');
    expect(homeTerritoryForDay(feed,day)?.key).toBe(homeTerritoryForDay(feed,new Date('2026-11-28T20:00:00Z'))?.key);
    expect(homeTerritoryForDay(feed,day)?.key).not.toBe(homeTerritoryForDay(feed,new Date('2026-11-29T12:00:00Z'))?.key);
  });
  it('evita schede duplicate tra focus e categorie',()=>{
    const current=territory('a');
    const groups=homeDiscoveryForDay(feed,new Date('2026-11-28T13:00:00Z'),current);
    const hrefs=groups.flatMap(g=>g.items.map(x=>x.href));
    expect(new Set(hrefs).size).toBe(hrefs.length);
    expect(hrefs).not.toContain(current.town.href);
    expect(hrefs).not.toContain(current.refuge.href);
    expect(hrefs).not.toContain(current.bivacco?.href);
  });
  it('rifiuta un feed non qualificato',()=>{
    expect(validHomeEditorialFeed({...feed,policy:'unverified'})).toBe(false);
    expect(validHomeEditorialFeed({territories:[]})).toBe(false);
    expect(validHomeEditorialFeed(feed)).toBe(true);
    expect(homeTerritoryForDay({...feed,territories:[]},new Date())).toBeNull();
  });
});
