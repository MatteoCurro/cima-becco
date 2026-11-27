# Cima Becco — Verifica compilazione

Verificato da GitHub Actions su commit: `d95b040`

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
[41m[1m FAIL [22m[49m src/lib/routeEditorial.test.ts[2m > [22meditoriale Cima Becco[2m > [22mnon inventa quota e panorami quando il DEM manca
[31m[1mAssertionError[22m: expected 'Il percorso si sviluppa nell’area Dol…' to match /479/[39m

[32m- Expected:[39m
/479/

[31m+ Received:[39m
"Il percorso si sviluppa nell’area Dolomiti orientali per circa 7,8 km."

[36m [2m❯[22m src/lib/routeEditorial.test.ts:[2m24:25[22m[39m
    [90m 22|[39m     const description = trailDescription(route());
    [90m 23|[39m     expect(description).toMatch(/7,8 km/);
    [90m 24|[39m     expect(description).toMatch(/479/);
    [90m   |[39m                         [31m^[39m
    [90m 25|[39m     expect(description).not.toMatch(/panoram|dislivello positivo stima…
    [90m 26|[39m   });

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[8/10]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routeQuality.test.ts[2m > [22melevation[2m > [22mholds an altimeter that jumps hundreds of metres in a second
[31m[1mAssertionError[22m: expected [ 'impossible-speed' ] to include 'implausible-elevation'[39m
[36m [2m❯[22m src/lib/routeQuality.test.ts:[2m118:44[22m[39m
    [90m116|[39m   it('holds an altimeter that jumps hundreds of metres in a second', (…
    [90m117|[39m     const { points, times } = walk(100, { stepS: 2, ele: (i) => (i ===…
    [90m118|[39m     expect(ids(assess({ points, times }))).toContain('implausible-elev…
    [90m   |[39m                                            [31m^[39m
    [90m119|[39m   });
    [90m120|[39m

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[9/10]⎯[22m[39m

[41m[1m FAIL [22m[49m src/lib/routeQuality.test.ts[2m > [22melevation[2m > [22mholds noise that climbs hundreds of metres per km
[31m[1mAssertionError[22m: expected [] to include 'implausible-elevation'[39m
[36m [2m❯[22m src/lib/routeQuality.test.ts:[2m123:44[22m[39m
    [90m121|[39m   it('holds noise that climbs hundreds of metres per km', () => {
    [90m122|[39m     const { points, times } = walk(400, { stepS: 5, degPerStep: 0.0000…
    [90m123|[39m     expect(ids(assess({ points, times }))).toContain('implausible-elev…
    [90m   |[39m                                            [31m^[39m
    [90m124|[39m   });
    [90m125|[39m

[31m[2m⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[10/10]⎯[22m[39m


[2m Test Files [22m [1m[31m6 failed[39m[22m[2m | [22m[1m[32m20 passed[39m[22m[90m (26)[39m
[2m      Tests [22m [1m[31m6 failed[39m[22m[2m | [22m[1m[32m190 passed[39m[22m[90m (196)[39m
[2m   Start at [22m 11:13:10
[2m   Duration [22m 10.15s[2m (environment 81%, tests 6%, transform 5%, import 5%, worker 3%)[22m

[2mEnvironment [22m [33mjsdom was created 26 times[39m[2m · 20.95s total, 81% of tracked time[22m
[2m            [22m [2mcreate it once per worker with [22m[33mpool: 'vmThreads'[39m[2m (keeps per-file isolation) or [22m[33misolate: false[39m[2m (shares it across files)[22m
[2m            [22m [2mlearn more: https://vitest.dev/guide/improving-performance#test-environments[22m


::error file=/home/runner/work/cima-becco/cima-becco/src/lib/auth.test.ts,title=src/lib/auth.test.ts > auth > asks for email confirmation when no session comes back,line=54,column=27::AssertionError: expected 'https://unconfigured.invalid/auth/v1/…' to contain 'redirect_to=https%253A%252F%252Fhillgpx.com'%0A%0AExpected: "redirect_to=https%253A%252F%252Fhillgpx.com"%0AReceived: "https://unconfigured.invalid/auth/v1/signup?redirect_to=http%253A%252F%252Flocalhost%253A3000"%0A%0A ❯ src/lib/auth.test.ts:54:27%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/auth.test.ts,title=src/lib/auth.test.ts > auth > emails a password-reset link to the canonical site,line=62,column=21::AssertionError: expected 'https://unconfigured.invalid/auth/v1/…' to contain 'redirect_to=https%253A%252F%252Fhillgpx.com'%0A%0AExpected: "redirect_to=https%253A%252F%252Fhillgpx.com"%0AReceived: "https://unconfigured.invalid/auth/v1/recover?redirect_to=http%253A%252F%252Flocalhost%253A3000"%0A%0A ❯ src/lib/auth.test.ts:62:21%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/auth.test.ts,title=src/lib/auth.test.ts > auth > logs in and stores the session,line=89,column=83::AssertionError: expected undefined to be 'tok123' // Object.is equality%0A%0A- Expected:%0A"tok123"%0A%0A+ Received:%0Aundefined%0A%0A ❯ src/lib/auth.test.ts:89:83%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeEditorial.test.ts,title=src/lib/routeEditorial.test.ts > editoriale Cima Becco > non inventa quota e panorami quando il DEM manca,line=24,column=25::AssertionError: expected 'Il percorso si sviluppa nell’area Dol…' to match /479/%0A%0A- Expected:%0A/479/%0A%0A+ Received:%0A"Il percorso si sviluppa nell’area Dolomiti orientali per circa 7,8 km."%0A%0A ❯ src/lib/routeEditorial.test.ts:24:25%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeQuality.test.ts,title=src/lib/routeQuality.test.ts > elevation > holds an altimeter that jumps hundreds of metres in a second,line=118,column=44::AssertionError: expected [ 'impossible-speed' ] to include 'implausible-elevation'%0A ❯ src/lib/routeQuality.test.ts:118:44%0A%0A

::error file=/home/runner/work/cima-becco/cima-becco/src/lib/routeQuality.test.ts,title=src/lib/routeQuality.test.ts > elevation > holds noise that climbs hundreds of metres per km,line=123,column=44::AssertionError: expected [] to include 'implausible-elevation'%0A ❯ src/lib/routeQuality.test.ts:123:44%0A%0A
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
dist/assets/worker-DOrDcHJP.js                  0.13 kB │ gzip:   0.15 kB │ map:     0.69 kB
dist/assets/MiniMap-DkXlScBe.js                 1.43 kB │ gzip:   0.82 kB │ map:     4.09 kB
dist/assets/renderThumb-DEm-JPye.js             1.43 kB │ gzip:   0.89 kB │ map:     3.82 kB
dist/assets/PlannerPage-CWswaVBW.js             8.27 kB │ gzip:   3.53 kB │ map:    21.85 kB
dist/assets/timeZoneCountries-GK1VZQgF.js      10.22 kB │ gzip:   3.58 kB │ map:    12.03 kB
dist/assets/MapView-B0SEk3ko.js                37.40 kB │ gzip:  12.08 kB │ map:   138.46 kB
dist/assets/venueGlyphs-DJfeYNKu.js           248.09 kB │ gzip:  67.31 kB │ map: 1,303.83 kB
dist/assets/index-BbET0uxG.js               1,494.64 kB │ gzip: 420.19 kB │ map: 3,520.46 kB

[32m✓ built in 1.19s[39m
SEO: 4,125 pages, sitemap with 4,126 URLs, robots.txt, llms.txt for https://matteocurro.github.io/cima-becco
~~~

## File del sito verificati
~~~
4205
~~~
- JSON pilota: presente
- Manifest percorsi: presente
- index: presente
