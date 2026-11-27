import type { Map as MlMap, GeoJSONSource } from 'maplibre-gl';
import type { FeatureCollection, Point } from 'geojson';
import type { AlpinePlace } from '../lib/alpinePlaces';

/** GeoJSON a basso costo: coordinate e soli quattro campi nel worker. */
export function alpinePlacesGeoJSON(places: AlpinePlace[]): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: places.map(p => ({
      type: 'Feature' as const, id:p.slug,
      geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
      properties:{slug:p.slug,name:p.name,kind:p.kind},
    })),
  };
}

export interface AlpineMapOptions {
  kind?: AlpinePlace['kind'];
  onSelect?: (place: AlpinePlace) => void;
  getPlace?: (slug:string) => AlpinePlace | undefined;
}

/** Icone proprietarie disegnate in canvas: casetta/rifugio e paese. */
function addMapIcons(map: MlMap): void {
  for (const kind of ['rifugio','bivacco','borgo'] as const) {
    const key='cb-poi-'+kind;
    if(map.hasImage(key))continue;
    const size=60;
    const canvas=document.createElement('canvas');
    canvas.width=canvas.height=size;
    const ctx=canvas.getContext('2d');
    if(!ctx)continue;
    ctx.fillStyle=kind==='rifugio'?'#ff2677':kind==='bivacco'?'#ffc97a':'#e4ffbe';
    ctx.beginPath();ctx.arc(30,30,28,0,Math.PI*2);ctx.fill();
    ctx.lineWidth=3;ctx.strokeStyle='#173f30';ctx.stroke();
    ctx.fillStyle='#163b2b';
    if(kind==='rifugio') {
      ctx.beginPath();ctx.moveTo(12,31);ctx.lineTo(30,14);ctx.lineTo(48,31);ctx.closePath();ctx.fill();
      ctx.fillRect(17,31,26,17);
      ctx.fillStyle='#fffcf4';ctx.fillRect(26,35,8,13);
      ctx.fillRect(20,35,4,5);ctx.fillRect(36,35,4,5);
    } else if(kind==='bivacco'){
      ctx.beginPath();ctx.moveTo(12,44);ctx.lineTo(30,14);ctx.lineTo(48,44);ctx.closePath();ctx.fill();
      ctx.fillStyle='#fffcf4';ctx.fillRect(26,30,8,14);
    } else {
      ctx.fillRect(13,28,12,20);ctx.fillRect(29,22,14,26);
      ctx.beginPath();ctx.moveTo(10,28);ctx.lineTo(19,18);ctx.lineTo(28,28);ctx.closePath();ctx.fill();
      ctx.beginPath();ctx.moveTo(26,22);ctx.lineTo(36,12);ctx.lineTo(46,22);ctx.closePath();ctx.fill();
      ctx.fillStyle='#e4ffbe';ctx.fillRect(17,33,4,6);ctx.fillRect(33,27,5,7);
    }
    map.addImage(key,ctx.getImageData(0,0,size,size),{pixelRatio:2});
  }
  if(!map.hasImage('cb-poi-cluster-pill')){
    const canvas=document.createElement('canvas');canvas.width=100;canvas.height=48;
    const ctx=canvas.getContext('2d');
    if(ctx){
      ctx.fillStyle='#173e30';ctx.strokeStyle='#e9ffc9';ctx.lineWidth=3;
      ctx.beginPath();ctx.roundRect(2,2,96,44,20);ctx.fill();ctx.stroke();
      map.addImage('cb-poi-cluster-pill',ctx.getImageData(0,0,100,48),{pixelRatio:2,
        stretchX:[[35,65]],stretchY:[[18,30]],content:[12,5,88,43]});
    }
  }
}

/**
 * Supercluster nativo nel worker: a basso zoom solo aggregati, a zoom medio
 * icone, ad alto zoom toponimi. La stessa implementazione serve a:
 * - mappa generale (rifugi + borghi)
 * - mappa autonoma rifugi
 * - mappa autonoma borghi
 * - schede dei singoli luoghi.
 */
export function addAlpinePlaceLayers(map: MlMap, all: AlpinePlace[], options: AlpineMapOptions = {}): void {
  const places=options.kind?all.filter(p=>p.kind===options.kind):all;
  const sourceId='cb-atlas-places';
  if(map.getSource(sourceId)) {
    (map.getSource(sourceId) as GeoJSONSource).setData(alpinePlacesGeoJSON(places));
    return;
  }
  addMapIcons(map);
  map.addSource(sourceId,{
    type:'geojson',data:alpinePlacesGeoJSON(places),
    cluster:true,clusterRadius:44,clusterMaxZoom:12,
    tolerance:0,buffer:16,
  });
  map.addLayer({
    id:'cb-atlas-clusters',type:'symbol',source:sourceId,
    filter:['has','point_count'],minzoom:4,
    layout:{
      'icon-image':'cb-poi-cluster-pill',
      'icon-text-fit':'both',
      'icon-text-fit-padding':[9,13,9,13],
      'text-field':['get','point_count_abbreviated'],
      'text-font':['Noto Sans Bold'],'text-size':13,
      'icon-allow-overlap':false,
    },
    paint:{'text-color':'#ffffff'},
  });
  map.addLayer({
    id:'cb-atlas-poi-icons',type:'symbol',source:sourceId,
    filter:['!',['has','point_count']],minzoom:9,
    layout:{
      'icon-image':['match',['get','kind'],'rifugio','cb-poi-rifugio','bivacco','cb-poi-bivacco','cb-poi-borgo'],
      'icon-size':['interpolate',['linear'],['zoom'],9,.7,14,1.05],
      'icon-allow-overlap':false,
    },
  });
  map.addLayer({
    id:'cb-atlas-poi-label',type:'symbol',source:sourceId,
    filter:['!',['has','point_count']],minzoom:13,
    layout:{
      'text-field':['get','name'],
      'text-size':['interpolate',['linear'],['zoom'],13,10,16,12],
      'text-font':['Noto Sans Bold'],
      'text-variable-anchor':['top','bottom','left','right'],
      'text-radial-offset':1.1,'text-optional':true,
    },
    paint:{'text-color':'#173f2e','text-halo-color':'#fffef4','text-halo-width':1.7},
  });
  map.on('click','cb-atlas-clusters',(event)=>{
    const f=event.features?.[0];const count=f?.properties?.cluster_id;
    if(typeof count!=='number')return;
    void (map.getSource(sourceId) as GeoJSONSource).getClusterExpansionZoom(count)
      .then(zoom=>map.easeTo({center:event.lngLat,zoom,duration:420}))
      .catch(()=>undefined);
  });
  const selected=(event:{features?:{properties?:Record<string,unknown>}[];originalEvent?:Event})=>{
    const f=event.features?.[0];
    const slug=f?.properties?.slug, kind=f?.properties?.kind;
    if(typeof slug!=='string'||(kind!=='rifugio'&&kind!=='bivacco'&&kind!=='borgo'))return;
    event.originalEvent?.stopPropagation();
    // Non catturare la lista iniziale dei POI: l'atlante carica il JSON
    // dopo la mappa, e i click devono usare i properties aggiornati del source.
    if(options.onSelect){
      const item=options.getPlace?.(slug) ?? places.find(p=>p.slug===slug);
      if(item)options.onSelect(item);
    }else window.location.hash=`#atlante/${kind==='rifugio'?'rifugi':kind==='bivacco'?'bivacchi':'borghi'}/${slug}`;
  };
  for(const layer of ['cb-atlas-poi-icons','cb-atlas-poi-label']){
    map.on('click',layer,selected);
    map.on('mouseenter',layer,()=>{map.getCanvas().style.cursor='pointer';});
    map.on('mouseleave',layer,()=>{map.getCanvas().style.cursor='';});
  }
  map.on('mouseenter','cb-atlas-clusters',()=>{map.getCanvas().style.cursor='zoom-in';});
  map.on('mouseleave','cb-atlas-clusters',()=>{map.getCanvas().style.cursor='';});
}
