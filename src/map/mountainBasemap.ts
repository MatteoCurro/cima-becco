import type { Map as MlMap, IControl } from 'maplibre-gl';

/**
 * La base stradale OpenFreeMap resta sotto le raster: quando il provider
 * esterno è irraggiungibile la mappa e i sentieri non spariscono.
 * Non facciamo prefetch e rispettiamo le attribution dei fornitori.
 */
export type MountainBasemap = 'topo' | 'satellite';
const STORAGE_KEY = 'cimabecco:basemap';
const TOPO_SOURCE = 'cb-topo-tiles';
const SAT_SOURCE = 'cb-satellite-tiles';
const TOPO_LAYER = 'cb-topographic-base';
const SAT_LAYER = 'cb-satellite-base';

export function preferredBasemap(): MountainBasemap {
  try {
    return localStorage.getItem(STORAGE_KEY) === 'satellite' ? 'satellite' : 'topo';
  } catch {
    return 'topo';
  }
}

export function installMountainBasemap(map: MlMap, preferred: MountainBasemap = preferredBasemap()): void {
  if (!map.getSource(TOPO_SOURCE)) {
    map.addSource(TOPO_SOURCE, {
      type: 'raster',
      tiles: ['https://tile.openmaps.fr/opentopomap/{z}/{x}/{y}.png'],
      tileSize: 256,
      maxzoom: 17,
      attribution: '<a href="https://github.com/sletuffe/OpenTopoMap" target="_blank" rel="noopener noreferrer">© OpenTopoMap-R</a> · <a href="https://openmaps.fr/donate" target="_blank" rel="noopener noreferrer">Sostieni la mappa</a> · <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap</a>',
    });
    map.addLayer({
      id: TOPO_LAYER,
      type: 'raster',
      source: TOPO_SOURCE,
      layout: { visibility: preferred === 'topo' ? 'visible' : 'none' },
      paint: { 'raster-fade-duration': 180 },
    });
  }
  if (!map.getSource(SAT_SOURCE)) {
    map.addSource(SAT_SOURCE, {
      type: 'raster',
      tiles: ['https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'],
      tileSize: 256,
      maxzoom: 19,
      attribution: '<a href="https://www.esri.com/en-us/legal/terms/full-master-agreement" target="_blank" rel="noopener noreferrer">Esri World Imagery</a> · imagery providers',
    });
    map.addLayer({
      id: SAT_LAYER,
      type: 'raster',
      source: SAT_SOURCE,
      layout: { visibility: preferred === 'satellite' ? 'visible' : 'none' },
      paint: { 'raster-fade-duration': 180 },
    });
  }
}

export function setMountainBasemap(map: MlMap, mode: MountainBasemap): void {
  if (!map.getLayer(TOPO_LAYER) || !map.getLayer(SAT_LAYER)) return;
  map.setLayoutProperty(TOPO_LAYER, 'visibility', mode === 'topo' ? 'visible' : 'none');
  map.setLayoutProperty(SAT_LAYER, 'visibility', mode === 'satellite' ? 'visible' : 'none');
  try { localStorage.setItem(STORAGE_KEY, mode); } catch { /* Preferenza facoltativa */ }
}

/** Un unico selettore per atlante e planner: non ricarica MapLibre o i marker. */
export class MountainBasemapControl implements IControl {
  private root: HTMLDivElement | null = null;
  private buttons: HTMLButtonElement[] = [];
  private current = preferredBasemap();

  onAdd(map: MlMap): HTMLElement {
    const root = document.createElement('div');
    root.className = 'maplibregl-ctrl cb-basemap-control';
    root.setAttribute('role', 'group');
    root.setAttribute('aria-label', 'Tipo di carta');
    for (const [mode, name, tip] of [
      ['topo', 'TOPO', 'Carta topografica con sentieri e isoipse'],
      ['satellite', 'SAT', 'Vista satellitare'],
    ] as const) {
      const button = document.createElement('button');
      button.type = 'button';
      button.textContent = name;
      button.dataset.basemap = mode;
      button.title = tip;
      button.setAttribute('aria-label', tip);
      button.addEventListener('click', () => {
        this.current = mode;
        setMountainBasemap(map, mode);
        this.sync();
      });
      this.buttons.push(button);
      root.appendChild(button);
    }
    this.root = root;
    this.sync();
    return root;
  }

  onRemove(): void {
    this.root?.remove();
    this.root = null;
    this.buttons = [];
  }

  private sync(): void {
    for (const button of this.buttons) {
      const selected = button.dataset.basemap === this.current;
      button.classList.toggle('is-active', selected);
      button.setAttribute('aria-pressed', String(selected));
    }
  }
}
