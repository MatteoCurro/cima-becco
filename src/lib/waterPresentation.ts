import type { AlpineWaterPoint } from './alpineWater';

/** La tipologia è distinta dalla potabilità; tre pittogrammi condivisi fra UI e MapLibre. */
export const WATER_KINDS = {
  fontanella: {
    label: 'Fontanella', color: '#176b9a',
    paths: ['M6 21h12M8 19h8M9 19V11h6v8M6 11h12M8 7h8M12 3v4'],
  },
  sorgente: {
    label: 'Sorgente', color: '#267568',
    paths: ['M12 2C9 6 6 9 6 13a6 6 0 0 0 12 0c0-4-3-7-6-11Z', 'M4 21c2-1.5 4-1.5 6 0s4 1.5 6 0 4-1.5 5 0'],
  },
  rubinetto: {
    label: 'Rubinetto', color: '#79549a',
    paths: ['M10 3v4M7 4h6M7 7h6M13 7h3a4 4 0 0 1 4 4v3h-5M4 11h11M4 11v4h11v-4M18 17l-1 2'],
  },
} as const;

export type WaterKind = keyof typeof WATER_KINDS;
export function waterKindLabel(kind: AlpineWaterPoint['kind']): string {
  return WATER_KINDS[kind]?.label || 'Punto acqua';
}
export function waterDisplayName(point:Pick<AlpineWaterPoint,'kind'|'name'>, index?:number):string{
  const kind=waterKindLabel(point.kind);
  const generic=['Punto acqua','Sorgente','Rubinetto','Fontanella'];
  if(!point.name?.trim() || generic.includes(point.name.trim())) return kind+(index ? ' '+index : '');
  return point.name;
}
