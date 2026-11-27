# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `ca06e42`

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
✓ 185 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                 3.58 kB │ gzip:   1.42 kB
dist/assets/maplibre-gl-worker-CNLXcz58.js    508.54 kB
dist/assets/PlannerPage-hKS15PBr.css            2.65 kB │ gzip:   1.03 kB
dist/assets/maplibre-gl-CKRTiAqP.css           82.86 kB │ gzip:  10.71 kB
dist/assets/index-CEJT3ApS.css                180.24 kB │ gzip:  33.56 kB
dist/assets/constants-50oENZrn.js               0.11 kB │ gzip:   0.12 kB │ map:     0.22 kB
dist/assets/worker-BwnPtOf9.js                  0.13 kB │ gzip:   0.14 kB │ map:     0.69 kB
dist/assets/MiniMap-DLIlaRnj.js                 1.43 kB │ gzip:   0.82 kB │ map:     4.09 kB
dist/assets/renderThumb-FGTEzdLA.js             1.43 kB │ gzip:   0.89 kB │ map:     3.82 kB
dist/assets/PlannerPage-DHu7dYvh.js             8.27 kB │ gzip:   3.53 kB │ map:    21.85 kB
dist/assets/timeZoneCountries-GK1VZQgF.js      10.22 kB │ gzip:   3.58 kB │ map:    12.03 kB
dist/assets/sgAreas-C8_0UVS-.js                32.31 kB │ gzip:   8.04 kB │ map:    40.43 kB
dist/assets/MapView-HqbsmWFY.js                37.40 kB │ gzip:  12.08 kB │ map:   138.46 kB
dist/assets/venueGlyphs-B8qN5Cf4.js           248.13 kB │ gzip:  67.34 kB │ map: 1,303.88 kB
dist/assets/index-DU0klsk1.js               1,506.03 kB │ gzip: 423.13 kB │ map: 3,526.32 kB

[32m✓ built in 903ms[39m
[33m[plugin builtin:vite-reporter] 
(!) Some chunks are larger than 1500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.[39m
SEO: 4,125 pages, sitemap with 4,126 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
4205
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
