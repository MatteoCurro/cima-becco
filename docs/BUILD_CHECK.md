# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `3ec491b`

- installazione npm: **0**
- TypeScript: **2**
- build e SEO: **99**
- test Vitest: **0**

## Ultimi messaggi TypeScript
~~~

> cima-becco@0.1.0 typecheck
> tsc --noEmit

src/components/AlpineAtlasPage.tsx(81,46): error TS6133: 'places' is declared but its value is never read.
src/components/AlpineAtlasPage.tsx(132,9): error TS2322: Type '{ lng: number; lat: number; name: string; kind: "fontanella" | "sorgente" | "rubinetto"; potable: Potability; }[]' is not assignable to type '{ lng: number; lat: number; potable: boolean; }[]'.
  Type '{ lng: number; lat: number; name: string; kind: "fontanella" | "sorgente" | "rubinetto"; potable: Potability; }' is not assignable to type '{ lng: number; lat: number; potable: boolean; }'.
    Types of property 'potable' are incompatible.
      Type 'string' is not assignable to type 'boolean'.
        Type 'string' is not assignable to type 'boolean'.
~~~

## Test di regressione
~~~

[90mstderr[2m | src/lib/auth.test.ts[2m > [22m[2mauth[2m > [22m[2mreports a route the fallback cannot delete instead of failing silently
[22m[39mhillgpx delete RPC unavailable, deleting row directly PGRST202 Could not find the function

 [32m✓[39m src/lib/auth.test.ts [2m([22m[2m23 tests[22m[2m)[22m[32m 147[2mms[22m[39m
 [32m✓[39m src/components/account.test.tsx [2m([22m[2m14 tests[22m[2m)[22m[33m 561[2mms[22m[39m
[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mmints a fresh token to revoke when none is held in memory
[22m[39mGoTrueClient@sb-unconfigured-auth-token:1 (2.117.0) 2026-11-27T16:44:38.527Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mclears the local link silently when no grant exists at Google
[22m[39mGoTrueClient@sb-unconfigured-auth-token:2 (2.117.0) 2026-11-27T16:44:38.536Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mdrops a held token before consenting so a relink re-consents
[22m[39mGoTrueClient@sb-unconfigured-auth-token:3 (2.117.0) 2026-11-27T16:44:38.544Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mkeeps the local link and reports failure when Google refuses the revoke
[22m[39mGoTrueClient@sb-unconfigured-auth-token:4 (2.117.0) 2026-11-27T16:44:38.555Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mwarms the GIS script on a status check so the Link click keeps its gesture
[22m[39mGoTrueClient@sb-unconfigured-auth-token:5 (2.117.0) 2026-11-27T16:44:38.559Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mcounts an already-dead grant (invalid_token) as revoked
[22m[39mGoTrueClient@sb-unconfigured-auth-token:6 (2.117.0) 2026-11-27T16:44:38.561Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mfalls back to the same-origin relay when Google is unreachable
[22m[39mGoTrueClient@sb-unconfigured-auth-token:7 (2.117.0) 2026-11-27T16:44:38.563Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

[90mstderr[2m | src/lib/googleHealth.test.ts[2m > [22m[2mgoogleHealth link/unlink[2m > [22m[2mtreats a relay-less host (dev, GitHub Pages) as unreachable
[22m[39mGoTrueClient@sb-unconfigured-auth-token:8 (2.117.0) 2026-11-27T16:44:38.569Z Multiple GoTrueClient instances detected in the same browser context. It is not an error, but this should be avoided as it may produce undefined behavior when used concurrently under the same storage key.

 [32m✓[39m src/lib/googleHealth.test.ts [2m([22m[2m9 tests[22m[2m)[22m[32m 121[2mms[22m[39m
 [32m✓[39m src/lib/routeTime.test.ts [2m([22m[2m20 tests[22m[2m)[22m[32m 19[2mms[22m[39m
 [32m✓[39m src/lib/routes.test.ts [2m([22m[2m15 tests[22m[2m)[22m[32m 25[2mms[22m[39m
 [32m✓[39m src/lib/rangeScale.test.ts [2m([22m[2m17 tests[22m[2m)[22m[32m 17[2mms[22m[39m
 [32m✓[39m src/lib/routeQuality.test.ts [2m([22m[2m17 tests[22m[2m)[22m[32m 16[2mms[22m[39m
 [32m✓[39m src/lib/routeMatch.test.ts [2m([22m[2m9 tests[22m[2m)[22m[32m 10[2mms[22m[39m
 [32m✓[39m src/lib/moderate.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 15[2mms[22m[39m
 [32m✓[39m src/lib/tcx.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 41[2mms[22m[39m
 [32m✓[39m src/lib/routeAnalysis.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 25[2mms[22m[39m
 [32m✓[39m src/lib/routeEditorial.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 28[2mms[22m[39m
 [32m✓[39m src/components/AuthModal.test.tsx [2m([22m[2m3 tests[22m[2m)[22m[32m 300[2mms[22m[39m
 [32m✓[39m src/lib/regions.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 11[2mms[22m[39m
 [32m✓[39m src/map/camera.test.ts [2m([22m[2m10 tests[22m[2m)[22m[32m 13[2mms[22m[39m
 [32m✓[39m src/lib/saved.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 8[2mms[22m[39m
 [32m✓[39m src/lib/bookmarks.test.ts [2m([22m[2m7 tests[22m[2m)[22m[32m 9[2mms[22m[39m
 [32m✓[39m src/lib/geolocation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 12[2mms[22m[39m
 [32m✓[39m src/lib/alpineWeather.test.ts [2m([22m[2m4 tests[22m[2m)[22m[32m 5[2mms[22m[39m
 [32m✓[39m src/map/collisions.test.ts [2m([22m[2m6 tests[22m[2m)[22m[32m 18[2mms[22m[39m
 [32m✓[39m src/lib/dom.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 21[2mms[22m[39m
 [32m✓[39m src/lib/username.test.ts [2m([22m[2m5 tests[22m[2m)[22m[32m 5[2mms[22m[39m
 [32m✓[39m src/styles.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 4[2mms[22m[39m
 [32m✓[39m src/map/routeGeometry.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 30[2mms[22m[39m
 [32m✓[39m src/lib/elevation.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 4[2mms[22m[39m
 [32m✓[39m src/lib/country.test.ts [2m([22m[2m3 tests[22m[2m)[22m[32m 10[2mms[22m[39m
 [32m✓[39m src/lib/gpx.test.ts [2m([22m[2m2 tests[22m[2m)[22m[32m 3[2mms[22m[39m

[2m Test Files [22m [1m[32m28 passed[39m[22m[90m (28)[39m
[2m      Tests [22m [1m[32m235 passed[39m[22m[90m (235)[39m
[2m   Start at [22m 16:44:36
[2m   Duration [22m 10.29s[2m (environment 80%, tests 6%, import 6%, transform 5%, worker 3%)[22m

[2mEnvironment [22m [33mjsdom was created 28 times[39m[2m · 21.22s total, 80% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m

~~~

## Ultimi messaggi build
~~~
TypeScript non superato
~~~

