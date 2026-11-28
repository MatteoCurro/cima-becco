import type { Venue } from '../types';
import { AtlasDossierBlocks } from './AtlasDossierBlocks';

const INTERNAL_KEYS = new Set([
  'elevationM', 'featureClass', 'wikidataElevationReportedM', 'wikidataIdentityVerified',
]);
const FEATURE_LABELS: Record<string, string> = {
  PK: 'Cima', MT: 'Montagna', VLC: 'Vulcano', HLL: 'Rilievo',
  PKS: 'Gruppo di vette', MTS: 'Massiccio montuoso',
};
const COUNTRY_LABELS: Record<string, string> = {
  IT: 'Italia', AT: 'Austria', CH: 'Svizzera', FR: 'Francia', SI: 'Slovenia',
};
export function summitGeography(venue: Venue) {
  const source = venue.facts?.elevationM;
  const sourceAltitude = typeof source?.value === 'number' ? source.value : null;
  const wikidata = venue.facts?.wikidataElevationReportedM;
  const secondAltitude = typeof wikidata?.value === 'number' ? wikidata.value : null;
  const typeCode = String(venue.facts?.featureClass?.value ?? '');
  const country = venue.administrativeHierarchy?.country;
  const names = [...(venue.localNames ?? []), ...(venue.aliases ?? [])]
    .filter(x => x.value && x.value.toLocaleLowerCase('it') !== venue.name.toLocaleLowerCase('it'));
  const dedupNames = [...new Map(names.map(x => [x.value.toLocaleLowerCase('it'), x])).values()];
  return {
    type: FEATURE_LABELS[typeCode] ?? 'Cima',
    country: country ? COUNTRY_LABELS[country] ?? country : null,
    province: venue.administrativeHierarchy?.province,
    region: venue.administrativeHierarchy?.region,
    sourceAltitude, secondAltitude,
    differs: sourceAltitude !== null && secondAltitude !== null && Math.abs(sourceAltitude-secondAltitude) >= 1,
    method: source?.method ?? null,
    names: dedupNames,
  };
}
export function SummitGeography({ venue }: { venue: Venue }) {
  const geo = summitGeography(venue);
  const extraFacts = Object.fromEntries(Object.entries(venue.facts ?? {})
    .filter(([key]) => !INTERNAL_KEYS.has(key)));
  const extraRecord = {
    ...venue, facts: extraFacts,
    aliases: [], localNames: [], administrativeHierarchy: undefined,
  };
  return <>
    <section className="venue-detail-section cb-detail-group cb-summit-geography" id="cb-summit-geography">
      <p className="cb-summit-kicker">GEOGRAFIA E TOPONIMI</p>
      <h2>La cima, sulla carta.</h2>
      <dl className="cb-summit-geo-list">
        <div><dt>Tipo di rilievo</dt><dd>{geo.type}</dd></div>
        {geo.country && <div><dt>Paese</dt><dd>{geo.country}</dd></div>}
        {geo.region && <div><dt>Regione</dt><dd>{geo.region}</dd></div>}
        {geo.province && <div><dt>Provincia</dt><dd>{geo.province}</dd></div>}
        <div><dt>Coordinate</dt><dd>{venue.lat.toFixed(5)}° N · {venue.lng.toFixed(5)}° E</dd></div>
        {geo.method && <div><dt>Metodo della quota</dt><dd>{geo.method==='reported'?'Quota riportata dalla fonte':geo.method==='estimated'?'Quota stimata':'Quota calcolata'}</dd></div>}
        {geo.differs && <div><dt>Quota alternativa documentata</dt><dd>{geo.secondAltitude?.toLocaleString('it-IT')} m <small>(Wikidata; non sostituisce il valore principale)</small></dd></div>}
      </dl>
      {geo.names.length>0 && <div className="cb-summit-geo-names">
        <strong>La conoscono anche come</strong>
        <p>{geo.names.map((item,i)=><span key={item.value+i}>{item.value}{item.language ? ' ('+item.language+')' : ''}</span>)}</p>
      </div>}
    </section>
    <AtlasDossierBlocks record={extraRecord} placement="core"/>
  </>;
}
