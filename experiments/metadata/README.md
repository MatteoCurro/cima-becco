# Cima Becco — simulazione del motore metadata-first
Data: 27 novembre 2026. Solo branch `experiment/metadata-atlas-engine`, nessun rilascio in produzione.

## Obiettivo
Riutilizzare i dati geografici e i metadati già censiti per sviluppare un atlante indicizzabile di luoghi e itinerari, **senza importare ulteriori tracce**. Distinguere costantemente le descrizioni realmente presenti nelle fonti dalle descrizioni di servizio costruite con template.

## Inventario integrale dei luoghi (dati effettivi)
Fonte: `public/data/alpine-places.json`. Analizzati **2.326** luoghi: **1.857 borghi/località**, **436 rifugi**, **33 bivacchi**.
- **934** con identificativo Wikidata valido (Q-id).
- **73** con collegamento Wikipedia.
- **1.430** con quota numerica (alcune quote stimate da DEM, non ufficiali).
- **172** con sito web; **122** con gestore indicato.
- **5** descrizioni originali; **10** con foto.
- **248** record hanno un nome ripetuto all'interno della rispettiva categoria. Non si deve deduplicare solo per nome.
- **1.610** hanno score editoriale <= 1 con la semplice euristica sperimentale.
- **180** sono candidati a revisione editoriale secondo score >= 3 e nome univoco: **non sono automaticamente pronti per l'indicizzazione**.

Esportazione reale normalizzata: `experiments/metadata/places-normalized-preview.json`. Nessuna informazione esterna aggiunta; ogni record conserva l'origine OSM.

## Campione effettivo dei metadati itinerario
Fonte: 4 shard geografici esistenti (`it_46_11_000`, `it_46_11_001`, `it_46_12_000`, `it_46_13_000`). **770** itinerari analizzati su un catalogo censito di **7.755**; campione di convenienza, non rappresentativo dell'intero archivio.
- **611** con numero/riferimento sentiero.
- **272** con uno o più POI/luoghi vicini; **353** identificativi di luogo distinti in tali collegamenti.
- **264** con operatore/gestore indicato.
- **185** con difficoltà CAI.
- **178** con URL di approfondimento.
- **9** con identificativo Wikidata.
- **0** con descrizione originale differente dal boilerplate presente nei record del campione.
- **295** record con nomi duplicati nel campione: una località o il riferimento devono disambiguare il titolo.

Esportazione reale: `experiments/metadata/routes-normalized-preview.json`; **nessun GPX, nessuna coordinata, nessuna geometria**. Le associazioni ai POI indicano **prossimità geometrica**, non passaggio certo o accessibilità.

## Motore prototipo
- `scripts/metadata_atlas_engine.mjs`: normalizza tutte le schede luogo, registra provenienza, score e collisioni; modalità simulazione offline e modalità **esplicita** `--fetch` per arricchimento Wikidata in batch con cache e retry, senza scraping indiscriminato.
- `scripts/metadata_route_catalog.mjs`: rilegge tutti gli shard della repository e genera un archivio SOLO metadati e l'indice inverso percorsi↔luoghi; non copia geometrie.
- `tests/metadata_engine.test.mjs`: test di provenienza, stime, collisioni, falsi duplicati, filtraggio di testo boilerplate e assenza di coordinate dal documento itinerario.

### Comandi di prova (dopo checkout del branch)
```bash
node --test tests/metadata_engine.test.mjs
node scripts/metadata_atlas_engine.mjs
node scripts/metadata_route_catalog.mjs
# Solo quando si vuole interrogare davvero Wikidata:
node scripts/metadata_atlas_engine.mjs --fetch --limit 100
```
Il fetch Wikidata **non è stato eseguito in questa simulazione**: qui misuriamo il potenziale e prepariamo la raccolta. Il comando `--fetch` è pensato per l'esecuzione controllata, non per interrogazioni aggressive.

## Regole da mantenere nella fase operativa
1. Una risorsa ha identificativo interno stabile e riferimenti esterni multipli. Non deduplicare per semplice somiglianza dei nomi.
2. Separare dato originale OSM (ODbL), dato Wikidata (CC0), descrizioni Wikipedia (se riusate, licenza e attribuzione specifiche), stime DEM e testi editoriali originali.
3. Mai presentare descrizioni generate da template come conoscenza storica verificata. La marcatura `isTemplate` consente di lasciarle fuori dall'indicizzazione selettiva.
4. Non chiamare “percorso che attraversa il rifugio” un tracciato che passa soltanto nelle vicinanze.
5. Nessuna modifica al catalogo, ai permalink o al frontend di produzione durante l'attuale revisione UI.
6. Per i grandi volumi, preferire acquisizioni incrementali da dataset/download ufficiali e cache anziché chiamate massicce agli endpoint comunitari.

## Risultato
Il collo di bottiglia NON è la quantità di tracce. È la scarsa densità di metadati: nel catalogo luoghi troviamo già centinaia di identificativi esterni recuperabili, ma quasi nessuna descrizione utilizzabile. La prossima attività è collaudare l'arricchimento dei 934 Q-id, verificare fonti/licenze e fare il matching dei nomi ambigui prima di pubblicare nuove pagine SEO.

## Collaudo completo su GitHub Actions — esito verificato
Esecuzione [metadata-only atlas](https://github.com/MatteoCurro/cima-becco/actions/runs/46036891237) conclusa con **successo** il 27/11/2026.

- 3 test automatici superati, 0 falliti.
- 7.755 schede itinerario deduplicate per slug ed elaborate senza geometrie; 6.318 con riferimento sentiero, 1.748 con difficoltà CAI riportata, 1.742 con luoghi vicini, 1.573 luoghi distinti associati, 3.193 record con titolo non univoco.
- 934 record luogo con Q-id; **931 entità Wikidata distinte recuperate** con descrizioni brevi, denominazioni alternative quando presenti e collegamento alla voce italiana quando disponibile.
- Archivio cache salvato nel **solo branch sperimentale**: `experiments/metadata/wikidata-cache.json`.
- Le schede luogo candidate alla **revisione** secondo un'euristica interna salgono da 180 (solo OSM) a **852** con l'arricchimento Wikidata. Questo numero NON equivale a 852 pagine pronte per Google.
- Nessuna modifica al sito in produzione e nessun GPX/geometria distribuito nell'output editoriale.

Criterio di conteggio: 934 record OSM fanno riferimento a 931 Q-id unici, perché alcuni luoghi condividono lo stesso identificativo. Non vanno fusi automaticamente: è un segnale che richiede verifica di identità.
