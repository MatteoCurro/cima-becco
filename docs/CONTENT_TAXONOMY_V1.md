# Cima Becco — tassonomia contenuti e fonti v1 (studio + import pilota)

**Ambito:** atlante italiano e aree alpine confinanti. **Stato:** sperimentale; nessuna pubblicazione automatica. Non modifica i componenti UI esistenti.

## Regole comuni per tutte le entità

Campi condivisi: `id` stabile interno, `type`, `name`, `aliases[]` multilingue, `slug` parlante con disambiguazione geografica, `summary`, `description` originale con evidenze, `geo` (punto e opzionalmente area), `elevation`, `adminHierarchy`, `parentIds[]`, `relatedIds[]`, `sources[]`, `photos[]`, `quality`, `lifecycle`, `updatedAt`, `editorialStatus`.

**Ogni campo informativo sostanziale è un claim:** `value`, `source`, `sourceUrl`, `licence`, `retrievedAt`, `sourceUpdatedAt`, `validFrom`, `validUntil`, `method` (reported/derived/estimated), `confidence`. Valore assente `null`, non zero e non falso. Date e limiti non inventati.

**Identità:** OSM node/way/relation, Wikidata QID, GeoNames, ID ISTAT, CAI/SAT, identificativi federali e cataloghi specializzati conservati separatamente; lo slug non determina l'identità. Geometria non necessaria alla pagina SEO, ma può essere necessaria al motore geografico e di routing.

**Qualità editoriale:** `raw` → `linked` → `enriched` → `reviewed`; diversa da `safetyVerified` (che richiede evidenza specialistica recente). I dati locali/sicurezza superano per priorità le stime algoritmiche; conflitti conservati, non occultati.

## A. Luoghi, paesi e ambiente

| Entità | Dati principali | Fonti prioritarie |
|---|---|---|
| **Comune** | codice ISTAT, provincia, regione, superficie, quota centro, popolazione datata, demografia, toponomastica, storia, stemma, sindaco attuale e mandato, fonti istituzionali, meteo, clima e neve, media immagini, webcam, alpinisti documentati, montagne/rifugi/palestre vicine | ISTAT; DAIT; Wikidata/Commons; sito comune; Meteotrentino/ARPAV/Open-Meteo |
| **Frazione / borgo / località** | comune di appartenenza, toponimi italiani e locali, quota, eventuale popolazione subcomunale verificata, storia locale, luoghi di interesse, trasporti, servizi, webcam, meteo | ISTAT località 2021; OSM; Wikidata; archivi locali; Commons |
| **Cima / gruppo montuoso** | nomi, prominenza se disponibile, altitudine e metodo, catena/gruppo, geologia, prime ascensioni e alpinisti, itinerari di salita, vie, rifugi, periodi/condizioni, foto, panorami | GeoNames; Wikidata; CAI; OSM; Commons; fonti alpinistiche autorizzate |
| **Passo / forcella / lago / cascata / punto panoramico** | coordinate, quota, idrografia/geomorfologia, raggiungibilità, storia del nome, sentieri, rifugi, divieti e foto | OSM; Wikidata; geoportali; siti di parchi |
| **Personaggio montano** | identità, professione (guida/alpinista/chiodatore/scalatore/esploratore), nascita e morte, residenze documentate, ascensioni/aperture attribuite, rapporto col luogo, biografia e fonti | Wikidata; CAI; biografie documentali; archivi |
| **Meteo / clima / webcam** | rilevazioni orarie con riferimento stazione e quota, previsioni a 1h/1d, medie climatiche mensili con periodo, neve caduta vs manto, link webcam e timestamp, avvisi e validità | ARPA; Meteotrentino; Open-Meteo; enti pubblici; gestori autorizzati |

**Distinzione obbligatoria:** popolazione e sindaco appartengono al comune, non automaticamente alla frazione; altitudine DEM è stima; distanza in linea d'aria è diversa da distanza su sentiero.

## B. Sentieri e trekking

| Entità | Dati principali | Fonti |
|---|---|---|
| **Sentiero/rete** | nome, sigla/numero CAI/SAT, gestore, segnavia, classificazioni originali CAI/SAC, stato e chiusure datate, larghezza/superficie, quota, accessi, punti d'acqua, rifugi, fonte istituzionale | OSM relazioni hiking; CAI INFOMONT; SAT; geoportali |
| **Itinerario/escursione** | nome, area, partenza/arrivo, circuito o traversata, lunghezza, D+/D− stimati o ufficiali, quote, tempo indicativo con metodo, stagionalità, avvicinamenti, varianti, fonti e foto | OSM, CAI/SAT, contributi autorizzati |
| **Trekking lungo** | nome e denominazioni, ente promotore, storia, anno di apertura o ideazione se documentato, riconoscimento, logo con permesso, tappe ufficiali, regioni attraversate, lunghezza e quota totali verificati, rifugi e servizi, fonti delle varianti | portali ufficiali Sentiero Italia, Alte Vie, GR/ERA, SAT |
| **Tappa** | numero/ID, da/a, punti intermedi, lunghezza, tempi, dislivello, fonti ufficiali, rifugi, difficoltà, possibili varianti, collegamento alla tappa precedente e successiva | relazioni OSM `stage`, `superroute`, enti gestori |
| **Trekking algoritmico** | sequenza continua di archi pedonali verificati, giunzioni, soste, limiti per giornata, difficoltà massima, incertezze, algoritmo e versione | grafo OSM/CAI con routing; mai come “tappa ufficiale” |

## C. Arrampicata su roccia

**Gerarchia:** climbing area → crag/falesia → sector → route → pitch. Le vie monotiro non richiedono un record pitch artificiale. Una via può appartenere a parete/sottosettore/area; usare `parentId`, non join basati solo sul nome.

| Entità | Dati principali |
|---|---|
| **Area arrampicata** | nome, paesi/cime, crag e settori, quota prevalente, tipo roccia, accessi e servizi, storia dell'arrampicata, divieti |
| **Falesia / parete** | nome e varianti, coordinate, comune, elevazione, roccia, orientamento, altezza, stile (placca, verticale, strapiombo, tetto), presenza sole/ombra, stagione, accesso e parcheggio, lunghezza avvicinamento, numero vie censite, distribuzione gradi, manutentore se documentato, divieti, fotografie, topo con licenza |
| **Settore** | falesia madre, nome, orientamento proprio, ombra, avvicinamento, morfologia, roccia, lunghezza vie min/max, numero vie, gradi estremi, vincoli |
| **Via monotiro** | nome, indice parete, settore, grado originale e sistema, lunghezza sviluppata, stile (sport/trad/mixed/toprope), tipo chiodatura, numero ancoraggi intermedi, **rinvii consigliati dalla fonte** separati dagli spit, caratteristiche sosta, tipo protezioni integrative, corda raccomandata da fonte, quota base, inclinazione, storia, apritori, FA/FFA, richiodature, foto, topo autorizzata, criticità e restrizioni |
| **Via multipitch** | campi via + sviluppo totale, numero di tiri, grado massimo/obbligatorio, impegno, modalità protezione, corda singola/doppie ove documentate, relazione discesa, soste, itinerario d'avvicinamento, lista pitch ordinata |
| **Singolo tiro** | numero progressivo, grado *del tiro* in scala originale, sviluppo in m, stile, numero spit se documentato, **rinvii del tiro se documentati**, friend/dadi/protezioni aggiuntive, tipo sosta e caratteristiche, passaggi chiave testuali autorizzati, eventuali criticità |
| **Sosta** | tipo dichiarato, componenti riportati (catena, anello, golfare, fittoni…), possibilità di calata dichiarata, ultimo controllo riportato, fonte e limiti; mai certificare sicurezza automaticamente |
| **Boulder area / blocco / problema** | area, singolo blocco, linea, grado blocco originale (Font/V), altezza, atterraggio, crash pad *se indicati*, esposizione sole, qualità roccia, partenza seduta/in piedi, rischio evidenziato, accessi, divieti, foto e topo |

**Campi critici e conflitti:** `climbing:bolts` OSM è numero di ancoraggi in parete, non `quickdrawsRecommended`; `climbing:bolted` può riferirsi a distanza media fra ancoraggi o a yes/no. `anchorType` non è sinonimo di `safetyStatus`. Un grado non viene convertito in altre scale senza un'indicazione di derivazione. `pitchCount=1` non prova monotiro se la fonte manca.

**Sicurezza:** status `unknown` fino a verifica specialistica; closure/access restriction sempre con fonte, validità e ambito (falesia, settore o via). Non riusare foto topo e relazioni protette senza autorizzazione.

**Provenienza:** OSM (ODbL), OpenClimbing (export OSM ODbL), OpenBeta (dati CC0 esclusi media), guide e portali ufficiali come fonti editoriali con riuso da autorizzare, theCrag API solo previo accordo. Gare e accessi federativi non equivalgono a condizioni tecniche in parete.

## D. Strutture e servizi

| Entità | Dati principali | Fonti |
|---|---|---|
| **Rifugio** | nome, quota, proprietario e gestore distinti, stagione di apertura, orari/servizi, posti letto, contatti, modalità prenotazione, acqua/energia/ristoro, storia, foto con licenza, webcam, sentieri accesso, cime e falesie vicine | CAI Unico Rifugi; SAT; siti strutture; OSM |
| **Bivacco** | tipologia libero/gestito, quota, posizione, capienza, dotazioni, acqua, accesso, eventuali prenotazioni o regolamenti, manutentore e stato segnalato, foto | CAI/SAT, gestori, OSM |
| **Palestra arrampicata** | identità, coordinate, sport (boulder/lead/speed/toprope), metri parete, numero linee se noto, auto-belay, MoonBoard/KilterBoard, cambio tracciatura, orari, ingressi/abbonamenti, corsi, noleggio, accessibilità, contatti, servizi, logo e foto | OSM, sito ufficiale, elenchi FASI come supporto |
| **Impianto/trasporto/parcheggio** | tipologia, orario stagionale e prezzo se ufficiali, gestore, accessi, fermate, biglietteria, percorso fino ai POI | OSM; siti ufficiali; dataset mobilità |
| **Parco/area protetta** | confini, regolamenti, chiusure temporanee, nidificazione, tutela ambientale, accessi ufficiali | portali enti parco/istituzioni |
| **Notizia/avviso territoriale** | soggetto interessato, categoria, messaggio, validità, livello, fonte ufficiale, data ultimo controllo, stato | enti parco, CAI/SAT, comuni, gestori |

## Politica URL e SEO

Slug pubblici leggibili con disambiguazione solo quando necessaria: `/falesie/placche-di-baone-arco/`, `/falesie/placche-di-baone-arco/<settore>/`, `/vie/nome-via-placche-di-baone/`, `/trekking/translagorai/`, `/trekking/translagorai/tappa-1/`. Gli identificativi della sorgente stanno in `sources` e nell'accordion finale `Fonti e crediti` (non nello slug). Preservare link legacy tramite redirects/alias. Indicizzare soltanto contenuti informativi originali, non pagine template prive di dati.

## Fonti verificate per lo studio
- https://wiki.openstreetmap.org/wiki/Climbing
- https://wiki.openstreetmap.org/wiki/Climbing/Grading
- https://wiki.openstreetmap.org/wiki/Climbing/Gyms
- https://wiki.openstreetmap.org/wiki/Key:climbing:bolts
- https://wiki.openstreetmap.org/wiki/Key:stage
- https://openclimbing.org/export
- https://github.com/OpenBeta/openbeta-graphql
- https://openbeta.io/about
- https://www.thecrag.com/en/article/extend
- https://www.cai.it/sentieri-e-rifugi/infomont/
- https://www.sat.tn.it/sentieri/mappa-sentieri/
- https://www.gardatrentino.it/it/outdoor/climbing
- https://www.theuiaa.org/uiaa-co-authors-guide-to-installing-and-replacing-bolts-on-climbing-routes/

## Import sperimentale

`scripts/pilot_climbing_metadata.py` interroga OSM (Overpass) su una bbox di Arco, normalizza solo attributi metadata e genera un rapporto di copertura dei campi. Nessuna geometria di vie o tracce GPX viene importata e nessuna pagina viene pubblicata. Il job ha limiti, retry e conserva dati di origine per eventuale audit.
