import { describe, expect, it } from 'vitest';
import { summitByGeonames, withVerifiedSummit } from './summitRelease';
import type { Venue } from '../types';

const legacy:Venue={
  slug:'gn100-45x10',name:'Cima delle Prove',type:'hill',
  lat:46.5,lng:12.3,summitM:2450,gainM:null,
  elevationSource:'community',routeSlugs:[]
};
const profile={
  id:'598ed681-d801-59c9-927a-a5c59c708fcc',
  kind:'summit',subtype:'mountain',slug:'cima-delle-prove',
  slugAliases:['gn100-45x10'],name:'Cima delle Prove',
  sourceIds:{geonames:'100',wikidata:'Q123',wikidataVerifiedBy:'P1566+P625'},
  geo:{point:{lat:46.5001,lng:12.3001}},
  quality:{gate:'G2',seoIndexable:true},
  facts:{elevationM:{value:2450,unit:'m'}},
  textSources:[{text:'Biografia geografica documentata sul territorio',licence:'CC BY-SA 4.0',
    sourceId:'wikipedia:it:10',sourceUrl:'https://it.wikipedia.org/wiki/Cima'}],
  media:[{id:'m1',kind:'photo',url:'https://upload.wikimedia.org/test.jpg',
    sourceUrl:'https://commons.wikimedia.org/wiki/File:Peak.jpg',
    author:'Archivista',licence:'CC BY-SA 4.0',
    subjectVerified:true,reuseAllowed:true}]
};

describe('G2 cime → GeoNames map adapter',()=>{
  it('only accepts explicitly published and verified dossiers',()=>{
    const data={releaseChannel:'GEONAMES_SUMMITS_G2',isPublished:true,entities:[profile]};
    expect(summitByGeonames(data).size).toBe(1);
    expect(summitByGeonames({...data,isPublished:false}).size).toBe(0);
    expect(summitByGeonames({...data,entities:[{...profile,quality:{gate:'G1',seoIndexable:false}}]}).size).toBe(0);
  });
  it('preserves the original map and favorite slug and adds factual media',()=>{
    const data={releaseChannel:'GEONAMES_SUMMITS_G2',isPublished:true,entities:[profile]};
    const v=withVerifiedSummit(legacy,summitByGeonames(data));
    expect(v.slug).toBe('gn100-45x10');
    expect(v.id).toBe(profile.id);
    expect(v.sourceIds?.wikidata).toBe('Q123');
    expect(v.photo?.sourceUrl).toContain('commons.wikimedia.org');
    expect(v.textSources?.[0].sourceId).toBe('wikipedia:it:10');
  });
  it('does not merge the same ID at incompatible coordinates or slug',()=>{
    const copy={...profile,geo:{point:{lat:47.8,lng:12.3}}};
    const data={releaseChannel:'GEONAMES_SUMMITS_G2',isPublished:true,entities:[copy]};
    expect(withVerifiedSummit(legacy,summitByGeonames(data))).toEqual(legacy);
    const wrong={...profile,slugAliases:['gn100-40x10']};
    const other={...data,entities:[wrong]};
    expect(withVerifiedSummit(legacy,summitByGeonames(other))).toEqual(legacy);
  });
  it('rejects duplicated Wikidata QID instead of picking a wrong summit',()=>{
    const second={...profile,id:'secondary',sourceIds:{...profile.sourceIds,geonames:'101'}};
    const data={releaseChannel:'GEONAMES_SUMMITS_G2',isPublished:true,entities:[profile,second]};
    expect(summitByGeonames(data).size).toBe(0);
  });
});
