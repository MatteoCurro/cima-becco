import { describe,it,expect } from 'vitest';
import type { AlpinePlace } from './alpinePlaces';
import { municipalityArchiveFacts,municipalityNumber,municipalityText,municipalityDisplayDate } from './municipalityPresentation';
import { municipalityAsAlpinePlace } from './municipalityRelease';

const sample:AlpinePlace={
  kind:'borgo',subtype:'italian_municipality',slug:'sesto-021092',name:'Sesto',
  lat:46.7,lng:12.3,osmUrl:'https://www.openstreetmap.org/#map=14/46.7/12.3',
  facts:{elevationReportedM:{value:1310},altitudineTerritorioMaxM:{value:3032},
    sindacoNome:{value:'Esempio'},municipalityNumericCode:{value:'021092'},
    nuts1_2024:{value:'ITH'},provinceCapitalFlag:{value:false}}
};
describe('scheda comunale G2',()=>{
 it('distingue quote territoriali e dati istituzionali da codici archivistici',()=>{
   expect(municipalityNumber(sample,'elevationReportedM')).toBe(1310);
   expect(municipalityText(sample,'sindacoNome')).toBe('Esempio');
   const extra=municipalityArchiveFacts(sample);
   expect(Object.keys(extra)).toEqual(['municipalityNumericCode','nuts1_2024','provinceCapitalFlag']);
   expect(extra.municipalityNumericCode.label).toBe('Codice ISTAT del comune');
   expect(extra.provinceCapitalFlag.value).toBe(false);
 });
 it('formatta le date esplicite senza inventarne quando assenti',()=>{
   expect(municipalityDisplayDate('2025-05-04')).toBe('4 maggio 2025');
   expect(municipalityDisplayDate(null)).toBe(null);
 });
 it('normalizza alias ISTAT con name anziché value e non mostra undefined',()=>{
   const place=municipalityAsAlpinePlace({
     id:'mun:021092',kind:'municipality',subtype:'italian_municipality',slug:'sesto-021092',
     name:'Sesto',sourceIds:{istat:'021092'},geo:{point:{lat:46.7,lng:12.3}},
     quality:{gate:'G2',seoIndexable:true},
     aliases:[{name:'Sexten',language:null},{name:'Sesto/Sexten',language:null},{name:'Sesto'}],
   });
   expect(place?.aliases?.map(a=>a.value)).toEqual(['Sexten','Sesto/Sexten']);
 });
});
