import { describe,it,expect } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import type { AlpineWaterPoint } from './alpineWater';
import { waterDisplayName,waterKindLabel,WATER_KINDS } from './waterPresentation';
import { WaterNearbyList } from '../components/WaterNearbyList';
const points:AlpineWaterPoint[] = [
 {slug:'a',name:'Punto acqua',kind:'fontanella',potable:'unknown',lat:46,lng:12,osmUrl:'https://www.openstreetmap.org/node/1'},
 {slug:'b',name:'Sorgente',kind:'sorgente',potable:'no',lat:46,lng:12,osmUrl:'https://www.openstreetmap.org/node/2'},
 {slug:'c',name:'Rubinetto',kind:'rubinetto',potable:'yes',lat:46,lng:12,osmUrl:'https://www.openstreetmap.org/node/3'},
];
describe('punti acqua identificabili',()=>{
 it('ogni tipo ha un simbolo e una denominazione distinta',()=>{
  expect(Object.keys(WATER_KINDS)).toEqual(['fontanella','sorgente','rubinetto']);
  expect(points.map(p=>waterKindLabel(p.kind))).toEqual(['Fontanella','Sorgente','Rubinetto']);
  expect(waterDisplayName(points[0],1)).toBe('Fontanella 1');
 });
 it('stampa numeri e simboli disponibili senza hover',()=>{
  const html=renderToStaticMarkup(createElement(WaterNearbyList,{points,onSelect:()=>undefined,selectedSlug:'b'}));
  expect(html).toContain('Fontanella 1');
  expect(html).toContain('Sorgente 2');
  expect(html).toContain('Rubinetto 3');
  expect(html).toContain('aria-pressed="true"');
  expect(html).toContain('cb-water-kind-icon--sorgente');
  expect(html).toContain('Segnalata non potabile');
 });
});
