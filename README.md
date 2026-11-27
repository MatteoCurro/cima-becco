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

La repository contiene il workflow `.github/workflows/deploy.yml`. In **Settings → Pages** selezionare **GitHub Actions**. Il build pubblica il sito su `https://matteocurro.github.io/cima-becco/`.

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

## Roadmap

1. Concludere il test di deployment e pulire riferimenti non pertinenti all'Italia.
2. Attivare il nostro Supabase, con account, percorsi pubblici/privati e moderazione.
3. Importare i dataset CAI/SAT/OSM, con deduplicazione e provenienza.
4. Aggiungere il follow GPS, i pacchetti mappa offline e gli avvisi di deviazione.
5. Arricchire cime e località con Wikidata, Wikipedia e Commons e pubblicare pagine SEO di qualità.
