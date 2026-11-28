/** Common SEO build adapter: only reviewed, licensed G2 settlements. */
export function mergeSettlementsForSeo(base,release) {
  if(!release||release.releaseChannel!=='ISTAT21_OSM_SETTLEMENTS'||
     release.isPublished!==true||!Array.isArray(release.entities)) return base;
  const rows=[];
  for(const entity of release.entities){
    const point=entity.geo?.point;
    const photo=(entity.media||[]).find(m=>m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&
      m.url?.startsWith('https://')&&m.sourceUrl?.startsWith('https://')&&m.licence&&m.author);
    if(entity.kind!=='settlement'||entity.quality?.gate!=='G2'||!entity.quality?.seoIndexable||
       !point||!Number.isFinite(point.lat)||!Number.isFinite(point.lng)||
       !entity.sourceIds?.wikidata||!entity.slug||!entity.name||!photo||
       !entity.description||entity.description.trim().length<120) continue;
    const osm=entity.sourceIds.osm;
    rows.push({
      id:entity.id,slug:entity.slug,name:entity.name,kind:'borgo',
      subtype:entity.subtype,slugAliases:entity.slugAliases||[],
      sourceIds:entity.sourceIds, lat:point.lat,lng:point.lng,
      osmUrl:/^(node|way|relation)\/[1-9][0-9]*$/.test(osm||'')
        ?'https://www.openstreetmap.org/'+osm
        :'https://www.openstreetmap.org/#map=13/'+point.lat+'/'+point.lng,
      facts:entity.facts||{},relations:entity.relations||[],media:entity.media||[],
      description:entity.description,shortSummary:entity.shortSummary,
      textSources:entity.textSources||[],
      administrativeHierarchy:entity.administrativeHierarchy,
      connectedPeople:entity.connectedPeople||[],
      elevationM:typeof entity.facts?.elevationM?.value==='number'
        ?entity.facts.elevationM.value:undefined,
      photo:{url:photo.url,sourceUrl:photo.sourceUrl,
        author:photo.author,license:photo.licence},
    });
  }
  const osm=new Set(rows.map(e=>e.sourceIds.osm).filter(Boolean));
  const qids=new Set(rows.map(e=>e.sourceIds.wikidata).filter(Boolean));
  const keep=base.filter(p=>p.kind!=='borgo'||(
    !osm.has(p.osmUrl?.replace('https://www.openstreetmap.org/',''))&&
    !qids.has(p.wikidata)));
  const seen=new Set(keep.map(p=>p.slug));
  return [...keep,...rows.filter(e=>{if(seen.has(e.slug))return false;
    seen.add(e.slug);return true;})];
}
