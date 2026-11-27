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
              "Altitudine del centro (metri)", "Superficie territoriale (kmq)"]
DAIT_COLS = ["Codice Comune", "Comune", "Provincia", "Cognome", "Nome",
             "Carica", "Data Elezione"]

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
            ["022039", "Canazei", "Trentino-Alto Adige", "Trento", "1465", "67,55"],
            ["025013", "Cortina d'Ampezzo", "Veneto", "Belluno", "1224", "254,51"],
            ["025001", "Agordo", "Veneto", "Belluno", "-1", ""],
        ])

    def sample_dait(self):
        return b"Aggiornato al 24/08/2026\n" + csv_data(DAIT_COLS, [
            ["022039", "Canazei", "Trento", "Bernard", "Giovanni", "Sindaco", "08/05/2025"],
            ["025013", "Cortina d'Ampezzo", "Belluno", "Lorenzi", "Gianluca", "Sindaco", "12/06/2022"],
            ["025001", "Agordo", "Belluno", "Rossi", "Mario", "Consigliere", "01/01/2024"],
        ]).replace(b"\xef\xbb\xbf", b"")

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
            [22039, "Canazei", "Trentino-Alto Adige", "Trento", 1465, 67.55],
            [25013, "Cortina d'Ampezzo", "Veneto", "Belluno", 1224, 254.51],
        ])
        rows, cols, _ = rows_istat(raw)
        self.assertEqual(len(rows), 2)
        entity = municipality(rows[0], cols, "2026-11-27T12:00:00+00:00")
        self.assertEqual(entity["sourceIds"]["istat"], "022039")
        self.assertEqual(entity["facts"]["surfaceKm2"]["value"], 67.55)

    def test_official_identity_and_dait_join_only_by_code(self):
        doc, report = build(self.sample_istat(), self.sample_dait(), retrieved_at="2026-11-27",
                            min_municipalities=3)
        self.assertEqual(report["municipalities"], 3)
        self.assertEqual(report["mayorsMatched"], 2)
        self.assertEqual(report["indexed"], 0)
        by_code = {e["sourceIds"]["istat"]: e for e in doc["entities"]}
        canazei = by_code["022039"]
        self.assertEqual(canazei["facts"]["mayorNameReported"]["value"], "Giovanni Bernard")
        self.assertEqual(canazei["facts"]["mayorElectionDate"]["value"], "2025-05-08")
        self.assertNotIn("population", canazei["facts"])
        self.assertNotIn("mayorNameReported", by_code["025001"]["facts"])
        self.assertEqual(canazei["quality"]["gate"], "G0")
        self.assertEqual(canazei["facts"]["elevationM"]["unit"], "m")
        self.assertIsNone(canazei["facts"]["elevationM"]["licence"])

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
        self.assertNotIn("mayorNameReported", osm[0])

    def test_same_name_does_not_create_link(self):
        doc, report = build(self.sample_istat(), retrieved_at="2026-11-27", min_municipalities=3,
                            osm_places=[{"kind": "borgo", "name": "Canazei", "wikidata": "Q123",
                                         "lat": 46.47, "lng": 11.77, "slug": "osm-n-1"}])
        self.assertEqual(report["osmLinkedByVerifiedIds"], 0)

    def test_duplicate_istat_is_hard_error(self):
        source = csv_data(ISTAT_COLS, [
            ["022039", "Canazei", "Trentino-Alto Adige", "Trento", "", ""],
            ["022039", "Canazei", "Trentino-Alto Adige", "Trento", "", ""],
        ])
        with self.assertRaisesRegex(ValueError, "duplicati"):
            build(source, retrieved_at="2026-11-27", min_municipalities=1)

    def test_failed_dait_header_is_not_silent(self):
        with self.assertRaisesRegex(ValueError, "Intestazioni"):
            rows_dait(b"foo;bar;baz\n1;2;3")

    def test_mayor_ambiguity_does_not_publish_any_value(self):
        dait = csv_data(DAIT_COLS, [
            ["022039", "Canazei", "Trento", "Rossi", "Mario", "Sindaco", ""],
            ["022039", "Canazei", "Trento", "Bianchi", "Luigi", "Sindaco", ""],
        ])
        doc, report = build(self.sample_istat(), dait, retrieved_at="2026-11-27",
                            min_municipalities=3)
        self.assertEqual(report["mayorsAmbiguous"], 1)
        canazei = next(e for e in doc["entities"] if e["sourceIds"]["istat"] == "022039")
        self.assertNotIn("mayorNameReported", canazei["facts"])

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
