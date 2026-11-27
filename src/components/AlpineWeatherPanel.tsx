import { useEffect, useState } from 'react';
import { loadMountainWeather, loadSeasonalMeans, weatherLabel, weatherPhrase, type MountainWeather, type SeasonalWeather } from '../lib/alpineWeather';
import '../alpineWeatherV2.css';

interface Props {lat:number;lng:number;name:string}
const WEEKDAY = new Intl.DateTimeFormat('it-IT',{weekday:'short',day:'numeric'});
const integer=(value:number)=>Math.round(value).toLocaleString('it-IT');

function WeatherGlyph({code,size=50,isDay=true}:{code:number;size?:number;isDay?:boolean}) {
  const rain=[51,53,55,56,57,61,63,65,66,67,80,81,82].includes(code);
  const snow=[71,73,75,77,85,86].includes(code);
  const storm=[95,96,99].includes(code);
  const mist=[45,48].includes(code);
  const cloud=code>=2;
  return <svg width={size} height={size} viewBox="0 0 68 68" fill="none" role="img" aria-label={weatherLabel(code)}>
    {!cloud&&<><circle cx="34" cy="34" r="14" fill={isDay?'#ffca66':'#e8f2ff'} stroke="#174736" strokeWidth="2.8"/>
      <path d="M34 6v7M34 55v7M6 34h7M55 34h7M14 14l6 6M48 48l6 6M14 54l6-6M48 20l6-6" stroke="#b97518" strokeWidth="3" strokeLinecap="round"/></>}
    {cloud&&<><circle cx="46" cy="20" r="10" fill="#ffd07d" opacity=".88"/>
      <path d="M16 45c-8 0-10-10-5-15 3-3 6-4 11-4 2-11 12-17 23-12 6 2 9 8 9 13 8 1 11 5 11 10 0 5-4 9-10 9H16Z" fill="#f9fff9" stroke="#1d4a3a" strokeWidth="2.6" strokeLinejoin="round"/></>}
    {rain&&<g stroke="#1689c3" strokeWidth="3.4" strokeLinecap="round"><path d="m20 51-4 7M36 51l-4 7M52 51l-4 7"/></g>}
    {snow&&<g stroke="#4a98bd" strokeWidth="2.8" strokeLinecap="round"><path d="M20 52v10m-4-5h8m24-5v10m-4-5h8"/></g>}
    {storm&&<path d="m35 44-8 11h9l-5 11 16-17H37l5-5" fill="#ffb63b" stroke="#194334" strokeWidth="1.7"/>}
    {mist&&<g stroke="#6794a4" strokeWidth="3" strokeLinecap="round"><path d="M9 52h49M17 60h34"/></g>}
  </svg>;
}

function TempTrend({days}:{days:MountainWeather['next']}) {
  if(days.length<2)return null;
  const min=Math.min(...days.map(d=>d.tempMin))-2,max=Math.max(...days.map(d=>d.tempMax))+2;
  const range=Math.max(4,max-min),x=(i:number)=>50+i*(580/Math.max(1,days.length-1));
  const y=(t:number)=>141-(t-min)/range*108;
  const high=days.map((d,i)=>x(i)+','+y(d.tempMax)).join(' ');
  const low=days.map((d,i)=>x(i)+','+y(d.tempMin)).join(' ');
  const band=days.map((d,i)=>(i===0?'M':'L')+x(i)+' '+y(d.tempMax)).join(' ')+
    [...days].map((d,i)=>({d,i})).reverse().map(({d,i})=>'L'+x(i)+' '+y(d.tempMin)).join(' ')+'Z';
  return <div className="cb-meteo-trend">
    <div className="cb-meteo-mini-heading"><strong>ANDAMENTO TERMICO</strong><small>Minime e massime · prossimi {days.length} giorni</small></div>
    <svg viewBox="0 0 680 168" preserveAspectRatio="none" role="img" aria-label="Grafico delle temperature massime e minime previste">
      <path d="M25 141H654M25 85H654M25 32H654" stroke="#cbded0" strokeDasharray="4 5" strokeWidth="1"/>
      <path d={band} fill="#badfc6" opacity=".52"/>
      <polyline points={high} fill="none" stroke="#c90053" strokeWidth="3.3" strokeLinecap="round" strokeLinejoin="round"/>
      <polyline points={low} fill="none" stroke="#258bb1" strokeWidth="2.8" strokeLinecap="round" strokeLinejoin="round"/>
      {days.map((day,i)=><g key={day.date}><circle cx={x(i)} cy={y(day.tempMax)} r="5" fill="#c90053" stroke="white" strokeWidth="2"/><circle cx={x(i)} cy={y(day.tempMin)} r="4.4" fill="#258bb1" stroke="white" strokeWidth="2"/></g>)}
    </svg>
    <div className="cb-meteo-legend"><span><i className="warm"/>Massima</span><span><i className="cold"/>Minima</span></div>
  </div>;
}

export function AlpineWeatherPanel({lat,lng,name}:Props) {
  const [weather,setWeather]=useState<MountainWeather|null>(null);
  const [seasonal,setSeasonal]=useState<SeasonalWeather|null>(null);
  const [error,setError]=useState(false);
  const [historicalError,setHistoricalError]=useState(false);
  useEffect(()=>{
    let active=true;
    setWeather(null);setSeasonal(null);setError(false);setHistoricalError(false);
    void loadMountainWeather(lat,lng).then(d=>{if(active)setWeather(d);}).catch(()=>{if(active)setError(true);});
    void loadSeasonalMeans(lat,lng).then(d=>{if(active)setSeasonal(d);}).catch(()=>{if(active)setHistoricalError(true);});
    return ()=>{active=false;};
  },[lat,lng]);
  const mood=weather?weatherPhrase(weather):null;
  const valid=seasonal?.seasons.filter(s=>Number.isFinite(s.averageC))||[];
  const minimum=valid.length?Math.min(...valid.map(s=>s.averageC)):0;
  const maximum=valid.length?Math.max(...valid.map(s=>s.averageC)):1;
  return <section className="cb-meteo-panel" aria-label={'Meteo e clima per '+name}>
    <div className="cb-location-section-heading"><span>METEO / CONDIZIONI LOCALI</span><h2>CHE ARIA TIRA?</h2>
      <p>Previsioni e temperature modellate per la zona. Verifica sempre il bollettino locale prima di partire.</p>
    </div>
    {weather ? <>
      <div className="cb-meteo-current">
        <div className="cb-meteo-current-main">
          <WeatherGlyph code={weather.current.code} size={82} isDay={weather.current.isDay}/>
          <div><span className="cb-meteo-now-label">ORA NELLA ZONA</span>
            <strong>{integer(weather.current.temp)}°</strong>
            <span className="cb-meteo-condition">{weatherLabel(weather.current.code)}</span>
            <span className="cb-meteo-feels">Percepiti {integer(weather.current.feels)}°C</span>
          </div>
        </div>
        <div className="cb-meteo-current-facts">
          <div><span>VENTO</span><strong>{integer(weather.current.wind)} <small>km/h</small></strong></div>
          <div><span>PRECIPITAZIONE ORA</span><strong>{weather.current.precipitation.toLocaleString('it-IT',{maximumFractionDigits:1})} <small>mm</small></strong></div>
        </div>
      </div>
      {mood&&<div className={'cb-meteo-mood cb-meteo-mood--'+mood.level}><strong>{mood.title}</strong><p>{mood.description}</p></div>}
      <TempTrend days={weather.next}/>
      <div className="cb-meteo-forecast-heading"><h3>NEI PROSSIMI GIORNI</h3><span>MODELLO / {weather.next.length} GIORNI</span></div>
      <div className="cb-meteo-forecast">
        {weather.next.map((day,i)=><div key={day.date} className="cb-meteo-day">
          <div className="cb-meteo-day-top"><strong>{i===0?'OGGI':WEEKDAY.format(new Date(day.date+'T12:00:00')).toUpperCase()}</strong>
            <WeatherGlyph code={day.code??(i===0?weather.current.code:3)} size={40}/></div>
          <span className="cb-meteo-range"><strong>{integer(day.tempMax)}°</strong><small>{integer(day.tempMin)}°</small></span>
          <div className="cb-meteo-rain"><div><span>Prob. precipitazioni</span><strong>{integer(day.precipitationChance)}%</strong></div>
            <div className="cb-meteo-rain-track"><i style={{width:Math.max(0,Math.min(100,day.precipitationChance))+'%'}}/></div>
          </div>
          <div className="cb-meteo-day-amounts"><span>Pioggia <b>{day.rainMm.toLocaleString('it-IT',{maximumFractionDigits:1})} mm</b></span>
            <span>Neve <b>{day.snowCm.toLocaleString('it-IT',{maximumFractionDigits:1})} cm</b></span></div>
        </div>)}
      </div>
      <p className="cb-meteo-timestamp">Previsioni Open-Meteo aggiornate: {weather.updated||'orario non disponibile'}. Modello, non misurazione presso la struttura.</p>
    </> : <p className="cb-meteo-loading" role="status">{error?'Meteo temporaneamente non disponibile: consulta un bollettino locale.':'Caricamento delle previsioni…'}</p>}
    <div className="cb-meteo-seasons">
      <div className="cb-meteo-forecast-heading"><h3>COME CAMBIA NELLE STAGIONI?</h3><span>MEDIE 2021–2025</span></div>
      <p>Temperature medie da dati storici modellati, non normali climatiche trentennali.</p>
      {seasonal?<div className="cb-meteo-season-grid">
        {seasonal.seasons.map(season=><div key={season.season} className="cb-meteo-season">
          <span>{season.season.toUpperCase()}</span><strong>{Number.isFinite(season.averageC)?season.averageC.toLocaleString('it-IT',{maximumFractionDigits:1})+'°C':'n.d.'}</strong>
          <div className="cb-meteo-season-track"><i style={{width:Number.isFinite(season.averageC)?Math.max(8,(season.averageC-minimum)/(maximum-minimum||1)*100)+'%':'0%'}}/></div>
        </div>)}
      </div>:<p className="cb-meteo-loading">{historicalError?'Temperature storiche non disponibili.':'Recupero le temperature stagionali…'}</p>}
    </div>
    <p className="cb-meteo-legal">Le previsioni non sostituiscono osservazioni locali, valutazione del terreno e bollettino valanghe. Fonte: <a href="https://open-meteo.com/" target="_blank" rel="noopener noreferrer">Open-Meteo</a>.</p>
  </section>;
}
