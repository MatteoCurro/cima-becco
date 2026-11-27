import type { ReactNode } from 'react';

export type DetailMetric = { label: string; value: ReactNode; title?: string };
export type DetailFact = { label: string; value: ReactNode };

/** Gli stessi elementi informativi per rifugi, bivacchi, paesi, trekking e percorsi. */
export function DetailMetrics({ items, label }: { items: readonly DetailMetric[]; label?: string }) {
  return <div className="cb-detail-metrics" aria-label={label}>
    {items.map(item => <div className="cb-detail-metric" key={item.label} title={item.title}>
      <strong>{item.value}</strong><span>{item.label}</span>
    </div>)}
  </div>;
}

export function DetailFacts({ rows }: { rows: readonly DetailFact[] }) {
  return <dl className="cb-detail-facts">{rows.map(row =>
    <div key={row.label}><dt>{row.label}</dt><dd>{row.value}</dd></div>
  )}</dl>;
}

export function DetailSectionHeading({ kicker, title, description, id }: { kicker: string; title: string; description?: string; id?: string }) {
  return <div className="cb-detail-section-heading">
    <span>{kicker}</span><h2 id={id}>{title}</h2>{description && <p>{description}</p>}
  </div>;
}
