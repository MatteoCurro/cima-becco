/**
 * Pure, deterministic refuge copy used by both the React dossier and SEO build.
 * All claims originate from normalized facts, never inferred from proximity,
 * current weather, or catalogue status.
 */
export function refugeFact(place, key) {
  const fact = place?.facts?.[key];
  return fact && (fact.sourceId || fact.sourceUrl) && fact.value !== null && fact.value !== undefined
    ? fact.value : null;
}

export const REFUGE_AMENITIES = Object.freeze([
  {key:'meals',label:'ristorazione',schema:'foodEstablishment'},
  {key:'wifi',label:'Wi-Fi',schema:'wifi'},
  {key:'showers',label:'docce',schema:'showers'},
  {key:'cardPayments',label:'pagamento con carta',schema:'creditCard'},
  {key:'electricity',label:'corrente elettrica',schema:'electricity'},
  {key:'kitchen',label:'uso cucina',schema:'kitchen'},
  {key:'pets',label:'animali ammessi',schema:'petsAllowed'},
  {key:'accessibility',label:'accessibilità dichiarata',schema:'wheelchairAccessible'},
  {key:'defibrillator',label:'defibrillatore',schema:'defibrillator'},
  {key:'waterAvailableReported',label:'acqua in struttura (potabilità non attestata)',schema:'waterAvailable'},
  {key:'drinkingWater',label:'acqua potabile (se specificamente attestata)',schema:'drinkingWater'},
  {key:'hotWater',label:'acqua calda',schema:'hotWater'},
  {key:'mobileSignal',label:'segnale telefonico',schema:'mobileSignal'},
  {key:'accessibleToilets',label:'servizi igienici accessibili',schema:'accessibleToilets'},
  {key:'outsideWater',label:'acqua esterna (potabilità non attestata)',schema:'outsideWater'},
  {key:'sleepingBagLiner',label:'sacco lenzuolo in vendita',schema:'sleepingBagLiner'},
  {key:'solarPower',label:'impianto fotovoltaico',schema:'solarPower'},
  {key:'hydropower',label:'impianto idroelettrico',schema:'hydropower'},
  {key:'generatorPower',label:'generatore',schema:'powerGenerator'},
]);

export function refugeOverview(place) {
  if (typeof place?.shortSummary === 'string' && place.shortSummary.trim()) return place.shortSummary.trim();
  const elevation = refugeFact(place,'elevationM') ?? (Number.isFinite(place?.elevationM) ? place.elevationM : null);
  const location = ['localityId','valleyName','mountainGroupId','municipalityId'].map(key=>refugeFact(place,key))
    .find(value=>typeof value==='string' && value.trim());
  const municipality = place?.administrativeHierarchy?.municipality;
  const where = location || municipality || null;
  const first = place?.name
    ? place.name + (where ? ' si trova nella zona di ' + where : ' è un rifugio alpino censito nell’Atlante Cima Becco')
    : 'Rifugio alpino';
  const intro = first + (typeof elevation==='number' && elevation>0
    ? ', a ' + elevation.toLocaleString('it-IT') + ' metri di quota.' : '.');
  const beds = refugeFact(place,'bedsTotal') ?? (Number.isFinite(place?.capacity) ? place.capacity : null);
  const winter = refugeFact(place,'bedsWinter');
  const capacity = typeof beds==='number' && beds>0
    ? ' Sono indicati ' + beds.toLocaleString('it-IT') + ' posti letto' +
      (typeof winter==='number' && winter>0 ? ', di cui ' + winter + ' invernali' : '') + '.'
    : (typeof winter==='number' && winter>0 ? ' Sono indicati ' + winter + ' posti letto invernali.' : '');
  const positives=REFUGE_AMENITIES.filter(item=>refugeFact(place,item.key)===true);
  const services = positives.length
    ? ' Tra i servizi dichiarati: ' + positives.slice(0,4).map(item=>item.label).join(', ') + '.'
    : '';
  return intro + capacity + services;
}

export function refugeServiceFacts(place) {
  return REFUGE_AMENITIES
    .map(item=>({...item, value:refugeFact(place,item.key)}))
    .filter(item=>item.value===true || item.value===false);
}

export function refugeSeoDescription(place) {
  const copy = refugeOverview(place);
  const trimmed = copy.length>230 ? copy.slice(0,227).replace(/\s+\S*$/,'') + '…' : copy;
  return (trimmed + ' Scopri servizi, contatti, sentieri e mappa su Cima Becco.').slice(0,300);
}
