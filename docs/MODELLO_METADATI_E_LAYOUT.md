# Cima Becco — Dizionario dei metadati, dei contenuti e dei layout

**Versione:** 1.0 · **Data:** 27 novembre 2026 · **Stato:** specifica funzionale canonica per la progettazione futura, non inventario di dati già pubblicati.  
**Ambito:** montagne, outdoor a piedi, arrampicata e territorio alpino; Italia e aree confinanti.  
**Documenti collegati:** [Architettura UI](ARCHITECTURE.md), [fonti escursionistiche](FONTI_ESCURSIONISTICHE.md), tassonomia sperimentale della PR #7 e audit delle fonti della PR #8.

> **Regola di progetto:** Cima Becco è un **atlante di conoscenza della montagna**, non un catalogo di tracce. Prima di disegnare una sezione UI bisogna definirne dati, relazioni, fonte, disponibilità e aggiornamento. Un solo motore di ricerca/mappa e un solo sistema visivo; le sezioni delle schede sono modulari.

## 0. Come leggere questa specifica

**Priorità dei campi**: **P0** = identità/sicurezza/struttura indispensabile; **P1** = informazioni caratteristiche per una scheda di qualità; **P2** = arricchimento distintivo. Non equivale a disponibilità del dato.  
**Collocazione UI**: **H** hero/titolo; **K** metriche rapide; **B** contenuti editoriali; **T** tabella/dati strutturati; **G** grafici; **M** mappa e relazioni; **V** media; **F** filtri; **C** pagina centralizzata **/fonti-e-crediti/**. Crediti e provenienza restano nel modello di ogni elemento, ma si presentano nella pagina centrale (decisione editoriale 27/11/2026).  
**Fonti**: **OSM**, **WD** Wikidata, **WC** Wikimedia Commons, **WP** Wikipedia/archivi, **CAI**, **SAT**, **ISTAT**, **DAIT**, **METEO** Open-Meteo/ARPA/Meteotrentino, **OB** OpenBeta, **OFF** sito/ente ufficiale, **USR** dato verificato da community.

I nomi tecnici proposti sono *chiavi canoniche*, non una migrazione già implementata. Ogni campo opzionale rimane assente se non verificato. **null ≠ 0 ≠ false ≠ dato non aggiornato**. Le grandezze numeriche hanno unità esplicite; le date includono contesto e, se necessario, fuso orario.

## 1. Contratto dati comune a tutte le schede

| Campo canonico | Significato / forma | Priorità | Layout |
|---|---|---|---|
| id | ID interno stabile, **non derivato dallo slug** | P0 | — |
| kind / subtype | Tipologia e sottotipo ontologico; es. municipio ≠ frazione, falesia ≠ settore, sentiero ≠ itinerario | P0 | F |
| name / displayName | Nome documentato, forma estesa per il titolo | P0 | H |
| aliases[] / localNames[] | Varianti italiane, tedesche, ladine, denominazioni storiche con lingua e fonte | P1 | H, ricerca |
| slug / slugAliases[] | URL parlante unico, storico alias e redirect/compatibilità legacy | P0 | SEO |
| shortSummary | Sommario documentato non generico, distinto da contenuti generati automaticamente | P1 | H |
| description / history | Testi editoriali con fatti e fonti verificabili; eventuale versione multilingue | P1/P2 | B |
| textSources[] | Riferimenti verificati a testi riutilizzati con autore collettivo/individuale, URL originale, licenza, lingua, data, QID/ID sorgente e distinzione estratto vs testo editoriale originale; vietata attribuzione per sola omonimia | P1 | B, C |
| geo.point / geo.area | Latitudine, longitudine, eventuale poligono, precisione e metodo | P0 per POI | M |
| elevationM / elevationMethod | Quota, fonte, datum/precisione quando nota; DEM = stima | P1 | K |
| administrativeHierarchy | Stato, regione/provincia, comune e ID ufficiale ove pertinente | P1 | B, F |
| sourceIds{} | OSM, Wikidata, ISTAT, CAI/SAT, GeoNames, OpenBeta, identificativi fornitori | P0 per import | C |
| facts{} | Fatti tipizzati con valore, unità, provenienza, data/validità e confidenza | P0 | K, B, T |
| relations[] | Collegamenti semanticamente tipizzati a entità note | P1 | M, B |
| media[] | Immagini, logo/stemma, foto storiche, video e topo con singola licenza | P1/P2 | H, V |
| weatherRef / climateRef | Serie temporali/meteo separati dalla scheda statica | P2 | G |
| restrictions[] / alerts[] | Limitazioni con territorio/elemento interessato, fonte, validità, ultimo controllo | P0 se presenti | H, B |
| editorialStatus / quality | raw, linked, enriched, reviewed; indicatori di dati insufficienti/confitti | P0 | SEO, interno |
| checkedAt / updatedAt | Ultima verifica del fatto e ultima generazione della scheda | P1 | C |

### 1.1 Struttura minima di ogni fatto

Ogni informazione non banale deve poter conservare: **value, unit, sourceId, sourceUrl, licence, retrievedAt, sourceUpdatedAt, validFrom, validUntil, method (reported/derived/estimated), confidence, notes, rawValue**. Per dati contestati o diversi fra fonti, mantenere **factsAlternatives[]** e spiegazione della scelta editoriale; mai cancellare l'origine.

Le informazioni operative (sindaco, gestore, apertura, prezzo, webcam, chiusure, meteo, ancoraggi segnalati) richiedono timestamp, validità e livello di conferma. Valori sentinella come **-1** vanno normalizzati a null quando significano sconosciuto.

### 1.2 Relazioni semantiche condivise

Tipi richiesti: **located_in, part_of, contains, near (con straightLineKm e metodo), starts_at, ends_at, passes_near, passes_through, ascends_to, accessible_from (solo verificato), managed_by, owned_by, founded_by, first_ascended_by, opened_by, overlaps, alternative_to, stage_of, previous_stage, next_stage, served_by, recorded_by, restricted_by**.

**Estensione tipizzata persone 28/11/2026**: `born_in` / `birthplace_of` (Wikidata P19, solo luogo esatto); `resided_in` / `historical_residence_of` (P551, per profili storici/deceduti); `worked_in` / `workplace_of` (P937, attività attestata). Sono legami biografici, **non** prima ascensione, fondazione, intitolazione o appartenenza provinciale: queste relazioni necessitano di una fonte specifica. Conservare QID persona, identificativo comune ISTAT-QID già riconciliato, ruolo P106, URL, timestamp e gate G1; una persona G1 non diventa pagina SEO prima di una scheda biografica G2. Per i viventi evitare dati di residenza privata o contatti personali.

**Due invarianti**: prossimità geografica **non** prova attraversamento o raggiungibilità; il collegamento di un luogo a una persona **non** si deduce dalla sola appartenenza provinciale.

### 1.3 SEO e permalink

Title e meta description si basano su fatti specifici; schema.org selezionato secondo tipologia solo con contenuto verificato; canonical, hreflang dove presente, alt fotografici e breadcrumb. **Un URL stabile per entità**; gli ID delle sorgenti non sono rivolti al pubblico. Non cambiare gli URL live senza gestione degli alias e dei redirect. Il contenuto scarso o solo template resta **noindex,follow**, ma accessibile via mappa. Le migrazioni rispetto agli URL oggi in uso sono un progetto SEO separato.

### 1.4 Sistema unico di layout

Conservare il contratto di [ARCHITECTURE.md](ARCHITECTURE.md): dettaglio desktop **42% contenuti / 58% mappa**, senza larghezze globali arbitrarie; mobile con sezioni full-width. Gli stessi componenti **DetailLayout, DetailMetrics, DetailFacts, media gallery, weather charts, RelatedEntities, CreditsAccordion** ricevono adapter diversi secondo kind. Mappa e ricerca condivise, filtri faccettati per categoria. Non riprodurre header, navbar, map engine o CSS strutturali per ogni tipologia.

**Ordine modulare**: hero verificata + titolo → metriche essenziali → contenuto descrittivo → blocco specialistico primario → informazioni operative/servizi → storia e approfondimenti → media/grafici → entità vicine/collegate. Le attribuzioni si consultano nella pagina centrale, non nel dossier. Un alert effettivo e datato è visibile in alto senza essere nascosto nei moduli.

### 1.5 Politica unificata di fonti e crediti (decisione editoriale vincolante)

L'attribuzione visibile di **dati, immagini, testi e fotografie** è in una pagina dedicata, `/fonti-e-crediti/`, raggiungibile nel menu/footer e indicizzata. Non inserire crediti fotografici, nomi di autori, licenze, collegamenti alla singola fonte o accordion di crediti all'interno del dossier di ogni luogo. Fanno eccezione i collegamenti **operativi indispensabili** a fonti ufficiali di avvisi/chiusure/restrizioni, il cui contenuto deve essere immediatamente verificabile per ragioni di sicurezza.

La centralizzazione riguarda **soltanto la visualizzazione**, non la conservazione: i campi `facts{}`, `factsAlternatives[]`, `media[]`, `textSources[]`, `geo`, `relations[]` e `sourceIds{}` devono **continuare a contenere fonte, URL, autore, licenza, validità, timestamp, metodo e identità originali**. L'indice pubblico `credits-v1.json` è derivato dagli stessi dati pubblicati, non una seconda verità o una tabella compilata a mano. I contenuti provenienti da CAI conservano gli identificativi ufficiali e il riuso dichiarato dall'utente titolare del progetto; non servono verifiche ripetute sui permessi CAI.

Per le fotografie, la pagina attribuisce ogni media visibile alla sua **scheda concreta**, con autore/licenza/URL originali, filtri di ricerca e limite di caricamento iniziale. Eventuali casi con metadati incompleti vanno revisionati, non mascherati. Per i testi ripresi da Wikipedia, la verifica del QID della voce e la conservazione della licenza CC BY-SA sono indispensabili; un estratto attribuito resta distinto da una sintesi originale e non può sostituire dati demografici ISTAT datati.

---

## 2. Comuni — scheda amministrativa e territoriale

**Identità**: municipalityCodeISTAT (P0, C), name/aliases, provincia/regione/stato, toponimi ladini/tedeschi, confine amministrativo (P1, M).

| Metadati | Priorità | Fonte preferita | UI |
|---|---|---|---|
| quotaCentroM, superficieKm2, coordinateCentro | P1 | ISTAT/geoportale, OSM, DEM dichiarato | K, M |
| popolazione, populationReferenceDate, residenti per età/sesso se disponibili | P1 | **ISTAT ufficiale**, anno obbligatorio | K, G |
| sindacoNome, mandatoInizio/Fine, carica, ultima verifica | P1 | **DAIT**, comune identificato per codice | B, T |
| stemma, logo istituzionale, sede e sito del municipio | P1 | Comune, WC con diritti | H, V |
| frazioni[] / località[] / municipalRelations[] | P1 | ISTAT, OSM, WD | M, B |
| etimologia, prime attestazioni, storia sintetica, tradizioni legate alla montagna | P1 | Archivi locali, WP documentata, siti comunali, ICCD | B |
| patrimonio naturale/culturale, musei e monumenti | P1 | ICCD, OSM, siti ufficiali | B, M |
| alpinisti/guide e personalità montane nate o vissute qui | P2 | WD + riscontri CAI/biografie | B, M |
| connectedPeople[] / relations[] persone | P2 | WD P19/P937/P551 + P106, verifica diretta del QID; futuro riscontro biografico CAI/archivi | B, M |
| temperature e precipitazioni medie mensili, neve caduta vs manto | P1/P2 | METEO con periodo e quota modello | G |
| currentWeather, forecastHourly/daily, stazioni, webcam | P1/P2 | METEO, portali autorizzati | H, G, V |
| cime, rifugi, falesie, palestre, laghi, passi, impianti e sentieri vicini | P1 | Motore relazioni territoriali | M, B |
| galleria recente e archivio fotografico storico con data scatto | P2 | WC, Europeana, archivi locali | V |
| accessi stradali, trasporto, parcheggi, servizi utili | P2 | OSM, GTFS, operatori | B, M |

**Layout**: hero con foto geograficamente verificata e stemma; KPI quota/popolazione/territorio; blocchi **Il paese**, **Storia e toponimi**, **Vivere la montagna**, **Meteo e clima** (grafici con assi e unità), **Luoghi da scoprire**, **Fotografie ieri/oggi**, **Amministrazione**. **Sindaco e popolazione non si ereditano alle frazioni**.

**Stemmi e simboli (importatore 28/11/2026):** il comune è identificato prima con codice ISTAT e Wikidata `P635`; `P94` è **stemma** e `P154` è **logo istituzionale**, non sono sinonimi. Acquisire anche lo stemma nelle immagini della **voce Wikipedia italiana col medesimo QID**, se il nome completo del Comune è esplicito nel titolo del file e il riferimento è araldico; in ulteriore fallback usare una ricerca Commons con conferma incrociata di **nome esatto nel titolo e descrizione araldica del Comune**, senza accettare template o stemmi di territori omonimi. Verificare ciascun file su Commons (autore, licenza, URL). Per SVG originali il frontend usa **solo la miniatura raster** fornita da Commons; non mostra SVG remoti grezzi. Conservare sempre la fonte verificata e la distinzione `symbolType=coat_of_arms|institutional_logo`.

**Fotografie storiche:** due modalità automatiche ammesse, entrambe con licenza/autore Commons verificati e data storica **documentata** (creazione `P571` MediaInfo oppure `DateTimeOriginal`, non la data di upload): (a) `P180` MediaInfo = esatto QID del Comune; (b) file citato dalla pagina Wikipedia italiana con **QID confermato** e **nome completo del Comune nel titolo dell'immagine**. Salvare `capturedAt` con precisione disponibile, `historicalDateMethod`, `subjectMethod` e originale Commons, distinguendo `historical_photo` da fotografia contemporanea. Per questa prima fase la classificazione cronologica conservativa è antecedente al 1975; file ambigui o privi di data rimangono da revisionare, senza età simulata. Archivi comunali, Europeana, ICCD e biblioteche fotografiche locali sono fonti candidate aggiuntive, ma richiedono **licenze e collegamenti oggetto–Comune verificati** prima della promozione G2. Nessuna pagina deve presentare una foto generica delle Dolomiti come immagine storica del centro comunale.

**Avanzamento importazioni:** si parte dall'archivio ISTAT/DAIT nazionale, con pubblicazione delle sole schede che raggiungono G2; G0/G1 non diventano pagine indicizzate. Il cursore `municipality-import-progress-v1.json` registra i Comuni già tentati e il loro stato dopo ogni esecuzione riuscita, per dare precedenza ai **nuovi Comuni** e ritentare più tardi quelli incompleti; il refresh degli G2 viene distribuito su più lotti, senza arrestare la crescita. I candidati storici si scandiscono a rotazione. I grafici di copertura distinguono **numero nazionale ISTAT**, **Comuni effettivamente tentati**, **G2 pubblicati**, **stemmi verificati** e **foto storiche con data**. Le informazioni non presenti nei dataset non vengono inventate.


## 3. Frazioni, borghi, abitati e località

| Metadati | Priorità | Fonte | UI |
|---|---|---|---|
| kindDettagliato: frazione, centro abitato, nucleo, località, toponimo | P0 | ISTAT località, OSM, WD | H, F |
| parentMunicipalityId, parentMunicipalityName | P0/P1 | ISTAT/OSM/WD riconciliati | B, M |
| coordinate, quota e tipo di stima, varianti linguistiche | P1 | OSM, WD, DEM | K, H |
| residentiLocale + anno + perimetro *solo se esistono dati subcomunali* | P2 | Censimento località ISTAT | K |
| storia, etimologia, caratteristiche e ruolo nel territorio | P1 | Archivi locali e fonti documentali | B |
| servizi, parcheggi, fermate, accesso ai sentieri | P1 | OSM/operatori | M, B |
| meteo, clima, immagini, webcam, POI vicini, rifugi e cime | P1/P2 | METEO, WC, OSM | G, V, M |
| personaggi montani collegati specificamente alla località | P2 | WD/CAI/biografie | B |

**Layout**: stessa scheda locale del comune ma senza sezione sindaco proprio; riportare la dicitura **«Frazione/località del comune di …»**. Per omonimi usare slug con disambiguazione territoriale, non ID OSM.

**Applicazione operativa località 2021 (28/11/2026, blocco 4).** La fonte ISTAT ufficiale *Basi territoriali e variabili censuarie 2021* distingue il repertorio regionale `LOC_Rxx_21.csv` (codici e sottotipo) dal prodotto nazionale *Località puntuali 2021* (`LocalitaPuntuali_21.zip`, `Localita_2021_Point.dbf`, shapefile e `.prj`). Quest’ultimo registra `LOC_ID`, `PRO_COM`, `LOC`, `TIPO_LOC`, `NOME`, `POINT_X`, `POINT_Y`, quota `ALTITUDINE` e indicatori `POP21` residenti, `FAM21` famiglie, `ABI21` abitazioni, `EDI21` edifici. **EPSG:32632** è il CRS di origine dichiarato; in archivio web il punto è trasformato in EPSG:4326 con metodo, data e fonte registrati. Non interpretare X/Y UTM come latitudine/longitudine.

**Gate di identità:** `LOC_ID = PRO_COM + LOC` (con riempimento zeri esplicito), coerenza di `TIPO_LOC` e nome completo normalizzato; in caso di contrasto non attribuire coordinate o dati demografici. Il codice e la gerarchia fanno riferimento al 2021; non dichiarare equivalenza amministrativa contemporanea quando un Comune è stato fuso o rinominato. `TIPO_LOC` 1 e 2 sono centro e nucleo abitato; 3 e 4 non diventano automaticamente schede di borgo. L'attributo `CENTRO_CL` non dimostra lo status giuridico di frazione. Conservare i quattro conteggi ISTAT con anno e perimetro di località, distinguendo `0` da assenza del dato e impedendo l'eredità dal Comune.

**Reconciliazione OSM/Wikidata:** il nome comune e la vicinanza sono indizi, non prova. Un collegamento fra località puntuale ISTAT e OSM richiede QID univoco, nome, coordinate congruenti e una relazione amministrativa esplicita (`P131`) verificata contro il Comune; i conflitti restano indipendenti e in revisione. Per pubblicare un dossier G2 iniziale sono inoltre necessari testo della pagina Wikipedia con medesimo QID, immagine Commons `P18` con soggetto/diritti/autore verificati e quote, popolazione e relazione solo dove realmente disponibili. Le persone sono collegate alla località specifica unicamente mediante claim biografici diretti. Le fotografie storiche seguono le verifiche `P180`/P571/DateTimeOriginal della sezione 2; gli stemmi dei Comuni non si ereditano agli abitati. Il corpo del dossier non mostra i crediti, che rimangono per-oggetto in `/fonti-e-crediti/`.

## 4. Cime, montagne e gruppi montuosi

| Metadati | Priorità | Fonti | UI |
|---|---|---|---|
| tipo: cima/sottocima/massiccio/gruppo/cresta | P0 | GeoNames, OSM, WD | H, F |
| elevazioneM, prominenzaM, quota fonte, coordinate o area | P1 | GeoNames, OSM, DEM, cataloghi | K, M |
| gruppo, catena, regione, confini, cime secondarie | P1 | WD, OSM, archivi | B, M |
| etimologia, nomi locali, storia, prime ascensioni documentate | P1 | CAI/biografie/archivi, WD | B |
| primi salitori/anno, vie classiche, pareti, difficoltà originali | P2 | Guide autorizzate, CAI | B |
| sentieri di accesso, vie ferrate, multipitch, rifugi, forcelle | P1 | Catasto rete/relazioni | M, B |
| geologia/litologia, protezione ambientale e limitazioni | P2 | Geoportali, enti parco | B |
| quota del punto meteo vicino, vento, previsione e webcam | P1/P2 | METEO; quota dichiarata | G, V |
| panorami e fotografie georeferenziate, punti di osservazione | P1/P2 | WC e media verificati | V, M |

**Layout**: hero cima → quota/gruppo, descrizione, storia alpinistica, **Come raggiungerla** (solo collegamenti confermati), vie/ferrate, rifugi, meteo in quota, immagini e mappa.

**Contratto operativo cime GeoNames G2 (28/11/2026).** L'archivio grezzo già esistente in `public/data/peaks` resta la sorgente di geometria e dell'identificativo GeoNames; la corrispondenza Wikidata usa esclusivamente la proprietà `P1566` uguale all'ID e coordinate `P625` congruenti (soglia della verifica puntuale documentata). La quota GeoNames `s` (riportata) e `d` (stimata) conserva il metodo; `P2044` Wikidata è un fatto separato `wikidataElevationReportedM`, con unità verificata, **mai** una sostituzione silenziosa. In caso di differenza sostanziale, l'entità resta in revisione. Gruppi montuosi senza perimetro verificato e toponimi omonimi non si pubblicano come G2. Gli archi `near` restano distanze rettilinee, non dimostrano una via di accesso.

**Gate editoriale cime G2 e URL.** Prima dell'indicizzazione servono: ID GeoNames-QID uno a uno, fotografie `P18` della stessa entità con metadati di licenza/autore su Commons, testo enciclopedico della stessa voce con QID `pageprops` verificato, quota con metodo, testo non generico, nessun conflitto di ID o slug. Le informazioni di prima ascensione, vie e accessibilità richiedono una fonte qualificata propria. Il permalink editoriale è `/cime/<slug>/`, con vecchio `/place/gn<ID>-<tile>/` preservato come alias noindex/redirect; l'app conserva il `gn...` come identità tecnica dei pin e dei preferiti. Crediti esclusivamente nel registro centrale `/fonti-e-crediti/`.



## 5. Passi, forcelle, valichi, valli, laghi, cascate, sorgenti, panorami

**Identità**: kind/subtype, nome e varianti, coordinate, quota/estensione, gruppo/valle/comune, accessibilità, ente e aree protette.  
**Campi specifici**:
- **Passo/forcella**: quota, valichi collegati, segnavia, rifugi e itinerari di attraversamento, apertura stradale solo se pertinente, divieti (P1).
- **Valle**: sviluppo ed estensione se documentati, torrente, comuni attraversati, accessi, sentieri, caratteristiche geologiche (P2).
- **Lago**: tipo naturale/artificiale, superficie/profondità se documentate, quota, lago balneabile **solo con fonte**, sentieri di accesso, eventuali interdizioni (P1/P2).
- **Cascata**: salto e regime stagionale *se noto*, belvedere, accessi, restrizioni (P2).
- **Sorgente/fontana**: tipo (spring, drinking_water), coordinate, eventuale potabilità **solo esplicitamente segnalata**, disponibilità stagionale, ultimo controllo (P0 se dichiarata).
- **Punto panoramico**: posizione, orientamento, cime visibili quando calcolate con metodo, accessibilità, foto (P1).
- **Memoriale/luogo storico**: epoca, dedica, storia, fonte, fotografie, preservazione e regole (P1).

**Layout**: hero → pochi KPI appropriati → spiegazione → accesso → natura/storia → dintorni → media; niente campi vuoti o meteo identico duplicato senza necessità.

**Importazione elementi naturali — requisiti operativi (28/11/2026).** Una singola categoria canonica `natural_feature` distingue `mountain_pass`, `saddle`, `lake`, `reservoir`, `valley`, `waterfall`, `viewpoint`, con identificativo stabile indipendente dal nome/slug. **Lago e invaso artificiale non sono sinonimi**, quota assoluta `elevationM` e salto di cascata `waterfallDropM` non sono la stessa misura; un punto rappresentativo estratto dal centro di una way/relation **non** è un poligono lacustre, una riva, una valle delimitata o un accesso. Quote DEM vanno etichettate come stime e mantenute separate dalle quote dichiarate. Per i passi l'apertura, la transitabilità e il collegamento ai sentieri richiedono una fonte appropriata e datata; nessuna apertura viene dedotta dal solo tag di localizzazione.

**Proprietà della fonte e riconciliazione.** Gli elementi OSM usano `sourceIds.osm` con `node/way/relation`; GeoNames usa `sourceIds.geonames`, feature class/codice e origine CC BY 4.0. Identità OSM e GeoNames sono **dataset indipendenti** finché Wikidata e coordinate non confermano il crosswalk; distanza/nome non bastano. `natural=spring`, fontane e rubinetti rimangono nella pipeline `import_alpine_water.py` e in `alpine-water.json`: non creare duplicati di sorgenti nella pipeline di feature naturali, né qualificare l'acqua potabile per sola presenza. I collegamenti `near` sono distanze in linea d'aria, non `accessible_from`. I raw del pilota restano in staging G0/G1 e **noindex**; solo identità verificata, contenuto specifico, media con fonte/licenza e QA consentono future schede G2.

**Gate di riconciliazione ed audit quote dei valichi (28/11/2026).** Una crosswalk GeoNames–Wikidata richiede una corrispondenza biunivoca `wdt:P1566` con l'ID GeoNames e coordinate `P625` nel limite di compatibilità della sottotipologia; una seconda lettura dei claim deve confermare tali condizioni prima di qualsiasi output G2. Un OSM con tag `wikidata=Q...` è comunque un candidato finché QID, tipologia e coordinate non sono stati verificati separatamente; il collegamento finale conserva entrambi gli ID senza forzare la geometria OSM sul punto GeoNames. Estratti Wikipedia solo se la voce dichiara lo stesso QID attraverso `pageprops.wikibase_item`, immagini Commons per soggetto tramite `P18` e per file con autore/licenza, didascalia descrittiva fedele al file fotografico. **Divergenze nella quota `m s.l.m.` descritta nel testo originale** si conservano come `factsAlternatives[]` e non sovrascrivono la quota GeoNames né quella Wikidata; sui valichi una differenza oltre 45 m è criterio di revisione, non dato da mediare. Ciò non rappresenta una misura ufficiale né una conferma di transitabilità. Per laghi e valli senza perimetro/aree certi, il profilo informativo può arricchirsi restando G1 e noindex.



---

## 6. Rifugi alpini

**Gerarchia**: struttura (entità fisica) → proprietà → gestione attuale → servizi / apertura temporale → sentieri di accesso. Il proprietario non coincide necessariamente col gestore.

| Metadati | Priorità | Fonti | UI |
|---|---|---|---|
| nome, varianti, tipo (rifugio gestito/non gestito), id CAI | P0 | CAI Unico Rifugi, SAT, OSM | H, C |
| quota, coordinate, località, gruppo, disponibilità accesso | P0/P1 | CAI, SAT, OSM | K, M |
| proprietario, sezione, gestore, contatto gestore, validità | P1 | CAI dettaglio, SAT, OFF | B, T |
| apertura: stagionale, invernale, giorni/orari, **data verifica** | P1 | OFF, SAT, CAI dettaglio | H, T |
| letti totali, letti invernali, camerate, rifugio invernale | P1 | CAI dettaglio, OFF | K, T |
| telefono, email, web, prenotazione/booking ufficiale | P1 | OFF, CAI, SAT | B |
| prezzi: pernottamento, mezza pensione, soci, stagionalità | P2 | OFF, validità datata | T |
| servizi acqua, pasti, corrente, Wi-Fi, docce, POS, cucina, animali, accessibilità | P1 | CAI fields[], OFF, OSM | B, F |
| storia, anno costruzione/inaugurazione, intitolazione | P2 | SAT, CAI, archivi | B |
| sentieri di partenza e accesso verificati, segnavia, tempi dichiarati | P1 | CAI/SAT/rete, OFF | M, B |
| tappe di trekking e cime vicine; rifugi alternativi | P1 | Grafo relazioni | M, B |
| foto attuali, storiche, logo solo autorizzato, webcam | P2 | CAI media, WC, OFF | H, V |
| meteo locale, neve prevista, modello/altitudine di riferimento | P1/P2 | METEO | G |

**Chiarimento CAI sui servizi (audit 27/11/2026):** il campo `acqua_in_rifugio_service` indica *disponibilità d'acqua dichiarata* (`waterAvailableReported`) e **non** ne certifica la potabilità (`drinkingWater`, solo con fonte esplicita). `camerate_superiore_4_posti_service` indica la presenza dichiarata di camerate con più di quattro posti (`largeDormitoriesAvailableReported`), **non** il loro numero né i letti totali. Entrambi sono fatti booleani con fonte, data e validità quando presenti; un valore assente resta sconosciuto. Gli ulteriori campi CAI su energia, certificazioni, servizi, accessi e requisiti gestionali restano candidati alla mappatura tipizzata: la mera presenza delle chiavi non implica contenuto pubblicabile o attendibile. I campi contrattuali, fiscali e i recapiti personali non si pubblicano tramite import automatico.

**Layout**: hero con foto autentica e nome/quota → **stato apertura datato** → posti letto/contatti/prenotazione → servizi → storia → **Come arrivare / sentieri / trekking che passano qui** → meteo, foto e webcam → crediti.

**Evidenza di copertura al 27/11/2026**: API CAI indica 764 strutture, 80 record d'elenco testati con nome/quota/coordinate. Il dettaglio offre fields[] con chiavi quali posti_totali_service, posti_letto_invernali_service, openingTime_contact, name_management_property, wifi_service, defibrillatore_service, media[]; **presenza della chiave non prova valore valorizzato né permesso di ripubblicazione**.

## 7. Bivacchi, ricoveri e capanne non gestite

| Metadati | Priorità | Fonte | UI |
|---|---|---|---|
| nome, kind: bivacco fisso, ricovero, capanna, emergenza | P0 | CAI/SAT, OSM, OFF | H |
| quota, posizione, accesso e difficoltà documentata | P1 | CAI/SAT, OSM | K, M |
| ente proprietario/manutentore, data ultimo controllo | P1 | OFF, CAI | B |
| posti disponibili, letti/cuccette, riparo invernale | P1 | OFF, CAI/OSM | K, T |
| dotazioni acqua, stufa, gas, energia, materassi, coperte, servizi | P1 | OFF, verifiche documentate | T |
| regole di uso, prenotazione, eventuali chiusure | P0 se presenti | gestore ufficiale | H, B |
| sentieri di accesso, traversate vicine, cime e tempi dichiarati | P1 | rete verificata | M, B |
| fotografie, stato apparente non certificato, storia e intitolazione | P2 | WC, CAI/archivi | V, B |

**Malga / casera / baita: interpretazione tipologica (28/11/2026).** La denominazione tradizionale indica il manufatto o l'uso d'alpeggio, **non** prova il diritto d'accesso, l'attività ricettiva o la disponibilità di posti letto. Analogamente, il tag OSM `tourism=alpine_hut` senza ulteriori verifiche non dimostra un rifugio escursionistico con pernottamento. Tenere distinti:
- **Rifugio**: funzione ricettiva attestata da ente CAI/SAT, sito ufficiale o evidenza specifica di pernottamento; anche i rifugi non custoditi possono esserlo.
- **Casera / malga a uso ricovero**: `alpine_casera_shelter` nella navigazione «Bivacchi e ricoveri», con capienza solo se documentata. *Malga Casera Campigàt* e *Malga Valbona* sono esempi con fonte territoriale puntuale, identità OSM stabile e redirect dagli URL storici.
- **Malga di ristoro / punto d'appoggio**: `support_point`; servizi alimentari stagionali, eventuale riparo d'emergenza e pernottamento **ordinario** sono informazioni indipendenti. *Malga Bosch Brusà* di Falcade va censita anche senza un OSM `alpine_hut`; ricovero soltanto d'emergenza dichiarato, nessuna apertura in tempo reale confermata.
- **Tipologia rurale non confermata**: `rural_type_unverified`, G0, `reviewRequired`, noindex, nessuna promessa di ricovero, ristorazione o pernottamento. L'esistenza del nome «Malga/Casera» senza prova della funzione non autorizza una riclassificazione definitiva. I rifugi CAI confermati non devono essere declassati dal nome.

**Import e relazioni:** Overpass acquisisce in revisione anche malghe censite come ristoranti, aziende ricettive agricole o fabbricati rurali (`amenity=restaurant/cafe`, `tourism=farmstay/attraction`, `building=cabin/farm_auxiliary`), senza generare automaticamente nuove schede G2. La coda `rural-classification-candidates-v1.json` conserva identità OSM, coordinate e tag in G0; un registro di evidenze ufficiali `alpine-structure-evidence-v1.json` conserva decisione, fonte, qualificazione, alternative e data. Deduplicare mediante ID OSM o fonte ufficiale sicura, mai per nome e prossimità soltanto. Se la tipologia cambia, conservare slug/ID e redirect dagli URL precedenti; non eliminare foto, collegamenti ai sentieri o fatti verificati.

**Layout**: informazioni operative e limiti prima della storia. Non indicare un bivacco come aperto/sicuro soltanto perché mappato.

---

## 8. Rete sentieristica: sentiero, tratto e infrastruttura

Il **sentiero** è l'elemento del **grafo fisico**; l'**itinerario** è una sequenza di segmenti. Relazione OSM hiking ≠ escursione ufficiale percorribile. Non sono richiesti nuovi GPX per l'arricchimento di schede SEO, ma la geometria resta necessaria alla verifica delle connessioni e al routing.

| Metadati | Priorità | Fonti | UI |
|---|---|---|---|
| ID del tratto e della rete, ref/numero sentiero, denominazioni | P0 | OSM, INFOMONT, SAT | H, C |
| gestore e rete (CAI/SAT, locale, internazionale), segnavia e colori | P1 | OSM, CAI/SAT | K, B |
| due estremità/geometria **solo se disponibile**, stato connessioni | P0 per routing | geodata | M |
| categorie: hiking, trail running, ferrata; scala CAI/SAC/ferrata originale | P1 | fonti esplicite | K, F |
| lunghezza, quota min/max, superficie, esposizione, attrezzature | P1/P2 | geodati e fonti | K, B |
| intersezioni, cime, acqua, rifugi, paesi e punti di accesso | P1 | grafo | M, B |
| manutenzione/chiusura/vincoli, periodo di validità | P0 se presenti | enti, CAI/SAT | H |
| descrizioni, storia del sentiero, denominazione e riferimenti ufficiali | P1/P2 | fonti documentali | B |

**Layout**: testata con numero/simbolo + difficoltà dichiarata, descrizione, caratteristiche e relazioni. Evitare pagine seriali con soltanto nome/numero e boilerplate.

## 9. Escursione o itinerario giornaliero

| Metadati | Priorità | UI |
|---|---|---|
| nome, tipologia anello/andata-ritorno/traversata; fonte ufficiale o community | P0 | H |
| partenza/arrivo, località, parcheggio/trasporto, punti intermedi | P1 | H, M |
| distanzaKm, ascesa/discesaM, altitudine min/max, durata stimata o ufficiale + metodo | P1 | K |
| difficoltà dichiarata, esposizione, terreno, ferrata, passaggi tecnici | P1 | K, B |
| periodo ideale, meteo e informazioni su neve **con fonte** | P2 | G |
| punti acqua, rifugi, cime, passi e aree protette attraversati/vicini distinti | P1 | M |
| varianti/alternative, sentieri della rete utilizzati | P1 | B, M |
| descrizione originale e curiosità storiche, fotografie contestuali | P1/P2 | B, V |
| chiusure ed avvisi documentati con validità | P0 se presenti | H |

**Layout**: metriche escursionistiche → testo descrittivo → tappe/punti salienti → mappa e profilo altimetrico se realmente disponibile → logistica → meteo → POI e crediti. Un tracciato importato non equivale a un percorso verificato sul campo.

## 10. Grandi trekking / cammini / Alte Vie

| Metadati | Priorità | UI |
|---|---|---|
| denominazione, sigle e rete (SI, GR9, Alta Via 1/2, Translagorai), promotore | P0 | H |
| storia: ideazione, inaugurazione, significato e riferimenti documentati | P1 | B |
| regioni e gruppi attraversati, estremità, distanza e dislivelli ufficiali | P1 | K, M |
| numero tappe **ufficiali**, varianti e revisioni nel tempo | P1 | K, T |
| difficoltà massima e frequente, periodi, logistica/trasporti, rifornimenti | P1 | B |
| tappaId[], ordini, rifugi, paesi e punti di appoggio | P1 | T, M |
| descrizione narrativa verificata di ogni sezione, foto e marchio autorizzato | P1/P2 | B, V |
| note di percorribilità, restrizioni, chiusure, gestione | P0 se presenti | H |

**Layout**: hero editoriale → panoramica/metriche → storia del cammino → **elenco tappe navigabile** con filtri e riepilogo → mappa di insieme → collegamenti a rifugi/paesi → consigli logistici documentati → fonti.

## 11. Tappa trekking, variante e proposta algoritmica

| Metadati | Priorità | UI |
|---|---|---|
| trekId, stageNumber, officialStageId, nome tappa | P0 | H |
| startPlaceId, endPlaceId, intermediatePlaces[], punti d'appoggio | P1 | H, M |
| distanzaKm, ascesaM, discesaM, durata, difficoltà e data fonte | P1 | K |
| segmento della rete e connessioni geografiche verificabili | P0 se dichiarata continua | M |
| previousStageId / nextStageId, varianti documentate | P1 | B |
| acqua, rifugi, impianti e servizi utili | P1 | M, B |
| tipologia: official / documented_variant / proposed_by_algorithm | P0 | H |
| algorithmVersion, constraints, confidence, discontinuities | P0 per proposte | C, H |

**Layout**: navigazione tappa precedente/successiva, KPI, descrizione, profilo se disponibile, rifugi, mappa, fonti. **Non chiamare ufficiale una suddivisione calcolata**.

**Evidenza 27/11/2026**: import pilota della tabella SAT Sentiero Italia trentino: 18 tappe con 18 durate, 18 dislivelli negativi, 17 dislivelli positivi e 18 difficoltà. Dati da connettere al grafo, non sinonimo di itinerario concatenato e navigabile.

## 12. Vie ferrate

| Metadati | Priorità | UI |
|---|---|---|
| nome, cima/parete, punti di ingresso/uscita, avvicinamento | P0/P1 | H, M |
| difficoltà **scala originale e fonte**, esposizione, sviluppo/dislivello | P1 | K |
| tratti attrezzati, tipologia di attrezzatura (cavi, scale, staffe) se documentata | P1 | B |
| tempo avvicinamento/via/discesa e itinerario di rientro | P1 | T |
| materiale indicato dalla fonte, gestione, chiusure/restrizioni | P1/P0 | H, B |
| storia, costruttori, rifacimenti, panorami e foto | P2 | B, V |

**Layout**: difficoltà tecnica e avvisi prioritari; descrizione, logistica, collegamenti cime/rifugi, immagini. Mai dedurre sicurezza dell'attrezzatura dal solo tracciato.

---

## 13. Aree di arrampicata e distretti

| Metadati | Priorità | UI |
|---|---|---|
| nome e perimetro geografico, comuni/valle | P0 | H, M |
| elenco falesie, settori, aree boulder, multipitch, palestre vicine | P1 | M, B |
| tipi di roccia prevalenti, esposizioni, varietà di gradi, stagioni | P1/P2 | K, F |
| storia dell'arrampicata, personaggi, chiodatori e fonti | P1/P2 | B |
| accessi, trasporti, servizi e restrizioni territoriali | P1 | M, H |
| fotografie panoramiche e mappe di settore con licenza | P2 | V |

**Layout**: pagina distretto con filtri, mappe e schede figlie; non simulare numero vie se alcune fonti non censiscono tutte le linee.

## 14. Falesie e pareti

| Metadati | Priorità | Fonti | UI |
|---|---|---|---|
| falesiaId, nome, areaId, nome locale, sottotipo crag/parete | P0 | OSM, OpenClimbing, OB | H |
| coordinate, quota baseM, esposizione azimuth, altezza parete | P1 | OSM, fonti | K, M |
| roccia/litologia, stile placca/verticale/strapiombo/diedro/tetto/fessura | P1 | fonti locali | B, F |
| settori[], routesCountKnown, gradesDistribution e scale | P1 | catalogo vie, senza stima | K, T, G |
| orientamento/sole e ombra, stagionalità, asciugatura solo documentata | P1/P2 | fonti territoriali, meteo con prudenza | B, G |
| avvicinamento, parcheggio, accessi consentiti e trasporti | P1 | OSM, OFF, relazioni | B, M |
| manutentore/responsabile chiodatura e data verifica | P1/P2 | OFF, chiodatori | B |
| attrezzatura tipica, accesso per famiglie, servizi | P2 | fonti documentate | B |
| divieti, nidificazione, settore chiuso, dati e scadenza | P0 se esistono | Enti parco/comuni | H |
| storia, prime aperture, foto/settori, topo **solo autorizzata** | P1/P2 | archivi, WC, autori | B, V |

**Layout**: hero roccia verificata → esposizione/roccia/vie/gradi → **settori** → lista vie filtrabile → accesso e parcheggio → avvisi → storia → media e mappe.

## 15. Settori di falesia

| Metadati | Priorità | UI |
|---|---|---|
| sectorId, cragId, nome, aliases, ordine nella guida | P0 | H |
| posizione e orientamento locale, altezza, roccia e ombra | P1 | K, M |
| numero vie censite, lunghezze min/max, intervallo/distribuzione gradi | P1 | T, F |
| difficoltà d'accesso, condizioni particolari, servizi vicino | P1 | B, M |
| restrizioni specifiche e date, topo autorizzate/foto settore | P0/P2 | H, V |

**Layout**: testata compatta, elenco vie come contenuto principale, cartografia del settore, informazioni locali.

## 16. Via di arrampicata monotiro

| Metadati | Priorità | UI |
|---|---|---|
| routeId, sectorId, cragId, nome, numero sulla guida | P0 | H |
| grado originale + gradeSystem + gradeSource; eventuali varianti documentate | P1 | K, F |
| routeLengthM, stile: sport/trad/mixed/toprope, inclinazione | P1 | K, T |
| **boltingType** (spit/fix/resinati/trad/mista), manutenzione datata | P1 | T |
| **boltsCount** = punti intermedi dichiarati e conteggio originale | P1 se disponibile | T |
| **quickdrawsRecommended** **solo da fonte esplicita**, non da boltsCount | P1 se disponibile | T |
| **anchorType**, sosta e calata **come riportate**, senza certificazione | P1 se disponibile | T |
| ropeLengthRecommendedM esplicitamente dichiarata | P1 se disponibile | T |
| friend, dadi, fettucce, materiale extra dichiarato | P1 se disponibile | T |
| stile di scalata, continuità, boulderosa, note tecniche autorizzate | P2 | B |
| apritori, prima libera, data, richiodature e storia | P2 | B |
| avvisi datati, chiusure, roccia o chiodatura segnalate | P0 se esistono | H |
| media della via specifica, topo autorizzata con fonte/licenza | P2 | V |

**Layout**: grado, lunghezza e stile → tabella **protezioni/rinvii/sosta/corda** con campi mancanti marcati «Non disponibile» → contesto e storia → settore e vie vicine. **Numero di spit ≠ numero di rinvii**. Dato assente ≠ via con 0 spit.

## 17. Via multipitch e via alpinistica

Include tutti i campi della via monotiro più:

| Metadati | Priorità | UI |
|---|---|---|
| mountainId, wallId, routeId e attacco documentato | P0/P1 | H, M |
| sviluppo totaleM, dislivello, pitchCount documentato | P1 | K |
| grado max e **grado obbligatorio** distinti, scala originale | P1 | K |
| impegno globale e stile (sport, trad, alpinistica, mista) | P1 | K, B |
| materiale complessivo indicato, tipo di corde documentato | P1 se disponibile | T |
| sequenza pitches[] con note di singolo tiro, discese e soste | P1 | T |
| avvicinamento, discesa, calate, possibili ritirate documentate | P1 | B, M |
| prima ascensione/libera e chiodatori, richiodature | P2 | B |
| topo e immagini parete **con licenza specifica** | P2 | V |

**Layout**: hero della parete, KPI tecnici, **tabella interattiva L1…Ln**, materiale complessivo, storia, accesso/discesa, mappa e fonti. La UI distingue grado max, grado obbligatorio e gradi dei singoli tiri.

## 18. Singolo tiro e singola sosta

| Metadati | Priorità | UI |
|---|---|---|
| routeId, pitchNumber, pitchLengthM, originalGrade/system | P0/P1 | T |
| stile e passaggi caratteristici documentati | P2 | T |
| numero punti fissi **del tiro**, protezioni integrative | P1 se disponibile | T |
| quickdrawsRecommended del tiro, **solo se dichiarati** | P1 se disponibile | T |
| belayId, anchorType, sosta/calata documentate | P1 se disponibile | T |
| eventuale scorrimento corda, difficoltà aggiuntive e avvisi | P2/P0 | T |
| foto/topo di tiro autorizzata, editore e data | P2 | V |

**Non generare pitch sintetici** per monotiri per riempire tabelle. Una sosta non è automaticamente sicura perché presente nel database; eventuale «ultimo controllo» richiede una fonte qualificata.

## 19. Boulder outdoor: area, blocco, problema

**Area**: nome, accesso, roccia, stagionalità, parcheggi, restrizioni, blocchi e fotografìe (P1).  
**Blocco**: posizione, altezza, orientamento, roccia, caratteristiche atterraggio se documentate (P1).  
**Problema**: nome, linea, posizione sul blocco, grado originale Fontainebleau/V, sit/stand, first ascent, altezza, uscita, passaggi, crash-pad **solo se dichiarati**, media e divieti (P1/P2).

**Layout**: overview area → gradi e settori → catalogo blocchi → problemi con filtro per grado e stile → accessi e divieti. Non usare scale sportiva francese e boulder Font come equivalenti.

## 20. Palestre di arrampicata indoor

| Metadati | Priorità | Fonti | UI |
|---|---|---|---|
| nome, indirizzo, coordinate, telefono, sito/social | P0 | OSM, OFF | H, M |
| discipline boulder, lead, speed, top rope, auto-belay | P1 | OFF | K, F |
| pareti, altezza, mq, numero linee/prese se documentati | P2 | OFF | T |
| MoonBoard/KilterBoard/spray wall, palestra pesi, servizi | P1/P2 | OFF | B |
| orari ordinari/festivi e ultimo controllo | P1 | OFF | H |
| ingresso singolo, abbonamenti, noleggio, prezzi con validità | P1/P2 | OFF | T |
| corsi e target, istruttori qualificati se dichiarati, eventi | P2 | OFF/FASI | B |
| accessibilità, docce, parcheggi, bar/ristoro | P1 | OFF/OSM | B, M |
| società/associazione FASI, **non equivalente alla sede fisica** | P2 | FASI | C, B |
| foto/brand ufficiale, aggiornamenti del gestore autorizzati | P2 | OFF | H, V |

**Layout**: contatti/orari, discipline, servizi, prezzi aggiornati, corsi/eventi, falesie vicine e mappa.

---

## 21. Persone, storia dell'alpinismo, vie e prime ascensioni

| Metadati | Priorità | UI |
|---|---|---|
| personId, nome, pseudonimi, date e luoghi di nascita/morte | P0/P1 | H |
| professione/ruolo montano attestato e disciplina | P1 | K |
| città di residenza o luogo attività con relazione **documentata** | P1 | B, M |
| biografia, cronologia, ascensioni/aperture/prime libere | P1/P2 | B, T |
| associazioni, compagni, scuole, rifugi o vie intitolate | P2 | B |
| fotografie storiche, citazioni brevi attribuite, bibliografia | P2 | V, C |

**Layout**: profilo biografico e timeline delle imprese, vie e montagne collegate, luoghi documentati. Filtrare per figure realmente legate alla montagna, non celebrità generiche della stessa provincia.

**Due livelli distinti:** nella scheda del comune si presentano relazioni G1 verificate (nome, ruolo, tipo di legame, eventuale biografia esterna); nel futuro dossier Persona G2 si aggiungeranno cronologia, foto, bibliografia e ascensioni con fonti proprie. Altre figure culturali rilevanti possono figurare in un blocco subordinato solo con **nascita nel comune verificata e biografia enciclopedica identificata**, senza attribuire loro un ruolo alpinistico inesistente.

**Arricchimento tecnico Persona G1 (28/11/2026):** il catalogo `public/data/atlas/people-v1.json` è il registro identitario delle persone; la chiave interna stabile è `person:QID`, distinta dal nome visualizzato e da qualsiasi account. Si importano **P18** (foto legata esplicitamente al soggetto umano), **P569/P570** (date con precisione originale), **P19/P20** (luoghi di nascita/morte, QID), **P106** (ruoli attestati), **P742** (pseudonimi) e, separatamente come *candidati a crosswalk*, **P800/P793/P1344/P463/P166/P101** (opere, eventi, partecipazioni, associazioni, riconoscimenti e campi di attività). I candidati esterni sono relazioni vere in Wikidata **ma non sono automaticamente eventi, falesie, vie o ascensioni del nostro Atlante**: richiedono risoluzione d'identità del target e fonte specifica prima della promozione a `opened_by`, `first_ascended_by`, `managed_by` e simili.

**Media e biografie:** verificare ogni immagine con Commons `imageinfo/extmetadata` (autore/licenza/URL HTTPS) e relazione con il soggetto tramite **P18 su QID umano**. Attenzione: **P18 non dimostra da solo che l'immagine sia un ritratto**; può essere il manifesto di una mostra, un monumento o un'opera. Mantenere anche tali media collegati all'entità, ma usare `portraitCandidate=false` e `needsPortraitReview=true` per impedirne l'uso come avatar. Estratti Wikipedia solo dopo `pageprops.wikibase_item == QID`, conservando licenza CC BY-SA, titolo e URL. Non dedurre immagini dalla somiglianza del nome né generare ritratti. I crediti, inclusi quelli dei personaggi, sono accentrati in `/fonti-e-crediti/`. L'assenza di una foto non è un gate per escludere una persona realmente documentata; non importare contatti privati, indirizzi, residenze attuali di viventi o contenuti sensibili non necessari.

**Profili unificati e rivendicazione futura:** il modello Persona prepara l'interfaccia di profilo pubblico condivisibile con i profili della community, ma **non crea utenti, non collega automaticamente account, non abilita rivendicazioni e non rende le schede biografiche G1 indicizzabili**. `claim.status=not_enabled` e `verifiedUserId=null`; qualsiasi procedura futura esigerà verifica di identità, assenso esplicito e moderazione, distinguendo persona vivente, biografia storica ed eventuali curatori/eredi. Una rivendicazione non deve sovrascrivere facts o relazioni storiche di fonte documentata: contributi e attributi verificati restano separati. Le prime ascensioni e gli apritori delle vie potranno usare gli stessi `personId/QID`, ma solo dopo conferma su fonte pertinente.


## 22. Parchi naturali, aree protette e regolamenti

Campi: nome, ente, confini, categoria e data istituzione, regolamenti documentati, siti ufficiali, ambienti/habitat e geologia, centri visita, sentieri consentiti, zone di nidificazione e divieti con **periodo di validità**, foto e media, collegamenti a POI e falesie (P0/P1).  
**Layout**: overview → territorio → aree di visita → regole e limitazioni datate → POI. Mai presentare un confine amministrativo come accesso consentito.

## 23. Mobilità, impianti, parcheggi e accessi

| Tipologia | Campi specialistici |
|---|---|
| **Funivia/seggiovia/skilift** | nome, stazioni, operatore, orari e stagione, prezzi con data, capacità se ufficiale, collegamento a punti montani, stato confermato |
| **Fermata e trasporto pubblico** | nome, linee, operatore, orari ufficiali/GTFS, accessibilità, ultimo aggiornamento; no orari inventati |
| **Parcheggio** | posizione, posti se mappati, costo e orari datati, restrizioni, distanza al punto di partenza |
| **Accesso sentiero** | coordinate, eventuale trailhead e segnaletica, POI, raggiungibilità certificata soltanto se fonte/routing verificati |

**Layout**: elemento operativo riutilizzabile dentro schede luogo, trekking, falesia, palestra; non generare migliaia di pagine SEO autonome per parcheggi anonimi.

## 24. Meteo corrente, previsione, clima e neve

**Schema di una misura**: metricId, locationId, lat/lon, **modelElevationM o stationElevationM**, observedAt/forecastAt, timezone, variable, unit, value, provider, model/station, precision e retrievedAt.

| Tipo | Metadati | UI |
|---|---|---|
| **Meteo corrente** | temperatura °C, percepita se disponibile, vento km/h e direzione, umidità %, precipitazioni recenti, codice meteo, ultimo update | H, K |
| **Previsione oraria** | ore locali, temperatura, precipitazione mm, neve cm, vento, copertura nuvolosa, probabilità precipitazioni se disponibile | G |
| **Previsione giornaliera** | min/max °C, pioggia, neve, vento, codice e validità previsione | G |
| **Clima storico** | medie mensili °C, medie precipitazione mm, giorni di gelo/pioggia; **periodo pluriennale**, fonte e completezza | G |
| **Neve** | neve caduta cm separata da altezza manto cm, giorni di neve, stazione, quota, fonte, timestamp | G |
| **Avvisi** | allerte vento, valanghe, pioggia, neve, chiusure ufficiali, validFrom/Until | H, B |

**Regole di grafico**: asse x con ore/giorni reali, asse y e unità espliciti, serie neve/precipitazione separate, icone meteo da codici fonte, legenda, tooltip, fuso orario; **vietate linee senza scala**. Il dataset ERA5-Land 2025 non va chiamato *media climatica*: è un solo anno. Nel pilota di due località le temperature storiche erano disponibili, **serie storiche neve/precipitazione assenti**.

**Caching**: previsione e clima sono risorse separate, aggiornamenti differenziati, pagina SEO statica non ricostruita ad ogni ora.

## 25. Webcam e multimedia

| Tipo | Metadati obbligatori o desiderabili | UI |
|---|---|---|
| **Foto attuale** | subjectId verificato, autore, scattoAt se noto, licenza e URL licenza, sourcePage, didascalia, orientamento, dimensione, thumbnail | H, V |
| **Foto storica** | soggetto, anno **dello scatto** e non upload, archivio/autore, diritti, descrizione, collegamenti a soggetti | V |
| **Logo/stemma** | titolare dei diritti, tipo immagine, licenza o permesso, contesto di utilizzo; no loghi inventati | H |
| **Topo/diagramma via** | autore/editore, versione, licenza/permesso e ambito, fonte; link anziché copia se non autorizzato | V |
| **Webcam** | id, operatore, coordinate, **direzione della telecamera**, target visibile, permalink ufficiale, stream/still autorizzato, refreshedAt, licenza, status | V |
| **Video** | provider, id embed autorizzato, titolo, data, credit, soggetti | V |

Nessuna immagine scelta per pura omonimia. **Live ≠ immagine ferma**: ultimo aggiornamento e permessi espliciti. Accordion crediti centralizzato per i dettagli, attribuzioni immediatamente visibili dove imposte dalle licenze.

## 26. Restrizioni, avvisi e informazioni temporanee

Campi: alertId, subjectIds[], affectedGeometry/sections, kind (chiusura, nidificazione, pericolo documentato, accesso, lavori, stagionale), severity **dichiarata dalla fonte**, message, authority, sourceUrl, issuedAt, validFrom/Until, checkedAt, supersededBy, status (active/expired/unverified).  
**Layout**: badge discreto e avviso in alto *solo se supportato da fonte e validità attiva*. Distingue allerta ufficiale, segnalazione community e informazione storica. Non attribuire sicurezza certificata a sentieri, chiodatura e attrezzature.

## 27. Contributi e recensioni della community (futuro, non inventati)

Utente/consenso, resourceId, tipo (correzione, foto, apertura aggiornata, segnalazione danno, commento, recensione), contenuto, createdAt, coordinate se necessarie, stato moderazione, evidenze, validUntil, privacy e licenceConsent. Non fondere automaticamente una segnalazione non verificata con i dati ufficiali. Backend separato da archivio statico; Supabase solo se servono account, file e moderazione.

---

## 28. Sezioni/layout riutilizzabili per tutte le tipologie

| Modulo | Input richiesto | Mostrato se… | Impiego |
|---|---|---|---|
| HeroProfile | name, kind, heroMedia?, shortSummary?, badge verificato? | sempre, fallback topografico se manca foto | tutti |
| QuickFacts | elenco Facts con unità e fonte | almeno 1 fatto non inventato | tutti |
| LocalWeather | weatherRef + quota modello e timestamp | feed disponibile | luoghi, rifugi, cime |
| ClimateCharts | serie annuale con periodo e unità | serie sufficientemente completa | comuni/luoghi |
| HistoryBlock | testo originale e riferimenti | fatti storici con fonte | territorio, trekking, vie |
| IdentityAndOperations | recapiti, orari, proprietà, posti letto | almeno un fatto operativo valido | rifugi, palestre |
| RoutesList | relazioni typed e quality | relazioni effettivamente esistenti | luoghi, rifugi, cime |
| StageList | array di tappe ordinate e ufficialità | almeno una tappa | grandi trekking |
| RouteTechnical | grado, bolts, rinvii, soste, corde | vie; campi mancanti visibili come "Non disponibile" | arrampicata |
| PitchTable | array pitches reali | solo multipitch con tiri censiti | vie |
| GradeHistogram | distribuzione gradi con scala originale | catalogo vie sufficiente | falesie |
| NearbyPlaces | punti geolocalizzati + tipo relazione | join geografico eseguito | tutti i POI |
| TimelyAlert | fonte e validità | avviso documentato rilevante | tutti |
| PhotoArchive | media licensed e data scatto | immagini ammesse | tutti |
| WebcamPanel | feed autorizzato + refresh | feed verificato | luoghi/cime/rifugi |
| CreditsAccordion | sources[] per campo e immagine, aggiornamenti | sempre se importati dati esterni | tutti |

**Comportamento filtri**: motore unico; faccette tipizzate. Esempi: comuni → regione/altitudine/popolazione se presente; rifugi → quota/posti letto/apertura *solo se verificata*; trekking → tappe/durata/ente; falesie → esposizione/roccia/distribuzione gradi; vie → grado/tipo di chiodatura/lunghezza; palestre → discipline/orari/servizi.

## 29. Matrice delle fonti e disponibilità testata

**Legenda**: **TESTATO** = richiesta realmente eseguita nel progetto il 27/11/2026; **CANDIDATO** = fonte plausibile non ancora integrata in import affidabile; **DIRITTI** = licenza/accordo da controllare prima del riuso su scala.

| Fonte | Dati | Stato e limiti |
|---|---|---|
| OSM/Overpass | luoghi, rifugi, cime, acqua, falesie, sentieri, impianti | **TESTATO**; ODbL e attribuzione; dedup per node/way/relation |
| Wikidata | identità, nomi, geografia, popolazione storica, immagini, date, QID | **TESTATO** 37 entità multi-categoria; CC0, non fonte ufficiale per sindaci o censimenti correnti |
| CAI Unico Rifugi | 764 rifugi dichiarati, elenco e dettagli, fields[] e media[] | **TESTATO** 80 listati, 4 dettagli; diritti di ripubblicazione da definire |
| SAT | rifugi, storia, accessi e 18 tappe trentine Sentiero Italia | **TESTATO** con disponibilità occasionalmente variabile; rispettare attribuzioni e condizioni fonte |
| DAIT Ministero Interno | amministratori dei comuni italiani | **TESTATO** CSV con 7.783 record (24/08/2026 nel pilota); match per codice comune |
| ISTAT / cataloghi open data | popolazione e basi amministrative | **PARZIALMENTE TESTATO** accesso a cataloghi, non ancora importate serie recenti per ciascun comune |
| Open-Meteo / ERA5-Land | previsione, temperatura e storico | **TESTATO** 2 località; alcune variabili storiche nulle; quota del modello essenziale |
| Wikimedia Commons | immagini, autore e licenza per file | **TESTATO** 6 immagini; 5 con LicenseUrl esplicito |
| Wikipedia e archivi | sezioni storiche, toponimia e biografie | **TESTATO** rilevamento strutture di 4 pagine; non copia automatica di testi |
| OpenBeta | aree, vie, gradi e primi salitori | **TESTATO** campione 64 record, di cui 10 boulder; -1 = lunghezza assente; CC0 dati, non media |
| OpenClimbing | export OSM delle falesie/vie | **CANDIDATO**, stessa filiera OSM, no conteggio doppio |
| FASI / siti palestre | discipline, società, sedi fisiche, servizi | **CANDIDATO**; associazione FASI ≠ palestra fisica |
| theCrag / guide | chiodatura, vie, singoli tiri, attrezzatura | **CANDIDATO**, accordo/API e copyright prima del riuso |
| ARPA/Meteotrentino/Meteo Alto Adige | neve, stazioni, webcam, avvisi | **TEST ACCESSO PORTALI**: 3 HTTP 200; **nessun feed webcam autorizzato importato** |
| ICCD, Europeana, archivi CAI | storia locale e media storici | **CANDIDATO**, per elemento e licenza |
| INFOMONT/REI e geoportali regionali | catasto sentieri, classificazioni, geometrie | **CANDIDATO / integrazione da completare** |

Non sommare numeri di fonti sovrapposte (OSM e OpenClimbing, CAI e OSM, etc.). Le percentuali dei campioni non sono stime nazionali.

## 30. Progettazione tecnica: pipeline e qualità

1. **Registry** delle tipologie/campi, alias, unità, enum, widget suggerito e regole di validazione.
2. **Ingestion adapters** indipendenti per fonte (batch, rate limit, cache, snapshot, logging, incremental checkpoints).
3. **Raw staging** immutabile con data di recupero, payload minimale e licenze.
4. **Normalization** per tipo, parsing di numeri/date, sentinelle, distinzione ufficiale/stimato, categorie e ruoli.
5. **Entity resolution** OSM/WD/ISTAT/CAI/SAT tramite ID, distanze, nomi e hierarchy; mai auto-merge se ambigui.
6. **Graph enrichment** per relazioni amministrative, fisiche e trekking; distinguere «vicino» da «attraversa» e «raggiungibile».
7. **Editorial validation** con quality gate e revisione di anomalie (nome omonimo, quota incompatibile, sindaco senza anno, foto non pertinente, API in conflitto).
8. **Publish layer** JSON/static shards per pagine e ricerca; indice SEO solo per dossier sufficientemente ricchi. Meteo/live separati e cache.
9. **Frontend adapters** ai componenti unici di ricerca/detail/map; nuove categorie non introducono layout paralleli.
10. **Change log** per nuova fonte, nuove proprietà, versioni schema, regressioni e test UI.

## 31. Quality gate prima della pubblicazione SEO

**G0: grezzo** — fonte e ID, posizione/nome non necessariamente verificati; visibile solo in mappa/catalogo.  
**G1: identificato** — identità riconciliata, fonte e posizione congruenti, slug parlante e URL stabile.  
**G2: informativo** — almeno informazioni specifiche della tipologia, collegamenti pertinenti, testo non boilerplate, licenze e aggiornamenti. Candidato per revisione SEO.  
**G3: dossier verificato** — approfondimenti, media pertinenti, informazioni operative fresche e relazioni accertate.  
Un punteggio numerico è euristico: **non sostituisce la revisione della qualità o la sicurezza dell'itinerario**.

## 32. Decisioni vincolanti per i layout

- Non rifare hero, mapa, header, shell e filtri per ogni categoria: mantenere **un'unica piattaforma di componenti**.
- **I campi determinano le sezioni**, non viceversa; nessuna card vuota o testo inventato per riempire spazio.
- Componenti e spazi devono rispettare la UI full-width e la separazione 42/58 descritta in ARCHITECTURE.md.
- Mappa descrive posizione e relazioni; meteo/storia/grafici/contatti stanno nella colonna contenuti.
- Chiusure ufficiali, dati di apertura e limiti temporanei sono visibili e datati.
- Grafici sempre con scala, unità, legenda, timestamp e periodo; icone meteorologiche basate su codici reali.
- Media corretti per soggetto, con diritti per singolo oggetto; fonte dettagliata in accordion **Fonti e crediti**, attribuzione in vista quando obbligatoria.
- **Slug parlanti** senza codici fonte, con alias legacy e controllo permalink. Esempi futuri coerenti con migrazioni pianificate: /borghi/canazei/, /rifugi/rifugio-antermoia/, /trekking/translagorai/, /falesie/placche-di-baone-arco/, /vie/nome-via-placche-di-baone/.
- Preferire importazioni incrementali e archivio unico a nuove pipeline duplicate o scraping non autorizzato.
- Le informazioni tecniche su chiodatura, rinvii e soste **non costituiscono valutazione di sicurezza o istruzione sufficiente per arrampicare**.

## 33. Stato del documento, evoluzione e responsabilità

Questa è la **fonte canonica dei requisiti di metadati e dei moduli UI** del progetto Cima Becco. Il codice implementativo può usare nomi precedenti fino a migrazione tracciata. Aggiornare questo documento quando si introduce una nuova tipologia, campo, fonte, modulo UI o regola di qualità; annotare nuove verifiche senza confondere «schema supportato», «campo presente nell'API», «valore recuperato» e «dato pubblicato».

La documentazione in AGENTS.md indica questo file come riferimento operativo per gli sviluppi successivi. Le PR sperimentali #7 (arrampicata) e #8 (fonti multi-categoria) sono materiali di supporto, non modifiche live.