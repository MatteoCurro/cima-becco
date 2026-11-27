import { describe, expect, it } from 'vitest';
import { homeHref, routeDetailHref, routeHref } from '../src/lib/navigation';

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
