import { describe, expect, it } from 'vitest';
import { activeAtlasAlerts, authorizedAtlasMedia, formatAtlasFact, presentAtlasFacts, usableAtlasClimate } from './atlasDossier';

describe('metadati canonici: null non è zero e non è false', () => {
  it('mostra 0 e false, omette solo fatti assenti', () => {
    const rows=presentAtlasFacts({
      posti: {value:0,unit:'letti',sourceId:'CAI'},
      acqua: {value:false,sourceId:'OSM'},
      quota: {value:null},
      numeroErrato: {value:Number.NaN},
    });
    expect(rows.map(([name])=>name)).toEqual(['posti','acqua']);
    expect(formatAtlasFact(rows[0][1])).toBe('0 letti');
    expect(formatAtlasFact(rows[1][1])).toBe('No');
  });
});
describe('governo dei media e degli avvisi', () => {
  it('nasconde media privi di identificazione del soggetto, licenza o permesso', () => {
    const base={id:'foto1',kind:'photo' as const,url:'https://img.example.test/1.jpg',
      sourceUrl:'https://commons.example.test/1',licence:'CC BY-SA',subjectVerified:true,reuseAllowed:true};
    expect(authorizedAtlasMedia([base,{...base,id:'no-subject',subjectVerified:false},
      {...base,id:'no-license',licence:''},{...base,id:'no-rights',reuseAllowed:false}])).toHaveLength(1);
  });
  it('mostra avvisi solo nel periodo indicato e con fonte+verifica', () => {
    const now=new Date('2026-11-27T12:00:00Z');
    const base={id:'chiusura',title:'Chiusura',message:'Interdizione verificata',
      sourceUrl:'https://ente.example.test/avviso',checkedAt:'2026-11-26',
      validFrom:'2026-11-25',validUntil:'2026-11-30'};
    expect(activeAtlasAlerts([base,{...base,id:'expired',validUntil:'2026-11-01'},
      {...base,id:'unsourced',sourceUrl:''}],now).map(a=>a.id)).toEqual(['chiusura']);
  });
  it('non rappresenta un campione breve come clima mensile', () => {
    const base={id:'t',name:'Temperatura',unit:'°C',period:'1991–2020',
      sourceUrl:'https://meteo.example.test/clima',values:Array.from({length:5},(_,i)=>({month:i+1,value:1}))};
    expect(usableAtlasClimate([base])).toHaveLength(0);
    expect(usableAtlasClimate([{...base,values:[...base.values,{month:6,value:2}]}])).toHaveLength(1);
  });
});
