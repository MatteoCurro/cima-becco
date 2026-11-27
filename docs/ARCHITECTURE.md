# Cima Becco — architettura applicativa
## Contratto
- Un URL canonico per risorsa: /route/:slug/, /rifugi/:slug/, /bivacchi/:slug/, /borghi/:slug/, /trekking/:slug/. Cime: legacy #venue/:slug da migrare separatamente.
- Home e strumenti usano BASE_URL + hash; mai appendere un path a location.hash. La ricerca di un luogo alpino apre direttamente alpinePlaceLink. Gli intenti cartografici restano separati dagli URL di dettaglio.
- Esplorazione: anteprima compatta sulla mappa; azione Scheda completa apre il permalink. Il permalink è la scheda completa, non un secondo template. RoutePanel è la sorgente dei dati e delle sezioni; DetailPrimitives fornisce metriche, fatti, intestazioni e DetailLayout.
- SiteChrome è l'unica navbar/footer. exploreNavigation è il catalogo di navigazione; categorie future falesie e palestre non devono avere link fittizi.
- Shell mappa: stage e map-wrap hanno larghezza esplicita; desktop split, mobile lista o mappa. Navbar mobile su due righe quando c'è ricerca, una altrimenti. Nessun CSS specifico per singolo slug.
- CSS: styles.css base, design.css componenti e shell legacy, cimaSystem.css primitive condivise, locationProfile.css dettaglio geografico. Non duplicare regole nei CSS delle singole pagine.
## Estensioni
Falesie e palestre: scheda geografica con metriche e sezioni specifiche, catalogo e mappa; non creare un quarto layout. Distinguere dati verificati da dati mancanti.
## Gate di rilascio
TypeScript, unit test, build SEO, browser test a 320/375/390/768/1024/1440 px; controllare larghezza reale dei contenitori (non solo overflow), ricerca da home con query/hash, permalink diretto e da anteprima, back/forward, navbar con/senza ricerca. Safari iOS da verificare su dispositivo o WebKit. Non dichiarare verifiche non eseguite.
## Debito residuo
Migrazione completa dei link legacy e VenueDetail, consolidamento CSS storico, test browser effettivi e uniformità dei controlli mappa. Non confondere anteprima con scheda completa.
