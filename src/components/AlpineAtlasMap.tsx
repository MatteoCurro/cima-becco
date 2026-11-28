import { useEffect, useMemo, useRef, useState } from 'react';
import '../alpineMap.css';
import { Map as MapLibreMap, Marker, NavigationControl, Popup, type GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import '../map/worker';
import type { Route } from '../types';
import { MAP_STYLE_URL } from '../map/constants';
import { installMountainBasemap, MountainBasemapControl } from '../map/mountainBasemap';
import { addRouteHoverLayer, setRouteHover } from '../map/layers';
import { nearestRoutePointIndex } from '../lib/routeHover';
import { addAlpinePlaceLayers, alpinePlacesGeoJSON } from '../map/alpineOverlays';
import type { AlpinePlace } from '../lib/alpinePlaces';
import type { AlpineWaterPoint } from '../lib/alpineWater';
import { potabilityLabel } from '../lib/alpineWater';
import { waterDisplayName, waterKindLabel } from '../lib/waterPresentation';
import { registerWaterMapIcons } from '../map/waterIcons';
import { WaterPointIcon } from './WaterPointIcon';

export interface NaturalMapPoint {
  slug:string;
  name:string;
  lat:number;
  lng:number;
  subtype:string;
}
function naturalPointsGeoJSON(points:readonly NaturalMapPoint[]) {
  return {
    type:'FeatureCollection' as const,
    features:points.map(p=>({
      type:'Feature' as const,
      properties:{slug:p.slug,name:p.name,subtype:p.subtype},
      geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
    })),
  };
}


/** Verified lake geometry; never confuse water bodies with drinking-water POIs. */
export interface NaturalWaterPolygon {
  slug:string;
  name:string;
  subtype:'lake'|'reservoir';
  lat:number;
  lng:number;
  geometry:{type:'MultiPolygon';coordinates:number[][][][]};
}
const NO_NATURAL_POLYGONS:NaturalWaterPolygon[]=[];
function naturalWaterGeoJSON(features:readonly NaturalWaterPolygon[]){
  return {
    type:'FeatureCollection' as const,
    features:features.map(p=>({
      type:'Feature' as const,
      properties:{slug:p.slug,name:p.name,subtype:p.subtype},
      geometry:p.geometry,
    })),
  };
}

interface Props {
  places: AlpinePlace[];
  naturalPolygons?:NaturalWaterPolygon[];
  onNaturalPolygonSelect?:(place:NaturalWaterPolygon)=>void;
  naturalPoints?:NaturalMapPoint[];
  onNaturalSelect?:(place:NaturalMapPoint)=>void;
  kind: AlpinePlace['kind'];
  selected?: AlpinePlace | null;
  /** Punto geografico generico: per cime, falesie e future risorse senza anagrafica AlpinePlace. */
  selectedPoint?: {lat:number;lng:number;name:string;icon?:string} | null;
  routes?: Route[];
  height?: number | string;
  onSelect?: (place: AlpinePlace) => void;
  water?: AlpineWaterPoint[];
  selectedWaterSlug?:string|null;
  onWaterSelect?:(slug:string)=>void;
  caption?: string;
  hoverPoint?: [number,number] | null;
  onRouteHover?: (index:number|null)=>void;
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
export function AlpineAtlasMap({places,kind,naturalPoints=[],onNaturalSelect,naturalPolygons=NO_NATURAL_POLYGONS,onNaturalPolygonSelect,selected=null,selectedPoint=null,routes=NO_ROUTES,height=380,water=[],selectedWaterSlug=null,onWaterSelect,onSelect,caption,hoverPoint=null,onRouteHover}:Props) {
  const container=useRef<HTMLDivElement>(null);
  const mapRef=useRef<MapLibreMap | null>(null);
  const onSelectRef=useRef(onSelect);
  onSelectRef.current=onSelect;
  const placesRef=useRef(places);
  placesRef.current=places;
  const naturalRef=useRef(naturalPoints);naturalRef.current=naturalPoints;
  const naturalSelectRef=useRef(onNaturalSelect);naturalSelectRef.current=onNaturalSelect;
  const waterPolygonsRef=useRef(naturalPolygons);waterPolygonsRef.current=naturalPolygons;
  const polygonSelectRef=useRef(onNaturalPolygonSelect);polygonSelectRef.current=onNaturalPolygonSelect;
  const routesRef=useRef(routes);
  routesRef.current=routes;
  const onRouteHoverRef=useRef(onRouteHover);
  onRouteHoverRef.current=onRouteHover;
  const markerRef=useRef<Marker | null>(null);
  const popupRef=useRef<Popup | null>(null);
  const waterRef=useRef(water);waterRef.current=water;
  const onWaterSelectRef=useRef(onWaterSelect);onWaterSelectRef.current=onWaterSelect;
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
    let hoverFrame=0;
    const map=new MapLibreMap({
      container:container.current,style:MAP_STYLE_URL,
      center:selected?[selected.lng,selected.lat]:selectedPoint?[selectedPoint.lng,selectedPoint.lat]:[12.05,46.62],
      zoom:selected||selectedPoint?13:8.6,minZoom:4,attributionControl:{compact:false},
    });
    mapRef.current=map;
    map.addControl(new MountainBasemapControl(),'top-right');
    map.addControl(new NavigationControl({showCompass:false}),'bottom-right');
    map.on('load',()=>{
      if(mapRef.current!==map)return;
      installMountainBasemap(map);
      addAlpinePlaceLayers(map,places,{kind,onSelect:(place)=>onSelectRef.current?.(place),getPlace:(slug)=>placesRef.current.find(p=>p.slug===slug)});
      // One additional source on the same map instance. Only published G2
      // lake polygons are supplied; water points retain their own layer.
      map.addSource('cb-atlas-natural-lakes',{type:'geojson',
        data:naturalWaterGeoJSON(waterPolygonsRef.current)});
      map.addLayer({id:'cb-atlas-natural-lakes-fill',type:'fill',
        source:'cb-atlas-natural-lakes',
        paint:{'fill-color':['match',['get','subtype'],'reservoir','#679bb1','#57abb7'],
          'fill-opacity':0.5}});
      map.addLayer({id:'cb-atlas-natural-lakes-outline',type:'line',
        source:'cb-atlas-natural-lakes',
        paint:{'line-color':'#154c5a','line-width':2.5,'line-opacity':0.9}});
      map.on('click','cb-atlas-natural-lakes-fill',(event)=>{
        const slug=event.features?.[0]?.properties?.slug;
        if(typeof slug!=='string')return;
        const lake=waterPolygonsRef.current.find(item=>item.slug===slug);
        if(!lake)return;
        if(polygonSelectRef.current)polygonSelectRef.current(lake);
        else window.location.assign(import.meta.env.BASE_URL+'laghi/'+encodeURIComponent(slug)+'/');
      });
      map.on('mouseenter','cb-atlas-natural-lakes-fill',()=>{map.getCanvas().style.cursor='pointer';});
      map.on('mouseleave','cb-atlas-natural-lakes-fill',()=>{map.getCanvas().style.cursor='';});
      // A generic POI overlay in the SAME map engine, not a parallel map.
      // Nature points remain distinct from source-only water and refuges.
      map.addSource('cb-atlas-natural',{type:'geojson',
        data:naturalPointsGeoJSON(naturalRef.current),
        cluster:true,clusterRadius:40,clusterMaxZoom:11});
      map.addLayer({id:'cb-atlas-natural-clusters',type:'circle',source:'cb-atlas-natural',
        filter:['has','point_count'],paint:{'circle-radius':20,
          'circle-color':'#173f30','circle-stroke-color':'#e4ffbe','circle-stroke-width':3}});
      map.addLayer({id:'cb-atlas-natural-count',type:'symbol',source:'cb-atlas-natural',
        filter:['has','point_count'],
        layout:{'text-field':['get','point_count_abbreviated'],'text-size':12,
          'text-font':['Noto Sans Bold']},
        paint:{'text-color':'#ffffff'}});
      map.addLayer({id:'cb-atlas-natural-pins',type:'circle',source:'cb-atlas-natural',
        filter:['!',['has','point_count']],
        paint:{'circle-radius':['interpolate',['linear'],['zoom'],7,7,13,11],
          'circle-color':'#e4ffbe','circle-stroke-color':'#173f30','circle-stroke-width':2.5}});
      map.addLayer({id:'cb-atlas-natural-label',type:'symbol',source:'cb-atlas-natural',
        filter:['!',['has','point_count']],minzoom:11,
        layout:{'text-field':['get','name'],'text-font':['Noto Sans Bold'],
          'text-size':11,'text-variable-anchor':['top','bottom'],
          'text-radial-offset':1.2,'text-optional':true},
        paint:{'text-color':'#173f30','text-halo-color':'#fff','text-halo-width':2}});
      map.on('click','cb-atlas-natural-clusters',(event)=>{
        const id=event.features?.[0]?.properties?.cluster_id;
        if(typeof id!=='number')return;
        void (map.getSource('cb-atlas-natural') as GeoJSONSource)
          .getClusterExpansionZoom(id)
          .then(zoom=>map.easeTo({center:event.lngLat,zoom,duration:420}));
      });
      map.on('click','cb-atlas-natural-pins',(event)=>{
        const slug=event.features?.[0]?.properties?.slug;
        if(typeof slug!=='string')return;
        const item=naturalRef.current.find(p=>p.slug===slug);
        if(!item)return;
        if(naturalSelectRef.current)naturalSelectRef.current(item);
        else window.location.assign(import.meta.env.BASE_URL+'passi/'+encodeURIComponent(slug)+'/');
      });
      for(const layer of ['cb-atlas-natural-pins','cb-atlas-natural-label']){
        map.on('mouseenter',layer,()=>{map.getCanvas().style.cursor='pointer';});
        map.on('mouseleave',layer,()=>{map.getCanvas().style.cursor='';});
      }
      map.addSource('cb-atlas-nearby-routes',{type:'geojson',data:EMPTY_LINE});
      map.addLayer({id:'cb-atlas-nearby-route-outline',type:'line',source:'cb-atlas-nearby-routes',
        paint:{'line-color':'#fff','line-width':6,'line-opacity':.92}});
      map.addLayer({id:'cb-atlas-nearby-route-line',type:'line',source:'cb-atlas-nearby-routes',
        paint:{'line-color':'#f71970','line-width':3.2,'line-opacity':.9}});
      registerWaterMapIcons(map);
      map.addSource('cb-atlas-water',{type:'geojson',data:EMPTY_LINE});
      map.addLayer({id:'cb-atlas-water-focus',type:'circle',source:'cb-atlas-water',minzoom:8,
        filter:['==',['get','slug'],''],
        paint:{'circle-radius':21,'circle-color':'#fff','circle-opacity':0.45,
          'circle-stroke-color':'#b00053','circle-stroke-width':3}});
      map.addLayer({id:'cb-atlas-water-points',type:'symbol',source:'cb-atlas-water',minzoom:8,
        layout:{'icon-image':['concat','cb-water-',['get','kind']],
          'icon-size':1,'icon-allow-overlap':true,'text-field':['to-string',['get','index']],
          'text-font':['Noto Sans Bold'],'text-size':11,'text-offset':[0,1.55],
          'text-allow-overlap':true,'text-optional':true},
        paint:{'text-color':'#173f35','text-halo-color':'#fff','text-halo-width':2}});
      addRouteHoverLayer(map);
      map.on('mousemove',event=>{
        if(!onRouteHoverRef.current)return;
        cancelAnimationFrame(hoverFrame);
        hoverFrame=requestAnimationFrame(()=>{
          const route=routesRef.current.length===1?routesRef.current[0]:null;
          if(!route?.coordinates.length){onRouteHoverRef.current?.(null);return;}
          const hit=map.queryRenderedFeatures(
            [[event.point.x-7,event.point.y-7],[event.point.x+7,event.point.y+7]],
            {layers:['cb-atlas-nearby-route-line']},
          );
          onRouteHoverRef.current?.(hit.length
            ? nearestRoutePointIndex(route.coordinates,event.lngLat.lng,event.lngLat.lat)
            : null);
        });
      });
      map.on('mouseout',()=>onRouteHoverRef.current?.(null));
      map.on('click','cb-atlas-water-points',(event)=>{
        const point=event.features?.[0];
        if(!point||point.geometry.type!=='Point')return;
        const coordinates=point.geometry.coordinates as [number,number];
        const slug=String(point.properties?.slug||'');
        const item=waterRef.current.find(p=>p.slug===slug);
        if(!item)return;
        onWaterSelectRef.current?.(slug);
        openWaterPopup(map,item,Number(point.properties?.index)||undefined,coordinates);
      });
      map.on('mouseenter','cb-atlas-water-points',()=>{map.getCanvas().style.cursor='pointer';});
      map.on('mouseleave','cb-atlas-water-points',()=>{map.getCanvas().style.cursor='';});
      initialized.current=true;
      setReady(true);
      sync();
    });
    function openWaterPopup(target:MapLibreMap,point:AlpineWaterPoint,index?:number,coords?:[number,number]){
      popupRef.current?.remove();
      const node=document.createElement('div');
      node.className='cb-water-map-popover';
      const heading=document.createElement('strong');
      heading.textContent=waterDisplayName(point,index);
      const type=document.createElement('span');
      type.textContent=waterKindLabel(point.kind);
      const status=document.createElement('small');
      status.textContent=potabilityLabel(point.potable)+(point.seasonal?' · stagionale':'');
      node.append(heading,type,status);
      if(point.osmUrl?.startsWith('https://www.openstreetmap.org/')){
        const link=document.createElement('a');
        link.href=point.osmUrl;link.target='_blank';link.rel='noopener noreferrer';
        link.textContent='Verifica la scheda OpenStreetMap ↗';
        node.append(link);
      }
      popupRef.current=new Popup({closeButton:true,maxWidth:'280px'})
        .setLngLat(coords||[point.lng,point.lat]).setDOMContent(node).addTo(target);
    }
    function sync(){
      if(!initialized.current||mapRef.current!==map)return;
      (map.getSource('cb-atlas-natural-lakes') as GeoJSONSource).setData(naturalWaterGeoJSON(waterPolygonsRef.current));
      (map.getSource('cb-atlas-natural') as GeoJSONSource).setData(naturalPointsGeoJSON(naturalRef.current));
      (map.getSource('cb-atlas-nearby-routes') as GeoJSONSource).setData(routeGeometry(routes));
      (map.getSource('cb-atlas-water') as GeoJSONSource).setData({
        type:'FeatureCollection',features:water.map((p,index)=>({
          type:'Feature' as const,properties:{potable:p.potable,name:p.name,kind:p.kind,slug:p.slug,index:index+1,osmUrl:p.osmUrl},
          geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
        })),
      });
    }
    const observer=new ResizeObserver(()=>map.resize());
    if(container.current)observer.observe(container.current);
    return ()=>{cancelAnimationFrame(hoverFrame);observer.disconnect();initialized.current=false;markerRef.current?.remove();markerRef.current=null;popupRef.current?.remove();popupRef.current=null;map.remove();mapRef.current=null;};
    // Map init is deliberate: props are updated by separate effects, never re-create the map.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  },[]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!ready)return;
    setRouteHover(map,hoverPoint);
  },[hoverPoint,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    (map.getSource('cb-atlas-natural') as GeoJSONSource | undefined)
      ?.setData(naturalPointsGeoJSON(naturalPoints));
  },[naturalPoints,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    (map.getSource('cb-atlas-natural-lakes') as GeoJSONSource | undefined)
      ?.setData(naturalWaterGeoJSON(naturalPolygons));
  },[naturalPolygons,ready]);

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
      type:'FeatureCollection',features:water.map((p,index)=>({
        type:'Feature' as const,properties:{potable:p.potable,name:p.name,kind:p.kind,slug:p.slug,index:index+1,osmUrl:p.osmUrl},
        geometry:{type:'Point' as const,coordinates:[p.lng,p.lat]},
      })),
    });
  },[water,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!initialized.current)return;
    markerRef.current?.remove();
    markerRef.current=null;
    const target=selected??selectedPoint;
    if(target){
      const pin=document.createElement('span');
      pin.className='cb-atlas-selected-pin';
      pin.setAttribute('aria-label',target.name);
      pin.textContent=selectedPoint?(selectedPoint.icon||'◇'):kind==='rifugio'?'⌂':kind==='bivacco'?'△':'◆';
      markerRef.current=new Marker({element:pin,anchor:'bottom'})
        .setLngLat([target.lng,target.lat]).addTo(map);
      map.easeTo({center:[target.lng,target.lat],zoom:13,duration:400});
    }else{
      const list=places.filter(p=>p.kind===kind);
      if(!list.length && naturalPoints.length){
        const west=Math.min(...naturalPoints.map(p=>p.lng)),east=Math.max(...naturalPoints.map(p=>p.lng));
        const south=Math.min(...naturalPoints.map(p=>p.lat)),north=Math.max(...naturalPoints.map(p=>p.lat));
        map.fitBounds([[west,south],[east,north]],{padding:45,maxZoom:11,duration:300});
        return;
      }
      if(!list.length && naturalPolygons.length){
        // The actual shoreline, not a provider's centroid, controls framing.
        const coords=naturalPolygons.flatMap(lake=>lake.geometry.coordinates.flatMap(
          group=>group.flatMap(ring=>ring)));
        if(coords.length){
          map.fitBounds([
            [Math.min(...coords.map(p=>p[0])),Math.min(...coords.map(p=>p[1]))],
            [Math.max(...coords.map(p=>p[0])),Math.max(...coords.map(p=>p[1]))],
          ],{padding:45,maxZoom:11,duration:300});
          return;
        }
      }
      if(!list.length){if(routeExtent) map.fitBounds(routeExtent,{padding:45,maxZoom:11,duration:300});return;}
      const west=Math.min(...list.map(p=>p.lng)),east=Math.max(...list.map(p=>p.lng));
      const south=Math.min(...list.map(p=>p.lat)),north=Math.max(...list.map(p=>p.lat));
      map.fitBounds([[west,south],[east,north]],{padding:45,maxZoom:11,duration:300});
    }
  },[selected,selectedPoint,kind,places,naturalPoints,naturalPolygons,routeExtent,ready]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!ready)return;
    map.setFilter('cb-atlas-water-focus',['==',['get','slug'],selectedWaterSlug||'']);
    const item=water.find(p=>p.slug===selectedWaterSlug);
    if(!item)return;
    const index=water.findIndex(p=>p.slug===selectedWaterSlug)+1;
    map.easeTo({center:[item.lng,item.lat],zoom:Math.max(map.getZoom(),14),duration:400});
    popupRef.current?.remove();
    const node=document.createElement('div');
    node.className='cb-water-map-popover';
    const heading=document.createElement('strong');
    heading.textContent=waterDisplayName(item,index);
    const detail=document.createElement('small');
    detail.textContent=waterKindLabel(item.kind)+' · '+potabilityLabel(item.potable)+(item.seasonal?' · stagionale':'');
    node.append(heading,detail);
    popupRef.current=new Popup({closeButton:true,maxWidth:'280px'})
      .setLngLat([item.lng,item.lat]).setDOMContent(node).addTo(map);
  },[selectedWaterSlug,ready,water]);

  useEffect(()=>{
    const map=mapRef.current;if(!map||!ready)return;
    for(const id of ['cb-atlas-nearby-route-outline','cb-atlas-nearby-route-line']){
      if(map.getLayer(id))map.setLayoutProperty(id,'visibility',showTrails?'visible':'none');
    }
  },[ready,showTrails]);
  useEffect(()=>{
    const map=mapRef.current;if(!map||!ready)return;
    for(const id of ['cb-atlas-water-points','cb-atlas-water-focus'])
      if(map.getLayer(id))map.setLayoutProperty(id,'visibility',showWater?'visible':'none');
  },[ready,showWater]);

  return <div className="cb-atlas-map-wrap" data-route-cursor={hoverPoint?hoverPoint.join(","):"none"} data-cursor-ready={ready&&onRouteHover?"true":"false"}>
    <div className="cb-map-layer-switches" role="group" aria-label="Livelli sulla mappa">
      {(selected || routes.length>0)&&<button type="button" aria-pressed={showTrails} onClick={()=>setShowTrails(value=>!value)}>Sentieri {showTrails?'✓':'+'}</button>}
      {water.length>0&&<button type="button" aria-pressed={showWater} onClick={()=>setShowWater(value=>!value)}>Punti acqua {showWater?'✓':'+'}</button>}
    </div>
    {water.length>0&&showWater&&<div className="cb-water-map-legend" aria-label="Legenda tipologie di acqua">
      {(['fontanella','sorgente','rubinetto'] as const).map(waterKind=><span key={waterKind}>
        <WaterPointIcon kind={waterKind} size={16}/>{waterKindLabel(waterKind)}
      </span>)}
    </div>}
    <div ref={container} className="cb-atlas-map" style={{height}} role="application"
      aria-label={caption ? `Mappa topografica: ${caption}` : selected||selectedPoint ? `Mappa topografica di ${(selected??selectedPoint)!.name} con sentieri vicini` : naturalPoints.length ? 'Mappa topografica dei passi con punti documentati' : naturalPolygons.length ? 'Mappa topografica dei laghi con perimetri verificati' : `Mappa topografica dedicata a ${kind==='rifugio'?'rifugi':kind==='bivacco'?'bivacchi':'paesi di montagna'}`}/>
  </div>;
}
