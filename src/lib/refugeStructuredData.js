/**
 * JSON-LD per i rifugi. Solo proprietà con significato Schema.org chiaro e
 * valori effettivamente pubblicati; NON inferisce presenza da dato assente,
 * orari/periodi di apertura, disponibilità, prezzi o numero di camere.
 */
import { refugeFact, refugeServiceFacts } from './refugeEditorial.js';

const positiveInteger = value => typeof value==='number' && Number.isSafeInteger(value) && value>0;
const stringValue = value => typeof value==='string' && value.trim() ? value.trim() : null;
const validUrl = value => typeof value==='string' && /^https:\/\//.test(value) ? value : null;

export function refugeSchemaProperties(place) {
  const beds=refugeFact(place,'bedsTotal');
  const winter=refugeFact(place,'bedsWinter');
  const managerBeds=refugeFact(place,'managerBeds');
  const built=refugeFact(place,'yearBuilt');
  const serviceFacts=refugeServiceFacts(place);
  const pets=refugeFact(place,'pets');
  const additionalProperty=[
    ...(positiveInteger(beds)?[{'@type':'PropertyValue',name:'Posti letto totali dichiarati',value:beds,unitText:'posti letto'}]:[]),
    ...(positiveInteger(winter)?[{'@type':'PropertyValue',name:'Posti letto invernali dichiarati',value:winter,unitText:'posti letto'}]:[]),
    ...(positiveInteger(managerBeds)?[{'@type':'PropertyValue',name:'Posti riservati al gestore',value:managerBeds,unitText:'posti letto'}]:[]),
    ...(typeof built==='number' && Number.isInteger(built) && built>1700 && built<=2100?
      [{'@type':'PropertyValue',name:'Anno di costruzione dichiarato',value:built}]:[]),
  ];
  const website=validUrl(place.website || refugeFact(place,'website'));
  const official=validUrl(place.officialUrl);
  const address=stringValue(place.address || refugeFact(place,'address'));
  const email=stringValue(place.email || refugeFact(place,'email'));
  return {
    ...(additionalProperty.length?{additionalProperty}:{}),
    ...(serviceFacts.length?{amenityFeature:serviceFacts.map(item=>({
      '@type':'LocationFeatureSpecification',name:item.label,value:item.value,
    }))}:{}),
    ...(typeof pets==='boolean'?{petsAllowed:pets}:{}),
    ...(address?{address}:{}),
    ...(email?{email}:{}),
    ...((official||website)?{sameAs:[...new Set([official,website].filter(Boolean))]}:{}),
    ...(place.sourceIds?.cai?{identifier:{'@type':'PropertyValue',propertyID:'CAI',value:String(place.sourceIds.cai)}}:{}),
  };
}
