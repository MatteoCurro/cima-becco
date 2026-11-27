/** Identica intestazione cartografica per elenco, cima e dossier del luogo. */
export function MapContextLabel({kicker,title,detail}:{kicker:string;title:string;detail?:string}){
  return <div className="cb-map-context" role="note" aria-label={kicker+': '+title}>
    <span>{kicker}</span>
    <strong title={title}>{title}</strong>
    {detail&&<small>{detail}</small>}
  </div>;
}
