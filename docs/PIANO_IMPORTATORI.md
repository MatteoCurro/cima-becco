# Cima Becco — piano di importazione e collegamenti

**Data:** 27/11/2026. **Stato:** roadmap operativa, nessun nuovo job di pubblicazione attivato.  
**Specifica superiore e vincolante:** [MODELLO_METADATI_E_LAYOUT.md](MODELLO_METADATI_E_LAYOUT.md). Il presente piano organizza i lavori e NON cambia la tassonomia o le regole canoniche.  
**UI:** [ARCHITECTURE.md](ARCHITECTURE.md); un solo sistema di ricerca, mappa, dettaglio e filtri.

## Regole operative

1. **Un importatore per volta**. Per ciascuno: schema/adapter fonte, test offline con fixture, pilot su campione reale, report anomalie/copertura, revisione e solo dopo schedulazione.
2. **La specifica canonica è la base minima, non un limite massimo.** Ogni importatore deve avere un registro completo e verificabile dei metadati, comprendendo attributi, foto, loghi/stemmi, webcam, storia, servizi, restrizioni, provenienza, legami e aggiornamenti temporali. Se esistono dati ulteriori utili, si propone prima l'estensione del modello canonico e poi si integra l'importatore; non si scartano informazioni solo perché la scheda non le mostra ancora.
3. **Raw → Normalization → Entity resolution → Graph → Quality gate → Publish**. Snapshot minimali immutabili e checksum, ID stabili, sourceIds, facts con unità/licenza/date/metodo e identità separate dai permalink.
4. **No merge per mera omonimia o distanza**. La riconciliazione fra fonti richiede ID o controllo di congruenza multiplo; i conflitti restano in coda di revisione.
5. **near ≠ passes_through ≠ accessible_from**. Distanze lineari e proiezioni sul tracciato non attestano passaggio, accessibilità, sicurezza, apertura.
6. Non cambiare URL live e non rendere indicizzabili schede G0/G1 solo perché esistono nel catalogo. Niente testi/foto inventati o copia di materiale senza licenza.
7. Separare l'archivio stabile da meteo, prezzi, aperture, chiusure, allerte e altri dati con TTL. Niente cron a frequenza alta su Overpass; incrementali a celle o PBF.
8. Riutilizzare gli attuali importer OSM e il frontend legacy: mai far scrivere due job sugli stessi file di destinazione.

## Sequenza e dipendenze

| Ordine | Importatore | Fonti e legami necessari |
| --- | --- | --- |
| **1, in sviluppo** | **Rifugi: normalizzazione baseline OSM** | Snapshot esistente; identità, facts, vicino a località/cime e percorsi, SEO invariata |
| 2 | Rifugi: riconciliazione/arricchimento ufficiale | CAI Unico Rifugi e SAT (diritti da validare): proprietà, gestione, letti, servizi, orari e conflitti |
| 3 | Bivacchi e ricoveri | OSM + CAI/SAT/enti; schema diverso dai rifugi, chiusure e dotazioni |
| 4 | Comuni | ISTAT ufficiale (codici, confini, popolazione datata), DAIT per sindaci |
| 5 | Frazioni/località/borghi | ISTAT località + OSM + Wikidata: located_in documentato, non ereditare dati comunali |
| 6 | Cime e gruppi | GeoNames, OSM, Wikidata; quote con fonte, storia e immagini specifiche |
| 7 | Passi, laghi, valli, sorgenti e altri POI | OSM/geoportali; distinguere potabilità da presenza acqua |
| 8 | Rete sentieristica fisica | OSM + CAI INFOMONT + SAT; nodi, segmenti e geometrie con continuità verificata |
| 9 | Itinerari giornalieri | Tracce e fonti gestori; tappe, estremi e intersezioni, profili/calcoli con metodo |
| 10 | Grandi trekking, Alte Vie e tappe | Fonti ufficiali CAI/SAT/altre; stage_of, previous_stage, next_stage; ufficiale ≠ algoritmico |
| 11 | Vie ferrate | Difficoltà su scala originale, attrezzature e restrizioni con fonte |
| 12 | Aree e falesie/settori | OSM/OpenBeta, niente duplicazione con OpenClimbing, relazione padre/figlio |
| 13 | Vie monotiro | OpenBeta/archivi autorizzati, chiodatura/spit/rinvii separati, gradi e soste |
| 14 | Multipitch/tiri/soste | Tiri realmente censiti, obbligatorio ≠ massimo, nessun tiro sintetico |
| 15 | Boulder | Area, blocco e problema, scale Fontainebleau/V separate da gradi sportivi |
| 16 | Palestre indoor | Sede fisica OSM + sito ufficiale, distinta da società FASI |
| 17 | Parchi, trasporti, accessi | Vincoli territoriali e periodi; permessi e percorrenza soltanto attestati |
| 18 | Persone, storia, immagini e archivi | Wikidata, archivi e Commons: legami documentati e media con diritti |
| 19 | Meteo, neve, webcam, restrizioni e avvisi | Feed ufficiali e meteo cache separati; data/quota/validità sempre |

Il resolver comune convertirà progressivamente i riferimenti delle entità non ancora importate in ID canonici mantenendo sourceIds, metodo e qualità del join; non richiederà nuovi layout.

## Pianificazione trasversale verificabile delle fonti

La [matrice di acquisizione e normalizzazione](MATRICE_ACQUISIZIONE_DATI.md) documenta 26 classi di risorse, sorgenti reali, prove PR #7/#8 e limiti (CAI diritti, SAT live 0, Webcam 0 stream). Il [registro sorgenti](../scripts/metadata_source_registry_v1.json) descrive **26 provider e tipologie di fonte**, con accesso, stato test, diritti, refresh e riuso del codice esistente. L'[audit automatico](../scripts/audit_metadata_spec_v1.py) analizza **206 enunciati di requisiti** delle sezioni 1–27 della Bibbia; queste non sono 206 proprietà normalizzate né 206 dati importati. I controlli offline sono in [test_metadata_spec_coverage_v1.py](../tests/test_metadata_spec_coverage_v1.py).

**Primo riuso operativo dell'audit:** [mapping CAI](../scripts/cai_refuge_field_map_v1.json) con 47 nomi di campo già incontrati nel pilota; 29 puntano a chiavi presenti nel registro dei 80 campi rifugio e 18 sono candidati di estensione da verificare rispetto alla Bibbia. L'[adapter CAI offline](../scripts/normalize_cai_refuge_v1.py) normalizza soltanto in staging locale riservato, senza API live, mantiene alternative e segnala nomi di campo sconosciuti senza esporne i valori; maschera chiavi sensibili, non lega automaticamente al rifugio OSM e blocca la pubblicazione in assenza di diritti verificati.

**Attenzione:** il mapping fonte→tipologia è un elenco di fonti candidate, non la prova che il provider possieda *tutti* i campi. Ogni sottocampo va mappato esplicitamente, testato su payload reale autorizzato e validato prima di promuovere il modulo di categoria.

### Avanzamento CAI R1/R2 verificato, 27/11/2026

Il riuso offline del campione PR #8 ha individuato **3 coppie CAI↔OSM da revisionare** su 80 record (Boé, Torrani, Fiamme Gialle); **0 fuse/0 relazioni CAI pubblicate**. Il resolver `reconcile_cai_osm_refuges_v1.py` controlla tipo struttura, nome, coordinate, quota se attestata, più geometrie in conflitto, record non pubblicati e false prossimità, con 13 test offline.

La sonda CAI limitata a quattro dettagli ha confermato **125 nomi di campo**, 119 valorizzati in almeno un record e **7 voci media**; unione con il pilota precedente: **127 chiavi**. Tutte sono classificate nel [catalogo campi CAI](../scripts/cai_pilot_field_inventory_v1.json): 47 con mapping ristretto di staging, **50 con proposta di normalizzazione individuale** nel [piano di revisione](../scripts/cai_unmapped_fields_review_plan_v1.json), 22 campi privacy/contratti/contatti bloccati, 8 riferimenti tecnici interni. Nessuna chiave osservata viene eliminata silenziosamente. La Bibbia minima supporta **80 metadati rifugio** tracciati.

`openingTime_contact` risulta `value=null` e `data=array` negli esempi reali: i dati strutturati sono **presenti ma ancora da interpretare**, non vanno qualificati come apertura corrente. L'ispezione delle chiavi interne in un singolo record ha rivelato `attributes`, `key`, `layout`; per il calendario definitivo serve il parsing documentato della struttura e del periodo. Le immagini CAI hanno i metadati tecnici della risorsa ma **nessuna licenza singola accertata** nel pilot, pertanto nessuna ripubblicazione.

La specifica REST ufficiale indica `/api/v1/shelters/updatedAt`: la prova delimitata ha trovato **764 chiavi interne numeriche e 764 timestamp ISO senza fuso orario**. Il planner offline [plan_cai_refuge_delta_v1.py](../scripts/plan_cai_refuge_delta_v1.py) gestisce delta, regressioni, ID interno↔CAI e tombstone senza cancellazioni automatiche; finché il fornitore non conferma il fuso, tali date **NON superano il controllo di import**. L'[adapter media](../scripts/normalize_cai_media_v1.py) conserva UUID/mime/riferimento CAI, mai URL o contenuto in artefatti; le sette immagini CAI osservate non hanno una licenza riutilizzabile verificata. Prima di un job ricorrente valutare checkpoint e idempotenza e soprattutto diritti di riuso. Report CAI pilota solo in artefatti temporanei di staging, non `public/data`.

## Importatore 1: rifugi da snapshot OSM

**Codice:** [import_refuges_v1.py](../scripts/import_refuges_v1.py) · **test:** [test_import_refuges_v1.py](../tests/test_import_refuges_v1.py) · **CI:** [workflow di staging](../.github/workflows/test-import-refuges-v1.yml).

**Input di sola lettura:** catalogo OSM preesistente in public/data/alpine-places.json (solo kind=rifugio), routes-manifest e shard effettivamente disponibili, peaks GeoNames. Nessuna API viene interrogata in questo pilot.

**Output di staging (non pubblico):** build/import-refuges-v1 con raw/osm-refuges-SHA256.json immutabile, refuges.json (entità canoniche), links.json (archi di prossimità percorso → rifugio), identity-registry.json, review.json e report.json. La CI carica solo un artefatto scaricabile; non riscrive public/data né esegue il deploy.

**Riconciliazione:** rifugio → borgo e rifugio → cima hanno solo near con distanza Haversine; un legacy route.stops produce un arco dal percorso al rifugio di tipo passes_near, usando la distanza dalla polilinea. Non significa accessibile, né attraversato, né che il percorso sia ufficiale. I link saranno risolti agli ID canonici dopo i rispettivi importatori.

**Trattamento dati:** lo storico capacity deriva indistintamente dai tag OSM beds o capacity: viene nominato capacityReported e non posti letto certificati. Le quote DEM legacy senza provenienza del raster non vengono attribuite a OSM. Gli opening_hours sono segnalazioni OSM, non prova dell'apertura corrente. La data generatedAt dello snapshot non è una verifica campo per campo; i retrievedAt non dimostrabili restano null. Media con attribuzione/licenza incompleta esclusi.


**Inventario minimo vincolante del rifugio:** [refuge_field_registry_v1.json](../scripts/refuge_field_registry_v1.json). Traccia campo per campo copertura, priorità, fonte e frequenza prevista. Il file di staging `field-coverage.json` mostra per ognuno la quantità effettivamente valorizzata, quanta è presente nel legacy ma non ancora validata e quanta manca. **Avere un campo in schema non equivale ad aver raccolto il dato**.

**Media come risorse autonome:** lo stesso rifugio può avere molte fotografie correnti e storiche, foto di interni, esterni e panorami, stemma/logo istituzionale, video e più webcam. Le fotografie richiedono associazione al soggetto, data di scatto se nota, licenza, autore, URL della fonte e diritti per ciascun file; i loghi richiedono titolare e permesso. Le webcam richiedono posizione, orientamento, oggetto ripreso, operatore, permalink ufficiale, autorizzazione alla ripubblicazione dello still/stream, validità e stato: una webcam citata da una pagina non diventa uno stream live autorizzato. Tutto è collegato per ID della risorsa, non soltanto per nome o prossimità.

**Nella fase 1:** le foto già note con licenze ma soggetto non sufficientemente comprovato sono conservate in `mediaCandidates` come materiale **da verificare**, non pubblicate come `media`. Lo stesso meccanismo supporta loghi e webcam; la copertura non si azzera per assenza di un dato. L'acquisizione indipendente da Commons/Wikidata, siti ufficiali, archivi e portali webcam è una fase di arricchimento da implementare e provare all'interno della lavorazione dei rifugi, senza attendere un importatore multimediale globale a fine progetto. Non scraping indiscriminato delle immagini.

**Per le nuove fonti:** ciascuna sarà un adapter composabile sullo stesso entityId, con snapshot e licenza propri, senza sovrascrivere l'identità o l'URL stabilizzati da OSM. Ritmi di refresh indipendenti per immagini, news operative, webcam, meteo e metadati statici.

**Controllo duplicati:** nodi/edifici OSM con stesso nome entro 150 m, oppure lo stesso QID Wikidata entro 1 km, finiscono in review.json come candidati da verificare. Non vengono mai fusi automaticamente, neppure con lo stesso QID. Il caso del Rifugio Passo Lusia è già emerso nel pilota.

**Quality gate attuale:** G0, nessuna nuova pagina SEO; identità CAI/SAT ancora da risolvere. Slug parlante preliminare separato da slug alias e legacyUrl. Prima dell'automazione il registry va versionato e conservato, inclusi ID dismessi/tombstone, affinché una rinomina non cambi gli URL.

## Accettazione prima dell'importatore 2

- Tutti i test offline e il job CI verdi, errori di identità/duplicati bloccanti.
- Due esecuzioni dello stesso snapshot producono file con SHA-256 identico.
- Report quantitativo su tutti i rifugi pilota e analisi dei valori assenti e dei conflitti.
- Verifica manuale di almeno 10 rifugi eterogenei e di 10 collegamenti (nome, posizione, quota, licenza, distanza, assenza di affermazioni non provate).
- Registrazione dei conflitti e verifica di licenze e compatibilità dei permalink.
- Non si attiva una schedule né si pubblica un nuovo indice finché questi controlli non sono superati.

## Frequenze future (proposte, non attive)

Il numero N di aggiornamenti al giorno è **per fonte/tipologia** e sarà configurabile, non universale. Esempi iniziali da confermare: meteo/allerte ogni 3–6 ore se consentito dai feed; disponibilità e comunicazioni operative ufficiali 1–2 volte al giorno se esiste una fonte idonea; OSM in celle incrementali con revisita plurimensile o dopo alcune settimane; ISTAT, biografie e archivi quando il dataset cambia. Foto Commons in piccoli batch. Gli snapshot uguali (hash invariato) non creano nuovi commit; i refresh di meteo non ricostruiscono le pagine statiche.
