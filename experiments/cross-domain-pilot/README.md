# Cima Becco — collaudo trasversale fonti e metadati, 27 novembre 2026

Branch: `experiment/cross-domain-data-pilot`; PR draft [#8](https://github.com/MatteoCurro/cima-becco/pull/8) impilata sulla sperimentazione arrampicata #7. Non modifica produzione, frontend, permalink, SEO o GPX.

## Perimetro e risultato

| Area | Richiesta reale | Esito verificato | Limitazioni |
|---|---|---|---|
| **Comuni, frazioni, rifugi e bivacchi** | 37 entità Wikidata | 37/37 risposte; 18 località, 14 rifugi, 5 bivacchi. 24 quote, 25 immagini, 14 siti, 10 date fondazione, 3 popolazioni, 1 stemma, 33 P131 | popolazione QID non equivale a censimento ISTAT corrente, stessi nomi possono indicare entità diverse |
| **Geografia e POI montani** | Una bbox 46.40–46.57 N, 11.67–11.92 E | **1.778 elementi OSM**, inclusi 232 vette, 47 rifugi, 40 passi, 78 specchi d'acqua, 168 punti acqua, 269 stazioni impianti, 799 informazione | 1 elemento OSM ≠ 1 luogo editoriale; dedup obbligatoria |
| **Vicini geografici** | Join geodetico verso il nostro catalogo | 123 record esistenti con almeno un POI vicino | distanza **in linea d'aria**; nessuna raggiungibilità accertata |
| **Trekking a tappe** | Tabella SAT Sentiero Italia | **18 tappe** importate live in una delle esecuzioni, 17 D+, 18 D−, 18 durate, 18 classificazioni | terminazioni non sempre coincidono letteralmente; una prima richiesta a SAT aveva restituito pagina non utile. Previsto fallback con attribuzione esplicita |
| **Meteo** | Due località, Canazei e Rifugio Antermoia | 2 previsioni 5gg e 2 serie di temperatura mensile per il 2025 | 2025 **non** è media trentennale; per questa richiesta i campi storici pioggia/neve erano null (0/2 disponibili) |
| **Storia e toponimi** | Pagine SAT e Wikipedia | 2 schede rifugi SAT con sezioni Storia, Accessi, Ascensioni, Traversate; 4 pagine Wikipedia analizzate per intestazioni | nessun testo originale massivamente copiato; contenuti da licenziare/attribuire |
| **Fotografie** | Commons imageinfo | 6 file controllati, 5 con URL esplicito di licenza | anche il file privo di LicenseUrl può essere public domain, verificare metadati e autore prima del riuso |
| **Rifugi CAI** | OpenAPI + GET catalog | 10 endpoint documentati, GET elenco pubblico senza token, **80 record acquisiti**, tutti con quota, nome, coordinate. Il backend segnala **764** record totali | il campo annidato `data` nel listato è null. Dettagli e **licenza di ripubblicazione** da verificare prima del mass import; 764 è totale riportato dalla API, non ancora acquisito |
| **Sindaci italiani** | CSV ufficiale Ministero Interno / DAIT | 7.783 record dati dopo corretta gestione delle due righe introduttive, aggiornamento indicato **24/08/2026**. Campione: Canazei = **Giovanni Bernard**, Moena = **Alberto Kostner**, Cortina d'Ampezzo = **Gianluca Lorenzi**, con data di elezione nel CSV | sindaco = attributo del comune, non della frazione; confermare codici ISTAT, mandati e licenza |
| **Dati demografici istituzionali** | Cataloghi CKAN | 2 dataset trovati, 3 risorse ciascuno e risposta HTTP 200 | le risorse verificate sono 2019/2020, **non** copertura demografica aggiornata! Occorre fonte ISTAT attuale |
| **Alpinisti** | Wikidata SPARQL, professione + luogo nascita | 1 persona candidata nel piccolo campione: **Luigi Micheluzzi**, nato a Canazei, alpinista | collegamento editoriale da verificare nelle biografie indipendenti, non usare persone genericamente note come montanari |
| **Webcam** | Portali Meteotrentino, ARPAV, Alto Adige | 3 pagine HTTP 200 | **0** feed live/istantanee autorizzate importate, geolocalizzazione e diritti da indagare |

## Regole consolidate
1. Ogni fatto ha fonte, identificativo origine, data, licenza, unità e validità quando rilevante.
2. Rifugi e comuni si collegano tramite coordinate e ID, non sulla sola somiglianza dei nomi.
3. Data mancante, campo assente o -1 convenzionale diventano `null`, non 0; stagione rifugio e meteo hanno timestamp.
4. Sentieri, punti acqua, rifugi, falesie, vette e impianti possono essere indicizzati in un grafo spaziale; **vicino** non significa **accessibile da**.
5. Tappe SAT ufficiali sono separate da itinerari concatenati algoritmicamente; mai fingere continuità tecnica non verificata.
6. Le pagine aggregano dati strutturati e testi documentati; immagini e prose riutilizzate solo con diritti adeguati.
7. Slug parlanti e stabili; i codici delle fonti stanno nei credits centralizzati. Nessuna pubblicazione automatica prima del quality gate.
8. La possibilità tecnica di interrogare un'API **non equivale a permesso di copiare e ripubblicare** i suoi contenuti.

## Decisione e ordine di sviluppo

**Subito:** normalizzare 764 rifugi CAI se consentito (iniziare con dettagli), unire al catalogo luoghi con entity resolution; import DAIT keyed per comune e fonte ISTAT aggiornata; costruire 18 tappe SAT come entità con relazioni ufficiali; indice POI e distanze in linea d'aria.

**Poi:** temperature mensili 30 anni e meteo API, foto con crediti, contenuti storici sintetizzati da fonti, identità comunale/frazione; infine webcam live autorizzate e collegamenti sentieri verificati.

## Reperibilità
I JSON di esecuzione restano negli artifact GitHub Actions del workflow `Experimental — multi-domain data coverage`; lo staging è separato dai dati distribuiti da GitHub Pages. Nessun dataset nuovo è stato aggiunto al sito pubblico.
