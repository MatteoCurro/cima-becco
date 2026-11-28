# Cima Becco — piano di importazione e collegamenti

**Data aggiornamento:** 28/11/2026. **Stato verificato:** rifugi e ricoveri pubblicati; Comuni incrementali G2 pubblicati (111 al run 46108239132) e 258 profili persone G1 noindex; blocco 4 località ISTAT/OSM in pilota isolato PR #21, non pubblicato.  
**Specifica superiore e vincolante:** [MODELLO_METADATI_E_LAYOUT.md](MODELLO_METADATI_E_LAYOUT.md). Il presente piano organizza i lavori e NON cambia la tassonomia o le regole canoniche.  
**UI:** [ARCHITECTURE.md](ARCHITECTURE.md); un solo sistema di ricerca, mappa, dettaglio e filtri.

## Blocco 4 — rilascio verificato delle prime località G2 (28/11/2026)

- **Release su main completata:** [workflow #46117176744](https://github.com/MatteoCurro/cima-becco/actions/runs/46117176744), inclusi test Python, 292 test Vitest, TypeScript, build reale, verifica permalink e attribuzioni. Il catalogo `public/data/atlas/settlements-v1.json` contiene **14 schede G2**, tutte con QID/coordinate/fotografia Commons/licenza e testo verificato; nessuna entità G0/G1 è stata promossa.
- **Territorio ufficiale in archivio di staging:** 8.882 centri/nuclei tra Trentino-Alto Adige e Veneto, corrispondenze puntuali ISTAT 2021 complete con dati `POP21`, `FAM21`, `ABI21`, `EDI21`. Le entità restano separate dalle frazioni giuridiche salvo evidenza specifica. Le relazioni `near` a rifugi/ricoveri non dimostrano accessi.
- **Cursore corretto:** [PR #23](https://github.com/MatteoCurro/cima-becco/pull/23). Lo storico `import-history-localita-v1.json` conserva l'offset soltanto delle esecuzioni riuscite; ultimo batch verificato `offset=0`. Mai saltare lotti a causa di run falliti. Dopo 80 candidati verificati si prosegue con i successivi, tornando al primo dopo il lotto finale.
- **Concorrenza sicura:** [PR #24](https://github.com/MatteoCurro/cima-becco/pull/24) contiene unione per QID/ID/slug del catalogo G2, conservazione di foto storiche con autore/licenza/data, rifiuto dei conflitti d'identità, rebuild SEO/credits dell'unione e retry senza force-push; necessario perché altre Actions aggiornano `main` contemporaneamente.
- **Programmazione:** workflow `release-settlements-v1.yml` alle 06:10 UTC ogni giorno e all'occorrenza manualmente; solo cataloghi G2 pubblicati e report QA conservati. Sorgenti ufficiali ISTAT 2021 cache riutilizzata. Sono ancora arricchimenti futuri, non dati impliciti: figure collegate alla località esatta, foto storiche rigorosamente attribuite, popolazione aggiornata oltre il censimento 2021.

---

## Stato di preparazione alla produzione del blocco 4 (28/11/2026)

**Prima prova G2 su fonti reali:** 8 dossier eleggibili su 80 candidati Wikidata/OSM, con QID italiano, coordinate compatibili, P18 Commons, autore/licenza e estratto Wikipedia con QID corrispondente. Queste 8 schede erano ancora in **staging**, non pubblicate. 69.003 righe punti ufficiali ISTAT 2021 disponibili per georeferenziazione (EPSG:32632) e demografia di località con POP21/FAM21/ABI21/EDI21. La prova temporanea della build con 8 G2 ha superato 292 test unitari e la generazione di oltre 12.700 pagine SEO; il controllo permalink ha individuato l'assenza dei redirect legacy dei vecchi slug OSM. Correzione introdotta e test dedicati aggiunti: un errore in una prova NON equivale a una release superata.

**Sequenza di promozione:** il workflow di staging conserva raw G0/G1 in artifact, affianca fotografie storiche solo con soggetto e data originali e verifica il catalogo G2 mediante compilazione/frontend/SEO. Il workflow di release separato (`release-settlements-v1.yml`) verifica identità, qualità, sito, sitemap e URL, aggiorna poi `settlements-v1.json` e `import-history-localita-v1.json` con commit atomico. Pubblica solo se presente almeno un G2 valido; cron giornaliero alle 06:10 UTC, cache sorgenti territoriali 2021 e rotazione 80 QID ad esecuzione. Resta distinta la manutenzione del blocco Comuni per stemmi P94/P154 e fotografie storiche.

**Relazioni:** i punti ISTAT georeferenziati sono collegati con `near` ai rifugi e ricoveri già acquisiti (distanza in linea d'aria, mai accesso), `part_of` solo dal Comune ISTAT con riferimento 2021 e verifica delle eventuali riconciliazioni WD P131. Le persone sono legate con nascita P19 nell'abitato esatto, mai per appartenenza al Comune.

---

## Blocco 4 — località censuarie e borghi: pilota ISTAT 2021 + OSM (28/11/2026)

**PR di staging:** [#21](https://github.com/MatteoCurro/cima-becco/pull/21) · [adapter](../scripts/import_settlements_v1.py) · [registro campi](../scripts/settlement_field_registry_v1.json) · [test](../tests/test_import_settlements_v1.py) · [workflow](../.github/workflows/test-import-settlements-v1.yml).

**Perimetro:** Basi territoriali ISTAT 2021 (LOC_Rxx_21.csv negli ZIP regionali) e snapshot alpine-places.json con 1.857 elementi OSM etichettati «borgo». Pilota reale R04 Trentino-Alto Adige e R05 Veneto. Non riscaricare Overpass per normalizzare.

**Identità:** LOC21_ID = PRO_COM + COD_LOC. TIPO_LOC distingue centro abitato, nucleo abitato, località produttiva, case sparse. Soltanto i primi due sono candidati a schede. Centro censuario non significa frazione amministrativa; no sindaco, popolazione, superficie ereditati dal Comune.

**Grafo:** part_of verificato dal PRO_COM con vintage 2021 (solo per Comuni già catalogati); near Haversine, mai accessibilità. Non fondere elementi OSM e ISTAT per nome/distanza. Le persone vanno collegate al luogo esatto e non solo al Comune.

**Media e storia:** immagini con soggetto esatto, licenza e autore; per storiche data di scatto documentata. Lo stemma comunale non diventa automaticamente lo stemma della località. Il ciclo Comuni continua l'arricchimento stemmi, foto storiche e popolazione ISTAT datata.

**Gate:** output solo in build/import-settlements-v1 e artifact CI. G0/noindex fino a geometrie e reconciliation verificata e contenuto G2. Zero scritture in public/data, permalink e cron in questa PR. Test offline e pilota reale prima di promozione.

---

## Estensione Comuni — qualità territoriale, personaggi e osservatorio (28/11/2026)

**Gap documentato:** tutte le 19 schede Comuni inizialmente pubblicate avevano `quotaCentroM`, `elevationReportedM` e altimetria DEM assenti. Non è accettabile confondere livello G2 con completezza editoriale di tutti i P1.

**Altimetria e superficie:** fonte ISTAT [Altimetria Comuni 2021](https://www.istat.it/classificazione/principali-statistiche-geografiche-sui-comuni/) (xlsx pubblicato il 15/04/2026), codice `PRO_COM`, colonne **ALT MIN, ALT MAX** (riconosciute direttamente nella prova su dati reali). Sono *quote minime/massime del territorio comunale su DEM NASADEM*, non il livello del municipio o la quota del centro. Testata su 22 dossier G2 nel primo run: **22/22 ID riconciliati**, 44 nuove quote territoriali, 0 conflitti. Wikidata P2044 (metri Q11573) viene acquisita separatamente come `elevationReportedM`, non rinominata `quotaCentroM`; P2046 (km² Q712226) alimenta `superficieKm2` se unità verificata. Il valore della quota del centro resta vuoto finché non compare in una fonte adatta.

**Persone come grafo, non testo decorativo:** l'importatore di arricchimento `enrich_municipality_people_v1.py` utilizza solo Comuni con identità `ISTAT -> QID P635` verificata. Query di persone umane WD P31=Q5 con legami **P19 nascita nel Comune**, **P937 luogo di lavoro** o **P551 residenza storica per persone decedute**, controllati di nuovo sui claim dell'entità; professioni WD P106 coerenti con alpinismo/guide/sci/soccorso e, separatamente, biografie culturali di rilievo con voce itwiki e nascita diretta. Non basta l'omonimia o la provincia, non si afferma alcuna prima ascensione senza una propria fonte. Output: `people-v1.json` profili G1 noindex riutilizzabili, `connectedPeople[]` e `relations[]` nel Comune, con dati e link Wikidata/biografici verificati. La UI usa il dossier locale esistente, con sottosezione **Persone e montagna** e altre figure rilevanti.

**Osservatorio importazioni:** `import_metrics_v1.mjs` conta entità/fatti/media/relazioni nei JSON realmente pubblicati; il frontend Statistiche consente confronto dei cataloghi, grafici copertura dei campi, progressione dei workflow e registro run con link alle Actions. La serie storica è scritta solo dopo un job riuscito, un JSON per pipeline per evitare conflitti sui commit; nessuna serie retroattiva artificiale né scambio con analytics visitatori.

**Vincoli di rilascio:** test unitari su identità, privacy P551, tipi di quota, link e regressioni; esecuzione reale del workflow, quality gate di tutte le schede G2 con almeno quota documentata, build TS/Vitest e controllo SEO. Se una fonte non risponde conservare lo snapshot verificato, mai falsificare valori. Persone G1 non sono pagine SEO autonome. Continueranno a mancare popolazione datata ISTAT, stemmi per alcuni Comuni e storie locali approfondite: restano P1/P2 della Bibbia da acquisire prima di dichiarare il blocco editorialmente completo.

---

## Blocco 3 — Comuni ISTAT/DAIT: pilota di importazione e riconciliazione

**Rilascio controllato G2 (27/11/2026):** l'enrichment Commons/Wikidata/Wikipedia su 48 comuni candidati ha trovato 34 media riutilizzabili, 30 estratti testuali legati al QID ufficiale e **19 dossier G2** con foto, testo e coordinate validati. Le altre 7.875 entità ISTAT non diventano pagine SEO per inferenza; l'archivio nazionale resta input e le schede pubbliche sono nel canale `ISTAT_DAIT_MUNICIPALITIES`. Controlli offline/identità/licenza/TypeScript/Vitest/build/SEO superati nella workflow dedicata, dopo correzione dell'ambiente dei test auth. L'output usa gli stessi componenti `PlaceDetail`/`AlpineAtlasMap` nell'area Paesi con URL distinti `/comuni/<slug>/`; eventuali alias `/borghi/<slug>/` hanno redirect non indicizzabile. Fotografie e testi sono riferiti in `credits-v1.json` e consultabili da `/fonti-e-crediti/` (nessun credito nella singola scheda). L'importatore verifica P635 Wikidata, P18/P94 Commons con media author/license, e pageprops della voce italiana per prevenire collegamenti per omonimia.

**Riferimento vincolante:** sezioni 1, 2, 30 e 31 della Bibbia. **Stato:** ramo `feat/municipalities-istat-dait-pilot-v1`, test/offline + esecuzione pilota su fonti reali tramite CI; nessun write in `public/data`, nessuna nuova scheda SEO o cron di produzione finché i quality gate non saranno verificati.

**Identità e fonte primaria:** la classificazione ISTAT 2026 dei comuni (permalink XLSX: https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx) fornisce **codice ISTAT a sei cifre**, denominazione, regione e provincia/UTS; altitudine e superficie solo se intestazioni ufficiali contengono dati corrispondenti. Il numero ufficiale di comuni al 21/02/2026 è **7.894**; il pilota non assume una copertura numerica invariabile nel tempo. L'ID interno è UUID stabile derivato dal codice iniziale e viene mantenuto dal registro precedente, separato dallo slug parlante. Fusioni, soppressioni, variazioni di codici e omonimie sono operazioni di migrazione/revisione, non merge per nome.

**Amministrazione e crosswalk ufficiale:** CSV DAIT `https://dait.interno.gov.it/documenti/sindaciincarica.csv` acquisito come snapshot indipendente. **`codice_comune` DAIT NON è il codice ISTAT:** il pilota reale ha riscontrato che un join diretto produce solo 23 apparenti associazioni casuali, quindi è vietato. Si crea invece una crosswalk con **codice regione, sigla di provincia, denominazione comunale ufficiale normalizzata** da entrambi i registri, esigendo una singola corrispondenza; il codice composito originale DAIT è conservato in `sourceIds.dait` ed eventuali differenze sono sospese. Una volta riconciliata l'identità, `sindacoNome`, `carica`, `dataElezione` e **`mandatoInizio` dalla distinta colonna `data_entrata_in_carica`** sono attribuiti al comune identificato dal suo codice ISTAT; la scadenza di mandato non viene inferita. Nel pilota finale ISTAT **7.894 comuni**, DAIT **7.783 righe**, **7.779 sindaci associati**, **3 denominazioni in revisione** dopo normalizzazione; gli omonimi/denominazioni bilingui conservano gli alias ufficiali. Le frazioni **non** ereditano sindaco, popolazione, superficie o codice del comune.

**Identità geografica e relazioni:** riuso dello snapshot `alpine-places.json` (1.857 record OSM etichettati `borgo`, ma **non equiparabili a comuni**) e del resolver Wikidata `P635` = ISTAT ID. Solo join `ISTAT codice -> Wikidata QID -> OSM QID univoco`, con controllo del nome, abilita una posizione OSM dichiarata come punto dell'abitato, non confine/centro amministrativo ufficiale. Le relazioni verso rifugi e bivacchi già importati sono esclusivamente `near` con distanza Haversine misurata dal punto OSM, mai `located_in`, `passes_through` o `accessible_from` dedotte. Registrare mismatch in revisione.

**Copertura metadati:** il registro [municipality_field_registry_v1.json](../scripts/municipality_field_registry_v1.json) distingue campo previsto, importato, parziale o in attesa di fonte. Popolazione e anno da ISTAT demografia/censimento, confini da geodata ufficiale, stemmi/foto da Commons/sito istituzionale con licenza, storia documentata e dati climatici trentennali sono **fasi successive del medesimo blocco**, non valori sintetici. Informazioni live e temporali rimangono in un layer con TTL, non mescolate alla base statica.

**Pilota sorgenti reali (27/11/2026):** 12 test unitari superati, download ISTAT/DAIT completati, verifica Wikidata P635, **25 associazioni ISTAT-Wikidata-OSM univoche**, **150 relazioni di prossimità** verso strutture già importate; **0 schede indicizzate**. [Esecuzione GitHub Actions completata con successo](https://github.com/MatteoCurro/cima-becco/actions/runs/46067531645). Restano da verificare le 3 differenze DAIT e i link geografici non risolti senza identificatori incrociati.

**Pipeline e prova:** [import_municipalities_v1.py](../scripts/import_municipalities_v1.py), [resolver P635](../scripts/resolve_wikidata_istat_v1.py), [test contrattuali](../tests/test_import_municipalities_v1.py), [CI staging](../.github/workflows/test-import-municipalities-v1.yml). Input ufficiali sono snapshot raw con SHA256; parser XLSX OpenXML e CSV gestiscono intestazioni variabili/preamboli e falliscono esplicitamente se non riconosciuti; valori -1, data assente e numeri non validi non diventano fatti. Output: `build/import-municipalities-v1/{raw/,municipalities.json,report.json,wikidata-resolver.json}`, artefatto GitHub Actions. Nessun aggiornamento di pagine o motore UI in questo step.

**Criteri per la successiva promozione:** test offline e download reali verdi; copertura, checksum e collisioni verificate; sindaci e date controllati sul campione, nessuna popolazione senza data; entità OSM non promosse a comuni per omonimia; qualità G0/G1 `noindex`; poi eventuale arricchimento G2, collegamento frontend senza layout paralleli e solo infine job ricorrente per fonte. **Frequenze proposte per il rilascio:** ISTAT anagrafe a nuova pubblicazione/controllo giornaliero del checksum; DAIT controllo quotidiano e reimport solo a cambiamento; popolazione alla pubblicazione Istat; non moltiplicare richieste per entità.

---

### Correzione trasversale OSM — malghe, casere e baite (28/11/2026)

Audit sullo snapshot `alpine-places.json` (2.326 POI al controllo): 31 record che iniziano con «Malga» e 29 con «Casera» sono segnalati **rifugio** esclusivamente a causa del mapping `tourism=alpine_hut`; altri 15 iniziano con «Baita» e necessitano verifiche separate. **Non sono 60 casi automaticamente dimostrati come bivacchi**: alcune malghe gestite hanno posti letto, alcune sono punti ristoro, altre sono ripari, altre ancora non sono aperte.

Fonte diretta e ID certo: `way/175876228` Casera Campigàt e `way/199050050` Casera/Malga Valbona passano fra i ricoveri. *Malga Bosch Brusà* (Falcade, quota segnalata 1.867 m) entra con identità di fonte locale `official:falcade:bosch-brusa`, sottotipo `support_point`, senza inventare un OSM ID; pasti stagionali storici e ricovero esclusivamente d'emergenza non dimostrano apertura o ospitalità notturna. Le fonti sono nel registro `public/data/atlas/alpine-structure-evidence-v1.json`.

La trasformazione UI/SEO usa **lo stesso adapter** `src/lib/ruralStructureEvidence.js` dopo la riconciliazione CAI/OSM. Per gli altri nomi rurali privi di classificazione diretta: `rural_type_unverified` G0/noindex, preservando vecchi permalink /rifugi come redirect e conservando OSM, foto e tracce. L'importatore `scripts/import_alpine_places.py` aggiunge query per `restaurant/cafe`, `farmstay/attraction`, `cabin/farm_auxiliary` e salva la coda `public/data/atlas/rural-classification-candidates-v1.json`, non una nuova categoria di bivacchi inventati. Doppia scansione quotidiana a celle dell'area OSM, con checkpoint: non equivale a due scansioni complete di tutte le celle ogni giorno.

**Gate di pubblicazione:** test Python importer e Vitest adapter, TypeScript, build reale, redirect canonici, noindex support point G1 e G0, controlli browser. Questo blocco non altera i mapping del CAI e non modifica i record CAI verificati senza nuova evidenza. Per importazioni regionali future, ampliare i confini geografici e integrare sorgenti istituzionali senza deduplicare per nome.

---

## Blocco 2 — Bivacchi, capanne sociali e punti d'appoggio

**Modello canonico:** [shelter_field_registry_v1.json](../scripts/shelter_field_registry_v1.json), **81 slot** programmati a priorità P0/P1/P2, senza considerarli automaticamente valorizzati. Distinzioni vincolanti: `Bivacco` ≠ `Capanna sociale` ≠ `Punto d'appoggio` ≠ `Rifugio custodito/incustodito`. L'ultima differenza è nella fonte ufficiale CAI, mai inferita dal nome. La UI raccoglie le prime tre sotto la famiglia di navigazione «Bivacchi e ricoveri» mantenendo sottotipo e etichetta ufficiale.

**Pipeline:** [import_cai_refuges_v1.py](../scripts/import_cai_refuges_v1.py) riusa l'archivio completo CAI del blocco 1; ha effettuato una riconciliazione dei media HTTP→HTTPS per le 373 strutture prima non arricchite. [assemble_shelters_release_v1.py](../scripts/assemble_shelters_release_v1.py) produce [shelters-v1.json](../public/data/atlas/shelters-v1.json). Il pilota offline con 763 righe CAI e 33 bivacchi OSM ha accertato i risultati sotto riportati. **Il CAI possiede 252 bivacchi, 89 capanne sociali, 32 punti d'appoggio**; l'intera base CAI con 763 record resta nel dataset archivio `cai-refuges-v1.json` per non perdere altri fatti strutturati.

| Risultato QA sul catalogo canonico | Totale |
|---|---:|
| Bivacchi CAI classificati | 252 |
| Capanne sociali CAI classificate | 89 |
| Punti d'appoggio CAI classificati | 32 |
| Bivacchi OSM esaminati | 33 |
| Associazioni CAI↔OSM univoche | 12 |
| CAI nuovi e distinti da OSM | 355 |
| CAI con identità ambigua sospesa | 6 |
| OSM precedentemente etichettato rifugio e riclassificato grazie a CAI | 1 (Fiamme Gialle) |
| **Catalogo bivacchi e ricoveri risultante** | **389** |
| Fotografie CAI/OSM normalizzate e attribuite | 546 |
| Fatti tipizzati con origine (schede pubblicate) | 11.034 |
| Relazioni di vicinanza a località (non accessi) | 268 |
| Collisioni ID/permalink, aperture o potabilità inventate | 0 |

**Provenienza e layout:** ogni fatto e fotografia mantiene `sourceId/sourceUrl/author/licence`. I crediti sono aggregati in una [pagina dedicata](https://www.cimabecco.it/fonti-e-crediti/) tramite [build_source_credits.mjs](../scripts/build_source_credits.mjs), **senza presentare autori/licenze nel singolo dossier**. Si conserva l'avviso operativo con link ufficiale quando indispensabile. Registrati [18 bivacchi SAT](../scripts/sat_bivouacs_official_sources_v1.json) con i rispettivi URL ufficiali e segnalazione dell'eventuale criticità, ma ancora non associati senza prova d'identità; fonti da confrontare anche con la Provincia Autonoma di Trento. Non si copiain automatico il testo su avvicinamenti di pagine SAT quando non è sicuro che descriva proprio quel bivacco.

**Aggiornamento:** workflow esistente `import-cai-refuges-v1.yml` esteso ai bivacchi; l'aggiornamento quotidiano considera le revisioni CAI nuove/modificate e **non scarica di nuovo tutte le 763 schede** una volta effettuata la migrazione delle immagini. Scrittura dei tre JSON soltanto dopo i test Python/TypeScript/Vitest, qualità e build SEO/permalink.

**Sicurezza:** `In attività` è solo uno stato del catalogo, non `open_now`. L'acqua disponibile non certifica potabilità; la capienza storica non significa posti liberi. L'assenza di un dato non corrisponde a `false`. Le prossimità geometriche non attestano l'accesso percorribile. Nessun contatto, dato amministrativo privato o testo di disclaimer deve diventare un fatto d'accesso per deduzione.

---

## Blocco 1 — Rifugi: rilascio v1.1 verificato

**Importatore operativo e testato su cataloghi reali (27/11/2026):** [import CAI](../scripts/import_cai_refuges_v1.py) + [normalizzazione OSM](../scripts/import_refuges_v1.py) + [assemblaggio](../scripts/assemble_refuges_release_v1.py). L'utente titolare di Cima Becco ha confermato il riuso dei dati CAI. I diritti non sono un gate in sospeso per questo progetto. Rimangono obbligatori attribuzione, provenienza e qualità tecnica del dato.

**Output effettivo e stabile**: [refuges-v1.json](../public/data/atlas/refuges-v1.json), integrato nel motore Atlante e nella generazione delle pagine SEO. La [CI di rilascio](https://github.com/MatteoCurro/cima-becco/actions/runs/46056572061) ha superato test Python/TypeScript/Vitest, import completo, build SEO, 2.669 permalink controllati e commit atomico dei dati, senza sovrascrivere `alpine-places.json`.

| Indicatore | Risultato |
|---|---:|
| Schede CAI (tutte le categorie, archivio di base) | 763 |
| Rifugi CAI | 390 |
| Bivacchi CAI, separati per blocco 2 | 252 |
| Altre strutture CAI, separate | 121 |
| Rifugi OSM dopo revisione/quarantena | 433 |
| Rifugi CAI↔OSM unificati (stesso permalink OSM) | 30 |
| Rifugi soltanto CAI con nuovo permalink | 346 |
| Candidati CAI non uniti perché ambigui | 14 |
| **Rifugi nel catalogo pubblico unificato** | **779** |
| **Fotografie CAI con origine, credito e URL HTTPS** | **659** |
| Campi canonici rifugi predisposti | 80 |

**Rilascio e aggiornamenti:** la workflow [import-cai-refuges-v1.yml](../.github/workflows/import-cai-refuges-v1.yml) importa il catalogo paginato, riusa i dettagli invariati tramite `updated_at`, rielabora soltanto quelli nuovi o modificati, mantiene distinta la tipologia CAI, confronta identità per nome/coordinate/quota, pubblica due JSON atomici *solo dopo tutti i test* e conserva i report. Esecuzione pianificata una volta al giorno dopo l'integrazione in `main`; il deploy Pages è collegato al successo del job.

**Semantica:** la classificazione `Bivacco` non viene mostrata come rifugio; il conflitto Fiamme Gialle e il duplicato Passo Lusia sono in quarantena; 14 possibili duplicati CAI↔OSM sono in revisione e non pubblicati due volte. `In attività` è uno stato di catalogo, **non** un'informazione `open_now`. `near` non equivale a un accesso verificato. Campo sconosciuto e qualità G0/G1 non vengono promossi automaticamente. Foto e dettagli risiedono in risorse collegate al proprio ID sorgente; le webcam si aggiungeranno solo quando l'operatore espone risorse verificabili, non sono simulate.

**Stato progetto:** questo chiude **il primo blocco di rilascio dati**, non pretende una valorizzazione completa dei campi non presenti alla fonte. I 127 nomi di campo CAI osservati sono censiti e 80 attributi canonici sono pronti; successive acquisizioni possono arricchire le schede senza ricreare il modello.

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
| **1, rilasciato v1.1** | **Rifugi: normalizzazione baseline OSM** | Snapshot esistente; identità, facts, vicino a località/cime e percorsi, SEO invariata |
| 2 | Rifugi: riconciliazione/arricchimento ufficiale | CAI Unico Rifugi (riuso confermato) e SAT: proprietà, gestione, letti, servizi, orari e conflitti |
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

Il riuso offline del campione PR #8 ha individuato inizialmente **3 coppie CAI↔OSM** su 80 record; una verifica sulle pagine pubbliche ufficiali CAI ha confermato **Boé e Torrani come rifugi custoditi** ma **Fiamme Gialle come bivacco**, generando **2 candidati rifugio** e **1 conflitto di categoria CAI↔OSM** da conservare per il modulo bivacchi, **0 fusioni/0 relazioni pubblicate**. L'evidenza è versionata in [cai_official_type_evidence_v1.json](../scripts/cai_official_type_evidence_v1.json) e applicata al resolver, con test unitari. Il resolver `reconcile_cai_osm_refuges_v1.py` controlla tipo struttura, nome, coordinate, quota se attestata, più geometrie in conflitto, record non pubblicati e false prossimità, con 13 test offline.

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
