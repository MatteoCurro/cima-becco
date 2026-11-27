import { useEffect, useRef, useState } from 'react';
import { Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource } from 'maplibre-gl';
import type { Route } from '../types';
import { MAP_STYLE_URL } from '../map/constants';
import { installMountainBasemap, MountainBasemapControl } from '../map/mountainBasemap';
import { addAlpinePlaceLayers, alpinePlacesGeoJSON } from '../map/alpineOverlays';
import type { AlpinePlace } from '../lib/alpinePlaces';

interface Props {
  places: AlpinePlace[];
  kind: AlpinePlace['kind'];
  selected?: AlpinePlace | null;
  routes?: Route[];
  height?: number;
  water?: {lng:number;lat:number;potable:boolean}[];
}
const EMPTY_LINE = {type:'FeatureCollection' as const,features:[]};

function routeGeometry(routes: Route[]) {
  return {
    type:'FeatureCollection' as const,
    features:routes.filter(r=>r.coordinates.length>1).slice(0,22).map(r=>({
      type:'Feature' as const,properties:{slug:r.slug,name:r.name},
      geometry:{type:'LineString' as const,coordinates:r.coordinates.map(p=>[p[0],p[1]])},
    })),
  };
}

/** Mappa riusabile per listati rifugi, paesi e singole pagine locali. */
export function AlpineAtlasMap({places,kind,selected=null,routes=[],height=380,water=[]}:Props) {
  const container=useRef<HTMLDivElement>(null);
  const mapRef=useRef<MapLibreMap | null>(null);
  const markerRef=useRef<Marker | null>(null);
  const initialized=useRef(false);
  const [ready,setReady]=useState(false);

  useEffect(()=>{
    if(!container.current||mapRef.current)return;
    const map=new MapLibreMap({
      container:container.current,style:MAP_STYLE_URL,
      center:selected?[selected.lng,selected.lat]:[12.05,46.62],
      zoom:selected?13:8.6,minZoom:4,attributionControl:{compact:false},
    });
    mapRef.current=map;
    map.addControl(new MountainBasemapControl(),'top-right');
    map.addControl(new NavigationControl({showCompass:true}),'top-right');
    map.on('load',()=>{
      if(mapRef.current!==map)return;
      installMountainBasemap(map);
      addAlpinePlaceLayers(map,places,{kind});
      map.addSource('cb-atlas-nearby-routes',{type:'geojson',data:EMPTY_LINE});
      map.addLayer({id:'cb-atlas-nearby-route-outline',type:'line',source:'cb-atlas-nearby-routes',
        paint:{'line-color':'#fff','line-width':6,'line-opacity':.92}});
      map.addLayer({id:'cb-atlas-nearby-route-line',type:'line',source:'cb-atlas-nearby-routes',
        paint:{'line-color':'#f71970','line-width':3.2,'line-opacity':.9}});
      map.addSource('cb-atlas-water',{type:'geojson',data:EMPTY_LINE});
      map.addLayer({id:'cb-atlas-water-points',type:'circle',source:'cb-atlas-water',minzoom:11,
        paint:{'circle-radius':5.5,'circle-color':['case',['==',['get','potable'],true],'#168dd5','#7db6bc'],
          'circle-stroke-color':'#fff','circle-stroke-width':2}});
      initialized.current=true;
      setReady(true);
      sync();
    });
    function sync(){
      if(!initialized.current||mapRef.current!==map)return;
      (map.getSource('cb-atlas-nearby-routes') as GeoJSONSource).setData(routeGeometry(routes));
      (map.getSource('cb-atlas-water') as GeoJSONSource).setData({
        type:'FeatureCollection',features:water.map(p=>({
          type:'Feature' as const,properties:{potable:p.potable},
          geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
        })),
      });
    }
    return ()=>{initialized.current=false;markerRef.current?.remove();markerRef.current=null;map.remove();mapRef.current=null;};
    // Map init is deliberate: props are updated by separate effects, never re-create the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    const source=map.getSource('cb-atlas-places') as GeoJSONSource | undefined;
    source?.setData(alpinePlacesGeoJSON(places.filter(p=>p.kind===kind)));
  },[places,kind,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    (map.getSource('cb-atlas-nearby-routes') as GeoJSONSource | undefined)?.setData(routeGeometry(routes));
  },[routes,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    (map.getSource('cb-atlas-water') as GeoJSONSource | undefined)?.setData({
      type:'FeatureCollection',features:water.map(p=>({
        type:'Feature' as const,properties:{potable:p.potable},
        geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
      })),
    });
  },[water,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    markerRef.current?.remove();
    markerRef.current=null;
    if(selected){
      const pin=document.createElement('span');
      pin.className='cb-atlas-selected-pin';
      pin.setAttribute('aria-label',selected.name);
      pin.textContent=kind==='rifugio'?'⌂':'◆';
      markerRef.current=new Marker({element:pin,anchor:'bottom'})
        .setLngLat([selected.lng,selected.lat]).addTo(map);
      map.easeTo({center:[selected.lng,selected.lat],zoom:13,duration:400});
    }else{
      const list=places.filter(p=>p.kind===kind);
      if(!list.length)return;
      const west=Math.min(...list.map(p=>p.lng)),east=Math.max(...list.map(p=>p.lng));
      const south=Math.min(...list.map(p=>p.lat)),north=Math.max(...list.map(p=>p.lat));
      map.fitBounds([[west,south],[east,north]],{padding:45,maxZoom:11,duration:300});
    }
  },[selected,kind,places,ready]);

  return <div className="cb-atlas-map-wrap">
    <div ref={container} className="cb-atlas-map" style={{height}} role="application"
      aria-label={selected? `Mappa topografica di ${selected.name} con sentieri vicini` : `Mappa topografica dedicata a ${kind==='rifugio'?'rifugi':'paesi di montagna'}`}/>
    <span className="cb-atlas-map-caption">TOPO / SAT · {selected?.name ?? (kind==='rifugio'?'RIFUGI':'PAESI')} · + / − PER ZOOMARE</span>
  </div>;
}
