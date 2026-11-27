# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `2fe76d1`

- installazione npm: **0**
- TypeScript: **0**
- build e SEO: **0**
- test Vitest: **0**

## Ultimi messaggi TypeScript
~~~

> cima-becco@0.1.0 typecheck
> tsc --noEmit

~~~

## Test di regressione
~~~

[90mstderr[2m | src/lib/auth.test.ts[2m > [22m[2mauth[2m > [22m[2mreports a route the fallback cannot delete instead of failing silently
[22m[39mhillgpx delete RPC unavailable, deleting row directly PGRST202 Could not find the function

 [32m✓[39m src/lib/auth.test.ts [2m([22m[2m23 tests[22m[2m)[22m[32m 180[2mms[22m[39m
 [32m✓[39m src/components/account.test.tsx [2m([22m[2m14 tests[22m[2m)[22m[33m 693[2mms[22m[39m
[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mmints a fresh token to revoke when none is held in memory
[22m[39mGoTrueClient@sb-unconfigured-auth-token:1 (2.117.0) 2026-11-27T13:33:44.475Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mclears the local link silently when no grant exists at Google
[22m[39mGoTrueClient@sb-unconfigured-auth-token:2 (2.117.0) 2026-11-27T13:33:44.480Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mdrops a held token before consenting so a relink re-consents
[22m[39mGoTrueClient@sb-unconfigured-auth-token:3 (2.117.0) 2026-11-27T13:33:44.485Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mkeeps the local link and reports failure when Google refuses the revoke
[22m[39mGoTrueClient@sb-unconfigured-auth-token:4 (2.117.0) 2026-11-27T13:33:44.489Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mwarms the GIS script on a status check so the Link click keeps its gesture
[22m[39mGoTrueClient@sb-unconfigured-auth-token:5 (2.117.0) 2026-11-27T13:33:44.494Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mcounts an already-dead grant (invalid_token) as revoked
[22m[39mGoTrueClient@sb-unconfigured-auth-token:6 (2.117.0) 2026-11-27T13:33:44.497Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mfalls back to the same-origin relay when Google is unreachable
[22m[39mGoTrueClient@sb-unconfigured-auth-token:7 (2.117.0) 2026-11-27T13:33:44.501Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

 [32m✓[39m src/lib/routeTime.test.ts [2m([22m[2m20 tests[22m[2m)[22m[32m 27[2mms[22m[39m
[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mtreats a relay-less host (dev, GitHub Pages) as unreachable
[22m[39mGoTrueClient@sb-unconfigured-auth-token:8 (2.117.0) 2026-11-27T13:33:44.511Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

 [32m✓[39m src/lib/googleHealth.test.ts [2m([22m[2m9 tests[22m[2m)[22m[32m 154[2mms[22m[39m
 [32m✓[39m src/lib/routes.test.ts [2m([22m[2m15 tests[22m[2m)[22m[32m 21[2mms[22m[39m
 [32m✓[39m src/lib/routeQuality.test.ts [2m([22m[2m17 tests[22m[2m)[22m[32m 30[2mms[22m[39m
 [32m✓[39m src/lib/rangeScale.test.ts [2m([22m[2m17 tests[22m[2m)[22m[32m 29[2mms[22m[39m
 [32m✓[39m src/lib/routeMatch.test.ts [2m([22m[2m9 tests[22m[2m)[22m[32m 13[2mms[22m[39m
 [32m✓[39m src/lib/moderate.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 15[2mms[22m[39m
 [32m✓[39m src/lib/tcx.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 47[2mms[22m[39m
 [32m✓[39m src/lib/routeAnalysis.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 18[2mms[22m[39m
 [32m✓[39m src/lib/routeEditorial.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 30[2mms[22m[39m
 [32m✓[39m src/components/AuthModal.test.tsx [2m([22m[2m3 tests[22m[2m)[22m[33m 405[2mms[22m[39m
 [32m✓[39m src/lib/regions.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 13[2mms[22m[39m
 [32m✓[39m src/lib/saved.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 11[2mms[22m[39m
 [32m✓[39m src/map/camera.test.ts [2m([22m[2m10 tests[22m[2m)[22m[32m 9[2mms[22m[39m
 [32m✓[39m src/lib/bookmarks.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/geolocation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 7[2mms[22m[39m
 [32m✓[39m src/map/collisions.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 14[2mms[22m[39m
 [32m✓[39m src/lib/alpineWeather.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 6[2mms[22m[39m
 [32m✓[39m src/lib/dom.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 30[2mms[22m[39m
 [32m✓[39m src/lib/username.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 7[2mms[22m[39m
 [32m✓[39m src/styles.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 6[2mms[22m[39m
 [32m✓[39m src/map/routeGeometry.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 34[2mms[22m[39m
 [32m✓[39m src/lib/elevation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 6[2mms[22m[39m
 [32m✓[39m src/lib/country.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 20[2mms[22m[39m
 [32m✓[39m src/lib/gpx.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 5[2mms[22m[39m

[2m Test Files [22m [1m[32m28 passed[39m[22m[90m (28)[39m
[2m      Tests [22m [1m[32m235 passed[39m[22m[90m (235)[39m
[2m   Start at [22m 13:33:41
[2m   Duration [22m 12.44s[2m (environment 81%, tests 6%, import 5%, transform 5%, worker 3%)[22m

[2mEnvironment [22m [33mjsdom was created 28 times[39m[2m · 25.85s total, 81% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m

~~~

## Ultimi messaggi build
~~~

> cima-becco@0.1.0 build
> tsc --noEmit && vite build && node scripts/build_seo.mjs

[36mvite v8.3.0 [32mbuilding client environment for production...[36m[39m
transforming...
✓ 203 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                                 3.30 kB │ gzip:   1.37 kB
dist/assets/maplibre-gl-worker-CNLXcz58.js    508.54 kB
dist/assets/PlannerPage-D2ttDcd0.css            5.12 kB │ gzip:   1.66 kB
dist/assets/alpineAtlas-Dvj1Lkxw.css           17.03 kB │ gzip:   4.15 kB
dist/assets/maplibre-gl-CKRTiAqP.css           82.86 kB │ gzip:  10.71 kB
dist/assets/index-G-PtgAfC.css                209.47 kB │ gzip:  39.43 kB
dist/assets/constants-50oENZrn.js               0.11 kB │ gzip:   0.12 kB │ map:     0.22 kB
dist/assets/worker-1XRq5ljg.js                  0.13 kB │ gzip:   0.15 kB │ map:     0.69 kB
dist/assets/MiniMap-BzNEq59I.js                 1.43 kB │ gzip:   0.83 kB │ map:     4.09 kB
dist/assets/renderThumb-CUoQhxM-.js             1.43 kB │ gzip:   0.89 kB │ map:     3.82 kB
dist/assets/mountainBasemap-oLlS8Voj.js         2.43 kB │ gzip:   1.13 kB │ map:     6.26 kB
dist/assets/SiteInsightsPage-D9QaXjr1.js        2.90 kB │ gzip:   1.35 kB │ map:     6.03 kB
dist/assets/PublicProfilePage-DBZfy-z6.js       3.14 kB │ gzip:   1.51 kB │ map:     7.46 kB
dist/assets/timeZoneCountries-GK1VZQgF.js      10.22 kB │ gzip:   3.58 kB │ map:    12.03 kB
dist/assets/PlannerPage-B72W98fi.js            10.39 kB │ gzip:   4.25 kB │ map:    27.19 kB
dist/assets/MapView-_ex2D8Gx.js                36.34 kB │ gzip:  11.94 kB │ map:   137.40 kB
dist/assets/AlpineAtlasPage-DHuHsvxH.js        36.95 kB │ gzip:  12.40 kB │ map:    88.08 kB
dist/assets/venueGlyphs-C2AurfwZ.js           249.45 kB │ gzip:  67.83 kB │ map: 1,307.75 kB
dist/assets/index-JUbKMGE4.js               1,508.24 kB │ gzip: 425.04 kB │ map: 3,546.69 kB

[32m✓ built in 1.58s[39m
[33m[plugin builtin:vite-reporter] 
(!) Some chunks are larger than 1500 kB after minification. Consider:
- Using dynamic import() to code-split the application
- Use build.rolldownOptions.output.codeSplitting to improve chunking: https://rolldown.rs/reference/OutputOptions.codeSplitting
- Adjust chunk size limit for this warning via build.chunkSizeWarningLimit.[39m
SEO: 9,442 pages, sitemap with 9,443 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
9557
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
