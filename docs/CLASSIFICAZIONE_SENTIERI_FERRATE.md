# Cima Becco — Specifica futura: sentieri, ferrate e difficoltà

**Stato:** progettazione della prossima revisione dell'importatore sentieri. NON modifica la pipeline attuale.
**Specifiche vincolanti:** [MODELLO_METADATI_E_LAYOUT.md](MODELLO_METADATI_E_LAYOUT.md), §§ 4, 8–12, 28–32.

## Tipologia, scala tecnica e impegno fisico sono attributi distinti

Il modello deve rappresentare i **tratti della rete fisica** separati dall'**itinerario** (sequenza di tratti), e annotare l'eventuale presenza di segmenti tecnici in un itinerario misto.

1. **Tipo del tratto:** sentiero, mulattiera, ferrata, sentiero attrezzato, alpinistico, collegamento, ignoto; fonte e metodo di classificazione per ogni segmento.
2. **Difficoltà tecnica dichiarata:** sigla originale e scala con fonte (CAI T/E/EE/EEA, eventuale EEA-F/PD/D, SAC T1–T6, via ferrata scale originale). Non convertire le scale o inferire gradi tecnici da dislivello e lunghezza.
3. **Impegno fisico calcolato:** distanza, salita/discesa, quote min/max, salita/km, durata con metodo; qualità GPS/DEM e campi non disponibili esplicitamente distinti da zero.
4. **Esposizione, stato, attrezzature, chiusure e validità:** solo elementi documentati dalla fonte. La geometria GPX non certifica condizioni o protezioni.

## Criteri futuri per individuare le ferrate

| Indizio o evidenza | Trattamento prudente |
| --- | --- |
| Scheda CAI/SAT del percorso esatto, identità e geometria verificate | Ferrata documentata; mantenere grado tecnico originale |
| OSM way/relation con tipologia specifica (p.es. highway=via_ferrata, via_ferrata_scale) e geometria pertinente | Candidata ferrata con fonte, identità da verificare |
| Nome contenente «via ferrata», «ferrata» o «Klettersteig» | Possibile ferrata: revisione necessaria |
| CAI EEA senza altra evidenza | Percorso attrezzato: NON automaticamente una ferrata |
| GPX ripido, lento, breve o con forte dislivello | NON prova di ferrata o di difficoltà tecnica |
| Itinerario misto che attraversa una ferrata | Segnalare il segmento attrezzato, non riclassificare tutta la rete |

Una ferrata richiede metadati documentati su ingresso/uscita, sviluppo, avvicinamento, via, discesa, grado originale, esposizione, materiale, scale/staffe/catene/cavi, gestore, date e avvisi; campi ignoti non vanno riempiti. CAI distingue sentieri con brevi tratti attrezzati da ferrate propriamente dette. Fonti: [CAI classificazione delle difficoltà](https://organizzazione.cai.it/commissione-centrale-escursionismo-cicloescursionismo/documenti-cce/difficolta-escursionsistiche/), [CAI Pisa - classificazioni approvate](https://www.caipisa.it/chi-siamo/classificazione-dei-percorsi-in-base-alla-difficolta-in-ambito-escursionistico-e-cicloescursionistico/).

## Le etichette ironiche sono una terza dimensione editoriale

**Preservare** MERENDEROS, MUOVI QUELLE GAMBE, GAMBE IN SCIOPERO, OGGI SI BESTEMMIA, NON FARE IL FENOMENO, AVAMBRACCI IN LEASING e IL VUOTO TI FA CIAO. Non sono mai conversioni di una classe CAI/SAC.

Ogni scheda deve mostrare:
- grado **tecnico** originale e la sua fonte (oppure «da verificare»);
- **impegno fisico** stimato e spiegato con km, metri di salita, salita/km, quota e metodo;
- soprannome ironico dall'incrocio dei due assi, con motivazione testuale;
- avvisi ferrata, esposizione, eventuale meteo/chiusura e condizioni sempre separati dalla battuta.

Esempio astratto: CAI E, 18 km e +1.200 m può essere «GAMBE IN SCIOPERO» ma resta CAI E, NON diventa EE. Una ferrata senza scala mantiene grado tecnico ignoto a prescindere dalla lunghezza del GPX. Se il dislivello manca, la valutazione fisica resta parziale.

Prima di stabilizzare le soglie stimabili, campionare una varietà di percorsi reali e registrare algoritmo/versione, risultati e anomalie; non confondere uno score euristico con l'idoneità escursionistica.

## Relazioni cima–sentieri–ferrate–rifugi/bivacchi

- Accesso alla cima **verificato**: solo relazione esplicita e qualificata ascends_to / accessible_from sulla stessa identità, fonte e data.
- Estremità GPX entro 100 m dalla cima: «termina nei pressi», NON «raggiunge la vetta».
- Traccia entro 160 m: «passa vicino», NON accesso certo.
- Ferrata nel contesto territoriale: «ferrata nell'area», NON collegamento verificato.
- Rifugio/bivacco segnalato entro 180 m dal GPX negli stop associati: «presso una traccia mappata», non prova di accessibilità o apertura.
- Rifugio/bivacco a distanza limitata: «nei dintorni, distanza in linea d'aria», non punto d'appoggio certificato.
- Itinerari concatenati, grandi trekking e tappe: verificare intersezioni e continuità fisica del grafo prima di proporre l'attraversamento.

I componenti attuali di sola presentazione sono src/lib/routeClassification.ts, src/lib/routeEditorial.ts, src/lib/summitApproach.ts. Non modificano i dataset sorgenti.

## Fasi della prossima attività, NON avviate

1. Audit sui percorsi importati: falsi positivi ferrata/EEA e casi misti, confronto con fonti CAI/SAT; matrice di classificazione.
2. Progettazione registry segmenti/itinerari/ferrate con ID fonte e scala originale.
3. Staging con risoluzione identità OSM/CAI/SAT, deduplicazione e alternative.
4. Grafo dei sentieri e archi di accesso documentati, evitando geografia=accessibilità.
5. Interfaccia con segnalazioni tecniche e filtri ferrata distinti dalla semplice rete escursionistica.
6. Test offline, pilota reale, audit, rilascio graduale e controlli G0–G3 della bibbia.

**Esplicito vincolo operativo:** per questo intervento nessun importatore sentieri o file dei tracciati di produzione viene modificato.
