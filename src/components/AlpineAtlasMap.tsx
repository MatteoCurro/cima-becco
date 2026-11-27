import { useEffect, useMemo, useRef, useState } from 'react';
import { Map as MapLibreMap, Marker, NavigationControl, Popup, type GeoJSONSource } from 'maplibre-gl';
import type { Route } from '../types';
import { MAP_STYLE_URL } from '../map/constants';
import { installMountainBasemap, MountainBasemapControl } from '../map/mountainBasemap';
import { addAlpinePlaceLayers, alpinePlacesGeoJSON } from '../map/alpineOverlays';
import type { AlpinePlace } from '../lib/alpinePlaces';
import type { AlpineWaterPoint } from '../lib/alpineWater';

interface Props {
  places: AlpinePlace[];
  kind: AlpinePlace['kind'];
  selected?: AlpinePlace | null;
  routes?: Route[];
  height?: number | string;
  onSelect?: (place: AlpinePlace) => void;
  water?: Pick<AlpineWaterPoint,'lat'|'lng'|'name'|'kind'|'potable'>[];
  caption?: string;
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
const NO_ROUTES: Route[] = [];
export function AlpineAtlasMap({places,kind,selected=null,routes=NO_ROUTES,height=380,water=[],onSelect,caption}:Props) {
  const container=useRef<HTMLDivElement>(null);
  const mapRef=useRef<MapLibreMap | null>(null);
  const onSelectRef=useRef(onSelect);
  onSelectRef.current=onSelect;
  const placesRef=useRef(places);
  placesRef.current=places;
  const markerRef=useRef<Marker | null>(null);
  const initialized=useRef(false);
  const [ready,setReady]=useState(false);
  const [showTrails,setShowTrails]=useState(Boolean(selected || routes.length));
  const routeExtent=useMemo(() => {
    let west=Infinity,east=-Infinity,south=Infinity,north=-Infinity;
    for(const route of routes) for(const [lng,lat] of route.coordinates){
      west=Math.min(west,lng);east=Math.max(east,lng);south=Math.min(south,lat);north=Math.max(north,lat);
    }
    return Number.isFinite(west) ? [[west,south],[east,north]] as [[number,number],[number,number]] : null;
  },[routes]);
  useEffect(()=>{if(routes.length && !places.length) setShowTrails(true);},[routes.length,places.length]);
  const [showWater,setShowWater]=useState(true);

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
      addAlpinePlaceLayers(map,places,{kind,onSelect:(place)=>onSelectRef.current?.(place),getPlace:(slug)=>placesRef.current.find(p=>p.slug===slug)});
      map.addSource('cb-atlas-nearby-routes',{type:'geojson',data:EMPTY_LINE});
      map.addLayer({id:'cb-atlas-nearby-route-outline',type:'line',source:'cb-atlas-nearby-routes',
        paint:{'line-color':'#fff','line-width':6,'line-opacity':.92}});
      map.addLayer({id:'cb-atlas-nearby-route-line',type:'line',source:'cb-atlas-nearby-routes',
        paint:{'line-color':'#f71970','line-width':3.2,'line-opacity':.9}});
      map.addSource('cb-atlas-water',{type:'geojson',data:EMPTY_LINE});
      map.addLayer({id:'cb-atlas-water-points',type:'circle',source:'cb-atlas-water',minzoom:8,
        paint:{'circle-radius':5.5,'circle-color':['case',['==',['get','potable'],'yes'],'#168dd5','#7db6bc'],
          'circle-stroke-color':'#fff','circle-stroke-width':2}});
      map.on('click','cb-atlas-water-points',(event)=>{
        const point=event.features?.[0];
        if(!point||point.geometry.type!=='Point')return;
        const coordinates=point.geometry.coordinates as [number,number];
        const node=document.createElement('div');
        node.className='cb-water-map-popover';
        const heading=document.createElement('strong');
        heading.textContent=String(point.properties?.name||'Punto acqua mappato');
        const detail=document.createElement('small');
        const potable=String(point.properties?.potable||'unknown');
        detail.textContent=potable==='yes'?'Potabilità indicata in OSM · verificare sul posto':
          potable==='no'?'Segnalata NON potabile':'Potabilità non verificata';
        node.append(heading,detail);
        new Popup({closeButton:true,maxWidth:'260px'}).setLngLat(coordinates).setDOMContent(node).addTo(map);
      });
      map.on('mouseenter','cb-atlas-water-points',()=>{map.getCanvas().style.cursor='pointer';});
      map.on('mouseleave','cb-atlas-water-points',()=>{map.getCanvas().style.cursor='';});
      initialized.current=true;
      setReady(true);
      sync();
    });
    function sync(){
      if(!initialized.current||mapRef.current!==map)return;
      (map.getSource('cb-atlas-nearby-routes') as GeoJSONSource).setData(routeGeometry(routes));
      (map.getSource('cb-atlas-water') as GeoJSONSource).setData({
        type:'FeatureCollection',features:water.map(p=>({
          type:'Feature' as const,properties:{potable:p.potable,name:p.name,kind:p.kind},
          geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
        })),
      });
    }
    const observer=new ResizeObserver(()=>map.resize());
    if(container.current)observer.observe(container.current);
    return ()=>{observer.disconnect();initialized.current=false;markerRef.current?.remove();markerRef.current=null;map.remove();mapRef.current=null;};
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
        type:'Feature' as const,properties:{potable:p.potable,name:p.name,kind:p.kind},
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
      pin.textContent=kind==='rifugio'?'⌂':kind==='bivacco'?'△':'◆';
      markerRef.current=new Marker({element:pin,anchor:'bottom'})
        .setLngLat([selected.lng,selected.lat]).addTo(map);
      map.easeTo({center:[selected.lng,selected.lat],zoom:13,duration:400});
    }else{
      const list=places.filter(p=>p.kind===kind);
      if(!list.length){if(routeExtent) map.fitBounds(routeExtent,{padding:45,maxZoom:11,duration:300});return;}
      const west=Math.min(...list.map(p=>p.lng)),east=Math.max(...list.map(p=>p.lng));
      const south=Math.min(...list.map(p=>p.lat)),north=Math.max(...list.map(p=>p.lat));
      map.fitBounds([[west,south],[east,north]],{padding:45,maxZoom:11,duration:300});
    }
  },[selected,kind,places,routeExtent,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!ready)return;
    for(const id of ['cb-atlas-nearby-route-outline','cb-atlas-nearby-route-line']){
      if(map.getLayer(id))map.setLayoutProperty(id,'visibility',showTrails?'visible':'none');
    }
  },[ready,showTrails]);
  useEffect(()=>{
    const map=mapRef.current;if(!map||!ready)return;
    if(map.getLayer('cb-atlas-water-points'))map.setLayoutProperty('cb-atlas-water-points','visibility',showWater?'visible':'none');
  },[ready,showWater]);

  return <div className="cb-atlas-map-wrap">
    <div className="cb-map-layer-switches" role="group" aria-label="Livelli sulla mappa">
      {(selected || routes.length>0)&&<button type="button" aria-pressed={showTrails} onClick={()=>setShowTrails(value=>!value)}>Sentieri {showTrails?'✓':'+'}</button>}
      {water.length>0&&<button type="button" aria-pressed={showWater} onClick={()=>setShowWater(value=>!value)}>Punti acqua {showWater?'✓':'+'}</button>}
    </div>
    <div ref={container} className="cb-atlas-map" style={{height}} role="application"
      aria-label={caption ? `Mappa topografica: ${caption}` : selected? `Mappa topografica di ${selected.name} con sentieri vicini` : `Mappa topografica dedicata a ${kind==='rifugio'?'rifugi':kind==='bivacco'?'bivacchi':'paesi di montagna'}`}/>
    <span className="cb-atlas-map-caption">TOPO / SAT · {caption ?? selected?.name ?? (kind==='rifugio'?'RIFUGI':kind==='bivacco'?'BIVACCHI':'PAESI')} · + / − PER ZOOMARE</span>
  </div>;
}
