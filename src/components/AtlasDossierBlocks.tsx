import type { ReactNode } from 'react';
import {
  ATLAS_RELATION_LABELS, activeAtlasAlerts, authorizedAtlasMedia, formatAtlasFact,
  presentAtlasFacts, usableAtlasClimate, type AtlasEntityMetadata, type AtlasFact,
  type AtlasRelation, type AtlasTechnical,
} from '../lib/atlasDossier';
import './atlasDossier.css';

function Section({ kicker, title, children }: { kicker: string; title: string; children: ReactNode }) {
  return <section className="cb-dossier-section">
    <header className="cb-dossier-heading"><small>{kicker}</small><h2>{title}</h2></header>
    {children}
  </section>;
}
function Source({ url, label = 'Fonte' }: { url?: string; label?: string }) {
  return url && /^https:\/\//.test(url) ?
    <a href={url} rel="noopener noreferrer" target="_blank">{label} ↗</a> : null;
}
function FactTile({ name, fact }: { name: string; fact: AtlasFact }) {
  const label = fact.label || name.replace(/([a-z])([A-Z])/g, '$1 $2').replace(/_/g, ' ');
  return <div className="cb-dossier-fact">
    <dt>{label}</dt><dd>{formatAtlasFact(fact)}</dd>
    {(fact.method === 'estimated' || fact.method === 'derived') &&
      <small className="cb-dossier-method">{fact.method === 'estimated' ? 'Stima' : 'Calcolo derivato'}</small>}
    {fact.sourceUrl && <small className="cb-dossier-source"><Source url={fact.sourceUrl} label={fact.sourceId || 'Origine del dato'}/></small>}
  </div>;
}
function Technical({ technical }: { technical: AtlasTechnical }) {
  const values: { name: string; value: string | number | undefined }[] = [
    { name: 'Difficoltà', value: technical.grade && (technical.grade + (technical.gradeScale ? ' · ' + technical.gradeScale : '')) },
    { name: 'Chiodatura', value: technical.protection }, { name: 'Spit indicati', value: technical.bolts },
    { name: 'Rinvii dichiarati', value: technical.quickdraws }, { name: 'Lunghezza corda dichiarata', value: technical.ropeLengthM == null ? undefined : technical.ropeLengthM + ' m' },
    { name: 'Sosta', value: technical.belay }, { name: 'Esposizione', value: technical.exposure }, { name: 'Roccia', value: technical.rock },
  ];
  return <Section kicker="ARRAMPICATA / DATI TECNICI" title="Vie, gradi e protezioni">
    <dl className="cb-dossier-facts">{values.map(item =>
      <div className="cb-dossier-fact" key={item.name}><dt>{item.name}</dt><dd>{item.value ?? 'Non disponibile'}</dd></div>)}</dl>
    <p className="cb-dossier-note">Dati tecnici documentali: non attestano lo stato degli ancoraggi né la sicurezza della via. Spit e rinvii non vengono dedotti l'uno dall'altro.</p>
  </Section>;
}
function RelationItem({ relation }: { relation: AtlasRelation }) {
  const suffix = relation.type === 'near' || relation.type === 'passes_near'
    ? ' · prossimità geografica, non prova di accesso' : '';
  return <li className="cb-dossier-relation">
    <span>{ATLAS_RELATION_LABELS[relation.type]}</span>
    <strong>{relation.target.href
      ? <a href={relation.target.href}>{relation.target.name}</a>
      : relation.target.name}</strong>
    {relation.straightLineKm != null && relation.type === 'near' &&
      <small>{relation.straightLineKm.toLocaleString('it-IT', {maximumFractionDigits:1})} km in linea d'aria</small>}
    {suffix && <small>{suffix.replace(/^ · /, '')}</small>}
    {relation.sourceUrl && <small><Source url={relation.sourceUrl}/></small>}
  </li>;
}
/** Moduli separati per responsabilità; nessun blocco vuoto, nessuna fonte o immagine inventata. */
export function AtlasDossierBlocks({ record, placement }: {
  record: AtlasEntityMetadata; placement: 'alerts' | 'core' | 'connections' | 'media' | 'credits';
}) {
  if (placement === 'alerts') {
    const notices = activeAtlasAlerts(record.alerts);
    return notices.length ? <div className="cb-dossier-alerts" aria-label="Avvisi documentati">
      {notices.map(alert => <aside className="cb-dossier-alert" key={alert.id} role="status">
        <strong>{alert.title}</strong><p>{alert.message}</p>
        <small>Verificato: {alert.checkedAt}{alert.validUntil ? ' · validità fino al ' + alert.validUntil : ''} · <Source url={alert.sourceUrl} label="Avviso ufficiale"/></small>
      </aside>)}
    </div> : null;
  }

  if (placement === 'core') {
    const facts = presentAtlasFacts(record.facts);
    const climate = usableAtlasClimate(record.climate);
    const hasTechnical = Boolean(record.technical);
    const hasPitches = Boolean(record.pitches?.length);
    const hasStages = Boolean(record.stages?.length);
    if (!facts.length && !record.history && !climate.length && !hasTechnical && !hasPitches && !hasStages) return null;
    return <div className="cb-dossier-modules">
      {facts.length > 0 && <Section kicker="ATLANTE / DATI DOCUMENTATI" title="La scheda in dettaglio">
        <dl className="cb-dossier-facts">{facts.map(([name, fact]) => <FactTile name={name} fact={fact} key={name}/>)}</dl>
      </Section>}
      {record.history && record.historySourceUrl && <Section kicker="STORIA E TERRITORIO" title="Storie di montagna">
        <p className="cb-dossier-prose">{record.history}</p><Source url={record.historySourceUrl} label="Fonte storica"/>
      </Section>}
      {hasStages && <Section kicker="CAMMINI / TAPPE" title="Le tappe documentate">
        <ol className="cb-dossier-stages">{record.stages!.filter(stage => stage.id && stage.title && Number.isFinite(stage.ordinal))
          .sort((a,b) => a.ordinal-b.ordinal).map(stage => <li key={stage.id}>
            <span>Tappa {stage.ordinal}{stage.official === true ? ' · ufficiale' : stage.official === false ? ' · proposta' : ''}</span>
            <strong>{stage.href ? <a href={stage.href}>{stage.title}</a> : stage.title}</strong>
            <small>{[stage.lengthKm != null ? stage.lengthKm + ' km' : null,stage.gainM != null ? '+' + stage.gainM + ' m' : null].filter(Boolean).join(' · ')}</small>
            <Source url={stage.sourceUrl} label="Riferimento"/>
          </li>)}</ol>
      </Section>}
      {record.technical && <Technical technical={record.technical}/>}
      {hasPitches && <Section kicker="ARRAMPICATA / MULTIPITCH" title="Tiri della via">
        <div className="cb-dossier-table-wrap"><table className="cb-dossier-pitches"><thead><tr><th>Tiro</th><th>Grado</th><th>Metri</th><th>Spit</th><th>Rinvii</th><th>Sosta</th></tr></thead>
        <tbody>{record.pitches!.filter(p => p.id && Number.isFinite(p.ordinal)).sort((a,b)=>a.ordinal-b.ordinal).map(p => <tr key={p.id}>
          <th>{p.ordinal}</th><td>{p.grade ?? '—'}</td><td>{p.lengthM ?? '—'}</td><td>{p.bolts ?? '—'}</td><td>{p.quickdraws ?? '—'}</td><td>{p.belay ?? '—'}</td>
        </tr>)}</tbody></table></div>
      </Section>}
      {climate.map(series => <Section key={series.id} kicker="CLIMA / SERIE DOCUMENTATA" title={series.name}>
        <p className="cb-dossier-note">Periodo: {series.period} · unità: {series.unit} · <Source url={series.sourceUrl} label="Serie e metodo"/></p>
        <div className="cb-dossier-climate" role="list" aria-label={series.name + ', ' + series.unit}>
        {series.values.filter(v=>v.month>=1&&v.month<=12).sort((a,b)=>a.month-b.month).map(point=><div role="listitem" key={point.month}>
          <span>{new Date(Date.UTC(2026,point.month-1,1)).toLocaleString('it-IT',{month:'short',timeZone:'UTC'})}</span>
          <strong>{point.value == null ? '—' : point.value.toLocaleString('it-IT') + ' ' + series.unit}</strong>
        </div>)}</div>
      </Section>)}
    </div>;
  }

  if (placement === 'connections') {
    const relations = (record.relations ?? []).filter(r=>r.target?.id && r.target.name && ATLAS_RELATION_LABELS[r.type]);
    return relations.length ? <Section kicker="ATLANTE / CONNESSIONI" title="Nello stesso territorio">
      <ul className="cb-dossier-relations">{relations.map((relation,index)=><RelationItem relation={relation} key={relation.type + ':' + relation.target.id + ':' + index}/>)}</ul>
    </Section> : null;
  }

  if (placement === 'media') {
    const media = authorizedAtlasMedia(record.media);
    const webcams = (record.webcams ?? []).filter(cam => Boolean(cam.id && cam.officialUrl && cam.name && cam.operator));
    return media.length || webcams.length ? <div className="cb-dossier-modules">
      {media.length > 0 && <Section kicker="FOTOGRAFIE / ARCHIVIO" title="Immagini documentate">
        <div className="cb-dossier-gallery">{media.map(item => <figure key={item.id}>
          {item.kind === 'video' ? <a href={item.sourceUrl} target="_blank" rel="noopener noreferrer">Apri il video originale ↗</a> :
            <img src={item.url} alt={item.caption || 'Immagine documentata'} loading="lazy"/>}
          <figcaption>{item.caption || 'Immagine del luogo'}{item.capturedAt ? ' · scatto ' + item.capturedAt : ''}
            <small>{item.author || 'Autore non indicato'} · {item.licence} · <Source url={item.sourceUrl} label="Origine e licenza"/></small>
          </figcaption>
        </figure>)}</div>
      </Section>}
      {webcams.length > 0 && <Section kicker="OSSERVAZIONE / WEBCAM" title="Webcam del territorio">
        <div className="cb-dossier-webcams">{webcams.map(cam => <article key={cam.id}>
          <strong>{cam.name}</strong>
          {cam.stillUrl && cam.stillReuseAllowed && cam.stillLicence && <img src={cam.stillUrl} alt={'Ultima immagine disponibile: ' + cam.name} loading="lazy"/>}
          <p>{[cam.operator, cam.direction && 'Direzione: ' + cam.direction, cam.target && 'Inquadratura: ' + cam.target].filter(Boolean).join(' · ')}</p>
          <small>{cam.refreshedAt ? 'Immagine/stream aggiornato: ' + cam.refreshedAt : 'Aggiornamento non verificato'}{cam.status === 'offline' ? ' · Fuori servizio' : ''}</small>
          <Source url={cam.officialUrl} label="Webcam ufficiale"/>
        </article>)}</div>
      </Section>}
    </div> : null;
  }

  const sources = new Map<string, string>();
  for (const f of Object.values(record.facts ?? {})) if (f?.sourceUrl) sources.set(f.sourceUrl, f.sourceId || f.sourceUrl);
  for (const r of record.relations ?? []) if (r.sourceUrl) sources.set(r.sourceUrl, 'Relazione documentata');
  for (const m of record.media ?? []) if (m.sourceUrl) sources.set(m.sourceUrl, 'Media: ' + m.licence);
  if (record.historySourceUrl) sources.set(record.historySourceUrl, 'Archivio storico');
  for (const c of record.climate ?? []) if (c.sourceUrl) sources.set(c.sourceUrl, 'Serie climatica');
  return sources.size ? <details className="cb-dossier-credits"><summary>Fonti e crediti del dossier <span>{sources.size}</span></summary>
    <ul>{[...sources].map(([url,label])=><li key={url}><Source url={url} label={label}/></li>)}</ul>
    {record.checkedAt && <small>Ultima verifica: {record.checkedAt}</small>}
    {record.updatedAt && <small>Ultimo aggiornamento della scheda: {record.updatedAt}</small>}
  </details> : null;
}
