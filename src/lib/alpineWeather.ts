/**
 * Open-Meteo per pagine locali: previsioni vive e medie stagionali derivate
 * dai dati giornalieri ERA5 2021-2025 (cinque anni, NON valori climatici
 * normali trentennali). Solo on demand, nessuna chiamata per 2300 località.
 */
export interface MountainWeather {
  updated: string;
  current: { temp: number; feels: number; wind: number; precipitation: number; code: number; isDay: boolean };
  next: { date: string; tempMin: number; tempMax: number; rainMm: number; snowCm: number; precipitationChance: number; code?: number }[];
}
export interface SeasonalWeather { period: string; seasons: {season:'inverno'|'primavera'|'estate'|'autunno';averageC:number;days:number}[] }
type CacheRecord<T> = {time:number;value:T};
const memory = new Map<string,CacheRecord<unknown>>();
const pending = new Map<string,Promise<unknown>>();
const CACHE_VERSION = 'cb-weather-v3';

function inRange(value:unknown):value is number{return typeof value==='number' && Number.isFinite(value);}
function rounded(n:number){return Math.round(n*10)/10;}
function cached<T>(key:string,maxAgeMs:number,task:()=>Promise<T>):Promise<T>{
  const current=Date.now();
  const entry=memory.get(key) as CacheRecord<T>|undefined;
  if(entry && current-entry.time<maxAgeMs)return Promise.resolve(entry.value);
  try {
    const record=JSON.parse(sessionStorage.getItem(CACHE_VERSION+':'+key)||'null') as CacheRecord<T>|null;
    if(record && current-record.time<maxAgeMs){memory.set(key,record);return Promise.resolve(record.value);}
  } catch { /* privacy mode */ }
  const active=pending.get(key) as Promise<T>|undefined;
  if(active)return active;
  const p=task().then(value=>{
    const record={value,time:Date.now()};
    memory.set(key,record);
    try{sessionStorage.setItem(CACHE_VERSION+':'+key,JSON.stringify(record));}catch{/**/}
    return value;
  }).finally(()=>pending.delete(key));
  pending.set(key,p);
  return p;
}
function weatherUrl(lat:number,lng:number,path:'forecast'|'archive'):URL{
  const u=new URL(path==='forecast'?'https://api.open-meteo.com/v1/forecast':'https://archive-api.open-meteo.com/v1/archive');
  u.searchParams.set('latitude',lat.toFixed(4));u.searchParams.set('longitude',lng.toFixed(4));
  u.searchParams.set('timezone','Europe/Rome');
  return u;
}
async function getJson(url:URL,signal?:AbortSignal):Promise<any>{
  const res=await fetch(url.toString(),{signal});
  if(!res.ok)throw new Error('Il servizio meteo non risponde ('+res.status+').');
  return await res.json();
}
export function loadMountainWeather(lat:number,lng:number):Promise<MountainWeather>{
  const key='forecast:'+lat.toFixed(3)+':'+lng.toFixed(3);
  return cached(key,20*60*1000,async()=>{
    const u=weatherUrl(lat,lng,'forecast');
    u.searchParams.set('current','temperature_2m,apparent_temperature,precipitation,wind_speed_10m,weather_code,is_day');
    u.searchParams.set('daily','temperature_2m_min,temperature_2m_max,precipitation_sum,snowfall_sum,precipitation_probability_max,weather_code');
    u.searchParams.set('forecast_days','4');
    const d=await getJson(u);const now=d.current,days=d.daily;
    if(!now||!days||!inRange(now.temperature_2m))throw new Error('Dati meteo parziali o mancanti.');
    return {
      updated:String(now.time||''),
      current:{temp:now.temperature_2m,feels:now.apparent_temperature,wind:now.wind_speed_10m,
        precipitation:now.precipitation,code:now.weather_code,isDay:now.is_day===1},
      next:(days.time||[]).slice(0,4).map((date:string,i:number)=>({
        date,tempMin:days.temperature_2m_min?.[i],tempMax:days.temperature_2m_max?.[i],
        rainMm:days.precipitation_sum?.[i]??0,snowCm:days.snowfall_sum?.[i]??0,
        precipitationChance:days.precipitation_probability_max?.[i]??0,
        code:inRange(days.weather_code?.[i])?days.weather_code[i]:undefined,
      })).filter((v:{tempMin:number;tempMax:number})=>inRange(v.tempMin)&&inRange(v.tempMax)),
    };
  });
}
const SEASONS = ['inverno','primavera','estate','autunno'] as const;
function seasonFor(date:string):0|1|2|3{
  const month=Number(date.slice(5,7));
  if(month===12||month<=2)return 0;
  if(month<=5)return 1;
  if(month<=8)return 2;
  return 3;
}
export function seasonalMeans(dates:string[],temperatures:(number|null)[]):SeasonalWeather{
  const buckets=SEASONS.map(()=>({sum:0,count:0}));
  for(let i=0;i<dates.length;i++){
    const t=temperatures[i];
    if(!inRange(t)||!/^\d{4}-\d\d-\d\d$/.test(dates[i]))continue;
    const index=seasonFor(dates[i]);buckets[index].sum+=t;buckets[index].count++;
  }
  return {period:'2021–2025',seasons:SEASONS.map((season,i)=>({
    season,averageC:buckets[i].count?rounded(buckets[i].sum/buckets[i].count):NaN,days:buckets[i].count,
  }))};
}
export function loadSeasonalMeans(lat:number,lng:number):Promise<SeasonalWeather>{
  const key='seasons:'+lat.toFixed(2)+':'+lng.toFixed(2);
  return cached(key,30*24*60*60*1000,async()=>{
    const u=weatherUrl(lat,lng,'archive');
    u.searchParams.set('start_date','2021-01-01');u.searchParams.set('end_date','2025-12-31');
    u.searchParams.set('daily','temperature_2m_mean');
    const d=await getJson(u);
    if(!Array.isArray(d.daily?.time)||!Array.isArray(d.daily?.temperature_2m_mean))
      throw new Error('Storico meteo non disponibile.');
    return seasonalMeans(d.daily.time,d.daily.temperature_2m_mean);
  });
}

export function weatherPhrase(weather:MountainWeather):{title:string;description:string;level:'ok'|'caution'|'warning'}{
  const today=weather.next[0],now=weather.current;
  if((today?.snowCm||0)>=8)return {title:'DO VETO MORE? (NEVICA)',description:'Neve prevista: verifica condizioni, bollettino nivometeorologico e pericolo valanghe.',level:'warning'};
  if((today?.rainMm||0)>=15||now.precipitation>=2)return {title:'PIOVE A SECCHIATE, GENIO.',description:'Precipitazioni importanti: valuta i rischi del percorso e cerca aggiornamenti ufficiali.',level:'warning'};
  if(now.wind>=50)return {title:'IL VENTO HA ALTRI PIANI.',description:'Raffiche e vento forte sono critici in quota, specie in cresta.',level:'warning'};
  if(now.temp<=-7)return {title:'SURGELATI MA CON STILE.',description:'Temperature molto basse: verifica gelo e condizioni del terreno.',level:'caution'};
  if(now.temp>=28)return {title:'GRIGLIATA DI POLPACCI.',description:'Caldo in montagna: acqua, ombra e orari contano.',level:'caution'};
  if((today?.precipitationChance||0)>=65)return {title:'IL K-WAY NON È DECORATIVO.',description:'Alta probabilità di pioggia: controlla le previsioni prima della partenza.',level:'caution'};
  return {title:'IL METEO NON HA SCUSE.',description:'Previsione indicativa: in quota cambia rapidamente. Controlla sempre il bollettino locale.',level:'ok'};
}
export function weatherLabel(code:number):string{
  if([0,1].includes(code))return 'Sereno o quasi';
  if([2,3].includes(code))return 'Nuvoloso';
  if([45,48].includes(code))return 'Nebbia';
  if([51,53,55,56,57].includes(code))return 'Pioviggine';
  if([61,63,65,66,67,80,81,82].includes(code))return 'Pioggia';
  if([71,73,75,77,85,86].includes(code))return 'Neve';
  if([95,96,99].includes(code))return 'Temporali';
  return 'Variabile';
}
