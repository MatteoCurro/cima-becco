import type { Map as MlMap } from 'maplibre-gl';
import type { FeatureCollection, Point } from 'geojson';
import type { AlpinePlace } from '../lib/alpinePlaces';

/** Le schede hanno id OSM reali; i marker non introducono luoghi sintetici. */
export function alpinePlacesGeoJSON(places: AlpinePlace[]): FeatureCollection<Point> {
  return {
    type: 'FeatureCollection',
    features: places.map((p) => ({
      type: 'Feature' as const,
      id: p.slug,
      geometry: { type: 'Point' as const, coordinates: [p.lng,p.lat] },
      properties: { slug: p.slug, name: p.name, kind: p.kind },
    })),
  };
}

export function addAlpinePlaceLayers(map: MlMap, places: AlpinePlace[]): void {
  if (map.getSource('cb-atlas-places')) return;
  map.addSource('cb-atlas-places', { type: 'geojson', data: alpinePlacesGeoJSON(places) });
  map.addLayer({
    id: 'cb-atlas-poi-dot',
    type: 'circle',
    source: 'cb-atlas-places',
    minzoom: 10,
    paint: {
      'circle-color': ['match',['get','kind'],'rifugio','#ff2677','#e6b450'],
      'circle-radius': ['interpolate',['linear'],['zoom'],10,3.5,13,6.5,15,8],
      'circle-stroke-color':'#f7fff4',
      'circle-stroke-width':2,
      'circle-opacity':0.98,
    },
  });
  map.addLayer({
    id: 'cb-atlas-poi-label',
    type: 'symbol',
    source: 'cb-atlas-places',
    minzoom: 12,
    layout: {
      'text-field':['get','name'],
      'text-size':['interpolate',['linear'],['zoom'],12,10,15,12],
      'text-font':['Noto Sans Bold'],
      'text-variable-anchor':['top','bottom','left','right'],
      'text-radial-offset':0.7,
      'text-optional':true,
    },
    paint: {
      'text-color':'#172f27',
      'text-halo-color':'#fffdf4',
      'text-halo-width':1.7,
    },
  });
  const open = (event: { features?: { properties?: { slug?: string; kind?: string } }[]; originalEvent?: Event }) => {
    const feature = event.features?.[0];
    const kind = feature?.properties?.kind;
    const slug = feature?.properties?.slug;
    if (slug && (kind === 'rifugio' || kind === 'borgo')) {
      event.originalEvent?.stopPropagation();
      window.location.hash = `#atlante/${kind === 'rifugio' ? 'rifugi' : 'borghi'}/${slug}`;
    }
  };
  map.on('click','cb-atlas-poi-dot',open);
  for (const layer of ['cb-atlas-poi-dot','cb-atlas-poi-label']) {
    map.on('mouseenter',layer,()=>{map.getCanvas().style.cursor='pointer';});
    map.on('mouseleave',layer,()=>{map.getCanvas().style.cursor='';});
  }
}
