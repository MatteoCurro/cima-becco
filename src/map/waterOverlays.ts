import type { Map as MlMap } from 'maplibre-gl';
import type { AlpineWaterPoint } from '../lib/alpineWater';

/** Cluster nativi nei worker; non renderizzare migliaia di DOM marker. */
export function addAlpineWaterLayers(map:MlMap,water:AlpineWaterPoint[]):void{
 if(map.getSource('cb-water'))return;
 map.addSource('cb-water',{
  type:'geojson',
  data:{type:'FeatureCollection',features:water.map(p=>({
    type:'Feature' as const,
    geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
    properties:{name:p.name,osmUrl:p.osmUrl,potable:p.potable},
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
 map.addLayer({id:'cb-water-point',type:'circle',source:'cb-water',
   minzoom:12,filter:['!',['has','point_count']],
   paint:{'circle-color':['match',['get','potable'],'yes','#0089c5','no','#a8b7bc','#649db5'],
     'circle-radius':['interpolate',['linear'],['zoom'],12,4,15,7],
     'circle-stroke-color':'#fff','circle-stroke-width':2},
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
   const url=event.features?.[0]?.properties?.osmUrl;
   if(typeof url!=='string'||!url.startsWith('https://www.openstreetmap.org/'))return;
   event.originalEvent.stopPropagation();
   window.open(url,'_blank','noopener');
 });
 for(const layer of ['cb-water-point','cb-water-clusters']){
   map.on('mouseenter',layer,()=>{map.getCanvas().style.cursor='pointer';});
   map.on('mouseleave',layer,()=>{map.getCanvas().style.cursor='';});
 }
}
