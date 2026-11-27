# Cima Becco — architettura applicativa e regole di sviluppo

## Invarianti

1. **Una scheda per risorsa, indipendente dalla provenienza.** Ricerca, elenco, mappa e link esterni convergono sullo stesso componente. L'anteprima non è una seconda scheda.
2. **URL assoluti alla root applicativa** attraverso `src/lib/navigation.ts`. Non concatenare `window.location.hash` a un permalink: genera URL da `BASE_URL`.
3. **Percorsi censiti e indicizzati:** `/route/:slug/` (file SEO statico + SPA); **percorsi della comunità:** `/#route/:slug` finché il sito resta su GitHub Pages senza pagine dinamiche. Entrambi montano `RoutePanel` completo nello stesso shell. **GPX solo locali:** anteprima/esplorazione, nessun permalink pubblico fittizio.
4. **Luoghi alpini:** `/rifugi/:slug/`, `/bivacchi/:slug/`, `/borghi/:slug/`; trekking `/trekking/:slug/`. I vecchi link `#venue/:slug` per le cime restano supportati.
5. **Un solo header:** `SiteHeader` in `SiteChrome.tsx` e ricerca `SiteSearch` per tutte le pagine; `exploreNavigation.ts` è l'elenco delle sezioni. Falesie e palestre future saranno categorie, non nuove varianti della navbar.
6. **Mobile:** nessun contenitore può ridursi a una colonna involontaria o superare la larghezza del viewport. Scheda itinerario = contenuti e mappa impilati, desktop = due colonne reali. I filtri della mappa appartengono all'esplorazione, non alle schede.

## Proprietà dei componenti

| Responsabilità | Componente / file | Regola |
| --- | --- | --- |
| Vista SPA e scelta route/view | `src/App.tsx` | Non costruire link manuali nei callback |
| URL, permalinks, navigazione | `src/lib/navigation.ts`, `src/lib/mapIntent.ts` | Intents transitori diversi dagli URL pubblici |
| Header, footer, menu | `src/components/SiteChrome.tsx` | Una sola istanza per pagina |
| Esplorazione sentieri | `RoutesList`, `MapView`, `FilterBar` | Anteprima del percorso sulla mappa |
| Scheda sentiero | `RoutePanel`, `src/routeDetail.css` | Stessi dati per anteprima e pagina completa; diversi contenitori |
| Schede rifugi, bivacchi, paesi e trekking | `DetailLayout`, `AlpineAtlasPage`, `AlpineExplorePage` | Sezioni opzionali sulla stessa griglia |
| Metriche e intestazioni | `DetailPrimitives.tsx` | No card informative duplicate per categoria |
| Cime legacy | `VenueDetail.tsx` | Compatibilità mantenuta; migrazione dedicata, senza riscrittura affrettata |

## Stili

- `styles.css`: reset e base;
- `design.css`: componenti storici della mappa e dell'esplorazione;
- `cimaSystem.css`: token e primitive condivise;
- `locationProfile.css`: dettagli locali;
- `routeDetail.css`: SOLO layout del documento itinerario, non duplicare le regole generiche di RoutePanel;
- `alpineExplore.css` / `alpineAtlas.css`: solo elementi specifici dei relativi cataloghi.

Una nuova categoria riusa shell, primitive, header e modelli di URL, con differenze di dati esplicite. Non aggiungere `!important` per risolvere un conflitto senza identificare la regola originale.

## Verifiche per ogni modifica

- `npm run typecheck`, `npm run test`, `npm run build` e `scripts/check_css_layout.mjs`;
- Playwright Chromium e WebKit su `main`, layout a 320, 375, 390, 768, 1024 e 1440 px;
- controllo **larghezza effettiva** di barra, stage, pannello e mappa, oltre al solo overflow;
- apertura di un percorso dall'esplorazione, click **VEDI SCHEDA COMPLETA**, verifica permalink e stesso titolo/dati;
- apertura diretta di `/route/osm-hiking-13956722/`, ricerca da URL con parametri `?utm_...` e successiva navigazione;
- percorsi della comunità e GPX locali: non produrre link SEO inesistenti;
- la prova WebKit headless non sostituisce completamente Safari iOS reale.

## Ambiti volutamente separati

La conversione completa del vecchio `VenueDetail` (cime) e il consolidamento radicale dei CSS storici non devono essere infilati in un fix di routing. Si affrontano con test comparativi dedicati: preservare recensioni, gallerie, ricerca e login.
