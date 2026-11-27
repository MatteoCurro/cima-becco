# Cima Becco — memoria operativa del progetto

Questo file conserva le **decisioni tecniche e di prodotto vincolanti per chi sviluppa Cima Becco**. Non sostituisce la documentazione completa.

## Fonti di verità (leggere prima di lavorare)
1. [Dizionario canonico dei metadati e dei layout](docs/MODELLO_METADATI_E_LAYOUT.md) — **per tutte le entità, le fonti, i componenti UI e i quality gate**.
2. [Architettura e workspace](docs/ARCHITECTURE.md) — struttura dei componenti esistenti, responsive, percorso di navigazione e test.
3. [Fonti escursionistiche](docs/FONTI_ESCURSIONISTICHE.md) — provenienza, licenze, limiti tecnici dei sentieri.

## Decisioni di prodotto da ricordare

- Cima Becco è **atlante informativo della montagna**. Arricchimento massivo dei metadati e relazioni territoriali sono prioritari rispetto all'import di nuove tracce.
- **Una ricerca, una navigazione, un motore geografico, un DetailLayout**, con adapter e filtri specifici per categoria; non creare layout paralleli.
- Categorie: comuni, frazioni/borghi, cime/gruppi, passi/laghi/POI/acqua, rifugi/bivacchi, sentieri, escursioni, ferrate, grandi trekking/tappe, falesie/settori, vie mono-/multipitch/tiri/soste, boulder, palestre, alpinisti, parchi, trasporti, meteo, webcam e avvisi.
- Desktop dettaglio **42% contenuti / 58% mappa**, full-width, mobile responsive: attenersi ad ARCHITECTURE.md, senza stratificazioni CSS.
- Ogni entità possiede **ID interno stabile** indipendente dal **permalink parlante**, con slug alias/redirect per vecchi URL. ID OSM/Wikidata/CAI restano nei dati; la loro attribuzione pubblica e quella dei media e' centralizzata in **/fonti-e-crediti/**, non ripetuta nei dossier (MODELLO_METADATI_E_LAYOUT.md sez. 1.5).
- Dati per campo: fonte, URL, licenza, data, unità, metodo, validità e confidenza. **null** per dato sconosciuto; non inventare dati, storie, gradi, stato di apertura, collegamenti sentieristici e sicurezza.
- **Rinvii consigliati ≠ numero spit**; gradi e scale originali non vanno convertiti arbitrariamente; singoli tiri non devono essere creati se assenti. Priorità a limitazioni e aggiornamenti verificati.
- **Comune ≠ frazione**: sindaco e popolazione comunale non sono proprietà automatiche della frazione. **Vicino ≠ attraversato ≠ raggiungibile**.
- Foto e loghi solo se riferiti con certezza al soggetto e riutilizzabili con crediti; storia e topo protette non vanno copiate senza licenza/permesso.
- Meteo: quota modello, timestamp, assi e unità dei grafici; nevicata ≠ manto nevoso; un anno storico ≠ media trentennale.
- Catalogo e pagine statici dove possibile, API con cache per dati live, ingest incrementale con dedup e log. Solo schede informative sottoposte a quality gate sono candidabili SEO; noindex per contenuti scarsi.
- Non integrare dati del branch sperimentale direttamente in produzione senza revisione di **licenza, identità, qualità, build, URL e regressioni UI**.

## Stato delle prove (fotografia 27/11/2026, non garanzia di disponibilità futura)
- PR #7: arrampicata, OSM Arco e OpenBeta Italia, test import metadata-only.
- PR #8: 37 luoghi Wikidata, 1.778 POI OSM in area pilota, 18 tappe SAT, meteo 2 località, rifugi CAI 80/764 dichiarati, test DAIT/ISTAT/media.
- Per dettagli e limiti usare i report e gli script nelle rispettive PR. Non dichiarare pubblicati dati che sono soltanto in staging sperimentale.

Quando una nuova decisione modifica la tassonomia, aggiornare **prima** il dizionario canonico, poi codice, test e documenti di progetto.