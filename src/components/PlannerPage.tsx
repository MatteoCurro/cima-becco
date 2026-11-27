import { useEffect, useRef, useState } from 'react';
import { Map as MapLibreMap, Marker, NavigationControl, type GeoJSONSource } from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import { SiteFooter, SiteHeader } from './SiteChrome';
import { MAP_STYLE_URL } from '../map/constants';
import { calculateTrailRoute, directionsToStart, type PlanWaypoint, type PlannedTrack } from '../lib/cimaRouting';
import { toGpx } from '../lib/gpx';
import { routeFromPoints } from '../lib/routes';
import { loadLocalRoutes, saveLocalRoutes } from '../lib/localRoutes';
import '../cimaPlanner.css';

const INITIAL_CENTER: [number, number] = [12.0, 43.1];
const EMPTY_ROUTE = { type: 'FeatureCollection' as const, features: [] };

function routeGeoJSON(track: PlannedTrack | null) {
  return track ? {
    type: 'FeatureCollection' as const,
    features: [{
      type: 'Feature' as const,
      properties: {},
      geometry: { type: 'LineString' as const, coordinates: track.points.map((p) => [p[0], p[1]]) },
    }],
  } : EMPTY_ROUTE;
}

function downloadGPX(name: string, track: PlannedTrack) {
  const xml = toGpx(name, track.points, [], track.elevationAvailable);
  const url = URL.createObjectURL(new Blob([xml], { type: 'application/gpx+xml;charset=utf-8' }));
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = (name.trim().replace(/[^a-z0-9à-ÿ_-]+/gi, '-').slice(0, 70) || 'percorso') + '.gpx';
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

export function PlannerPage() {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<MapLibreMap | null>(null);
  const markers = useRef<Marker[]>([]);
  const [ready, setReady] = useState(false);
  const [waypoints, setWaypoints] = useState<PlanWaypoint[]>([]);
  const [track, setTrack] = useState<PlannedTrack | null>(null);
  const [name, setName] = useState('Il mio trekking');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!container.current) return;
    const instance = new MapLibreMap({
      container: container.current,
      style: MAP_STYLE_URL,
      center: INITIAL_CENTER,
      zoom: 5.7,
      minZoom: 3,
      attributionControl: true,
    });
    map.current = instance;
    instance.addControl(new NavigationControl({ showCompass: true }), 'top-right');
    const click = (event: { lngLat: { lng: number; lat: number } }) => {
      setWaypoints((previous) => previous.length >= 12 ? previous : [...previous, { lng: event.lngLat.lng, lat: event.lngLat.lat }]);
      setTrack(null);
      setError(null);
      setMessage(null);
    };
    instance.on('click', click);
    instance.on('load', () => {
      if (!instance.getSource('cb-route')) instance.addSource('cb-route', { type: 'geojson', data: EMPTY_ROUTE });
      instance.addLayer({ id: 'cb-route-outline', type: 'line', source: 'cb-route', paint: { 'line-color': '#fff', 'line-width': 8, 'line-opacity': 0.94 } });
      instance.addLayer({ id: 'cb-route-line', type: 'line', source: 'cb-route', paint: { 'line-color': '#296d58', 'line-width': 5 } });
      setReady(true);
    });
    return () => {
      markers.current.forEach((marker) => marker.remove());
      markers.current = [];
      instance.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    if (!ready || !map.current) return;
    markers.current.forEach((marker) => marker.remove());
    markers.current = waypoints.map((point, index) => {
      const element = document.createElement('div');
      element.className = 'cb-point';
      element.textContent = index === 0 ? 'P' : index === waypoints.length - 1 ? 'A' : String(index + 1);
      element.title = 'Trascina per spostare il punto';
      const marker = new Marker({ element, draggable: true }).setLngLat([point.lng, point.lat]).addTo(map.current!);
      marker.on('dragend', () => {
        const coordinate = marker.getLngLat();
        setWaypoints((existing) => existing.map((p, i) => i === index ? { lng: coordinate.lng, lat: coordinate.lat } : p));
        setTrack(null);
      });
      return marker;
    });
  }, [ready, waypoints]);

  useEffect(() => {
    if (!ready || !map.current) return;
    const source = map.current.getSource('cb-route') as GeoJSONSource | undefined;
    source?.setData(routeGeoJSON(track));
    if (track) {
      let west = Infinity, east = -Infinity, south = Infinity, north = -Infinity;
      for (const [lng, lat] of track.points) {
        west = Math.min(west, lng); east = Math.max(east, lng);
        south = Math.min(south, lat); north = Math.max(north, lat);
      }
      map.current.fitBounds([[west, south], [east, north]], { padding: 65, maxZoom: 14, duration: 450 });
    }
  }, [ready, track]);

  async function calculate() {
    if (busy || waypoints.length < 2) return;
    setBusy(true);
    setError(null);
    setMessage(null);
    setTrack(null);
    const controller = new AbortController();
    const timeout = window.setTimeout(() => controller.abort(), 30000);
    try {
      setTrack(await calculateTrailRoute(waypoints, controller.signal));
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Non è stato possibile calcolare il percorso.');
    } finally {
      window.clearTimeout(timeout);
      setBusy(false);
    }
  }

  function save() {
    if (!track) return;
    try {
      const route = routeFromPoints(name.trim() || 'Itinerario senza nome', track.points, []);
      route.elevationAvailable = track.elevationAvailable;
      route.activity = 'trail';
      route.description = 'Itinerario pianificato digitalmente; non verificato sul terreno.';
      route.source = 'local';
      const saved = loadLocalRoutes().filter((existing) => existing.slug !== route.slug);
      saveLocalRoutes([route, ...saved]);
      setMessage('Percorso salvato in questo browser. Lo trovi tra i percorsi sul dispositivo.');
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'Il percorso non è stato salvato.');
    }
  }

  return (
    <div className="cb-page">
      <SiteHeader sticky />
      <main className="cb-planner">
        <aside className="cb-side">
          <div className="cb-kicker">CIMA BECCO · PIANIFICA</div>
          <h1>Disegna il tuo trekking</h1>
          <p>Indica sulla mappa la partenza, la destinazione e le eventuali tappe. Il motore di routing proverà a seguire i sentieri disponibili.</p>
          <label className="cb-label" htmlFor="cb-name">Nome del percorso</label>
          <input id="cb-name" className="cb-input" value={name} onChange={(event) => setName(event.target.value)} maxLength={100} />
          <ol className="cb-point-list">
            {waypoints.map((point, index) => (
              <li key={index}>
                <span>{index === 0 ? 'Partenza' : index === waypoints.length - 1 ? 'Arrivo' : 'Tappa ' + index}</span>
                <small>{point.lat.toFixed(5)}, {point.lng.toFixed(5)}</small>
                <button type="button" aria-label={'Rimuovi punto ' + (index + 1)} onClick={() => {
                  setWaypoints((old) => old.filter((_, i) => i !== index)); setTrack(null);
                }}>×</button>
              </li>
            ))}
          </ol>
          {waypoints.length === 0 && <div className="cb-empty">Tocca la mappa per scegliere il punto di partenza.</div>}
          <div className="cb-buttons">
            <button className="cb-action primary" type="button" disabled={waypoints.length < 2 || busy} onClick={() => void calculate()}>
              {busy ? 'Calcolo in corso…' : 'Calcola itinerario'}
            </button>
            <button className="cb-action" type="button" disabled={waypoints.length < 2 || busy} onClick={() => {
              setWaypoints((old) => old.length > 2 ? [...old, { ...old[0] }] : old); setTrack(null);
            }}>Chiudi ad anello</button>
            <button className="cb-action" type="button" disabled={!waypoints.length || busy} onClick={() => {
              setWaypoints([]); setTrack(null); setMessage(null); setError(null);
            }}>Azzera</button>
          </div>
          {error && <div className="cb-message error" role="alert">{error}</div>}
          {message && <div className="cb-message" role="status">{message}</div>}
          {track && (
            <section className="cb-result">
              <h2>Il tuo itinerario</h2>
              <div className="cb-stats">
                <div><strong>{(track.distanceM / 1000).toFixed(1)} km</strong><small>Lunghezza</small></div>
                <div><strong>{track.gainM == null ? 'n/d' : '+' + Math.round(track.gainM) + ' m'}</strong><small>Dislivello</small></div>
              </div>
              <div className="cb-buttons">
                <button className="cb-action primary" type="button" onClick={save}>Salva</button>
                <button className="cb-action" type="button" onClick={() => downloadGPX(name, track)}>Esporta GPX</button>
                <a className="cb-action" href={directionsToStart(waypoints[0])} target="_blank" rel="noopener noreferrer">Raggiungi la partenza</a>
              </div>
              <p className="cb-note">Traccia automatica e non verificata sul terreno. Controlla condizioni, difficoltà e restrizioni prima di partire. Le ferrate non vengono generate automaticamente.</p>
            </section>
          )}
          <p className="cb-note">Questa prima versione salva i percorsi soltanto sul dispositivo. La pubblicazione condivisa richiederà il database Cima Becco; il servizio pubblico BRouter usato nei test potrebbe non essere sempre disponibile.</p>
          <a href="#routes">Esplora i percorsi</a>
        </aside>
        <div className="cb-map" ref={container} role="application" aria-label="Mappa di pianificazione trekking" />
      </main>
      <SiteFooter />
    </div>
  );
}
