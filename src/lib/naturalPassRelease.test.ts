import { describe, expect, it } from 'vitest';
import { verifiedNaturalPasses } from './naturalPassRelease';

const pass = {
  id: 'bb6ea2d9-b24c-5afd-86f3-873cdd1c8b9c',
  kind:'natural_feature',
  subtype:'mountain_pass',
  slug:'passo-di-prova',
  name:'Passo di Prova',
  geo:{point:{lat:46.5,lng:12.3}},
  sourceIds:{geonames:'100',wikidata:'Q123',wikidataVerifiedBy:'P1566+P625'},
  facts:{elevationM:{value:2450,unit:'m',licence:'CC BY 4.0',sourceId:'geonames:100'}},
  quality:{gate:'G2',seoIndexable:true},
  description:'Valico documentato nelle Alpi da una voce enciclopedica con rilievi, toponimi e peculiarità storiche accertate.'.repeat(2),
  media:[{id:'m1',kind:'photo',url:'https://upload.wikimedia.org/test.jpg',
    sourceUrl:'https://commons.wikimedia.org/wiki/File:Pass.jpg',
    author:'Autore attestato',licence:'CC BY-SA 4.0',reuseAllowed:true,subjectVerified:true,
    subjectMethod:'verified_GeoNames_P1566_Wikidata_P625_P18',sourceId:'wikidata:Q123:P18'}],
  textSources:[{text:'Passo geografico reale e nome storico dichiarato nella fonte enciclopedica.'.repeat(3),
    licence:'CC BY-SA 4.0',sourceId:'wikipedia:it:100',
    sourceUrl:'https://it.wikipedia.org/wiki/Passo_di_Prova'}],
};
const release = {releaseChannel:'NATURAL_FEATURES_PASSES_G2',isPublished:true,
  generatedAt:'2026-11-28T09:00:00Z',entities:[pass]};

describe('Natural pass G2 release → existing atlas components',()=>{
  it('shows only a published valid source-backed dossier',()=>{
    expect(verifiedNaturalPasses(release).features).toHaveLength(1);
    expect(verifiedNaturalPasses({...release,isPublished:false}).features).toHaveLength(0);
    expect(verifiedNaturalPasses({...release,releaseChannel:'OSM_NATURAL_FEATURES_STAGING_V1'}).features).toHaveLength(0);
  });
  it('holds unverified photographs, missing narrative, altitude conflicts',()=>{
    expect(verifiedNaturalPasses({...release,entities:[{...pass,
      media:[{...pass.media[0],subjectVerified:false}]}]}).features).toHaveLength(0);
    expect(verifiedNaturalPasses({...release,entities:[{...pass,
      textSources:[]}]}).features).toHaveLength(0);
    expect(verifiedNaturalPasses({...release,entities:[{...pass,
      quality:{...pass.quality,reviewRequired:true}}]}).features).toHaveLength(0);
  });
  it('fails closed on duplicate source identities instead of duplicating pass pins',()=>{
    const other={...pass,id:'another',slug:'altro-passo'};
    expect(verifiedNaturalPasses({...release,entities:[pass,other]}).features).toHaveLength(0);
  });
  it('refuses water, lakes and valleys without verified source-specific geometry',()=>{
    expect(verifiedNaturalPasses({...release,entities:[{...pass,
      subtype:'lake'}]}).features).toHaveLength(0);
  });
});
