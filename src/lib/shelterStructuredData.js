import { hutServiceFacts } from './hutEditorial.js';
import { refugeFact } from './refugeEditorial.js';

/** I bivacchi sono luoghi, non automaticamente attività commerciali o alberghi. */
export function shelterSchemaProperties(place) {
  const f=key=>refugeFact(place,key);
  const properties=[
    ['bedsTotal','Posti indicati','posti'],
    ['bedsWinter','Posti invernali','posti'],
    ['yearBuilt','Anno di costruzione',null],
    ['yearRebuilt','Anno di ricostruzione',null],
    ['keysRequired','Chiave richiesta',null],
    ['emergencyUseOnly','Uso riservato alle emergenze',null],
    ['reservationsRequired','Prenotazione richiesta',null],
  ].flatMap(([key,name,unit])=>{
    const v=f(key);
    const ok=typeof v==='boolean'||(typeof v==='number'&&Number.isFinite(v)&&v>0);
    return ok?[{'@type':'PropertyValue',name,value:v,...(unit?{unitText:unit}:{})}]:[];
  });
  const amenities=hutServiceFacts(place);
  const sourceId=place?.sourceIds?.cai;
  const official=place?.officialUrl;
  const website=place?.website;
  const urls=[official,website].filter(v=>typeof v==='string'&&/^https:\/\//.test(v));
  return {
    ...(place?.shelterTypeLabel?{additionalProperty:[...properties,{'@type':'PropertyValue',name:'Tipologia di ricovero',value:place.shelterTypeLabel}]}:properties.length?{additionalProperty:properties}:{}),

    ...(amenities.length?{amenityFeature:amenities.map(item=>({
      '@type':'LocationFeatureSpecification',name:item.label,value:item.value,
    }))}:{}),
    ...(sourceId?{identifier:{'@type':'PropertyValue',propertyID:'CAI',value:String(sourceId)}}:{}),
    ...(place?.email?{email:place.email}:{}),
    ...(place?.address?{address:place.address}:{}),
    ...(urls.length?{sameAs:[...new Set(urls)]}:{}),
  };
}
