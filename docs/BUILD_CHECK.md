# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `af9f9be`

- installazione npm: **0**
- TypeScript: **0**
- build e SEO: **0**

## Ultimi messaggi TypeScript
~~~

> cima-becco@0.1.0 typecheck
> tsc --noEmit

~~~

## Ultimi messaggi build
~~~

> cima-becco@0.1.0 build
> tsc --noEmit && vite build && node scripts/build_seo.mjs

[36mvite v8.3.0 [32mbuilding client environment for production...[36m[39m
transforming...
✓ 186 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                 3.41 kB │ gzip:   1.36 kB
dist/assets/maplibre-gl-worker-CNLXcz58.js    508.54 kB
dist/assets/PlannerPage-hKS15PBr.css            2.65 kB │ gzip:   1.03 kB
dist/assets/maplibre-gl-CKRTiAqP.css           82.86 kB │ gzip:  10.71 kB
dist/assets/index-BAYc6oM3.css                185.43 kB │ gzip:  34.84 kB
dist/assets/constants-50oENZrn.js               0.11 kB │ gzip:   0.12 kB │ map:     0.22 kB
dist/assets/worker-D2ZHuPJX.js                  0.13 kB │ gzip:   0.15 kB │ map:     0.69 kB
dist/assets/MiniMap-B8zztOfJ.js                 1.43 kB │ gzip:   0.83 kB │ map:     4.09 kB
dist/assets/renderThumb-Bvf7RyJA.js             1.43 kB │ gzip:   0.89 kB │ map:     3.82 kB
dist/assets/PlannerPage-COG5AYv-.js             8.27 kB │ gzip:   3.53 kB │ map:    21.85 kB
dist/assets/timeZoneCountries-GK1VZQgF.js      10.22 kB │ gzip:   3.58 kB │ map:    12.03 kB
dist/assets/MapView-slh-XXAE.js                37.40 kB │ gzip:  12.08 kB │ map:   138.46 kB
dist/assets/venueGlyphs-DJfeYNKu.js           248.09 kB │ gzip:  67.31 kB │ map: 1,303.83 kB
dist/assets/index-BXGuet8G.js               1,494.61 kB │ gzip: 420.17 kB │ map: 3,520.30 kB

[32m✓ built in 1.19s[39m
SEO: 4,125 pages, sitemap with 4,126 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
4204
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
