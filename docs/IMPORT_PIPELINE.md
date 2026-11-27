# Pipeline automatica degli itinerari — Cima Becco

## Architettura attiva

L'importazione non dipende da Supabase. Le geometrie OSM vengono acquisite da GitHub Actions in modo automatico; la pubblicazione rimane su GitHub Pages.

**Orario programmato**: 03:17 e 15:47 UTC, ogni giorno (GitHub Actions `schedule`; l'avvio può essere ritardato). Ogni esecuzione elabora al massimo **due celle geografiche da 1°×1°**, con una pausa tra le chiamate e retry prudente sui limiti di Overpass. Sono previste **107 celle** fra Alpi, Appennini, Sicilia e Sardegna, con priorità iniziale alle Dolomiti. A regime, le celle vengono riconsultate dopo 45 giorni. Non vengono inviate chiamate di rete se tutte sono aggiornate.

## Sequenza di una esecuzione

1. `tests/test_import_osm_routes.py` e `tests/test_harvest_routes.py` verificano parsing OSM, geometrie, attività pedonali, checkpoint e deduplica.
2. `scripts/harvest_routes.py` sceglie soltanto le prime celle non completate, oppure le più vecchie da aggiornare.
3. `scripts/import_osm_routes.py` interroga Overpass per le relazioni `route=hiking` e `route=via_ferrata`; non richiede token. Rifiuta lacune geometriche, percorsi fuori ambito e geometrie implausibili.
4. Ogni itinerario è associato stabilmente alla cella che contiene il centro della geometria. Le ripetizioni fra celle vengono eliminate per slug OSM.
5. I percorsi vengono suddivisi in file da **massimo 200 itinerari** (`public/data/routes-tiles/it_LAT_LON_XXX.json`); ogni geometria immutata non viene riscritta.
6. Il checkpoint `public/data/import-status.json` e il manifesto `public/data/routes-manifest.json` registrano l'avanzamento. I percorsi sono versionati in Git: un fallimento dell'import lascia intatti i dati pubblicati.
7. Il workflow committa gli aggiornamenti su `main`; l'evento GitHub `workflow_run` avvia il deploy Pages al termine dell'import riuscito.
8. Il frontend carica solo le celle vicine alla mappa in modalità Percorsi; i link condivisi usano la lookup dello slug, senza scaricare tutto il catalogo. Il build SEO genera pagine statiche a partire anche dagli shard.

## Dove controllare

- [Azioni di import](https://github.com/MatteoCurro/cima-becco/actions/workflows/import-osm-routes.yml) — verdi se il job è riuscito; rosse se API, test o commit hanno fallito.
- [Stato import](../public/data/import-status.json) — contiene `lastSuccess`, `lastArea` e conteggi per cella.
- [Manifest dei percorsi](../public/data/routes-manifest.json) — `completedTiles`, `plannedTiles`, `routeCount`, file di ogni area e lookup per permalink.
- [Workflow di pubblicazione](https://github.com/MatteoCurro/cima-becco/actions/workflows/deploy.yml).
- File di partenza `public/data/routes.json`: **80 percorsi del pilota**, mantenuti per compatibilità; i successivi vengono serviti dagli shard.

## Diagnosi delle vecchie lentezze

Il vecchio processo aveva un `--max-routes 80` fisso, interrogava sempre la stessa bbox e riscriveva un JSON monolitico. Non era pianificato, quindi non poteva proseguire senza un push al codice. Il nuovo flusso rimuove il tetto globale, evita il download completo dei dati sul client e registra il punto in cui riprendere. La velocità reale dipende anche dalla disponibilità delle API pubbliche e dalla frequenza dei cron GitHub.

## Limiti e fase successiva

Overpass è una risorsa comunitaria con limiti d'uso: per importazioni massive ricorrenti o milioni di segmenti si dovrà passare a **estratti OSM PBF Geofabrik** (aggiornamenti regionali) e `pyosmium`/Osmium, senza saturare Overpass. Il job attuale non importa ancora il catasto INFOMONT direttamente, né immagini o descrizioni del CAI: queste richiedono processi separati, verifiche di licenza e attributi di provenienza. Per le foto usare Wikimedia Commons, con ID del luogo, autore, licenza e pagina originale; non assumere che foto geolocalizzate vicine ritraggano il sentiero.

## Riavvio controllato

Da GitHub Actions → **Import OSM routes** → Run workflow è possibile lanciare un batch manuale. Se una richiesta fallisce, il checkpoint non viene avanzato nella repository: la successiva esecuzione programmata riprova la stessa cella. Non aumentare la frequenza senza verificare i limiti del provider. GitHub Actions può ritardare o perdere alcuni cron quando sovraccarico; i checkpoint impediscono duplicazioni anche se il cron viene ripetuto.
