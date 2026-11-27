"""Contratti offline dell'importatore ISTAT/DAIT, senza rete né mutazioni pubbliche."""
import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_municipalities_v1 import (build, rows_istat, rows_dait, municipality,
    code6, number, slugify, reconcile_osm, canonical_bytes)

ISTAT_COLS = ["Codice Comune formato alfanumerico", "Denominazione in italiano",
              "Denominazione Regione", "Denominazione dell'Unità territoriale sovracomunale",
              "Codice Regione", "Sigla automobilistica",
              "Altitudine del centro (metri)", "Superficie territoriale (kmq)"]
DAIT_COLS = ["Codice Regione", "Codice Provincia", "Codice Comune",
             "Denominazione Comune", "Sigla Provincia", "Cognome", "Nome",
             "Descrizione Carica", "Data Elezione", "Data Entrata in Carica"]

def csv_data(cols, data, delimiter=";"):
    file = io.StringIO()
    writer = csv.writer(file, delimiter=delimiter)
    writer.writerow(cols)
    writer.writerows(data)
    return file.getvalue().encode("utf-8-sig")

def xlsx_data(cols, data):
    """Tiny real XLSX OpenXML fixture with shared strings and numerical IDs."""
    from xml.sax.saxutils import escape
    strings = []
    lookup = {}
    def cell(value, index, row):
        col = chr(ord("A") + index)
        if isinstance(value, (int, float)):
            return f'<c r="{col}{row}"><v>{value}</v></c>'
        if value not in lookup:
            lookup[value] = len(strings)
            strings.append(value)
        return f'<c r="{col}{row}" t="s"><v>{lookup[value]}</v></c>'
    matrix = [["Report ufficiale ISTAT"], cols, *data]
    rows = "".join('<row r="%d">%s</row>' % (i, "".join(cell(v, j, i)
                   for j, v in enumerate(vals))) for i, vals in enumerate(matrix, 1))
    shared = "".join("<si><t>" + escape(str(v)) + "</t></si>" for v in strings)
    book = io.BytesIO()
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    with ZipFile(book, "w") as archive:
        archive.writestr("xl/sharedStrings.xml", f'<sst xmlns="{ns}">{shared}</sst>')
        archive.writestr("xl/worksheets/sheet1.xml", f'<worksheet xmlns="{ns}"><sheetData>{rows}</sheetData></worksheet>')
    return book.getvalue()

class MunicipalitiesContracts(unittest.TestCase):
    def sample_istat(self):
        return csv_data(ISTAT_COLS, [
            ["022039", "Canazei", "Trentino-Alto Adige", "Trento", "04", "TN", "1465", "67,55"],
            ["025013", "Cortina d'Ampezzo", "Veneto", "Belluno", "05", "BL", "1224", "254,51"],
            ["025001", "Agordo", "Veneto", "Belluno", "05", "BL", "-1", ""],
        ])

    def sample_dait(self):
        return b'Aggiornato al 24/08/2026\n' + csv_data(DAIT_COLS, [
            ["04", "015", "0390", "CANAZEI", "TN", "Bernard", "Giovanni", "Sindaco", "08/05/2025", "09/05/2025"],
            ["05", "002", "0130", "CORTINA D'AMPEZZO", "BL", "Lorenzi", "Gianluca", "Sindaco", "12/06/2022", "14/06/2022"],
            ["05", "002", "0010", "AGORDO", "BL", "Rossi", "Mario", "Consigliere", "01/01/2024", ""],
        ]).replace(b'\xef\xbb\xbf', b'')

    def test_codes_preserve_zero_and_sentinels(self):
        self.assertEqual(code6("22039"), "022039")
        self.assertEqual(code6("022039"), "022039")
        self.assertIsNone(code6("ABC"))
        self.assertIsNone(number("-1"))
        self.assertEqual(number("67,55"), 67.55)
        self.assertEqual(slugify("Cortina d'Ampezzo"), "cortina-d-ampezzo")

    def test_source_headers_support_csv_and_xlsx(self):
        csv_rows, _, _ = rows_istat(self.sample_istat())
        self.assertEqual(len(csv_rows), 3)
        raw = xlsx_data(ISTAT_COLS, [
            [22039, "Canazei", "Trentino-Alto Adige", "Trento", "04", "TN", 1465, 67.55],
            [25013, "Cortina d'Ampezzo", "Veneto", "Belluno", "05", "BL", 1224, 254.51],
        ])
        rows, cols, _ = rows_istat(raw)
        self.assertEqual(len(rows), 2)
        entity = municipality(rows[0], cols, "2026-11-27T12:00:00+00:00")
        self.assertEqual(entity["sourceIds"]["istat"], "022039")
        self.assertEqual(entity["facts"]["superficieKm2"]["value"], 67.55)

    def test_official_identity_and_dait_join_only_by_code(self):
        doc, report = build(self.sample_istat(), self.sample_dait(), retrieved_at="2026-11-27",
                            min_municipalities=3)
        self.assertEqual(report["municipalities"], 3)
        self.assertEqual(report["mayorsMatched"], 2)
        self.assertEqual(report["daitRowsOfficialCrosswalkRejected"], 0)
        self.assertEqual(report["daitOfficialCrosswalkType"], "ISTAT_REGION_PLUS_PROVINCE_SIGLA_PLUS_EXACT_NAME")
        self.assertEqual(report["indexed"], 0)
        by_code = {e["sourceIds"]["istat"]: e for e in doc["entities"]}
        canazei = by_code["022039"]
        self.assertEqual(canazei["facts"]["sindacoNome"]["value"], "Giovanni Bernard")
        self.assertEqual(canazei["facts"]["dataElezione"]["value"], "2025-05-08")
        self.assertEqual(canazei["facts"]["mandatoInizio"]["value"], "2025-05-09")
        self.assertEqual(canazei["sourceIds"]["dait"], "04/015/0390")
        self.assertNotEqual(canazei["sourceIds"]["dait"], canazei["sourceIds"]["istat"])
        self.assertNotIn("population", canazei["facts"])
        self.assertNotIn("sindacoNome", by_code["025001"]["facts"])
        self.assertEqual(canazei["quality"]["gate"], "G0")
        self.assertEqual(canazei["facts"]["quotaCentroM"]["unit"], "m")
        self.assertIsNone(canazei["facts"]["quotaCentroM"]["licence"])

    def test_qid_join_is_explicit_unique_and_not_name_guess(self):
        rows = json.loads(canonical_bytes(build(self.sample_istat(), retrieved_at="2026-11-27",
                                                min_municipalities=3)[0]))["entities"]
        osm = [
            {"kind": "borgo", "name": "Canazei", "slug": "osm-n-1", "wikidata": "Q123",
             "lat": 46.477, "lng": 11.77, "osmUrl": "https://www.openstreetmap.org/node/1"},
            {"kind": "borgo", "name": "Canazei", "slug": "osm-n-2", "wikidata": "Q999",
             "lat": 46.477, "lng": 11.77, "osmUrl": "https://www.openstreetmap.org/node/2"},
        ]
        qa = reconcile_osm(rows, osm, [{"istatCode": "022039", "wikidata": "Q123"}])
        self.assertEqual(qa["osmLinkedByVerifiedIds"], 1)
        chosen = next(e for e in rows if e["sourceIds"]["istat"] == "022039")
        self.assertEqual(chosen["quality"]["gate"], "G1")
        self.assertEqual(chosen["sourceIds"]["wikidata"], "Q123")
        self.assertFalse(chosen["quality"]["seoIndexable"])
        self.assertNotIn("sindacoNome", osm[0])

    def test_same_name_does_not_create_link(self):
        doc, report = build(self.sample_istat(), retrieved_at="2026-11-27", min_municipalities=3,
                            osm_places=[{"kind": "borgo", "name": "Canazei", "wikidata": "Q123",
                                         "lat": 46.47, "lng": 11.77, "slug": "osm-n-1"}])
        self.assertEqual(report["osmLinkedByVerifiedIds"], 0)

    def test_dait_code_is_not_istat_and_ambiguous_name_stays_unmatched(self):
        mismatched = csv_data(DAIT_COLS, [
            ["04", "015", "0010", "CANAZEI", "BL", "Neri", "Leo", "Sindaco", "", ""],
            ["05", "002", "0130", "CORTINA D'AMPEZZO", "BL", "Lorenzi", "Gianluca", "Sindaco", "", ""],
        ])
        doc, report = build(self.sample_istat(), mismatched, retrieved_at="2026-11-27",
                            min_municipalities=3)
        self.assertEqual(report["mayorsMatched"], 1)
        self.assertEqual(report["daitRowsOfficialCrosswalkRejected"], 1)
        canazei = next(x for x in doc["entities"] if x["sourceIds"]["istat"] == "022039")
        self.assertNotIn("sindacoNome", canazei["facts"])
        self.assertNotIn("dait", canazei["sourceIds"])

    def test_real_dait_format_separate_register_id(self):
        data = b'"Sindaci - elenco completo Italia"\n"Aggiornato al 24/08/2026"\n' + csv_data(
            DAIT_COLS, [["04", "015", "0390", "CANAZEI", "TN", "BERNARD",
                          "GIOVANNI", "Sindaco", "08/05/2025", "09/05/2025"]]).replace(b"\xef\xbb\xbf", b"")
        doc, report = build(self.sample_istat(), data, retrieved_at="2026-11-27",
                            min_municipalities=3)
        self.assertEqual(report["mayorsMatched"], 1)
        self.assertEqual(report["daitRowsOfficialCrosswalkRejected"], 0)

    def test_official_istat_extended_identifiers_and_languages(self):
        columns = ISTAT_COLS + [
            "Denominazione altra lingua", "Codice Catastale del Comune",
            "Codice NUTS3 2024", "Codice Comune numerico con 107 Province (dal 2017 al 2025)",
            "Flag Comune capoluogo di Provincia/Città metropolitana/libero consorzio",
        ]
        rows = [["022039", "Canazei", "Trentino-Alto Adige", "Trento", "04", "TN",
                 "", "", "Cianacei", "B579", "ITH20", "22039", "0"]]
        source = csv_data(columns, rows)
        doc, report = build(source, retrieved_at="2026-11-27", min_municipalities=1)
        entity = doc["entities"][0]
        self.assertEqual(entity["sourceIds"]["istat"], "022039")
        self.assertEqual(entity["sourceIds"]["cadastral"], "B579")
        self.assertEqual(entity["facts"]["nuts3_2024"]["value"], "ITH20")
        self.assertEqual(entity["facts"]["localName"]["value"], "Cianacei")
        self.assertEqual(entity["aliases"][0]["name"], "Cianacei")
        self.assertEqual(entity["facts"]["provinceCapitalFlag"]["value"], False)
        self.assertFalse(entity["quality"]["seoIndexable"])

    def test_south_tyrol_bilingual_name_uses_official_italian_key(self):
        cols = ISTAT_COLS + ["Denominazione (Italiana e straniera)", "Denominazione altra lingua"]
        istat = csv_data(cols, [
            ["021002", "Andriano", "Trentino-Alto Adige", "Bolzano/Bozen", "04", "BZ",
             "", "", "Andrian/Andriano", "Andrian"],
        ])
        dait = csv_data(DAIT_COLS, [
            ["04", "014", "0001", "ANDRIANO", "BZ", "Rossi", "Mario", "Sindaco", "01/05/2025", "01/05/2025"],
        ])
        doc, report = build(istat, dait, retrieved_at="2026-11-27", min_municipalities=1)
        row = doc["entities"][0]
        self.assertEqual(row["name"], "Andriano")
        self.assertEqual(row["slug"], "andriano")
        self.assertEqual(row["sourceIds"]["dait"], "04/014/0001")
        self.assertEqual(report["mayorsMatched"], 1)
        self.assertEqual(report["daitRowsOfficialCrosswalkRejected"], 0)
        self.assertIn("Andrian", [x["name"] for x in row["aliases"]])
        self.assertIn("Andrian/Andriano", [x["name"] for x in row["aliases"]])

    def test_duplicate_istat_is_hard_error(self):
        source = csv_data(ISTAT_COLS, [
            ["022039", "Canazei", "Trentino-Alto Adige", "Trento", "04", "TN", "", ""],
            ["022039", "Canazei", "Trentino-Alto Adige", "Trento", "04", "TN", "", ""],
        ])
        with self.assertRaisesRegex(ValueError, "duplicati"):
            build(source, retrieved_at="2026-11-27", min_municipalities=1)

    def test_failed_dait_header_is_not_silent(self):
        with self.assertRaisesRegex(ValueError, "Intestazioni"):
            rows_dait(b"foo;bar;baz\n1;2;3")

    def test_mayor_ambiguity_does_not_publish_any_value(self):
        dait = csv_data(DAIT_COLS, [
            ["04", "015", "0390", "CANAZEI", "TN", "Rossi", "Mario", "Sindaco", "", ""],
            ["04", "015", "0390", "CANAZEI", "TN", "Bianchi", "Luigi", "Sindaco", "", ""],
        ])
        doc, report = build(self.sample_istat(), dait, retrieved_at="2026-11-27",
                            min_municipalities=3)
        self.assertEqual(report["mayorsAmbiguous"], 1)
        canazei = next(e for e in doc["entities"] if e["sourceIds"]["istat"] == "022039")
        self.assertNotIn("sindacoNome", canazei["facts"])

    def test_stable_id_and_noindex_with_previous(self):
        former, _ = build(self.sample_istat(), retrieved_at="2026-11-27",
                          min_municipalities=3)
        former["entities"][0]["id"] = "permanent-id"
        former["entities"][0]["slug"] = "old-slug"
        revised, _ = build(self.sample_istat(), retrieved_at="2026-11-28",
                           previous=former, min_municipalities=3)
        first = revised["entities"][0]
        self.assertEqual(first["id"], "permanent-id")
        self.assertEqual(first["slug"], "old-slug")
        self.assertFalse(first["quality"]["seoIndexable"])

if __name__ == "__main__":
    unittest.main()
