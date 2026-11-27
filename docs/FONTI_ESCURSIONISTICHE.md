# Fonti escursionistiche e policy di importazione — Cima Becco

Aggiornato il 27 novembre 2026.

## Perimetro del prodotto

**Solo percorsi a piedi:** escursioni, trekking, trail running e vie ferrate. Nessun percorso MTB, cicloturismo o ciclismo su strada. Distinguere SEMPRE il sentiero (segmento della rete escursionistica) dall'itinerario (sequenza di segmenti): una relazione OSM non è necessariamente un itinerario chiuso né un percorso certificato.

## Fonti verificate

| Sorgente | Dati utilizzabili | Stato / licenza / limiti |
| --- | --- | --- |
| [CAI INFOMONT](https://www.cai.it/sentieri-e-rifugi/infomont/) | Geometrie e catasto REI, sentieri numerati, riferimenti CAI | **ODbL** dichiarata ufficialmente; obbligo di attribuzione CAI e OSM; portale/download da integrare e testare |
| [OpenStreetMap](https://wiki.openstreetmap.org/wiki/IT:Hiking) | Relazioni hiking, tracce, ref, operator, network, osmc:symbol, tratti con sac_scale, rifugi, acqua, accessi | **ODbL**; attivo import pilota Overpass; evitare bulk permanenti su endpoint condivisi |
| [OpenStreetMap – via ferrata](https://wiki.openstreetmap.org/wiki/Tag:route%3Dvia_ferrata) | Relazioni ferrata e scala via_ferrata_scale (se dichiarata) | ODbL; i soli GPX non descrivono adeguatamente difficoltà, esposizione o attrezzatura |
| [SAT – Mappa sentieri](https://www.sat.tn.it/sentieri/mappa-sentieri/) | GPX dei sentieri del Trentino e catasto locale | Dati aperti **ODbL** indicati dal gestore, scarico singolo GPX / dati da testare; utile per verificare e integrare OSM |
| [Sentiero Italia CAI](https://sentieroitalia.cai.it/faq/) | Schede tappe, GPX, quote, dislivelli, durata, descrizioni, foto, punti accoglienza | Disponibilità pubblica **non equivale** ad autorizzazione a copiare testi e fotografie; usare riferimenti e metadati, riprodurre solo materiali con licenza esplicita |
| [CAI Bergamo](https://www.caibergamo.it/geoportale/istruzioni) | Dettagli di sentieri e itinerari delle Orobie, difficoltà, tempi, descrizioni e GPX | Portale con servizi [ArcGIS](https://cartografia.globogis.it/arcgis/rest/services/CAI_Bergamo/CAI/MapServer); verificare licenza dei contenuti prima di importazione massiva |
| [Emilia-Romagna – REER](https://geoportale.regione.emilia-romagna.it/in-primo-piano/db-reer-news-lug-26) | Esportazioni GPX, GeoJSON, SHP, KMZ del DB regionale | Export confermato luglio 2026; controllare licenza specifica e fonte prima dell'uso |
| [Veneto – sentieri storici](https://dati.veneto.it/opendata/Sentieri_Storico_Culturali_e_Panoramici_del_Veneto) | Inventario sentieri e riferimenti a GPX/KML | Recuperare licenza dataset e risolvere collegamenti, non inferire che siano tutti CAI |
| [Wikidata](https://www.wikidata.org/) | Elementi di montagna, rifugi, luoghi, coordinate, identificativi esterni, riferimenti a Commons | Metadati CC0; collegare per ID e posizione, non per mera omonimia |
| [Wikimedia Commons](https://commons.wikimedia.org/wiki/Commons:Machine-readable_data) | Miniature, autore, pagina originale, licenza, geotag e crediti | Licenza **per singola foto**; preferire immagini del luogo identificato da ID, verificare metadati via imageinfo e associazione geografica |

## Schema operativo di un itinerario

Usare il modello Route in `src/types.ts`. I campi della geometria e delle stime (distanceM, gainM, lossM, elevationAvailable) **non** sono dati ufficiali CAI se non importati come tali.

- Identità: `slug` sorgente stabile, `name`, `activity` (`hike` | `trail` | `ferrata`), `sourceUrl`, `sourceUpdatedAt`, `licence`.
- Geometria: `coordinates`, `distanceM`, quote e profilo solo se attendibili; percorso incompleto rifiutato, mai collegato con linea retta fittizia.
- Segnaletica: `trailRef`, `caiTrailNumber` solo con attribuzione esplicita a CAI, `osmcSymbol`, `operator`, `network`.
- Difficoltà: `caiDifficulty` T/E/EE/EEA solo se la fonte la dichiara; `sacScale` e `viaFerrataScale` restano scale distinte, non convertire arbitrariamente.
- Descrizioni: `description` originale/sintesi dal dato verificato; `officialDescriptionUrl` verso la relazione del gestore senza copiare testi altrui.
- Contenuti multimediali: `photos[]` con `url`, `sourceUrl`, `author`, `license`, `caption`, provenance su ogni immagine. Una foto della cima non implica una foto lungo il sentiero.
- POI associati: rifugi, bivacchi, sorgenti, punti panoramici, parcheggi, fermate e punti di accesso: mantenere ID del POI e distanza dal percorso, non introdurre dati inventati.
- Sicurezza: condizioni attuali, chiusure, valanghe o meteo **non possono** essere dedotte dai GPX. Avvisi aggiornati solo da fonti ufficiali e con data.

## Processo di acquisizione

1. **Estrarre** per area e fonte, memorizzando identificativo, licenza, data e URL; piccoli batch da API pubbliche, estratti planet/regionali per import ricorrenti più grandi.
2. **Validare** geometrie con distanza massima dei gap, continuità, duplicati/fingerprint e restrizioni di accesso; escludere percorsi bici e sentieri dichiarati chiusi.
3. **Normalizzare** separatamente i metadati ufficiali e le stime calcolate; preservare `null` per valori non disponibili.
4. **Deduplicare** OSM/INFOMONT/SAT per ID di provenienza, confronto geometrico e numero sentiero; un itinerario può attraversare molti sentieri.
5. **Arricchire** con punti d'interesse, foto Commons con riferimento e licenza, Wikidata, e link alla scheda CAI/SAT.
6. **Pubblicare** il JSON statico su GitHub Pages per il catalogo; utilizzare Supabase solo per contributi, profili, recensioni e foto caricate dagli utenti.
7. **Riconciliare** gli aggiornamenti per ID sorgente, mantenendo versioni e log; rimuovere o segnalare tracce obsolete.

## Stato tecnico

- Pilota `scripts/import_osm_routes.py`: ricerca relazioni hiking/via_ferrata OSM nell'area dolomitica, legge tag di fonte, controlla continuità e deduplica per ID.
- Attivazione `.github/workflows/import-osm-routes.yml`. Confermare log GitHub Actions; non dare per acquisito un import finché il catalogo `public/data/routes.json` non contiene itinerari reali.
- La struttura delle foto di percorso è disponibile in `Route.photos`; il frontend può mostrarle con attribuzione. Upload diretti da utenti richiedono backend/moderazione Supabase, non attivi.
- Prima di una release pubblica: controllare autorizzazione a ridistribuire dataset derivati ODbL, attribuzioni visibili, qualità e avvisi di sicurezza.
