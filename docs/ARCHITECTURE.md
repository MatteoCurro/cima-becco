# Cima Becco — Architettura dell'interfaccia e contratto dei contenuti

> Fonte operativa versionata. Ogni nuova tipologia di risorsa deve usare i componenti e i pattern elencati qui. Questa versione sostituisce le decisioni precedenti basate su layout differenziati e `max-width` arbitrari.

## 1. Obiettivo di prodotto

Cima Becco è un esploratore territoriale e cartografico, con risorse individuali raggiungibili da URL propri. La ricerca determina **cosa** si consulta; la struttura non cambia. I dati mancanti vengono mostrati come mancanti, mai inventati.

I principi adottati sono verificabili anche nelle linee guida di:
- Nielsen Norman Group, *Defining Helpful Filter Categories and Values* — https://www.nngroup.com/articles/filter-categories-values/
- Nielsen Norman Group, *User Intent Affects Filter Design* — https://www.nngroup.com/articles/applying-filters/
- Material, *Canonical list-detail layouts* — https://developer.android.com/develop/adaptive-apps/guides/canonical-layouts
- Mapbox, *Store Locator Web App* — https://docs.mapbox.com/help/demo-apps/store-locator-web-app/

Sono riferimenti per la struttura delle informazioni, non per duplicare loghi, estetica, servizi o codice delle piattaforme.

## 2. Due workspace; un sistema visivo

### Esplorazione
- `SiteHeader` include l'identità, ricerca globale e azioni; nessuna navbar specifica per tipologia.
- `ExploreNavigation` è l'unico selettore di categoria; `EXPLORE_CATEGORIES` in `src/lib/exploreNavigation.ts` è l'unico registro delle risorse, utilizzato anche dal menu `SiteChrome`. Prima riga: sentieri, cime, rifugi, bivacchi, paesi, trekking, future falesie e palestre. Seconda riga: faccette che dipendono dalla categoria scelta. Il menu generale `SiteChrome` rimane un punto di accesso, non una seconda navigazione delle faccette.
- Desktop: elenco e mappa affiancati, colonna elenco `42%`, restante mappa. Mobile: elenco/mappa alternativi, categoria e filtri a scorrimento orizzontale senza allargare il documento.
- `FilterBar` contiene le faccette escursioni/cime; `AlpineExplorePage` le faccette foto/recapiti/quota dei luoghi. Sono **adapter di dati** del medesimo schema `ExploreNavigation`, non nav indipendenti.
- Il click su un risultato localizza sulla mappa; `Apri scheda` apre l'URL canonico. Il dettaglio non mostra altri risultati sovrapposti alla mappa.

### Dettaglio
- Desktop: `--cb-detail-column:42%` contenuti a sinistra, `58%` mappa pertinente a destra, **senza limite globale di `max-width`** e senza pannelli informativi sopra la mappa.
- Mobile: due sezioni a larghezza piena; la posizione della mappa nella colonna verticale può essere adeguata al contesto, mantenendo hero, contenuti e cartografia disponibili.
- Ogni scheda locale ha una **hero fotografica** oppure fallback topografico dichiarato, titolo, metriche e **logo ufficiale solo se verificato e licenziato**. Mai assegnare una fotografia per mera somiglianza del nome.
- Il meteo, i contatti, i prezzi dichiarati, la storia e gli itinerari vicini stanno nell'editoriale e non dentro la mappa. La mappa contiene solo elementi effettivamente selezionati / pertinenti.

## 3. Componenti e singola responsabilità

| Componente | Responsabilità | Modifiche future |
| --- | --- | --- |
| `src/components/SiteChrome.tsx` | Un header/footer riutilizzabile; ricerca sempre disponibile | Niente header duplicati |
| `src/components/ExploreNavigation.tsx` | Registro categorie e filtri contestuali | Aggiungere categorie qui |
| `src/components/FilterBar.tsx` | Filtri di sentieri e cime | Mai ripristinare `mode-switch` alternativo |
| `src/components/AlpineExplorePage.tsx` | Adapter catalogo località OSM, filtri luoghi, lista+preview | Non duplicare un secondo Atlante |
| `src/components/AlpineAtlasPage.tsx` | Dossier `PlaceDetail`, trekking e collegamenti SEO legacy | Dati specifici nel template comune |
| `src/components/DetailPrimitives.tsx` | `DetailLayout`, `DetailMetrics`, `DetailFacts` | Sezioni opzionali, nessun nuovo layout |
| `src/components/RoutePanel.tsx` | Contenuti itinerario/GPX sia preview sia dettaglio | Varia solo la modalità `fullDetail` |
| `src/components/VenueDetail.tsx` | Dettagli cime con foto, recensioni e indicazioni esistenti | Hero+info+mappa con workspace comune |
| `src/components/AlpineAtlasMap.tsx` | Mappa località, rifugi, trekking e sentiero singolo con livelli acqua/GPX | Sovrapposizioni come dati, non nuove mappe |
| `src/components/MiniMap.tsx` | Mappa geografica della cima, con controlli cartografici | Solo POI selezionato |
| `src/App.tsx` | Router SPA, stato mappa avanzata, permalink itinerario | Non concentrare ulteriore UI qui |
| `src/lib/navigation.ts`, `src/lib/mapIntent.ts` | Costruzione URL canonici vs intenti transitori di ricerca | Nessun `window.location.hash = pathname` |

## 4. Stili: proprietà e limitazioni

| File | Proprietà |
| --- | --- |
| `src/styles.css` | Base originale ed elementi storici non ancora migrati |
| `src/design.css` | Componenti storici, non il nuovo workspace |
| `src/cimaSystem.css` | Variabili e primitive UI condivise |
| `src/cimaWorkspace.css` | **Unica proprietà** della griglia delle schede e della colonna cartografica `42/58`, anche per cime |
| `src/exploreNavigation.css` | Unico selettore categorie e filtri contestuali |
| `src/alpineExplore.css` | Lista, card e switch mobile del catalogo luoghi |
| `src/alpineMap.css` | Base della mappa località / acqua, importata dal componente mappa |
| `src/locationProfile.css` | Solo stile del contenuto locale, hero e contatti, niente struttura grid |
| `src/routeDetail.css` | Solo personalizzazione di `RoutePanel` nel dettaglio, niente layout duplicati |
| `src/alpineAtlas.css` | Solo presentazione dell'Atlante trekking / dati locali |

Le dimensioni delle colonne sono governate da **una variabile**, non da numeri diversi per pagina. Limitare la larghezza *del testo* può avere senso in articoli editoriali, ma non deve restringere il `main`, il documento o la mappa. Prima di qualsiasi nuova regola CSS verificare specificità e proprietà esistenti; non introdurre `!important` come fix rapido.

## 5. Identità, dati e URL

- `/route/:slug/` per sentieri censiti in build; `/#route/:slug` per percorsi della comunità finché non hanno prerender; GPX locali senza falso permalink pubblico.
- `/rifugi/:slug/`, `/bivacchi/:slug/`, `/borghi/:slug/` per tutte le voci del catalogo `alpine-places.json`; per borghi poco documentati file fisico disponibile ma `noindex,follow`. Questo impedisce link rotti senza creare SEO seriale ingannevole.
- `/trekking/:slug/` per itinerari a tappe. `#atlante/rifugi|bivacchi|borghi` viene ricondotto al catalogo unificato.
- Cime: manteniamo URL `#venue/:slug` e pagine `/place/:slug/` dove prerenderizzate; l'oggetto `VenueDetail` conserva metadati, foto, recensioni, favoriti. Una migrazione ulteriore degli URL richiede un progetto SEO separato.
- Acqua: `alpine-water.json` fornisce coordinate reali e potabilità OSM; `route.waterSources[].slug` è la relazione per abbinarli al percorso. Niente coordinate inventate, né codici OSM come unica modalità di fruizione. Marker cliccabili espongono nome e stato, non una garanzia di sicurezza.

## 6. Estensioni future

- **Falesia:** nuova tipologia geografica nel registro; scheda territoriale con foto verificata, map marker, numero vie, gradi, esposizione, roccia, accesso e disponibilità delle info, senza costruire un nuovo `DetailLayout`.
- **Palestra arrampicata:** località fisica con indirizzo, orari, contatti, servizi e geometria del luogo; struttura identica, faccette differenti.
- Separare sempre *metadata import*, *tipo di risorsa*, *faccette disponibili*, *renderer del dettaglio* e *sovrapposizioni mappa*.

## 7. Gate di rilascio

1. TypeScript, Vitest, Vite + SEO, check CSS, `scripts/check_permalinks.mjs` per ogni voce del catalogo (campione obbligatorio `borghi/osm-n-240044790/`).
2. Playwright Chromium e WebKit desktop/mobile alle larghezze 320, 375, 390, 768, 1024 e 1440 px; controllare larghezza reale di header, lista, pannello, mappa e `scrollWidth`.
3. Ricerca da home con `?utm...`, click scheda da esplorazione, permalink diretto, ritorno e ricerche da dettaglio, filtri contestuali e disattivazione categorie ancora prive di dataset.
4. Niente risorse false: assenza di foto/quote/potabilità/orari esplicita, attribution OSM/Commons conservata.
5. Non dichiarare "testati iOS Safari" se è stata eseguita solo la suite WebKit.

**Debito tecnico residuale separato:** eliminazione progressiva delle regole morte dentro il corposo `design.css` e `styles.css`, da guidare con analisi delle dipendenze e test browser. Non rimuovere funzionalità che ancora vi si appoggiano.
