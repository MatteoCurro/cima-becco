import type { AlpinePlace } from './alpinePlaces';
import type { AtlasFact } from './atlasDossier';

export const MUNICIPALITY_FEATURED_FIELDS = new Set([
  'quotaCentroM','elevationReportedM','altitudineTerritorioMinM','altitudineTerritorioMaxM',
  'altitudineTerritorioMediaM','superficieKm2','popolazione','populationReferenceDate',
  'sindacoNome','carica','dataElezione','mandatoInizio','mandatoFine','sitoUfficiale',
  'fullOfficialName','italianName','localName','regionName','provinceName',
]);
const ARCHIVE_LABELS:Record<string,string>={
  cadastralCode:'Codice catastale',
  regionCodeISTAT:'Codice ISTAT della regione',
  municipalityNumericCode:'Codice ISTAT del comune',
  municipalityProgressive:'Progressivo comunale ISTAT',
  municipalityNumericCode1995to2005:'Codice ISTAT (1995–2005)',
  municipalityNumericCode2006to2009:'Codice ISTAT (2006–2009)',
  municipalityNumericCode2010to2016:'Codice ISTAT (2010–2016)',
  municipalityNumericCode2017to2025:'Codice ISTAT (2017–2025)',
  provinceCodeHistorical:'Codice storico della provincia',
  provinceCapitalFlag:'Capoluogo di provincia',
  vehicleRegistrationProvinceCode:'Sigla automobilistica della provincia',
  geographicalMacroRegionName:'Ripartizione geografica',
  geographicalMacroRegionCode:'Codice ripartizione geografica',
  statisticalTerritorialUnitCode:'Codice unità territoriale statistica',
  statisticalTerritorialUnitTypeCode:'Tipo di unità territoriale statistica',
  provinceName:'Denominazione provinciale',
  nuts1_2021:'NUTS 1 (2021)',nuts2_2021:'NUTS 2 (2021)',nuts3_2021:'NUTS 3 (2021)',
  nuts1_2024:'NUTS 1 (2024)',nuts2_2024:'NUTS 2 (2024)',nuts3_2024:'NUTS 3 (2024)',
};
export function municipalityNumber(place:Partial<AlpinePlace>,key:string):number|null{
  const v=place.facts?.[key]?.value;
  return typeof v==='number'&&Number.isFinite(v)?v:null;
}
export function municipalityText(place:Partial<AlpinePlace>,key:string):string|null{
  const v=place.facts?.[key]?.value;
  return typeof v==='string'&&v.trim()?v.trim():null;
}
export function municipalityArchiveFacts(place:Partial<AlpinePlace>):Record<string,AtlasFact>{
  return Object.fromEntries(Object.entries(place.facts||{})
    .filter(([key,fact])=>!MUNICIPALITY_FEATURED_FIELDS.has(key)&&fact &&
      fact.value!==null&&fact.value!==undefined&&
      (typeof fact.value!=='number'||Number.isFinite(fact.value)))
    .map(([key,fact])=>[key,{...fact,label:ARCHIVE_LABELS[key]||fact.label||key,
      group:/^municipalityNumericCode(19|20)/.test(key)?'Codici ISTAT storici':
      /^nuts/.test(key)?'Classificazione NUTS':
      /Code|Flag|Progressive/.test(key)?'Codici e classificazioni':'Altri dati amministrativi'}]));
}
export function municipalityDisplayDate(raw:string|null|undefined):string|null{
  if(!raw)return null;
  const match=/^(\d{4})-(\d\d)-(\d\d)$/.exec(raw);
  if(!match)return raw;
  const dt=new Date(raw+'T12:00:00Z');
  return Number.isNaN(dt.valueOf())?raw:dt.toLocaleDateString('it-IT',
    {day:'numeric',month:'long',year:'numeric',timeZone:'UTC'});
}
