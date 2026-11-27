/** Central credits manifest. Provenance remains in its originating records. */
export const SOURCE_PROVIDERS = Object.freeze([
  {id:'osm',name:'OpenStreetMap contributors',category:'Geografia, sentieri e punti d’interesse',
   url:'https://www.openstreetmap.org/copyright',licence:'ODbL 1.0'},
  {id:'cai',name:'Club Alpino Italiano · Unico Rifugi',category:'Rifugi, bivacchi, capanne e punti d’appoggio',
   url:'https://rifugi.cai.it/',licence:'Riuso confermato dal titolare Cima Becco'},
  {id:'sat',name:'Società degli Alpinisti Tridentini (SAT)',category:'Rifugi, bivacchi, sentieri e riferimenti ufficiali',
   url:'https://www.sat.tn.it/elenco-bivacchi/',licence:'Fonte istituzionale identificata'},
  {id:'commons',name:'Wikimedia Commons',category:'Immagini, panorami e fotografie',
   url:'https://commons.wikimedia.org/',licence:'Licenza originale conservata per ciascuna fotografia'},
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

export function makeCentralCredits(places=[],routes=[],peakPhotos={}, generatedAt='') {
  const records=[];
  const dedup=new Set();
  const add=(kind,slug,name,src,author,licence,mediaUrl)=>{
    if (typeof src!=='string'||!src.startsWith('https://') ||
        typeof licence!=='string'||!licence ||
        typeof author!=='string'||!author.trim()) return;
    const key=[kind,slug,src].join('\x1f');
    if(dedup.has(key))return; dedup.add(key);
    const path=kind==='route'?'route':kind==='peak'?'place':
      kind==='rifugio'?'rifugi':kind==='bivacco'?'bivacchi':'borghi';
    records.push({
      kind,slug,name:String(name||slug).slice(0,180),
      entityUrl:'/'+path+'/'+encodeURIComponent(slug)+'/',
      sourceUrl:src,author:author.trim().slice(0,240),
      licence:licence.slice(0,150),mediaUrl:mediaUrl||null,
    });
  };
  for(const p of places) {
    if(!p?.slug || !p.kind)continue;
    if(p.photo?.url)add(p.kind,p.slug,p.name,p.photo.sourceUrl,p.photo.author,p.photo.license,p.photo.url);
    for(const m of p.media||[])
      if((m.kind==='photo'||m.kind==='historical_photo'||m.kind==='logo') &&
         m.reuseAllowed && m.subjectVerified)
        add(p.kind,p.slug,p.name,m.sourceUrl,m.author||'Archivio della fonte',m.licence,m.url);
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
    counts:{
      total:records.length,
      byType:Object.fromEntries([...new Set(records.map(x=>x.kind))].sort().map(k=>
        [k,records.filter(x=>x.kind===k).length])),
    },
  };
}
