# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `12ebdb9`

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
  File: [36m/home/runner/work/cima-becco/cima-becco/src/lib/routeAnalysis.test.ts[39m:1:22
[33m  1  |  import kluangGpx from "../../data/routes/kluang-district-trail-run.gpx?raw";
     |                         ^
  2  |  import ridgesGpx from "../../data/routes/southern-ridges-walk.gpx?raw";
  3  |  import { describe, expect, it } from "vitest";[39m
[90m [2m❯[22m TransformPluginContext._formatLog node_modules/vite/dist/node/chunks/node.js:[2m8393:39[22m[39m
[90m [2m❯[22m TransformPluginContext.error node_modules/vite/dist/node/chunks/node.js:[2m8390:14[22m[39m
[90m [2m❯[22m normalizeUrl node_modules/vite/dist/node/chunks/node.js:[2m26058:18[22m[39m
[90m [2m❯[22m node_modules/vite/dist/node/chunks/node.js:[2m26128:30[22m[39m
[90m [2m❯[22m TransformPluginContext.transform node_modules/vite/dist/node/chunks/node.js:[2m26094:4[22m[39m
[90m [2m❯[22m EnvironmentPluginContainer.transform node_modules/vite/dist/node/chunks/node.js:[2m8172:14[22m[39m
[90m [2m❯[22m loadAndTransform node_modules/vite/dist/node/chunks/node.js:[2m19634:26[22m[39m

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/4]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routeMatch.test.ts[2m [ src/lib/routeMatch.test.ts ][22m
[31m[1mError[22m: Failed to resolve import "../../data/routes/kluang-district-trail-run.gpx?raw" from "src/lib/routeMatch.test.ts". Does the file exist?[39m
  Plugin: [35mvite:import-analysis[39m
  File: [36m/home/runner/work/cima-becco/cima-becco/src/lib/routeMatch.test.ts[39m:1:22
[33m  1  |  import kluangGpx from "../../data/routes/kluang-district-trail-run.gpx?raw";
     |                         ^
  2  |  import ridgesGpx from "../../data/routes/southern-ridges-walk.gpx?raw";
  3  |  import hk2Gpx from "../../data/routes/hong-kong-trail-section-2.gpx?raw";[39m
[90m [2m❯[22m TransformPluginContext._formatLog node_modules/vite/dist/node/chunks/node.js:[2m8393:39[22m[39m
[90m [2m❯[22m TransformPluginContext.error node_modules/vite/dist/node/chunks/node.js:[2m8390:14[22m[39m
[90m [2m❯[22m normalizeUrl node_modules/vite/dist/node/chunks/node.js:[2m26058:18[22m[39m
[90m [2m❯[22m node_modules/vite/dist/node/chunks/node.js:[2m26128:30[22m[39m
[90m [2m❯[22m TransformPluginContext.transform node_modules/vite/dist/node/chunks/node.js:[2m26094:4[22m[39m
[90m [2m❯[22m EnvironmentPluginContainer.transform node_modules/vite/dist/node/chunks/node.js:[2m8172:14[22m[39m
[90m [2m❯[22m loadAndTransform node_modules/vite/dist/node/chunks/node.js:[2m19634:26[22m[39m

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[2/4]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routeQuality.test.ts[2m > [22mreal hiking routes
[31m[1mError[22m: No test found in suite real hiking routes[39m
[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[3/4]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routes.test.ts[2m [ src/lib/routes.test.ts ][22m
[31m[1mError[22m: Failed to resolve import "../../data/routes/kluang-district-trail-run.gpx?raw" from "src/lib/routes.test.ts". Does the file exist?[39m
  Plugin: [35mvite:import-analysis[39m
  File: [36m/home/runner/work/cima-becco/cima-becco/src/lib/routes.test.ts[39m:1:22
[33m  1  |  import kluangGpx from "../../data/routes/kluang-district-trail-run.gpx?raw";
     |                         ^
  2  |  import ridgesGpx from "../../data/routes/southern-ridges-walk.gpx?raw";
  3  |  import { describe, expect, it } from "vitest";[39m
[90m [2m❯[22m TransformPluginContext._formatLog node_modules/vite/dist/node/chunks/node.js:[2m8393:39[22m[39m
[90m [2m❯[22m TransformPluginContext.error node_modules/vite/dist/node/chunks/node.js:[2m8390:14[22m[39m
[90m [2m❯[22m normalizeUrl node_modules/vite/dist/node/chunks/node.js:[2m26058:18[22m[39m
[90m [2m❯[22m node_modules/vite/dist/node/chunks/node.js:[2m26128:30[22m[39m
[90m [2m❯[22m TransformPluginContext.transform node_modules/vite/dist/node/chunks/node.js:[2m26094:4[22m[39m
[90m [2m❯[22m EnvironmentPluginContainer.transform node_modules/vite/dist/node/chunks/node.js:[2m8172:14[22m[39m
[90m [2m❯[22m loadAndTransform node_modules/vite/dist/node/chunks/node.js:[2m19634:26[22m[39m

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[4/4]⎯[22m[39m


[2m Test Files [22m [1m[31m4 failed[39m[22m[2m | [22m[1m[32m22 passed[39m[22m[90m (26)[39m
[2m      Tests [22m [1m[32m196 passed[39m[22m[90m (196)[39m
[2m   Start at [22m 11:16:00
[2m   Duration [22m 9.70s[2m (environment 81%, tests 6%, import 5%, transform 5%, worker 3%)[22m

[2mEnvironment [22m [33mjsdom was created 26 times[39m[2m · 19.81s total, 81% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m

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

[32m✓ built in 1.15s[39m
SEO: 4,125 pages, sitemap with 4,126 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
4205
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
