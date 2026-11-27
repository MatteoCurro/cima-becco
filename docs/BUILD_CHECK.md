# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `111cb0f`

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
     [32m✓[39m rende un nome sentiero generico leggibile senza inventare luoghi[32m 6[2mms[22m[39m
     [32m✓[39m non inventa quota e panorami quando il DEM manca[32m 31[2mms[22m[39m
[31m     [31m×[31m separa difficoltà CAI e tag umoristici[39m[32m 9[2mms[22m[39m
[31m     [31m×[31m non attribuisce a una ferrata una difficoltà se manca la scala[39m[32m 1[2mms[22m[39m
     [32m✓[39m esclude le homepage CAI/SAT scambiate per schede singole[32m 1[2mms[22m[39m
 [32m✓[39m src/lib/saved.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 9[2mms[22m[39m
 [32m✓[39m src/map/camera.test.ts [2m([22m[2m10 tests[22m[2m)[22m[32m 7[2mms[22m[39m
 [32m✓[39m src/lib/bookmarks.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 12[2mms[22m[39m
 [32m✓[39m src/lib/geolocation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 7[2mms[22m[39m
 [32m✓[39m src/map/collisions.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/dom.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 24[2mms[22m[39m
 [32m✓[39m src/lib/username.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 5[2mms[22m[39m
 [32m✓[39m src/styles.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/elevation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 5[2mms[22m[39m
 [32m✓[39m src/lib/country.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 16[2mms[22m[39m
 [32m✓[39m src/lib/gpx.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 3[2mms[22m[39m

[31m⎯⎯⎯⎯⎯⎯⎯[39m[1m[41m Failed Tests 2 [49m[22m[31m⎯⎯⎯⎯⎯⎯⎯[39m

[41m[1m FAIL [22m[49m src/lib/routeEditorial.test.ts[2m > [22meditoriale Cima Becco[2m > [22msepara difficoltà CAI e tag umoristici
[31m[1mAssertionError[22m: expected 'MERENDEROS' to be 'Due curve e spiana' // Object.is equality[39m

Expected: [32m"Due curve e spiana"[39m
Received: [31m"MERENDEROS"[39m

[36m [2m❯[22m src/lib/routeEditorial.test.ts:[2m28:59[22m[39m
    [90m 26|[39m   });
    [90m 27|[39m   it('separa difficoltà CAI e tag umoristici', () => {
    [90m 28|[39m     expect(trailMood(route({ caiDifficulty: 'T' })).quip).toBe('Due cu…
    [90m   |[39m                                                           [31m^[39m
    [90m 29|[39m     expect(trailMood(route({ caiDifficulty: 'EE' })).quip).toBe('Non s…
    [90m 30|[39m     expect(trailMood(route({ caiDifficulty: 'EEA' })).label).toBe('Esp…

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/2]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routeEditorial.test.ts[2m > [22meditoriale Cima Becco[2m > [22mnon attribuisce a una ferrata una difficoltà se manca la scala
[31m[1mAssertionError[22m: expected 'AVAMBRACCI IN LEASING' to be 'Strattona' // Object.is equality[39m

Expected: [32m"Strattona"[39m
Received: [31m"AVAMBRACCI IN LEASING"[39m

[36m [2m❯[22m src/lib/routeEditorial.test.ts:[2m35:83[22m[39m
    [90m 33|[39m   it('non attribuisce a una ferrata una difficoltà se manca la scala',…
    [90m 34|[39m     expect(trailMood(route({ activity: 'ferrata' })).level).toBe('unkn…
    [90m 35|[39m     expect(trailMood(route({ activity: 'ferrata', viaFerrataScale: '3+…
    [90m   |[39m                                                                                   [31m^[39m
    [90m 36|[39m   });
    [90m 37|[39m   it('esclude le homepage CAI/SAT scambiate per schede singole', () =>…

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[2/2]⎯[22m[39m


[2m Test Files [22m [1m[31m1 failed[39m[22m[2m | [22m[1m[32m25 passed[39m[22m[90m (26)[39m
[2m      Tests [22m [1m[31m2 failed[39m[22m[2m | [22m[1m[32m226 passed[39m[22m[90m (228)[39m
[2m   Start at [22m 11:47:51
[2m   Duration [22m 9.79s[2m (environment 80%, tests 6%, import 6%, transform 5%, worker 4%)[22m

[2mEnvironment [22m [33mjsdom was created 26 times[39m[2m · 19.92s total, 80% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m


::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeEditorial.test.ts,title=src/lib/routeEditorial.test.ts > editoriale Cima Becco > separa difficoltà CAI e tag umoristici,line=28,column=59::AssertionError: expected 'MERENDEROS' to be 'Due curve e spiana' // Object.is equality%0A%0AExpected: "Due curve e spiana"%0AReceived: "MERENDEROS"%0A%0A ❯ src/lib/routeEditorial.test.ts:28:59%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeEditorial.test.ts,title=src/lib/routeEditorial.test.ts > editoriale Cima Becco > non attribuisce a una ferrata una difficoltà se manca la scala,line=35,column=83::AssertionError: expected 'AVAMBRACCI IN LEASING' to be 'Strattona' // Object.is equality%0A%0AExpected: "Strattona"%0AReceived: "AVAMBRACCI IN LEASING"%0A%0A ❯ src/lib/routeEditorial.test.ts:35:83%0A%0A
~~~

## Ultimi messaggi build
~~~

> cima-becco@0.1.0 build
> tsc --noEmit && vite build && node scripts/build_seo.mjs

[36mvite v8.3.0 [32mbuilding client environment for production...[36m[39m
transforming...
✓ 191 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                 3.30 kB │ gzip:   1.37 kB
dist/assets/maplibre-gl-worker-CNLXcz58.js    508.54 kB
dist/assets/PlannerPage-D2ttDcd0.css            5.12 kB │ gzip:   1.66 kB
dist/assets/AlpineAtlasPage-DPoL260a.css        6.43 kB │ gzip:   1.92 kB
dist/assets/maplibre-gl-CKRTiAqP.css           82.86 kB │ gzip:  10.71 kB
dist/assets/index-CTSQ7QhS.css                197.39 kB │ gzip:  37.19 kB
dist/assets/constants-50oENZrn.js               0.11 kB │ gzip:   0.12 kB │ map:     0.22 kB
dist/assets/worker-BmWK89Hx.js                  0.13 kB │ gzip:   0.15 kB │ map:     0.69 kB
dist/assets/alpinePlaces-JMex8AZj.js            0.69 kB │ gzip:   0.48 kB │ map:     2.72 kB
dist/assets/MiniMap-CMVLP6aN.js                 1.43 kB │ gzip:   0.83 kB │ map:     4.09 kB
dist/assets/renderThumb-Y-sBQ7Wk.js             1.43 kB │ gzip:   0.89 kB │ map:     3.82 kB
dist/assets/mountainBasemap-oLlS8Voj.js         2.43 kB │ gzip:   1.13 kB │ map:     6.26 kB
dist/assets/AlpineAtlasPage-CIchw2Zk.js         9.37 kB │ gzip:   3.40 kB │ map:    27.34 kB
dist/assets/timeZoneCountries-GK1VZQgF.js      10.22 kB │ gzip:   3.58 kB │ map:    12.03 kB
dist/assets/PlannerPage-DsQsdohp.js            10.43 kB │ gzip:   4.27 kB │ map:    27.19 kB
dist/assets/MapView-gAFSdtTY.js                38.90 kB │ gzip:  12.59 kB │ map:   142.57 kB
dist/assets/venueGlyphs-DJfeYNKu.js           248.09 kB │ gzip:  67.31 kB │ map: 1,303.83 kB
dist/assets/index-DsT15aGz.js               1,498.54 kB │ gzip: 421.68 kB │ map: 3,527.01 kB

[32m✓ built in 1.23s[39m
SEO: 7,457 pages, sitemap with 7,458 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
7557
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
