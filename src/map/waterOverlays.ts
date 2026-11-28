import { Popup,type Map as MlMap } from 'maplibre-gl';
import type { AlpineWaterPoint } from '../lib/alpineWater';
import { potabilityLabel } from '../lib/alpineWater';
import { waterDisplayName,waterKindLabel } from '../lib/waterPresentation';
import { registerWaterMapIcons } from './waterIcons';

/** Cluster nativi nei worker, con icone vettoriali rasterizzate una volta per tipologia. */
export function addAlpineWaterLayers(map:MlMap,water:AlpineWaterPoint[]):void{
 if(map.getSource('cb-water'))return;
 registerWaterMapIcons(map);
 map.addSource('cb-water',{
  type:'geojson',
  data:{type:'FeatureCollection',features:water.map(p=>({
    type:'Feature' as const,
    geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
    properties:{slug:p.slug,name:p.name,kind:p.kind,osmUrl:p.osmUrl,potable:p.potable,seasonal:p.seasonal===true},
  }))},
  cluster:true,clusterRadius:40,clusterMaxZoom:13,
  tolerance:0,buffer:16,
 });
 map.addLayer({id:'cb-water-clusters',type:'circle',source:'cb-water',
   minzoom:11,filter:['has','point_count'],
   paint:{'circle-color':'#74c8e9','circle-radius':['step',['get','point_count'],12,20,18,80,23],
     'circle-stroke-width':2,'circle-stroke-color':'#fff'},
 });
 map.addLayer({id:'cb-water-count',type:'symbol',source:'cb-water',
   minzoom:11,filter:['has','point_count'],
   layout:{'text-field':['get','point_count_abbreviated'],'text-font':['Noto Sans Bold'],'text-size':11},
   paint:{'text-color':'#124b66'},
 });
 map.addLayer({id:'cb-water-point',type:'symbol',source:'cb-water',
   minzoom:12,filter:['!',['has','point_count']],
   layout:{'icon-image':['concat','cb-water-',['get','kind']],
     'icon-size':1,'icon-allow-overlap':true},
 });
 map.on('click','cb-water-clusters',event=>{
   const id=event.features?.[0]?.properties?.cluster_id;
   if(typeof id!=='number')return;
   const source=map.getSource('cb-water');
   if(source&&'getClusterExpansionZoom' in source){
     void (source as import('maplibre-gl').GeoJSONSource).getClusterExpansionZoom(id).then(zoom=>{
       map.easeTo({center:event.lngLat,zoom,duration:360});
     }).catch(()=>undefined);
   }
 });
 map.on('click','cb-water-point',event=>{
   const properties=event.features?.[0]?.properties;
   if(!properties)return;
   event.originalEvent.stopPropagation();
   const node=document.createElement('div');
   node.className='cb-water-map-popover';
   const title=document.createElement('strong');
   title.textContent=waterDisplayName({
     name:String(properties.name||''),kind:properties.kind as AlpineWaterPoint['kind'],
   });
   const type=document.createElement('span');
   type.textContent=waterKindLabel(properties.kind as AlpineWaterPoint['kind']);
   const detail=document.createElement('small');
   detail.textContent=potabilityLabel(properties.potable as AlpineWaterPoint['potable'])+
     (properties.seasonal?' · stagionale':'');
   node.append(title,type,detail);
   const url=properties.osmUrl;
   if(typeof url==='string'&&url.startsWith('https://www.openstreetmap.org/')){
     const link=document.createElement('a');
     link.href=url;link.target='_blank';link.rel='noopener noreferrer';
     link.textContent='Apri su OpenStreetMap ↗';
     node.append(link);
   }
   new Popup({closeButton:true,maxWidth:'280px'}).setLngLat(event.lngLat).setDOMContent(node).addTo(map);
 });
 for(const layer of ['cb-water-point','cb-water-clusters']){
   map.on('mouseenter',layer,()=>{map.getCanvas().style.cursor='pointer';});
   map.on('mouseleave',layer,()=>{map.getCanvas().style.cursor='';});
 }
}