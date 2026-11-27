import { useEffect, useState } from 'react';
import { loadMountainWeather, loadSeasonalMeans, weatherLabel, weatherPhrase, type MountainWeather, type SeasonalWeather } from '../lib/alpineWeather';

interface Props {lat:number;lng:number;name:string}
const MONTHS=new Intl.DateTimeFormat('it-IT',{weekday:'short',day:'numeric',month:'short'});
export function AlpineWeatherPanel({lat,lng,name}:Props) {
  const [weather,setWeather]=useState<MountainWeather|null>(null);
  const [seasonal,setSeasonal]=useState<SeasonalWeather|null>(null);
  const [weatherError,setWeatherError]=useState(false);
  const [historyError,setHistoryError]=useState(false);
  useEffect(()=>{
    let active=true;
    setWeather(null);setSeasonal(null);setWeatherError(false);setHistoryError(false);
    void loadMountainWeather(lat,lng).then(d=>{if(active)setWeather(d);}).catch(()=>{if(active)setWeatherError(true);});
    void loadSeasonalMeans(lat,lng).then(d=>{if(active)setSeasonal(d);}).catch(()=>{if(active)setHistoryError(true);});
    return ()=>{active=false;};
  },[lat,lng]);
  const mood=weather?weatherPhrase(weather):null;
  return <section className="cb-local-weather" aria-label={`Meteo a ${name}`}>
    <div className="cb-local-heading"><span>METEO / MODELLO</span><h2>CHE ARIA TIRA?</h2></div>
    {weather ? <>
      <div className="cb-weather-now">
        <div><strong>{Math.round(weather.current.temp)}°</strong><span>{weatherLabel(weather.current.code)} · percepita {Math.round(weather.current.feels)}°C</span></div>
        <div className="cb-weather-now-minors"><span><strong>{Math.round(weather.current.wind)} km/h</strong>Vento</span><span><strong>{weather.current.precipitation.toFixed(1)} mm</strong>Precipitazione attuale</span></div>
      </div>
      {mood && <div className={`cb-weather-quip cb-weather-quip--${mood.level}`}><strong>{mood.title}</strong><p>{mood.description}</p></div>}
      <div className="cb-weather-days">
        {weather.next.map(day=><div key={day.date}><strong>{MONTHS.format(new Date(day.date+'T12:00:00'))}</strong>
          <span className="cb-weather-temperatures">{Math.round(day.tempMin)}° / {Math.round(day.tempMax)}°</span>
          <span>Pioggia {day.rainMm.toFixed(1)} mm</span><span>Neve {day.snowCm.toFixed(1)} cm</span>
          <span>Prob. pioggia {day.precipitationChance}%</span>
        </div>)}
      </div>
      <small className="cb-weather-stamp">Modello aggiornato: {weather.updated || 'ora'} · Open-Meteo</small>
    </> : <p className="cb-weather-loading">{weatherError?'Previsioni non disponibili ora. Controlla un bollettino meteo locale.':'Sto interrogando i modelli meteo…'}</p>}
    <div className="cb-weather-seasonal"><h3>COM’È DI SOLITO?</h3><p>Temperatura media stagionale modellata sul periodo 2021–2025. Non equivale alle normali climatiche trentennali.</p>
      {seasonal?<div className="cb-weather-seasons">{seasonal.seasons.map(s=><div key={s.season}>
        <small>{s.season.toUpperCase()}</small><strong>{Number.isFinite(s.averageC)?s.averageC.toLocaleString('it-IT',{maximumFractionDigits:1})+'°C':'n.d.'}</strong>
      </div>)}</div>:<p className="cb-weather-loading">{historyError?'Storico climatico temporaneamente indisponibile.':'Calcolo le medie dai dati storici…'}</p>}
    </div>
    <p className="cb-weather-disclaimer">Previsioni da modello, non osservazioni sul punto GPS. In montagna il meteo cambia velocemente: prima di salire consulta il bollettino ufficiale e, con neve, il bollettino valanghe. <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Fonte Open-Meteo</a>.</p>
  </section>;
}
