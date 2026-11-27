# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `729457d`

- installazione npm: **0**
- TypeScript: **2**
- build e SEO: **99**
- test Vitest: **1**

## Ultimi messaggi TypeScript
~~~

> cima-becco@0.1.0 typecheck
> tsc --noEmit

src/map/mountainBasemap.ts(67,11): error TS6133: 'map' is declared but its value is never read.
~~~

## Test di regressione
~~~
     [32m✓[39m rende un nome sentiero generico leggibile senza inventare luoghi[32m 3[2mms[22m[39m
     [32m✓[39m non inventa quota e panorami quando il DEM manca[32m 15[2mms[22m[39m
[31m     [31m×[31m separa difficoltà CAI e tag umoristici[39m[32m 6[2mms[22m[39m
[31m     [31m×[31m non attribuisce a una ferrata una difficoltà se manca la scala[39m[32m 1[2mms[22m[39m
     [32m✓[39m esclude le homepage CAI/SAT scambiate per schede singole[32m 1[2mms[22m[39m
 [32m✓[39m src/lib/saved.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/map/camera.test.ts [2m([22m[2m10 tests[22m[2m)[22m[32m 6[2mms[22m[39m
 [32m✓[39m src/lib/bookmarks.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 9[2mms[22m[39m
 [32m✓[39m src/lib/geolocation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 14[2mms[22m[39m
 [32m✓[39m src/map/collisions.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 5[2mms[22m[39m
 [32m✓[39m src/lib/dom.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 24[2mms[22m[39m
 [32m✓[39m src/lib/username.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 5[2mms[22m[39m
 [32m✓[39m src/styles.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 4[2mms[22m[39m
 [32m✓[39m src/lib/elevation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 4[2mms[22m[39m
 [32m✓[39m src/lib/country.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 15[2mms[22m[39m
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
[2m   Start at [22m 11:36:35
[2m   Duration [22m 8.42s[2m (environment 79%, tests 6%, import 6%, transform 5%, worker 4%)[22m

[2mEnvironment [22m [33mjsdom was created 26 times[39m[2m · 17.20s total, 79% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m


::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeEditorial.test.ts,title=src/lib/routeEditorial.test.ts > editoriale Cima Becco > separa difficoltà CAI e tag umoristici,line=28,column=59::AssertionError: expected 'MERENDEROS' to be 'Due curve e spiana' // Object.is equality%0A%0AExpected: "Due curve e spiana"%0AReceived: "MERENDEROS"%0A%0A ❯ src/lib/routeEditorial.test.ts:28:59%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeEditorial.test.ts,title=src/lib/routeEditorial.test.ts > editoriale Cima Becco > non attribuisce a una ferrata una difficoltà se manca la scala,line=35,column=83::AssertionError: expected 'AVAMBRACCI IN LEASING' to be 'Strattona' // Object.is equality%0A%0AExpected: "Strattona"%0AReceived: "AVAMBRACCI IN LEASING"%0A%0A ❯ src/lib/routeEditorial.test.ts:35:83%0A%0A
~~~

## Ultimi messaggi build
~~~
TypeScript non superato
~~~

