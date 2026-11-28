/** Central credits manifest. Provenance remains in its originating records. */
export const SOURCE_PROVIDERS = Object.freeze([
  {id:'osm',name:'OpenStreetMap contributors',category:'Geografia, sentieri e punti d’interesse',
   url:'https://www.openstreetmap.org/copyright',licence:'ODbL 1.0'},
  {id:'istat',name:'ISTAT',category:'Comuni, codici territoriali e statistiche amministrative',url:'https://www.istat.it/',licence:'Licenza della risorsa originale'},
  {id:'dait',name:'Ministero dell’Interno · DAIT',category:'Amministrazione comunale e titolari delle cariche',url:'https://dait.interno.gov.it/',licence:'Fonte istituzionale con data di estrazione'},
  {id:'wikipedia',name:'Wikipedia in italiano',category:'Testi territoriali e approfondimenti documentati',url:'https://it.wikipedia.org/',licence:'CC BY-SA 4.0 per gli estratti usati'},
  {id:'cai',name:'Club Alpino Italiano · Unico Rifugi',category:'Rifugi, bivacchi, capanne e punti d’appoggio',
   url:'https://rifugi.cai.it/',licence:'Riuso confermato dal titolare Cima Becco'},
  {id:'sat',name:'Società degli Alpinisti Tridentini (SAT)',category:'Rifugi, bivacchi, sentieri e riferimenti ufficiali',
   url:'https://www.sat.tn.it/elenco-bivacchi/',licence:'Fonte istituzionale identificata'},
  {id:'commons',name:'Wikimedia Commons',category:'Immagini, panorami e fotografie',
   url:'https://commons.wikimedia.org/',licence:'Licenza originale conservata per ciascuna fotografia'},
  {id:'prov-bolzano-lakes',name:'Provincia autonoma di Bolzano · Catasto laghi',
   category:'Perimetri e misure dei corpi idrici censiti (record WFS G0, non schede G2)',
   url:'https://data.civis.bz.it/dataset/laghi',licence:'CC0 1.0'},
  {id:'arpav-water-surfaces',name:'ARPAV · Idrografia e specchi d’acqua del Veneto',
   category:'Perimetri e classi di fonte dei corpi idrici (record WFS G0)',
   url:'https://geodati.gov.it/geoportale/visualizzazione-metadati/scheda-metadati?metadataid=arpa_ve:idrografia_specchio_acqua',
   licence:'CC BY 3.0'},
  {id:'geonames',name:'GeoNames',category:'Cime, coordinate e toponimi',
   url:'https://www.geonames.org/',licence:'CC BY 4.0'},
  {id:'wikidata',name:'Wikidata / Wikipedia',category:'Toponimi e approfondimenti',
   url:'https://www.wikidata.org/',licence:'CC0 per dati Wikidata; verificare singole pagine Wikipedia'},
  {id:'meteo',name:'Open-Meteo',category:'Meteo attuale, previsioni e serie storiche',
   url:'https://open-meteo.com/',licence:'Attribuzione e condizioni del servizio'},
  {id:'dem',name:'AWS Terrain Tiles / modelli altimetrici',category:'Stime di quota e dislivello',
   url:'https://registry.opendata.aws/terrain-tiles/',licence:'Provenienza tecnica per dataset'},
  {id:'map',name:'OpenTopoMap-R / OpenFreeMap / Esri',category:'Cartografia di base e vista satellitare',
   url:'https://openmaps.fr/tile-usage-policy.html',licence:'Condizioni dei rispettivi fornitori'},
  {id:'code',name:'HillGPX e componenti open-source',category:'Codice e componenti del progetto',
   url:'https://github.com/StarlightsJourney/HillGPX',licence:'MIT e altre licenze nelle dipendenze'},
]);

export function makeCentralCredits(places=[],routes=[],peakPhotos={}, generatedAt='',municipalities=[],people=[],summits=[],naturalPasses=[],naturalLakes=[],lakePointsG1=[]) {
  const records=[];
  const dedup=new Set();
  const add=(kind,slug,name,src,author,licence,mediaUrl)=>{
    if (typeof src!=='string'||!src.startsWith('https://') ||
        typeof licence!=='string'||!licence ||
        typeof author!=='string'||!author.trim()) return;
    // A CAI shelter may have multiple distinct photos all credited to the
    // SAME detail page: uniqueness must include each individual media URL.
    const key=[kind,slug,src,mediaUrl||''].join('\x1f');
    if(dedup.has(key))return; dedup.add(key);
    const path=kind==='person'?'fonti-e-crediti':kind==='route'?'route':kind==='peak'?'place':kind==='summit'?'cime':kind==='natural_pass'?'passi':kind==='natural_lake'?'laghi':kind==='natural_lake_g1'?'laghi/identificati':kind==='municipality'?'comuni':
      kind==='rifugio'?'rifugi':kind==='bivacco'?'bivacchi':'borghi';
    records.push({
      kind,slug,name:String(name||slug).slice(0,180),
      entityUrl:kind==='person'?'/fonti-e-crediti/':'/'+path+'/'+encodeURIComponent(slug)+'/',
      sourceUrl:src,author:author.trim().slice(0,240),
      licence:licence.slice(0,150),mediaUrl:mediaUrl||null,
    });
  };
  const textCredits=[];
  for(const p of places) {
    if(!p?.slug || !p.kind)continue;
    if(p.photo?.url)add(p.kind,p.slug,p.name,p.photo.sourceUrl,p.photo.author,p.photo.license,p.photo.url);
    for(const m of p.media||[])
      if((m.kind==='photo'||m.kind==='historical_photo'||m.kind==='logo') &&
         m.reuseAllowed && m.subjectVerified)
        add(p.kind,p.slug,p.name,m.sourceUrl,m.author||'Archivio della fonte',m.licence,m.url);
    // G2 insediamenti: estratti documentati legati alla stessa scheda e QID.
    // Le fonti mantengono la licenza originale (es. CC BY-SA 4.0).
    if(p.kind==='borgo' && p.sourceIds?.wikidata && p.subtype!=='italian_municipality') {
      for(const source of p.textSources||[]){
        if(source.text && source.sourceId && source.sourceUrl?.startsWith('https://') && source.licence)
          textCredits.push({kind:'borgo',slug:p.slug,name:p.name,
            entityUrl:'/borghi/'+encodeURIComponent(p.slug)+'/',
            sourceUrl:source.sourceUrl,author:'Contributori di Wikipedia',
            licence:source.licence,sourceId:source.sourceId,
            sourceUpdatedAt:source.sourceUpdatedAt||null});
      }
    }
  }
  for(const municipality of municipalities) {
    if(!municipality?.slug || municipality.kind!=='municipality')continue;
    const name=municipality.name;
    for(const m of municipality.media||[]) {
      if((m.kind==='photo'||m.kind==='historical_photo'||m.kind==='logo') &&
         m.reuseAllowed && m.subjectVerified && m.author && m.licence && m.sourceUrl)
        add('municipality',municipality.slug,name,m.sourceUrl,m.author,m.licence,m.url);
    }
    for(const source of municipality.textSources||[]) {
      if(source.text && source.sourceUrl?.startsWith('https://') && source.licence) {
        textCredits.push({kind:'municipality',slug:municipality.slug,name,
          entityUrl:'/comuni/'+encodeURIComponent(municipality.slug)+'/',
          sourceUrl:source.sourceUrl,author:'Contributori di Wikipedia',licence:source.licence,
          sourceId:source.sourceId,sourceUpdatedAt:source.sourceUpdatedAt||null});
      }
    }
  }
  // People are G1 linked entities, not yet indexable Person dossier pages.
  // Central credits link back to the credits register until a verified public
  // /persone/<slug>/ page is actually implemented.
  for(const person of people){
    if(!/^Q[1-9][0-9]*$/.test(String(person?.qid||'')))continue;
    for(const m of person.media||[]){
      if(m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&m.author&&m.licence&&m.sourceUrl)
        add('person',person.qid,person.name,m.sourceUrl,m.author,m.licence,m.url);
    }
    for(const source of person.textSources||[]){
      if(source.text&&source.sourceId&&source.sourceUrl?.startsWith('https://')&&source.licence){
        textCredits.push({kind:'person',slug:person.qid,name:person.name,
          entityUrl:'/fonti-e-crediti/',
          sourceUrl:source.sourceUrl,author:source.author||'Contributori di Wikipedia',
          licence:source.licence,sourceId:source.sourceId,
          sourceUpdatedAt:source.sourceUpdatedAt||null});
      }
    }
  }
  // Published G2 summit dossiers: photos and CC BY-SA excerpts are credited
  // in the central register, never repeated as text overlays on each SEO page.
  for(const e of summits) {
    if(e?.kind!=='summit'||e?.quality?.gate!=='G2'||!e.quality.seoIndexable||!e.slug)continue;
    for(const m of e.media||[]) {
      if(m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&m.author&&m.licence&&m.sourceUrl)
        add('summit',e.slug,e.name,m.sourceUrl,m.author,m.licence,m.url);
    }
    for(const source of e.textSources||[]) {
      if(source.text&&source.sourceId&&source.sourceUrl?.startsWith('https://')&&source.licence)
        textCredits.push({kind:'summit',slug:e.slug,name:e.name,
          entityUrl:'/cime/'+encodeURIComponent(e.slug)+'/',
          sourceUrl:source.sourceUrl,author:'Contributori di Wikipedia',
          licence:source.licence,sourceId:source.sourceId,
          sourceUpdatedAt:source.sourceUpdatedAt||null});
    }
  }
  // Nature passes use the same media/text provenance register as the other
  // atlas entities. No repeated author/license overlay on each pass dossier.
  for(const e of naturalPasses) {
    if(e?.kind!=='natural_feature' ||
       !['mountain_pass','saddle'].includes(e.subtype) ||
       e?.quality?.gate!=='G2' || e.quality.seoIndexable!==true || !e.slug)continue;
    for(const m of e.media||[]){
      if(m.kind==='photo' && m.subjectVerified && m.reuseAllowed &&
         m.author && m.licence && m.sourceUrl && m.url)
        add('natural_pass',e.slug,e.name,m.sourceUrl,m.author,m.licence,m.url);
    }
    for(const textSource of e.textSources||[]){
      if(textSource.text && textSource.sourceId &&
         textSource.sourceUrl?.startsWith('https://') && textSource.licence)
        textCredits.push({kind:'natural_pass',slug:e.slug,name:e.name,
          entityUrl:'/passi/'+encodeURIComponent(e.slug)+'/',
          sourceUrl:textSource.sourceUrl,author:'Contributori di Wikipedia',
          licence:textSource.licence,sourceId:textSource.sourceId,
          sourceUpdatedAt:textSource.sourceUpdatedAt||null});
    }
  }
  // Lakes G2 retain each image and encyclopedia source on the canonical
  // entity; only this derived central register renders author and licence.
  for(const e of naturalLakes){
    if(e?.kind!=='natural_feature' ||
       !['lake','reservoir'].includes(e.subtype) ||
       e?.quality?.gate!=='G2' || e.quality.seoIndexable!==true || !e.slug)continue;
    for(const m of e.media||[]){
      if(m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&
         m.author&&m.licence&&m.sourceUrl&&m.url)
        add('natural_lake',e.slug,e.name,m.sourceUrl,m.author,m.licence,m.url);
    }
    for(const t of e.textSources||[]){
      if(t.text&&t.sourceId&&t.licence&&t.sourceUrl?.startsWith('https://'))
        textCredits.push({kind:'natural_lake',slug:e.slug,name:e.name,
          entityUrl:'/laghi/'+encodeURIComponent(e.slug)+'/',
          sourceUrl:t.sourceUrl,author:'Contributori di Wikipedia',licence:t.licence,
          sourceId:t.sourceId,sourceUpdatedAt:t.sourceUpdatedAt||null});
    }
  }
  // G1 lake pages have no new accordion. The existing central register
  // derives attribution from verified P18 photo / itwiki QID fields.
  for(const e of lakePointsG1){
    if(e?.quality?.gate!=='G1'||e.quality.seoIndexable!==false||
       e.sourceIds?.wikidataVerifiedBy!=='P1566+P625'||!e.slug)continue;
    for(const m of e.media||[]){
      if(m.kind==='photo'&&m.subjectVerified&&m.reuseAllowed&&
         m.author&&m.licence&&m.sourceUrl&&m.url&&
         m.sourceId==='wikidata:'+e.sourceIds.wikidata+':P18')
        add('natural_lake_g1',e.slug,e.name,m.sourceUrl,m.author,m.licence,m.url);
    }
    for(const t of e.textSources||[]){
      if(t.text&&t.sourceId?.startsWith('wikipedia:it:')&&t.licence&&
         t.sourceUrl?.startsWith('https://it.wikipedia.org/'))
        textCredits.push({kind:'natural_lake_g1',slug:e.slug,name:e.name,
          entityUrl:'/laghi/identificati/'+encodeURIComponent(e.slug)+'/',
          sourceUrl:t.sourceUrl,author:'Contributori di Wikipedia',
          licence:t.licence,sourceId:t.sourceId,
          sourceUpdatedAt:t.sourceUpdatedAt||null});
    }
  }
  for(const r of routes) {
    if(!r?.slug)continue;
    for(const photo of r.photos||[])
      add('route',r.slug,r.name,photo.sourceUrl,photo.author||'Archivio della fonte',
          photo.license,photo.url);
  }
  for(const [slug,photo] of Object.entries(peakPhotos||{})) {
    if(Array.isArray(photo) && photo.length>=4)
      add('peak',slug,slug,photo[1],photo[2],photo[3],photo[0]);
  }
  records.sort((a,b)=>a.kind.localeCompare(b.kind)||
    a.name.localeCompare(b.name,'it')||a.sourceUrl.localeCompare(b.sourceUrl));
  return {
    schemaVersion:'1.0',generatedAt,
    centralPage:'/fonti-e-crediti/',
    provenancePolicy:'Source IDs, URLs, licences and authors remain within facts and media objects',
    providers:SOURCE_PROVIDERS,
    photoCredits:records,
    textCredits,
    counts:{
      total:records.length,
      textTotal:textCredits.length,
      byType:Object.fromEntries([...new Set(records.map(x=>x.kind))].sort().map(k=>
        [k,records.filter(x=>x.kind===k).length])),
    },
  };
}
