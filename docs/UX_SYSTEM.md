# Cima Becco — sistema UX e gerarchia dei contenuti

Versione di riferimento: novembre 2026. Questo documento evita interfacce duplicate e regole CSS ad hoc.

## Architettura di navigazione
1. **Sentieri** (`#routes`) e **Cime** (`#map`): esperienze cartografiche principali, stesso componente MapLibre, un solo dominio attivo per volta.
2. **Rifugi**, **Bivacchi**, **Paesi** (`#atlante/rifugi`, `#atlante/bivacchi`, `#atlante/borghi`): categorie distinte con mappa filtrata e scheda locale uniforme.
3. **Trekking a tappe**: progetti con segmenti verificati, mai tracce inventate.
4. **Atlante completo**: voce nel footer; non sostituisce la mappa principale.

## Principi di lettura: ordine obbligatorio
- **Scheda percorso:** tipologia e titolo → difficoltà tecnica/editoriale (etichetta compatta) → descrizione breve → distanza, dislivello +/−, tempo → profilo altimetrico → foto e tappe vicine → acqua e dettagli eventuali → navigazione, sicurezza, segnalazioni e recensioni.
- **Scheda locale:** categoria e nome → descrizione → quota / capienza / sentieri vicini → CTA telefono/email/mappa → immagine documentata con credito → dati strutturati → cartografia dedicata con layer opzionali → percorsi → meteo → acqua → gestione comunitaria → provenienza dati.
- **Bivacco:** categoria separata da un rifugio custodito; mostra disponibilità e accesso solo quando realmente dichiarati. Non attribuire servizi inesistenti.
- **Cima:** titolo, altitudine, posizione, difficoltà/itinerari collegati e fonti, senza appesantire il popup.

## Componenti e CSS
- Variabili e override condivise in `src/cimaSystem.css` (caricato dopo il CSS precedente); nuovi componenti devono usare gli stessi token. Evitare nuove classi di etichette/gradi e CSS `!important` locali.
- Titoli: **Bricolage Grotesque**, corpo e label: **Space Grotesk**; `Barlow Condensed` solo per accenti editoriali limitati.
- Contrasto: testo scuro su sfondi chiari, testo bianco su verde; fucsia per CTA e accenti, non per paragrafi.
- Metriche prima dei servizi opzionali, layout leggibile mobile (min 320–390px), CTA con area attiva >=44px.
- Le battute del progetto restano nel microcopy, ma non sostituiscono informazioni tecniche né norme di sicurezza.

## Regole mappe e cluster
- Mappa principale **solo cime oppure solo percorsi**; rifugi/paesi/bivacchi/acqua sono categorie autonome.
- Le mappe locali riusano la stessa basemap topo/satellite 2D; **nessun 3D** in questa fase.
- Aggregati come **pill** con un solo sistema numerico, non cerchi rosa + cifre né cluster simultanei di specie diverse.
- Acqua e sentieri vicini in una pagina locale come **layer separati**; acqua spenta per default.
- Non qualificare mai la mera distanza dal tracciato come accesso o collegamento certo.

## Contratto dati e immagini
- `AlpinePlace.kind` è `rifugio | bivacco | borgo`. Fonte primaria OSM, integrazione Wikidata/Commons; campo omesso significa **dato non disponibile**, non zero o chiuso.
- Foto: solo proprietà/licenze verificate da Commons e attribuzione visibile. Fonti ammesse: OSM File, Wikidata P18, categoria P373 puntuale, foto geolocalizzata **con forte match del nome**. Non assegnare foto per sola vicinanza.
- Foto non cliccabili nelle card e nelle hero: il link alla fonte serve solo nel credito discreto per rispetto della licenza.
- Non inventare quote, orari, apertura, gestore, recapiti, capienza, accessibilità, recensioni.
- Indicazioni neve e pioggia sono previsioni da modello; esplicitare l'origine e i limiti.

## Comunità: da sviluppare, NON attiva
- Gestore del rifugio richiede la presa in carico; l'amministratore verifica manualmente il ruolo e assegna permessi.
- Domande visibili solo dopo moderazione; risposte ufficiali firmate dall'account gestore verificato.
- Recensioni con autore autenticato, segnalazioni, antispam, audit e diritto di replica; non mostrare rating fino a dati sufficienti.
- Nessuna scheda può dirsi «gestita» prima che l'approvazione sia registrata lato server.

## Checklist per modifiche future
1. Verificare la pagina equivalente esistente e riusare componenti, mappa, API e CSS.
2. Controllare ordine delle informazioni e contrasto anche su mobile; non creare un secondo linguaggio grafico.
3. Verificare il tipo OSM e l'affidabilità dei dati (inclusi attributi mancanti).
4. Lanciare test Python, TypeScript, test web, build Vite/SEO; collegare PR e test.
5. Verificare foto, license credit, fonte e che i link di navigazione portino alla stessa esperienza.
