# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `63090ee`

- installazione npm: **0**
- TypeScript: **0**
- build e SEO: **0**
- test Vitest: **1**

## Ultimi messaggi TypeScript
~~~

> cima-becco@0.1.0 typecheck
> tsc --noEmit

~~~

## Test di regressione
~~~
     [32m✓[39m riconosce gli estremi e un vero anello[32m 1[2mms[22m[39m
     [32m✓[39m non crea endpoint per tracce senza geometria valida[32m 0[2mms[22m[39m
     [32m✓[39m costruisce permalink sicuri dei sentieri[32m 1[2mms[22m[39m
     [32m✓[39m mescola i livelli di difficoltà senza scartare nessun elemento[32m 1[2mms[22m[39m
 [32m✓[39m src/lib/routeQuality.test.ts [2m([22m[2m17 tests[22m[2m)[22m[32m 24[2mms[22m[39m
 [32m✓[39m src/lib/rangeScale.test.ts [2m([22m[2m17 tests[22m[2m)[22m[32m 15[2mms[22m[39m
 [32m✓[39m src/lib/routeMatch.test.ts [2m([22m[2m9 tests[22m[2m)[22m[32m 15[2mms[22m[39m
 [32m✓[39m src/lib/moderate.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 15[2mms[22m[39m
 [32m✓[39m src/lib/tcx.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 50[2mms[22m[39m
 [32m✓[39m src/lib/regions.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 14[2mms[22m[39m
 [32m✓[39m src/lib/routeAnalysis.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 17[2mms[22m[39m
 [32m✓[39m src/components/AuthModal.test.tsx [2m([22m[2m3 tests[22m[2m)[22m[33m 392[2mms[22m[39m
 [32m✓[39m src/lib/routeEditorial.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 45[2mms[22m[39m
 [32m✓[39m src/lib/saved.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 18[2mms[22m[39m
 [32m✓[39m src/map/camera.test.ts [2m([22m[2m10 tests[22m[2m)[22m[32m 13[2mms[22m[39m
 [32m✓[39m src/lib/geolocation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/bookmarks.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 9[2mms[22m[39m
 [32m✓[39m src/map/collisions.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/dom.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 30[2mms[22m[39m
 [32m✓[39m src/lib/username.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 10[2mms[22m[39m
 [32m✓[39m src/styles.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/elevation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 6[2mms[22m[39m
 [32m✓[39m src/lib/country.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 14[2mms[22m[39m
 [32m✓[39m src/lib/gpx.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 6[2mms[22m[39m

[31m⎯⎯⎯⎯⎯⎯⎯[39m[1m[41m Failed Tests 2 [49m[22m[31m⎯⎯⎯⎯⎯⎯⎯[39m

[41m[1m FAIL [22m[49m src/lib/routes.test.ts[2m > [22mricerca geografica percorsi a piedi[2m > [22mrileva le coordinate estreme e gestisce lista vuota
[31m[1mAssertionError[22m: expected 12.283999999999999 to be greater than or equal to 12.284[39m
[36m [2m❯[22m src/lib/routes.test.ts:[2m32:22[22m[39m
    [90m 30|[39m     const box = routesBounds(routes)!;
    [90m 31|[39m     expect(box.west).toBeLessThanOrEqual(11.65);
    [90m 32|[39m     expect(box.east).toBeGreaterThanOrEqual(12.284);
    [90m   |[39m                      [31m^[39m
    [90m 33|[39m     expect(box.north).toBeGreaterThanOrEqual(46.521);
    [90m 34|[39m     expect(routesBounds([])).toBeNull();

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/2]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routes.test.ts[2m > [22mfiltri escursionistici[2m > [22mapplica il limite sul tempo stimato dal modello escursionistico
[31m[1mAssertionError[22m: expected 1500 to be greater than 1500[39m
[36m [2m❯[22m src/lib/routes.test.ts:[2m61:35[22m[39m
    [90m 59|[39m   it('applica il limite sul tempo stimato dal modello escursionistico'…
    [90m 60|[39m     const threshold = Math.round((routeEstimateS(cadore) + routeEstima…
    [90m 61|[39m     expect(routeEstimateS(fassa)).toBeGreaterThan(routeEstimateS(cador…
    [90m   |[39m                                   [31m^[39m
    [90m 62|[39m     expect(filterRoutes(routes, { ...NO_ROUTE_FILTERS, maxDurationS: t…
    [90m 63|[39m     expect(filterRoutes(routes, { ...NO_ROUTE_FILTERS, minDurationS: t…

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[2/2]⎯[22m[39m


[2m Test Files [22m [1m[31m1 failed[39m[22m[2m | [22m[1m[32m25 passed[39m[22m[90m (26)[39m
[2m      Tests [22m [1m[31m2 failed[39m[22m[2m | [22m[1m[32m226 passed[39m[22m[90m (228)[39m
[2m   Start at [22m 11:18:46
[2m   Duration [22m 12.54s[2m (environment 82%, tests 6%, import 5%, transform 4%, worker 3%)[22m

[2mEnvironment [22m [33mjsdom was created 26 times[39m[2m · 26.34s total, 82% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m


::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routes.test.ts,title=src/lib/routes.test.ts > ricerca geografica percorsi a piedi > rileva le coordinate estreme e gestisce lista vuota,line=32,column=22::AssertionError: expected 12.283999999999999 to be greater than or equal to 12.284%0A ❯ src/lib/routes.test.ts:32:22%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routes.test.ts,title=src/lib/routes.test.ts > filtri escursionistici > applica il limite sul tempo stimato dal modello escursionistico,line=61,column=35::AssertionError: expected 1500 to be greater than 1500%0A ❯ src/lib/routes.test.ts:61:35%0A%0A
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
dist/index.html                                 3.41 kB │ gzip:   1.37 kB
dist/assets/maplibre-gl-worker-CNLXcz58.js    508.54 kB
dist/assets/PlannerPage-hKS15PBr.css            2.65 kB │ gzip:   1.03 kB
dist/assets/maplibre-gl-CKRTiAqP.css           82.86 kB │ gzip:  10.71 kB
dist/assets/index-BAYc6oM3.css                185.43 kB │ gzip:  34.84 kB
dist/assets/constants-50oENZrn.js               0.11 kB │ gzip:   0.12 kB │ map:     0.22 kB
dist/assets/worker-BqUCjFoK.js                  0.13 kB │ gzip:   0.15 kB │ map:     0.69 kB
dist/assets/MiniMap-6PUoTZ6X.js                 1.43 kB │ gzip:   0.83 kB │ map:     4.09 kB
dist/assets/renderThumb-ChsB3dKl.js             1.43 kB │ gzip:   0.89 kB │ map:     3.82 kB
dist/assets/PlannerPage-DfksQOY5.js             8.27 kB │ gzip:   3.52 kB │ map:    21.85 kB
dist/assets/timeZoneCountries-GK1VZQgF.js      10.22 kB │ gzip:   3.58 kB │ map:    12.03 kB
dist/assets/MapView-DKyjeori.js                37.40 kB │ gzip:  12.08 kB │ map:   138.46 kB
dist/assets/venueGlyphs-DJfeYNKu.js           248.09 kB │ gzip:  67.31 kB │ map: 1,303.83 kB
dist/assets/index-Dfwtjf1e.js               1,494.69 kB │ gzip: 420.20 kB │ map: 3,520.58 kB

[32m✓ built in 1.45s[39m
SEO: 4,125 pages, sitemap with 4,126 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
4205
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
