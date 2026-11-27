# Cima Becco — Architettura atlante alpino

## Stato reale del prototipo (27 novembre 2026)

- Catalogo geografico **statico e versionato** su GitHub Pages: shard GPX per cella, `routes-manifest.json`, fotografie selezionate, rifugi e località. Non servono query al DB per leggere la mappa.
- Pilota **Dolomiti**: `alpine-places.json` contiene rifugi e paesi da OpenStreetMap; `alpine-water.json` contiene fonti e fontanelle con campo `potable: yes | no | unknown`.
- `stops` e `waterSources` sono associazioni **geometriche** con il tracciato, non attestazioni di accessibilità. Un rifugio o una fonte a 90 m in linea d'aria possono essere irraggiungibili o trovarsi oltre un salto di roccia.
- La cartografia in MapLibre usa TOPO/SAT. Punti d'interesse clusterizzati nel worker, etichette solo agli zoom utili; geometrie inattive semplificate e cached (fino a 600 punti), GPX selezionato sempre integrale.
- Il **meteo** Open-Meteo si interroga esclusivamente all'apertura di una scheda, per coordinate e con cache client (20 minuti). Le medie stagionali sono derivate dai dati giornalieri ERA5/Open-Meteo **2021–2025**, NON da una normale climatica trentennale; richiesta separata e caching a 30 giorni.
- Le **foto** entrano solo tramite relazione OSM `wikimedia_commons=File:` o P18 dell'entità Wikidata, con immagine e metadati licenza verificati su Commons. Il job procede a lotti di 75 candidati; è ammessa una scheda senza foto, mai una foto di un altro monte.
- Le pagine statiche `/rifugi/osm-…/` e `/borghi/osm-…/` hanno testi, fatti, JSON-LD, link alle tracce e azione verso la scheda interattiva. I valori meteo live non devono essere congelati nell'HTML indicizzato.

## Frontend: architettura dei dati

```text
Overpass / OSM             GeoNames / Wikidata / Commons
   |                           |
   v                           v
import_alpine_places.py    enrich_alpine_photos.py
import_alpine_water.py     (P18, license, author)
   |                           |
   +------------+--------------+
                v
     /public/data/*.json
                |
   +------------+-------------+
   |                          |
build_seo.mjs           React / MapLibre
pagine locali           atlas per categoria
JSON-LD, sitemap        meteo on demand
                         |
                    route tiles GPX
                         |
                  stops + waterSources
```

**Non introdurre un database solo perché esistono relazioni.** I join fra 4.000+ GPX, 2.000+ luoghi e migliaia di punti acqua si possono precalcolare durante l'ingest e distribuire come JSON per celle. Il browser carica solo i tile necessari. L'eventuale crescita verso centinaia di migliaia di segmenti porta prima a vector tiles **PMTiles/MVT**, non necessariamente a Postgres per il frontend.

## Quando serve un database

Serve un **nuovo progetto Cima Becco**, separato dai progetti U.Venice Transport, per:

1. autenticazione con profili e preferenze di privacy;
2. richieste di gestione dei rifugi, verifica manuale e deleghe revocabili;
3. attribuzione immutabile e verificata dei GPX pubblicati e dei download;
4. pubblicazione **opt-in** dei preferiti, privati per impostazione predefinita;
5. eventi aggregati e statistiche cross-device (con protezione anti-spam e retention).

**Preparazione, non distribuzione:** lo schema proposto è in `docs/SCHEMA_SOCIAL_ATLAS.sql`. Non è stato applicato: non esiste un progetto Supabase denominato Cima Becco fra quelli attualmente collegati. Non utilizzare o alterare progetti di altri prodotti.

L'attuale `auth.ts` ha già profili, login e carichi GPX; `saved.ts` tiene i preferiti nel browser e li sincronizza se un Supabase appropriato è configurato. Le nuove preferenze `cima_public_profiles` e le richieste `hut_claim_requests` hanno UI pronta ma dipendono dall'applicazione delle tabelle. I GPX vanno attribuiti dal proprietario della riga `routes.user_id` **lato server**, mai da `contributor` (testo modificabile dall'utente). I rifugisti possono proporre l'accesso, ma non auto-approvarsi.

Le statistiche di `#statistiche` sono **solo di questo browser** finché non si configura un backend: non sono classifiche globali e non vanno pubblicizzate come tali. Prima di raccogliere eventi anonimi serve un endpoint server rate-limited, retention definita e informazioni adeguate.

## Prestazioni, sicurezza e limiti

- MapLibre: clustering GeoJSON con Supercluster nativo nei worker. Riferimento: https://maplibre.org/maplibre-gl-js/docs/guides/large-data/
- Per eventuale distribuzione europea ad alto traffico, valutare Planetiler/Tippecanoe + PMTiles e CDN, anziché migliaia di DOM marker o GPX integrali sul thread principale.
- Acqua: `amenity=drinking_water` e `drinking_water=yes` indicano acqua segnalata come potabile su OSM, mai garanzia sanitaria; `natural=spring` da sola **non implica potabilità**. Riferimento: https://wiki.openstreetmap.org/wiki/Tag:amenity=drinking_water.
- Meteo: https://open-meteo.com/en/docs e https://open-meteo.com/en/docs/historical-weather-api . Controllare licenze e condizioni per l'uso non più sperimentale o commerciale.
- Le foto Commons non si cercano col nome generico della cima. Riferimenti: https://www.mediawiki.org/wiki/API:Imageinfo e https://www.wikidata.org/wiki/Property:P18 .
- Sorgenti OSM/ODbL e fotografi restano attribuiti nella pagina Fonti e crediti e nelle attribuzioni obbligatorie cartografiche.
- Non sottintendere che il meteo del rifugio sostituisca ARPAV, bollettini regionali o bollettini valanghe.

## Controlli prima di un rilascio

1. `python -m unittest discover -s tests -p 'test_alpine_*.py'`
2. `npm run typecheck` e `npm test -- --run`
3. `npm run build` per pagine statiche e indici
4. Verificare sul sito TOPO/SAT, cluster rifugi, marker acqua, schermata meteo, schede GPX, mobile.
5. Controllare che le automazioni foto, POI, acqua e GPX completino i commit senza conflitti; cadenzarle e mantenere checkout coerenti.
