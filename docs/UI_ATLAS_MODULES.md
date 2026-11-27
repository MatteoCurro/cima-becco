# Frontend relazionale Cima Becco — contratto UI (fase grafica)

## Fonte e limiti

La fonte vincolante resta [MODELLO_METADATI_E_LAYOUT.md](MODELLO_METADATI_E_LAYOUT.md).
Questo file descrive **solo il consumo frontend** di record prodotti dagli importatori, senza
modificare pipeline, ID, deduplica, registry, SEO o pubblicazione. L'importatore Rifugi nella
PR #9 rimane indipendente e non va unito automaticamente per vedere la UI.

## Architettura

- Involucro del dossier: DetailLayout e griglia 42%/58% in cimaWorkspace.css; per le
  cime l'adattatore esistente cb-venue-grid conserva la stessa proporzione. Non duplicare
  mappe, SiteHeader, navigazione e route hover (profilo altimetrico → marker).
- Contenuto del dossier: AtlasDossierBlocks con placement alerts, core, connections,
  media, credits, definito in src/components/AtlasDossierBlocks.tsx. Non contiene
  griglie del workspace né decide la larghezza del main.
- Contratto tecnico src/lib/atlasDossier.ts: AtlasEntityMetadata opzionale per località,
  rifugi, bivacchi, cime e percorsi, o proprietà atlas per i grandi trekking legacy (il cui
  campo stages preesistente ha una struttura incompatibile). Le schede legacy funzionano
  senza questi campi e non creano pannelli vuoti.
- Filtri rifugi/bivacchi/paesi: AlpineExplorePage usa i campi legacy reali. Quota e
  capienza compaiono come faccette solo se almeno un record dispone del dato;
  attivarli esclude record con dato nullo, mai li equipara a zero.

## Contratti minimi per un adapter importato

1. facts è un dizionario tipizzato. value=null è dato ignoto,
   mentre 0 e false sono valori. Aggiungere unit, sourceId, sourceUrl, date e method.
2. relations[]: type dal vocabolario canonico, target.id stabile, target.name e
   href *solo quando l'URL è effettivamente risolto*. near è mera vicinanza;
   la UI non la presenta come percorso di accesso.
3. media[]: visualizzabile solo se subjectVerified + reuseAllowed e URL, fonte e
   licenza della singola risorsa. Il logo classico di AlpinePlace rimane autorizzato
   secondo il suo adapter esistente.
4. webcams[]: il collegamento ufficiale e l'operatore sono indispensabili;
   preview still solo con stillReuseAllowed e stillLicence. Mai dichiarare live
   in assenza di refreshedAt.
5. alerts[]: fonte e checkedAt obbligatori; la UI esclude quelli scaduti,
   mantiene gli avvisi validi in alto.
6. technical e pitches: solo record reali; bolts e quickdraws indipendenti;
   nessuna inferenza su lunghezza corde o ancoraggi. stages[]: il flag official
   deve provenire da una fonte, non da un algoritmo.
7. climate[]: periodo, unità, URL fonte e almeno sei mesi valorizzati;
   la vista attuale è una griglia mensile accessibile, non un grafico climatico
   completo. Non confondere previsione giornaliera con media climatologica.

## Prossimi collegamenti da attivare con i dati

Adattare il publish layer degli importatori ai nomi e tipi del contratto;
popolare sezioni meteo storico, webcam, foto, stemmi e storia *solo dopo* verifica
delle licenze e della qualità. Per falesie, vie e palestre: riutilizzare questi
moduli con faccette specialistiche, senza abilitare voci di navigazione prive di dati.

## Collaudi

TypeScript, Vitest, Playwright e scripts/check_css_layout.mjs + check_permalinks.
Regression suite: permeabilità full-width degli header, rapporto 42/58,
assenza di overflow a 320/390/768/1440, punto mappa ←→ profilo elevazione.
Per gli importatori, provare record completi, parziali, nulli e fonti scadute.


## Fase 2 — connessioni, navigation e fonti alternative

- src/lib/nearbyAtlas.ts: distanza ortodromica calcolata da coordinate reali. Non produce accessi
  né tratta la vicinanza come un percorso percorribile.
- src/components/NearbyAtlasPlaces.tsx: card verso permalink esistenti tra rifugi, bivacchi,
  località. Distanza dichiarata *in linea d'aria*, quota presente solo se censita.
- src/components/DetailJumpNav.tsx: indice orizzontale compatto della scheda locale.
  Resta nella colonna sinistra e non copre la mappa né modifica la griglia 42/58.
- src/lib/atlasFacets.ts: registro di faccette per webcam, Wi-Fi, defibrillatore, docce
  e animali; si attivano solo con almeno un fatto positivo e attribuito.
  Mai inventare lo stato aperto-adesso da valori non verificati.
- AtlasEntityMetadata: estensione opzionale con ID canonico, alias e toponimi,
  gerarchia amministrativa, source IDs, coordinate con metodo e precisione, fatti
  alternativi e restrizioni datate. In UI i dati contrastanti restano consultabili.
- AlpineAtlasPage: la navbar del catalogo trekking sta fuori dal main con padding.
  Le schede e i permalink conservano i loro CSS strutturali.
- Test WebKit: misura atomica e attesa dei nodi dopo il mount SPA, senza equiparare
  un nodo smontato a una larghezza nulla. Nessun workaround overflow-x:hidden.

### Casi da provare con i veri importatori

Record senza metadati, record con facts positivi/null/false, metadati conflittuali,
webcam senza licenza still, rifugio con service flags, borgo con amministrazione
documentata, foto e loghi con permessi per singolo file. Le faccette devono
scomparire quando nessun dato disponibile le giustifica.


## Rifugi CAI — profilo territoriale ricco e SEO (27/11/2026)

Componenti specialistici senza cambiare né il modello canonico né la griglia 42/58:

- `RefugeProfile.tsx` è l'adapter di presentazione per `AlpinePlace.kind === 'rifugio'`.
  Usa il `DetailLayout` comune; borghi, bivacchi, sentieri e trekking restano invariati.
- `RefugeGallery.tsx` usa `media[]` (fotografie correnti e storiche) e la foto
  legacy come fallback. Più immagini, miniature e crediti per singolo scatto,
  navigazione tastiera, niente auto-rotazione, deduplica per URL. Logo distinto
  dai media fotografici. Se manca una foto usa solo il fallback topografico.
- `refugeProfile.css` contiene esclusivamente componenti del profilo rifugio:
  nessun override di SiteChrome, nessuna seconda griglia mappa.
- `src/lib/refugeEditorial.js` è un modulo **puro condiviso** fra pagina React
  e `scripts/build_seo.mjs`. Compone testi coerenti da dati normalizzati
  e con provenienza documentata: quota, capienza, letti invernali, servizi.
  Non inventa storia, prezzi, disponibilità, accessi o apertura odierna.
- Sequenza: gallery → nome e riepilogo → apertura/pernottamento/contatti
  → servizi → itinerari con relazione vs semplicemente vicini → storia e geografia
  → meteo/acqua → dintorni → archivio dati residuali e fonti.
- I metadati presenti in `facts{}` vengono distribuiti nelle sezioni tematiche;
  il restante catalogo documentato resta consultabile nel dossier aggiuntivo,
  senza pubblicare tre volte lo stesso valore.
- Servizi `true`/ `false` restano distinti; `null` o senza fonte sono ignoti.
  `waterAvailableReported` NON prova `drinkingWater`.
- Le pagine SEO statiche leggono il medesimo release `refuges-v1.json`
  e aggiungono descrizione fattuale, servizi, letti invernali, foto secondarie,
  provenienza, eventuali dati storici. `LodgingBusiness` solo per rifugi
  con capienza documentata, altrimenti `Place`. Dati non documentati omessi.
  Nessuna garanzia di rich result Google.
- Il filtro `noindex` continua a proteggere le pagine CAI prive di sostanza
  editoriale, ma accetta dossier con almeno cinque fatti attribuiti anche senza foto.
- Verifica visiva a 320/390/768/1280 e CSS ownership. Non duplicare lo stato
  dell'app con testo SEO inventato: HTML statico e frontend usano un solo helper.

Riferimenti: W3C/WAI carousel APG
(https://www.w3.org/WAI/ARIA/apg/patterns/carousel/) e
Google Search Central immagini
(https://developers.google.com/search/docs/appearance/google-images).


## Rifugi — legami territoriali e permalink parlanti (fase 3, 27/11/2026)

Le pagine rifugio hanno un permalink pubblico `/rifugi/<nome-normalizzato>-cai-<id>/`
oppure `/rifugi/<nome-normalizzato>-osm-n-<id>/` in assenza dell'ID CAI.
L'ID finale evita collisioni per nomi uguali. **Non si cambia `AlpinePlace.slug`**,
che è l'identificativo storico utilizzato da tappe, GPX, tracciamento e cache.
La regola è condivisa tra React e SEO in `src/lib/placePermalinks.js`.
Il vecchio indirizzo `/rifugi/osm-…/` o `/rifugi/cai-…/` rimane disponibile
come pagina statica di trasferimento con canonical nuovo e `noindex,follow`.
GitHub Pages non offre redirect HTTP 301 sui singoli file: i vecchi URL usano
`meta refresh`; non promettere un codice di risposta 301.
Il catalogo, la navigazione fra schede e le pagine SEO di categoria usano il
nuovo permalink; i link storici continuano a trovare la scheda corretta.
I permalink degli altri tipi **non vengono migrati in questa fase**.

La riconciliazione dei nomi CAI con le pagine dei paesi è conservativa:
`src/lib/atlasConnections.js` usa valori documentati di
`municipalityNameReported` e `localityNameReported`; sceglie solo
l'unico record `borgo` con nome normalizzato identico e posizione entro
40 km (comune) o 12 km (località). Con omonimi compatibili, distanza maggiore
o fonte assente il toponimo resta testo non cliccabile. Un collegamento così
individuato è una corrispondenza di scheda territoriale, **non** una prova di
identità amministrativa formale, appartenenza o accesso escursionistico.
Il generatore statico e la pagina interattiva usano lo stesso algoritmo.

Le sezioni del profilo rifugio non ripetono un elenco uniforme di metadati:
la galleria introduce il luogo, l'ospitalità evidenzia i dati operativi,
i servizi sono distribuiti in capitoli (ristoro, connettività, dotazioni),
le località diventano un pannello narrativo e la storia valorizza
l'anno di costruzione se documentato. Le certificazioni ISO non sono mostrate.
Gli altri campi rimangono in un approfondimento espandibile con fonti.
La SEO statica conserva dati normalizzati significativi e link interni ai
rifugi, bivacchi, paesi e itinerari effettivamente indicizzati.

Regressioni da mantenere: URL storici con redirect, pagine canoniche
indicizzabili, mappa 42/58 invariata, passaggio comune/località solo
su match non ambiguo, falso vs ignoto nei servizi, CSS in file
specialistico e nessuna regressione negli slug GPX.


## Rifugi — gerarchia editoriale e Schema.org (rifinitura 27/11/2026)

Nel dossier rifugio i fatti principali non sono più tile con bordo, fonte
e aggiornamento ripetuti. `RefugeProfile.FactLines` rende una griglia
tipografica fluida di `dt` e `dd` con divisori sottili, gerarchia per
posti letto e valori economici, etichette leggibili e dimensioni responsive.
La provenienza **rimane nei dati normalizzati** e si consulta nella pagina centralizzata
`/fonti-e-crediti/`, che raccoglie anche le attribuzioni fotografiche e le
licenze per ciascuna risorsa. I campi tecnici residuali rimangono nell'archivio collassabile,
senza perdere qualità o attributi di provenienza. Non si altera la griglia
globale `DetailLayout` né i fogli di stile del chrome.

Servizi tri-state: i `true` vengono introdotti con «Servizi indicati come
disponibili», i `false` con «Servizi indicati esplicitamente come non
disponibili» e la spiegazione «la fonte riporta No», mentre `null` non
produce un'affermazione. Acqua disponibile e potabilità restano separate.
Questo vale anche per la descrizione SEO HTML generata.

Schema.org: `src/lib/refugeStructuredData.js` centralizza l'arricchimento
JSON-LD delle pagine rifugio. `LodgingBusiness` viene usato solo se la
capienza è realmente documentata; in caso contrario `Place` conserva le
proprietà lecite. Campi pubblicati: `amenityFeature` con valori booleani
espliciti, `petsAllowed` quando dichiarato, `additionalProperty` per
posti letto totali/invernali e anno di costruzione con fonte, `identifier`
per ID CAI, `address` e `email` se documentati, `sameAs` per i siti
esterni noti, immagini e coordinate dalla scheda. `numberOfRooms` NON
è derivato dal numero di letti; nessun `availability`, orario corrente,
prezzo, valutazione o `aggregateRating` inventato. Non è promessa
l'assegnazione di rich result Google. Test unitari con valori `false`,
ignoti e dati senza attribuzione verificano il contratto.

Riferimenti: https://schema.org/LodgingBusiness e
https://developers.google.com/search/docs/appearance/structured-data/local-business.


## Bivacchi e rifugi — dossier condiviso (27/11/2026, fase UI)

Il rendering specialistico `RefugeProfile` viene riutilizzato anche per
`AlpinePlace.kind='bivacco'`, mantenendo l'involucro `DetailLayout` 42/58
e la mappa laterale con i collegamenti GPX. Il sottotipo di ricovero
(`fixed_bivouac`, `social_cabin`, `support_point`, OSM) è conservato:
il bivacco non viene presentato come rifugio custodito o ricettività commerciale.
Le regole d'accesso, le chiavi, l'utilizzo d'emergenza, la capienza e la
manutenzione hanno posizioni dedicate, **solo se documentate**.

`src/lib/hutEditorial.js` è il contratto comune fra pagina, dati strutturati
e HTML SEO. `HutServices` usa Font Awesome SVG già distribuiti localmente e
non introduce nuove dipendenze: i valori `true` hanno simbolo normale e
descrizione, i `false` lo stesso simbolo barrato da una diagonale con la
dicitura «Non disponibile», mentre `null`/mancante/non attribuito non viene
mostrato. Le dotazioni specifiche del bivacco (materassi, coperte, stufa,
gas, legna, servizi igienici) non vengono confuse con le caratteristiche di
un rifugio custodito. Non aggiungere una frase fissa sulla potabilità:
i valori di potabilità, se disponibili, rimangono campi distinti e il
riferimento centrale mantiene i dettagli della fonte.

Le descrizioni integrali, ove esistenti, compaiono **una sola volta in
apertura**; si evita la ripetizione sotto il blocco territoriale. Subito
sotto il titolo compaiono le varianti di nome documentate, con eventuale
lingua o carattere storico. Il registro `/fonti-e-crediti/` conserva
l'attribuzione integrale; le singole schede restano editoriali. Gli
approfondimenti residuali si aprono in un accordion con sottosezioni,
gruppi etichettati in italiano e righe tipografiche, non mini-card seriali.

I permalink dei bivacchi diventano parlanti come quelli dei rifugi: per
esempio `/bivacchi/bivacco-fiamme-gialle-cai-922005301/`; il percorso
`/bivacchi/cai-922005301/` è conservato con pagina statica di
trasferimento e `noindex,follow` (GitHub Pages non offre 301 diretti).
L'identificativo `AlpinePlace.slug` resta intatto per GPX e cache.

Lo schema SEO resta `Place` per bivacchi, con coordinate, tipologia
dichiarata, `alternateName` e `amenityFeature` solo per valori espliciti;
gli altri dati pertinenti vengono rappresentati tramite `PropertyValue`.
`LodgingBusiness` resta riservato ai rifugi che documentano ricettività.
La descrizione SEO completa compare all'inizio della pagina statica, come
nel frontend; la meta-description può essere abbreviata. Non inventare
apertura, prezzi, camere, occupazione, recensioni o servizi.

Regressioni: frontend e SEO condividono i nomi alternativi, i bivacchi
non perdono i vecchi URL, le schede OSM isolate non mostrano servizi
inventati, layout e foto non invadono la mappa, il blocco dati non
ripete descrizioni e gli extra sono strutturati per gruppo.
