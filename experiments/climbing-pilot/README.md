# Cima Becco — Import pilota arrampicata, risultati verificati (27/11/2026)

Branch sperimentale: `experiment/content-taxonomy-climbing-import`, PR #7. Nessuna modifica a `main`, ai layout o alla SEO in produzione.

## Metodologia

- OSM: una richiesta Overpass limitata a bbox **45.87, 10.82, 45.99, 11.03** (Arco/Valle del Sarca), `nwr[sport=climbing]` + `nwr[climbing]`. Solo tag e localizzazione; nessuna geometria o GPX pubblicato.
- OpenBeta: una richiesta GraphQL, primi **25** sottosettori/aree terminali con filtro paese `Italy`. Campione di convenienza, **non** le medesime falesie di Arco.
- Provenienza: fonte/URL/licenza per record. Assenza dati `null` per l'uso successivo.
- Test automatici verificano che lo spit non venga trasformato in un numero di rinvii e che lunghezze `-1` non diventino misure reali.

## Risultati OSM Arco

| Campo | Copertura |
|---|---:|
| Elementi complessivi | **150** |
| Nome presente | **129** |
| Vie classificate come tali | **82** |
| Falesie/pareti `climbing=crag` | **31** |
| Siti `sport=climbing` non classificabili con certezza | **31** |
| Palestre | **4** |
| Vie con almeno un grado | **33 / 82** |
| Vie con lunghezza | **22 / 82** |
| Vie con numero tiri | **29 / 82** |
| Vie con numero spit esplicito | **1 / 82** |
| Vie con numero rinvii verificabile | **0 / 82** |

Nei 150 elementi, la copertura OSM include inoltre: tipo roccia **19**, accesso **16**, orientamento **6**, sito web **7**, descrizione **4**; non necessariamente riferiti alle sole vie.

Esempio specifico del campione: la voce OSM [Excalibur](https://www.openstreetmap.org/node/7709988020) riporta **9b+** e **7 spit**. È solo un valore di fonte **non verificato sul terreno** e NON autorizza a prescrivere 7 rinvii o attestare la sicurezza della chiodatura.

## Risultati OpenBeta Italia

| Campo | Copertura |
|---|---:|
| Aree terminali richieste | **25** |
| Record complessivi restituiti | **64** |
| Vie con corda (sport/trad) | **46** |
| Problemi boulder | **10** |
| Tipologia non classificata | **8** |
| Con almeno un grado | **45 / 64** |
| Lunghezza validata | **0 / 64** |
| Conteggio spit validato | **0 / 64** |
| Descrizione valorizzata | **5 / 64** |
| Prima ascensione valorizzata | **1 / 64** |

Il primo report provvisorio erroneamente contava **64 lunghezze**: tutti i record avevano il valore convenzionale `length=-1`. Il normalizzatore è stato corretto a `null`, con un test di regressione. Anche i boulder sono stati separati dalle vie.

## Decisioni

1. Salvare una *identità distinta per crag / settore / via / tiro*, senza inferire la gerarchia solo dal nome.
2. Preservare il grado originale, la scala e la fonte, incluse possibili incongruenze.
3. `boltsCount`, `quickdrawsRecommended`, `anchorType`, `pitchesCount`, `pitchDetails`, `ropeLengthRecommendedM` come campi autonomi, `null` se sconosciuti.
4. Non dedurre lo stato delle soste o la sicurezza dalla presenza di spit.
5. Importare da OpenClimbing quando è pratico usare l'export OSM, trattandolo **come stessa famiglia di dati OSM**, non fonte indipendente da conteggiare due volte.
6. OpenBeta è una sorgente complementare CC0 (non foto); in questo campione il numero di spit è assente nonostante il campo esista.
7. theCrag e guide commerciali: integrazione soltanto tramite API/autorizzazioni esplicite. Per chiodatura, rinvii, soste e tiri servono ulteriori fonti/partnership o contribuzioni controllate.
8. Pubblicare come pagina SEO solo entità con dati sufficienti e identificazione verificata; URL parlanti, fonti e riferimenti in accordion crediti.

## File

- [Tassonomia dettagliata](../../docs/CONTENT_TAXONOMY_V1.md)
- [Registro di campi machine-readable](../../schemas/content-registry.v1.json)
- [Importer OSM](../../scripts/pilot_climbing_metadata.py)
- [Importer OpenBeta](../../scripts/pilot_openbeta_metadata.py)
- [Workflow CI](../../.github/workflows/pilot-climbing-metadata.yml)

Dati completi scaricabili dagli artefatti GitHub Actions della PR. I due campioni non permettono una stima della disponibilità nazionale: servono più regioni e più fonti prima della produzione.
