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
  it('non pubblica fotografie senza permessi o restrizioni scadute',()=>{
    const record={media:[{id:'m',kind:'photo' as const,url:'https://example.org/a.jpg',
      sourceUrl:'https://example.org/license',licence:'CC BY',subjectVerified:true,reuseAllowed:false}],
      restrictions:[{id:'r',title:'Scaduto',message:'Chiusura',checkedAt:'2020-01-01',
      validUntil:'2020-12-31',sourceUrl:'https://example.org/notice'}]};
    expect(renderToStaticMarkup(<AtlasDossierBlocks placement="media" record={record}/>)).toBe('');
    expect(renderToStaticMarkup(<AtlasDossierBlocks placement="alerts" record={record}/>)).toBe('');
  });
});
