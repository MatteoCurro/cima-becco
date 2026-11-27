# Cima Becco — matrice di acquisizione e normalizzazione

**Stato:** piano tecnico in staging, 27/11/2026. **Specifiche sovraordinate:** [Bibbia](MODELLO_METADATI_E_LAYOUT.md) e [architettura UI](ARCHITECTURE.md). Questo piano non riduce i requisiti della Bibbia: ogni nuovo campo significativo deve essere definito anche lì prima della realizzazione.

**Registro sorgenti machine-readable:** [metadata_source_registry_v1.json](../scripts/metadata_source_registry_v1.json). **Controllo completezza:** [audit_metadata_spec_v1.py](../scripts/audit_metadata_spec_v1.py). **Registro rifugi (80 campi):** [refuge_field_registry_v1.json](../scripts/refuge_field_registry_v1.json). **Roadmap:** [PIANO_IMPORTATORI.md](PIANO_IMPORTATORI.md).

## 1. Cosa è stato davvero verificato: non ripetere i test

L'audit ha utilizzato gli artefatti reali delle PR sperimentali [#7](https://github.com/MatteoCurro/cima-becco/pull/7), [#8](https://github.com/MatteoCurro/cima-becco/pull/8) e della [#9](https://github.com/MatteoCurro/cima-becco/pull/9). Un job riuscito prova che il programma termina, NON necessariamente che l'API risponda con dati live.

| Sorgente | Risultato già testato | Da riusare | Blocco residuo |
|---|---|---|---|
| OSM/Overpass | Import OSM live in main, 1.748 POI nel pilota Val di Fassa, 150 oggetti climbing Arco (82 vie) | import_alpine_places.py, import_osm_routes.py, pilot_geography_pois.py, pilot_climbing_metadata.py | ODbL, quote/rapporto, PBF per bulk; niente doppia scrittura |
| CAI Unico Rifugi | OpenAPI 3, elenco 80 su totale API 764, 4 dettagli con 64–99 field entries e media[] | pilot_cai_api_access.py, pilot_cai_batch_metadata.py | diritti di ripubblicazione non confermati; elenco non contiene i fields[] completi |
| SAT | 2 schede con sezioni storia, 18 tappe conservate in fixture | pilot_media_hut_history.py e pilot_sat_trekking_stages.py | **ultima lettura live: 0 tappe**, pagina non compatibile con parser; ricorrere a dataset ufficiale o correggere parser |
| Wikidata | 37 QID richiesti e restituiti; 24 quote, 25 immagini, 33 locatedInQid | pilot_place_weather_wikidata.py | qualificatori/dating; WD non equivale a ISTAT/DAIT |
| Commons | 6 immagini esaminate, 5 con URL licenza; arricchimento foto già esiste in main | enrich_alpine_photos.py e relativo test | riuso per immagine, soggetto verificato; P18 non certifica diritti |
| OpenBeta | 64 record, 10 boulder, 45 con gradi | pilot_openbeta_metadata.py, relativi test | schema licenze e singoli media, sentinel -1, match con OSM |
| Meteo | 2 località con forecast e storico solo 2025 | pilot_place_weather_wikidata.py, weather client | nessun precipitato/neve storica nei due casi; quota e modello; uso commerciale |
| DAIT / ISTAT | CSV DAIT 7.783 righe, intestazione aggiornata nel campione al 24/08/2026; cataloghi ISTAT consultati | pilot_admin_biography_webcams.py | codici a sei cifre, dataset demografici e licenze ancora da integrare |
| Webcam | 3 portali HTTP 200 | pilot_admin_biography_webcams.py | **0 singole webcam/feed autorizzati estratti** |
| Rifugi normalizzati | 436 ID, 909 proximity links, 80 campi pianificati, 8 foto candidate | import_refuges_v1.py e test PR #9 | CAI/SAT, diritti, 0 logo e 0 webcam nello snapshot; G0 |

Riferimenti ufficiali da cui partire: [CAI REST](https://rifugi.cai.it/api/documentation), [INFOMONT](https://www.cai.it/sentieri-e-rifugi/infomont/), [SAT](https://www.sat.tn.it/sentiero-italia/), [Commons metadata](https://commons.wikimedia.org/wiki/Commons:Machine-readable_data), [codici ISTAT](https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/), [GeoNames](https://www.geonames.org/about.html), [OpenBeta](https://docs.openbeta.io/introduction/overview/), [Open-Meteo Terms](https://open-meteo.com/en/terms). La disponibilità pubblica di un endpoint NON autorizza automaticamente copie e ridistribuzione.

## 1.1 Aggiornamento sui rifugi CAI: pilot controllato e riconciliazione

**Riuso del campione PR #8:** dagli 80 record CAI disponibili nell'artefatto `multi-domain-places-weather-history`, confrontati con 436 rifugi OSM normalizzati della PR #9, il resolver conservativo ha proposto **3 coppie** (Boé 0,8 m; Torrani 1,1 m; Fiamme Gialle 13,7 m). Richiede nome coerente (similarità token ≥0,75), distanza ≤250 m, quota compatibile quando *entrambe* le quote sono attestate e revisione della tipologia. Una falsa associazione a 946 m è scartata. **0 merge, 0 relazioni CAI↔OSM pubblicate**, il campione CAI non dichiara il tipo nel listato. Output `cai-osm-match-review.json` in staging, test in `test_reconcile_cai_osm_refuges_v1.py`.

**Sonda live limitata a quattro dettagli pubblici:** richiesta 27/11/2026 su ID già presenti nel precedente pilota; tutti e 4 HTTP 200, **83 / 116 / 110 / 76 field entries** e **1 / 1 / 2 / 3 media**. Unione delle 4 risposte: **125 nomi di campo distinti**, **119 con almeno un valore non vuoto**. Unione con PR #8: **127 nomi di campo da gestire**, analizzati in `scripts/cai_pilot_field_inventory_v1.json`: **47** con mapping di staging, **50** da interpretare, **22** bloccati per privacy/contratti/contatti, **8** identificativi interni. Lo snapshot contiene **nomi e tipi, MAI valori originali o URL media**; l'accesso API e l'esistenza di media NON costituiscono licenza di ripubblicazione.

**Problema tecnico risolto a livello di tracciamento:** nei quattro dettagli `openingTime_contact` ha `value=null` ma `data` di tipo array; il mapper conserva `sourceStructuredData.shape/length` e stato `structured_source_requires_parser`, senza confondere questo con orario assente o aperto ora. Un parser del calendario deve attendere la verifica della struttura effettiva del sottoarray, dei periodi di apertura e dei diritti.

**Incrementale verificato:** `GET /api/v1/shelters/updatedAt` restituisce un oggetto JSON con **764 chiavi numeriche** (ID interni del fornitore, NON da assimilare a `id_cai`) e **764 date ISO senza offset**. Il parser `plan_cai_refuge_delta_v1.py` è stato predisposto offline per differenze di revisione e nessuna cancellazione, ma **rifiuta queste date finché il fuso orario ufficiale non è determinato**. Non anticipare UTC o Europe/Rome. Un batch idoneo dovrà prima collegare gli ID interni al codice CAI, poi recuperare solo i dettagli modificati. Il probe `pilot_cai_detail_shapes_v1.py` misura nomi, tipi e presenza dei dati senza esportare valore, URL media o dati personali. Le quattro schede CAI producono sette media: `normalize_cai_media_v1.py` conserva soltanto UUID/format/identità fonte, senza original_url e con RIGHTS_BLOCKED. Prima di schedulare, provare timestamp e ID/variazioni, checkpoint, tombstone e gestione 429/5xx; non scaricare ciclicamente tutte le schede. L'API documenta media con `original_url`, ma non attribuzione/licenza per ogni immagine: restano candidate non pubblicabili.

La base OSM continua ad avere **80 campi rifugio predisposti**, compresi `waterAvailableReported` distinto da `drinkingWater` e `largeDormitoriesAvailableReported` distinto dal numero di posti letto.

## 2. Architettura di ingestione e pubblicazione

La pipeline unica è: source adapter limitato → raw snapshot versionato e SHA-256 → normalizzatore di tipo → registry ID e deduplicazione → grafo tipizzato → verifica campi/licenze/validità → staging con diff e report → publishing autorizzato per shard → adapter UI condiviso.

Ogni fatto usa **value, unit, sourceId, sourceUrl, licence, retrievedAt, sourceUpdatedAt, validFrom, validUntil, method, confidence, notes, rawValue**. Più fonti discordanti producono factsAlternatives, non cancellazioni silenziose. Distinguere almeno questi stati: PROPOSED, SOURCE_MAPPED, FETCHED, PARSED, IDENTITY_RESOLVED, VERIFIED, LICENSED, PUBLISHED; e gli esiti NOT_AVAILABLE, NOT_APPLICABLE, STALE, SOURCE_ERROR, CONFLICT_REVIEW, RIGHTS_BLOCKED. Una fonte testata NON conferisce lo stato FETCHED a tutti i campi che potrebbe contenere.

Per entità: ID interno stabile (indipendente dallo slug), sourceIds multipli e versionati, alias/permalink storici, nome in lingua, tipo, geometria WGS84 e metodo, fatti e provenienza, linked entities, media separati, restrizioni e quality G0–G3. I permalinks live non cambiano per un import. Supporre omonimia ≠ prova identità; un OSM way e un OSM node dello stesso edificio richiedono review.

Per relazioni: near con distanza in linea d'aria; passes_near con distanza dalla polilinea; passes_through solo geometria/topologia comprovata; accessible_from solo routing/fonte verificati; managed_by ≠ owned_by; stage_of, previous_stage, next_stage solo da tappa ufficiale o classificata algoritmo. Un sentiero è rete fisica; un itinerario è una sequenza di segmenti: non intercambiabili.

Per media: più immagini/stemmi/loghi/webcam/video per soggetto, ognuno con assetId, subjectId, autore, fonte, permesso/licenza e validità, foto storiche con **data dello scatto distinta dalla data di upload**. Webcam con operatore, coordinate, orientamento, target, URL ufficiale, timestamp still e permessi di embed/still; un link pubblico NON è una webcam live autorizzata. I media senza diritti sufficienti restano candidati e non entrano nel frontend.

Per misure e operatività: quota in m con fonte e metodo/DEM; numeri decimali e date con parsing locale; date/timezone esplicite; 0 ≠ false ≠ null; -1 se sentinella → null; capacità generica ≠ letti certificati; apertura dichiarata OSM ≠ aperto oggi; neve caduta ≠ altezza manto; media annuale 2025 ≠ normale climatica. Gradi arrampicata restano nelle scale dichiarate, spit ≠ rinvii consigliati.

Per copyright e prestazioni: snapshot e facts si conservano separati; un nuovo API/aggiornamento di stato non riscrive tutta la UI; nessuna copia di foto, topos o testi storici non autorizzati; nessun scraping aggressivo su Overpass o portali. Usare PBF per bulk geografico e TTL per feed meteo/live.

## 3. Piano per TUTTE le categorie del dizionario canonico

| Bibbia | Tipo | Fonti e strategia di valorizzazione |
|---|---|---|
| §2 Comuni | ISTAT codici/confini/demografia, DAIT amministratori, OSM/WD, archivi, Commons | Codice ISTAT stringa di 6 cifre, confine con validità, popolazione con data/perimetro, sindaco e mandato, stemma autorizzato, relazioni a località |
| §3 Località e frazioni | ISTAT località, OSM, WD, archivi/Commons | Parent municipality solo attestato; residenti subcomunali solo se disponibili, toponimi con lingua; niente eredità indebita di popolazione/sindaco |
| §4 Cime/gruppi | GeoNames, OSM, WD, DEM, archivi, Commons | Peak ≠ mountain range, quota con metodo, prominenza quando disponibile, prime ascensioni con fonte, collegamenti cime/vie/rifugi |
| §5 Passi, laghi e POI | OSM, geoportali, WD, enti parco | Sottotipi separati, superficie/profondità datate, sorgenti con yes/no/unknown sulla potabilità, passaggi e accessi con evidenza |
| §6 Rifugi | OSM → CAI list/detail → SAT/gestori → Commons/WD → webcam | Owner/manager distinti; mapping campo per campo CAI fields[], posti, servizi, prenotazione/orari; foto/galleria, logo, storia, webcam, collegamenti |
| §7 Bivacchi | OSM, CAI/SAT, proprietari | Emergenza/non gestito distinto da rifugio; dotazioni e disponibilità non garantita; revisione delle limitazioni |
| §8 Sentieri fisici | OSM PBF, CAI INFOMONT, SAT, catasti regionali | Network/ref/OSMC, geometria continua, grafo nodi/archi, chiusure e manutenzione datate, non confondere con escursioni |
| §9 Escursioni | Geometrie validate, rete, enti, media con diritti | Metriche ufficiali vs calcolate, dislivello con DEM, scale non convertite, source e POI vicino/attraversato |
| §10 Trekking lunghi | SAT, Sentiero Italia CAI, promotori | Trek padre, tappe ufficiali, storia, varianti, interconnessioni navigabili solo se continuità provata |
| §11 Tappe | SAT/CAI, gestori, grafo | Stage ID, ordine, inizio/fine, durata e dislivelli, next/prev, etichetta official/documented_variant/algorithmic; correggere lettura SAT live |
| §12 Ferrate | OSM, CAI/SAT, fonti specialistiche autorizzate | Scala originale, tempi di avvicinamento/via/discesa, attrezzatura dichiarata, restrizioni e storico non inventati |
| §13 Distretti climbing | OSM/OpenBeta, fonti locali | Area padre, crag, settori, boulder figli; conteggi vie solo delle risorse realmente censite |
| §14 Falesie | OSM/OpenBeta, OpenClimbing deduplicato | Tipo, roccia, esposizione, vie figlie, gradi distribuiti per scala, accessi e restrizioni |
| §15 Settori | OpenBeta/OSM/fonti autorizzate | Parent falesia certo, orientamento e vie del settore senza generazione artificiale |
| §16 Monotiro | OpenBeta, OSM, guide con permesso | Via, scala originale, bolts, quickdraws, anchor e lunghezze separati; no numero rinvii inferito |
| §17 Multipitch | OpenBeta, fonti autorizzate | Via padre e tiri censiti, grado massimo/obbligatorio distinti; topo solo con diritti |
| §18 Tiri e soste | Guide/archivi autorizzati | Ordine, lunghezza, protezioni, ancoraggio realmente dichiarati; non creare tiri dal solo pitchesCount |
| §19 Boulder | OpenBeta, OSM, guide con permesso | Area → masso → problema, scala Font/V distinta; accessi e rischio solo documentati |
| §20 Palestre | OSM/sito ufficiale/FASI | Impianto fisico ≠ associazione, servizi, discipline, orari, prezzi/validità e logo autorizzato |
| §21 Persone/storia | WD, archivi CAI, ICCD/Europeana, bibliografie | Date, first ascents, opere e foto con fonte; legami personali solo espliciti, non per appartenenza provinciale |
| §22 Parchi | Autorità parchi, geoportali, OSM | Confini/versione, zoning e divieti con territorio e periodo, accessi non dedotti dai poligoni |
| §23 Trasporti/accessi | GTFS, OSM, impianti e gestori | Fermata, linea e operatore, orari con validità, parcheggi e trailhead; vicino non significa raggiungibile |
| §24 Meteo/clima/neve | Open-Meteo, ARPA/stazioni | Time series, modelElevation, fuso/orari, neve caduta distinta dal manto, grafici con periodo e unità, TTL |
| §25 Foto/logo/webcam/video | Commons P18/P154, gestori, ICCD/Europeana, portali | Asset indipendenti, autore/diritti, data scatto, webcam direzione e permessi, sito sorgente se embed non concesso |
| §26 Avvisi | Ordinanze ed enti parco, autorità meteo, CAI/SAT | Alert ID, area/soggetti, authority, validFrom/Until, supersededBy; mostrare solo valido e confermato |
| §27 Community | Backend separato futuro, consenso | Recensioni, segnalazioni e media con moderazione, privacy e attribuzione; niente fusione automatica con fatti ufficiali |

Il **contratto comune §1** si applica a tutte le categorie, come pure UI §28 e quality §31. Lo script genera un elenco di tutti gli enunciati canonici ricavati da tabelle, elenchi e paragrafi delle sezioni §§1–27, con riga di origine, fonti candidate e suggerimento di normalizzazione. **Non** confondere enunciati (spesso contengono più campi) con singoli fieldKey: la scomposizione e il mapping puntuale devono essere ultimati prima del gate di ogni importatore. Un 100% di requisiti *pianificati* NON significa 100% di dati recuperati.

## 4. Ordine esecutivo, un importatore alla volta

**Passo trasversale corrente:** registro fonti e script di audit sul branch PR #9 senza network e senza publishing; controllare le sezioni della Bibbia e le prove esistenti.

**Chiudere prima i rifugi in sette sottostep, senza introdurre nuovi importatori di categoria:**
1. R0 (già fatto): baseline OSM, ID, sourceIds, route links, coverage rifugi, G0.
2. R1: **adapter CAI offline** sui JSON salvati PR #8, mappatura esatta di fields[] per 4 dettagli e normalizzazione tipi, null, boolean, numeri, date, con provenance.
3. R2: ricerca e risoluzione CAI↔OSM per ID o evidenze multiple, con review degli ambigui (Passo Lusia), nessun merge solo per coordinate/nome.
4. R3: integrazione SAT/gestori con informazioni di proprietà, storia, servizi, orari, prezzi, booking; licenza e timestamp per ciascun campo. Correggere il parser SAT live rispetto alla fixture.
5. R4: gallerie, loghi, stemmi e foto storiche da Commons/WD, riusando enrich_alpine_photos.py, con licenza e soggetto per file.
6. R5: webcam, verifica camere e autorizzazioni; collegamento per ID con direzione, target, timestamp, fallback a link ufficiale.
7. R6: report completezza e confitti, licenze, test incrementale, 10 schede + 10 link revisionati manualmente, G2/G3/SEO solo dove giustificato; poi schedule.

**Solo dopo** biforcazioni per Bivacchi, comuni, frazioni, cime e via via climbing in base alla roadmap. Ogni nuovo tipo riutilizza Facts, SourceRegistry, media e grafo, senza replicare motore mappa/search o cron writer.

## 5. Aggiornamenti N volte al giorno: per fonte, non per entità

- Previsioni e bollettini da API autorizzata: 3–6 ore oppure TTL specifico provider; quota, aggiornamento e massimali sempre verificati.
- Webcam autorizzate: TTL ed ETag del provider; nessuna copia di immagini se riuso non autorizzato.
- Orari/prezzi/segnalazioni: 1–2 volte al giorno **solo** se esiste feed ufficiale idoneo; in altri casi controllo meno frequente/manuale.
- OSM e reti: scansione geografica incrementale a celle, revisita a settimane e PBF per grandi volumi; non interrogare ogni cosa più volte al giorno.
- CAI/SAT/WD: updatedAt, pagination/ETag se disponibile, checkpoint e recupero solo delta; niente richieste su tutta la popolazione per ogni batch.
- ISTAT/DAIT, storia e libri: aggiornamento al nuovo rilascio/edizione; medie e serie datate.
- SEO: ricostruzione solo quando un fatto canonical verificato cambia; non rigenerare a ogni refresh meteo.

**Ogni job**: quality test → fetch limitato → raw hash immutabile → normalization → identity resolution → graph → audit licenze/date → diff e review → scrittura atomica → pubblicazione se autorizzata. Per 429/5xx non cancellare niente né avanzare checkpoint. Ogni provider ha limiti/retry e il solo importer autorizzato a scrivere i suoi file. Le PR #7/#8 restano in staging e la PR #9 rimane draft finché questi gate non sono approvati.

## 6. Gate e test da non ripetere

Riutilizzare test esistenti: OSM e geometrie, Haversine, route stopping, dedup, null e sentinelle, difficulty/bolts/quickdraws, parser SAT fixture, immagini Commons con match soggetto, build e UI.

Aggiungere soltanto: audit Bibbia sezioni 1–27, correttezza source registry e licenze, mapping CAI fieldwise, ID CAI↔OSM, liste multi-asset con permessi, timestamp di webcam/live, diff/retention e controllo dei campi pubblicabili. I test dell'audit sono offline e NON scaricano nuovamente OSM, CAI, SAT o Wikidata.
