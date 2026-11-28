import { describe, expect, it } from 'vitest';
import { homeHref, routeDetailHref, routeHref, initialMapMode } from '../src/lib/navigation';

describe('permalink Cima Becco',()=>{
  it('scrive il frammento dopo la home, non nel percorso corrente',()=>{
    expect(homeHref('routes')).toBe('/#routes');
    expect(homeHref('#rifugi')).toBe('/#rifugi');
    expect(homeHref('')).toBe('/');
  });
  it('distingue pagine SEO da sentieri creati a runtime',()=>{
    expect(routeHref('osm-hiking-13956722')).toBe('/route/osm-hiking-13956722/');
    expect(routeDetailHref('osm-hiking-13956722','curated')).toBe('/route/osm-hiking-13956722/');
    expect(routeDetailHref('sentiero-condiviso','community')).toBe('/#route/sentiero-condiviso');
  });
});

describe('navigazione dalla home',()=>{
  it('il collegamento Cime non conserva una precedente modalità Sentieri',()=>{
    expect(initialMapMode('#map','routes')).toBe('climbs');
    expect(initialMapMode('#map/10.7,46.1,12.4,47.0','routes')).toBe('climbs');
    expect(initialMapMode('#venue/monte-piana','routes')).toBe('climbs');
  });
  it('Sentieri e i permalink dei percorsi aprono i sentieri',()=>{
    expect(initialMapMode('#routes','climbs')).toBe('routes');
    expect(initialMapMode('#route/itinerario','climbs')).toBe('routes');
    expect(initialMapMode('','climbs',true)).toBe('routes');
  });
  it('le preferenze valgono solo per URL che non scelgono il contenuto',()=>{
    expect(initialMapMode('#import','routes')).toBe('routes');
    expect(initialMapMode('#import',null)).toBe('climbs');
  });
});
