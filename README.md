# Cima Becco

Atlante collaborativo delle montagne italiane, con mappe, cime e itinerari GPX. Il progetto è autonomo da [HillGPX](https://github.com/StarlightsJourney/HillGPX) ma ne utilizza il codice open-source con licenza **MIT**: vedere [LICENSE](LICENSE).

## Stato attuale (prima versione)

- Interfaccia React/TypeScript e cartografia MapLibre derivate da HillGPX, adattate al nome **Cima Becco**.
- Catalogo geografico GeoNames di cime italiane e parte delle aree alpine confinanti, distribuito in tile JSON.
- Pianificatore `#pianifica` con punti sulla mappa, routing BRouter, GPX e indicazioni per raggiungere la partenza.
- Catalogo pilota Dolomiti: 80 relazioni escursionistiche OSM importate (76 escursioni e 4 ferrate) al 27/11/2026. Il tracciato non certifica la sicurezza o percorribilità.
- Tre tipi di percorsi: **escursioni**, **trail running**, **vie ferrate**; ciclismo e MTB esclusi da UI, import e filtri.
- Schede itinerario predisposte per numero sentiero, difficoltà CAI/SAC/ferrata, gestore, fonti originali, foto e crediti.
- Percorsi salvati nel browser: **non sono ancora pubblicati** nella community.
- L'import diretto dei cataloghi INFOMONT CAI/SAT, le fotografie specifiche dei percorsi, la navigazione GPS follow e il backend collaborativo **non sono ancora attivi**. I dati CAI presenti in OSM non sostituiscono un import certificato del catasto originale.

## Pubblicazione GitHub Pages

Il sito principale è **https://www.cimabecco.it/**. La repository pubblica con `.github/workflows/deploy.yml` tramite **GitHub Actions**; in **Settings → Pages → Custom domain** deve essere impostato `www.cimabecco.it` e va abilitato **Enforce HTTPS** dopo il rilascio del certificato.

Il file `public/CNAME` contiene il dominio canonico ed è usato **dalla nostra build** per compilare Vite con base `/` e generare URL canonici, sitemap e anteprime. **Non configura da solo il Custom domain di GitHub Pages** quando la pubblicazione avviene tramite GitHub Actions.

DNS sul provider: creare `CNAME` per l'host `www` verso `matteocurro.github.io` (senza il nome della repo). Per raggiungere anche `cimabecco.it` senza `www`, configurare il dominio principale con record A/ALIAS per GitHub Pages; con entrambi corretti GitHub reindirizza automaticamente l'apex a `www`. Non puntare `www` direttamente a `www.cimabecco.it` o a un URL contenente `/cima-becco`.

Gli URL completi per rifugi, bivacchi, paesi e percorsi vengono pubblicati direttamente sotto il dominio principale, ad esempio `https://www.cimabecco.it/rifugi/<slug>/`.

Per il test locale:

```bash
npm ci
npm run typecheck
npm run build
npm run dev
```

Le app sono distribuite staticamente; il routing richiede un endpoint BRouter raggiungibile dal browser e autorizzato a essere utilizzato. Per un servizio pubblico stabile occorrerà un'istanza dedicata o un fornitore compatibile. Il servizio di prova può avere limiti, CORS o indisponibilità.

## Account e sicurezza

La connessione alla community originale HillGPX è **disattivata**. Non viene utilizzato il Supabase dell'autore. Per abilitare registrazioni, profili e pubblicazione condivisa è necessario creare un **nostro** progetto Supabase, configurare Auth e applicare le migrazioni RLS dopo verifica. Usare nel frontend solo la chiave publishable, mai `service_role`.

## Provenienza e licenze

L'elenco verificato delle sorgenti, i dettagli di import e le regole di qualità sono in [docs/FONTI_ESCURSIONISTICHE.md](docs/FONTI_ESCURSIONISTICHE.md). La mappa e le relazioni OSM/INFOMONT utilizzano ODbL, i contributi degli utenti hanno licenze distinte. Non considerare tutte le tracce CC BY 4.0.

- Software originale: HillGPX, MIT. Copyright e avvisi originali in [LICENSE](LICENSE).
- Cime: GeoNames (CC BY 4.0), dataset geografico indicativo, con possibili toponimi e quote da verificare.
- Cartografia: OpenFreeMap, OpenStreetMap e i rispettivi termini.
- Immagini: attribuzioni specifiche riportate nei metadati Wikimedia Commons.
- Sentieri CAI/SAT: **importazione non ancora eseguita**, da verificare per disponibilità, qualità e licenze.

Le tracce pianificate automaticamente non costituiscono una certificazione di percorribilità o sicurezza in montagna.

## Import automatico e stato

La pipeline incrementale [Import OSM routes](.github/workflows/import-osm-routes.yml) è configurata per due esecuzioni quotidiane (03:17 e 15:47 UTC) e acquisisce due celle italiane per esecuzione. Il piano conta **107 celle**; al completamento del primo passaggio rinnova quelle scadute dopo 45 giorni. Le tracce sono suddivise in file per area con al massimo 200 itinerari ciascuno, distribuiti dal sito soltanto al bisogno.

- [Checkpoint import](public/data/import-status.json) — ultime celle elaborate, aree e date.
- [Manifest itinerari](public/data/routes-manifest.json) — conteggi, parti disponibili e lookup dei permalink.
- [Guida pipeline e ripresa dagli errori](docs/IMPORT_PIPELINE.md) — configurazione, limiti e manutenzione.
- Il catalogo pilota routes.json contiene i primi 80 percorsi; il totale effettivo include anche i file routes-tiles/ prodotti progressivamente.

L'esecuzione iniziale del nuovo processo non è da considerare riuscita fino alla comparsa di celle completate nel checkpoint e di un workflow GitHub Actions verde.

## Roadmap

1. Collaudare il primo batch automatico e il deploy Pages, controllando i risultati cartografici.
2. Ampliare la copertura nazionale con la pipeline incrementale, poi passare a estratti Geofabrik per importazioni massive.
3. Collegare le schede CAI/SAT, qualità del tracciato, dislivelli, cime e rifugi ai percorsi.
4. Arricchire fotografie/descrizioni con metadati Wikidata e Wikimedia e attribuzioni.
5. Attivare Supabase per la community, il follow GPS e le funzioni di condivisione avanzate.


## Specifica funzionale e memoria del progetto

La documentazione canonica per i futuri sviluppi è [Dizionario dei metadati e dei layout](docs/MODELLO_METADATI_E_LAYOUT.md): elenca per tipologia tutti i campi da raccogliere, le fonti, il grado di attendibilità, le relazioni con le altre schede e i moduli UX/UI previsti. La [memoria operativa per gli sviluppatori](AGENTS.md) riassume le decisioni progettuali da rispettare e rimanda alle specifiche e all'[architettura dei componenti](docs/ARCHITECTURE.md).

Le importazioni di arricchimento e i dati sperimentali delle PR #7 e #8 **non** sono automaticamente inclusi nel catalogo pubblico: per ogni fonte occorre verificare la licenza, la qualità dei valori e l'assenza di duplicati prima dell'integrazione.
