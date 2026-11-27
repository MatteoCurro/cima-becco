import { describe, expect, it } from 'vitest';
import { seasonalMeans, weatherPhrase, weatherLabel, type MountainWeather } from './alpineWeather';

const weather=(props:Partial<MountainWeather>={}):MountainWeather=>({
  updated:'2026-11-27T13:00',
  current:{temp:8,feels:5,wind:12,precipitation:0,code:3,isDay:true},
  next:[{date:'2026-11-27',tempMin:2,tempMax:8,rainMm:0,snowCm:0,precipitationChance:10}],
  ...props,
});

describe('meteo alpino sicuro e contestualizzato',()=>{
  it('calcola le stagioni su dati effettivi, non inventa valori mancanti',()=>{
    const r=seasonalMeans(
      ['2021-01-01','2021-02-16','2021-04-10','2021-07-22','2021-12-30','non-data'],
      [-2,0,8,20,4,30],
    );
    expect(r.period).toBe('2021–2025');
    expect(r.seasons[0].averageC).toBeCloseTo(( -2 + 0 + 4 )/3);
    expect(r.seasons[0].days).toBe(3);
    expect(r.seasons[1].averageC).toBe(8);
    expect(r.seasons[2].averageC).toBe(20);
    expect(r.seasons[3].days).toBe(0);
    expect(Number.isNaN(r.seasons[3].averageC)).toBe(true);
  });
  it('neve intensa non viene presentata come bel tempo',()=>{
    const w=weather({next:[{date:'2026-11-27',tempMin:-4,tempMax:1,rainMm:0,snowCm:12,precipitationChance:80}]});
    expect(weatherPhrase(w).level).toBe('warning');
    expect(weatherPhrase(w).description).toMatch(/valanghe/);
  });
  it('meteo umoristico ma allerta per pioggia e vento',()=>{
    expect(weatherPhrase(weather({current:{...weather().current,wind:54}})).level).toBe('warning');
    expect(weatherPhrase(weather({next:[{...weather().next[0],rainMm:22}]})).level).toBe('warning');
  });
  it('gli errori di codice meteo non diventano falsi bollettini',()=>{
    expect(weatherLabel(71)).toBe('Neve');
    expect(weatherLabel(95)).toBe('Temporali');
    expect(weatherLabel(900)).toBe('Variabile');
  });
});
