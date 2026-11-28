import { describe, expect, it } from 'vitest';
import { applyRuralStructureEvidence } from './ruralStructureEvidence';
import evidence from '../../public/data/atlas/alpine-structure-evidence-v1.json';
import type { AlpinePlace } from './alpinePlaces';

const fixture:AlpinePlace[]=[
  {slug:'osm-w-175876228',name:'Malga Casera Campigàt',kind:'rifugio',
   lat:46.299875,lng:11.891694,osmUrl:'https://www.openstreetmap.org/way/175876228',
   photo:{url:'https://example.org/photo.jpg',sourceUrl:'https://example.org/original',
     license:'CC BY 4.0',author:'Autore'}},
  {slug:'osm-w-199050050',name:'Malga Valbona',kind:'rifugio',
   lat:46.296992,lng:11.878975,osmUrl:'https://www.openstreetmap.org/way/199050050'},
  {slug:'osm-n-123',name:'Rifugio realmente gestito',kind:'rifugio',
   lat:46.35,lng:11.91,osmUrl:'https://www.openstreetmap.org/node/123'}
];
describe('Rural structure classification evidence',()=>{
  it('reclassifies Campigat and Valbona, retains OSM ID, photo and original slug',()=>{
    const rows=applyRuralStructureEvidence(fixture,evidence);
    for(const slug of ['osm-w-175876228','osm-w-199050050']){
      const row=rows.find(p=>p.slug===slug)!;
      expect(row.kind).toBe('bivacco');
      expect(row.subtype).toBe('alpine_casera_shelter');
      expect(row.classificationEvidence?.sourceUrl).toMatch(/^https:\/\//);
      expect(row.classificationEvidence?.previousKind).toBe('rifugio');
    }
    expect(rows.find(p=>p.slug==='osm-w-175876228')?.photo).toEqual(fixture[0].photo);
    expect(rows.find(p=>p.slug==='osm-n-123')?.kind).toBe('rifugio');
  });
  it('adds Bosch Brusa as a source-backed support point without invented OSM identity',()=>{
    const rows=applyRuralStructureEvidence(fixture,evidence);
    const malga=rows.find(p=>p.slug==='malga-bosch-brusa')!;
    expect(malga.kind).toBe('bivacco');
    expect(malga.subtype).toBe('support_point');
    expect(malga.sourceIds?.official).toBe('falcade:malga-bosch-brusa');
    expect(malga.sourceIds?.osm).toBeUndefined();
    expect(malga.facts?.emergencyUseOnly?.value).toBe(true);
    expect(malga.facts?.regularOvernightAccommodation?.value).toBe(false);
    expect(malga.capacity).toBeUndefined();
    expect(malga.quality?.seoIndexable).toBe(false);
  });
  it('leaves a genuine CAI-verified alpine refuge untouched even when called Malga',()=>{
    const managed:AlpinePlace={
      slug:'cai-777',kind:'rifugio',name:'Malga Rifugio Gestito',
      lat:46.3,lng:11.8,osmUrl:'https://www.openstreetmap.org/#map=14/46.3/11.8',
      sourceIds:{cai:'777'},capacity:12
    };
    const rows=applyRuralStructureEvidence([managed],evidence);
    expect(rows[0].kind).toBe('rifugio');
    expect(rows[0].subtype).toBeUndefined();
  });
  it('does not duplicate on repeated application or accept invalid/missing source',()=>{
    const once=applyRuralStructureEvidence(fixture,evidence);
    const twice=applyRuralStructureEvidence(once,evidence);
    expect(twice.filter(p=>p.slug==='malga-bosch-brusa')).toHaveLength(1);
    expect(applyRuralStructureEvidence(fixture,{releaseChannel:'WRONG',entries:evidence.entries})).toEqual(fixture);
  });
  it('never transforms a name-similar but distinct source identity',()=>{
    const other={...fixture[0],slug:'osm-w-1212',osmUrl:'https://www.openstreetmap.org/way/1212'};
    const rows=applyRuralStructureEvidence([other],evidence);
    expect(rows.find(p=>p.slug==='osm-w-1212')?.subtype).toBe('rural_type_unverified');
    expect(rows.find(p=>p.slug==='osm-w-1212')?.quality?.seoIndexable).toBe(false);
    expect(rows.find(p=>p.slug==='osm-w-1212')?.classificationEvidence?.sourceUrl)
      .toBe('https://www.openstreetmap.org/way/1212');
    // Only the verified identity can receive the official Casera label.
    expect(rows.find(p=>p.slug==='osm-w-1212')?.shelterTypeLabel)
      .toBe('Malga · uso da verificare');
  });
});
