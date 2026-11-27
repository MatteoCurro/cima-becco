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
