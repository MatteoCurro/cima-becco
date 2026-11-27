import { describe, expect, it } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';

describe('dossier condizionale',()=>{
  it('non crea moduli vuoti da una scheda senza metadati',()=>{
    expect(renderToStaticMarkup(<AtlasDossierBlocks record={{}} placement="core"/>)).toBe('');
    expect(renderToStaticMarkup(<AtlasDossierBlocks record={{}} placement="connections"/>)).toBe('');
    expect(renderToStaticMarkup(<AtlasDossierBlocks record={{}} placement="media"/>)).toBe('');
  });
  it('distingue prossimità da accesso e stampa fonte documentata',()=>{
    const html=renderToStaticMarkup(<AtlasDossierBlocks placement="connections" record={{relations:[
      {type:'near',target:{id:'x',kind:'rifugio',name:'Rifugio X',href:'/rifugi/x/'},straightLineKm:1.2,method:'haversine',sourceUrl:'https://example.org'},
    ]}}/>);
    expect(html).toContain('Rifugio X');
    expect(html).toContain('prossimità geografica');
    expect(html).toContain('in linea d');
    expect(html).toContain('/rifugi/x/');
  });
  it('mostra toponimi e amministrazione solo se forniti',()=>{
    const html=renderToStaticMarkup(<AtlasDossierBlocks placement="core" record={{
      aliases:[{value:'Nome ladino',language:'lld',sourceUrl:'https://example.org'}],
      administrativeHierarchy:{region:'Trentino-Alto Adige',municipality:'Canazei'},
    }}/>);
    expect(html).toContain('Nome ladino');
    expect(html).toContain('Canazei');
    expect(html).toContain('Trentino-Alto Adige');
  });
  it('concentra le fonti CAI e OSM in un unico registro, senza ripeterle sulle relazioni',()=>{
    const record={
      sourceIds:{osm:'way/451',cai:'123456'},
      facts:{wifi:{value:true,sourceId:'cai:shelter:123456',
        sourceUrl:'https://rifugi.cai.it/shelters/123456'}},
      relations:[{type:'near' as const,target:{id:'p',name:'Paese',kind:'borgo'},
        sourceUrl:'https://example.org/relation'}],
    };
    const relations=renderToStaticMarkup(<AtlasDossierBlocks record={record}
      placement="connections" suppressRelationSources/>);
    expect(relations).toContain('Paese');
    expect(relations).not.toContain('https://example.org/relation');
    const credits=renderToStaticMarkup(<AtlasDossierBlocks record={record} placement="credits"/>);
    expect(credits).toContain('OpenStreetMap · ODbL');
    expect(credits).toContain('Club Alpino Italiano · Unico Rifugi');
    expect(credits).toContain('https://example.org/relation');
  });
  it('non pubblica fotografie senza permessi o restrizioni scadute',()=>{
    const record={media:[{id:'m',kind:'photo' as const,url:'https://example.org/a.jpg',
      sourceUrl:'https://example.org/license',licence:'CC BY',subjectVerified:true,reuseAllowed:false}],
      restrictions:[{id:'r',title:'Scaduto',message:'Chiusura',checkedAt:'2020-01-01',
      validUntil:'2020-12-31',sourceUrl:'https://example.org/notice'}]};
    expect(renderToStaticMarkup(<AtlasDossierBlocks placement="media" record={record}/>)).toBe('');
    expect(renderToStaticMarkup(<AtlasDossierBlocks placement="alerts" record={record}/>)).toBe('');
  });
});
