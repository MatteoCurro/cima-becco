"""SAT 2026 real-field normalization: no unsafe official identity or auto ferrata."""
from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from normalize_sat_trails_v1 import (
    normalize_archive, as_nonnegative_integer, as_minutes, parse_line, CHANNEL,
)

AT = "2026-11-28T14:00:00+00:00"

VALUES = {
    "numero": "E731", "competenza": "SAT O.C.", "denominaz": "",
    "difficolta": "E", "loc_inizio": "BIVIO FOSNE", "loc_fine": "PRATI RONZI",
    "quota_iniz": "1329", "quota_fine": "1477", "quota_min": "1330",
    "quota_max": "1567", "lun_planim": "4360", "lun_inclin": "4410",
    "t_andata": "01:45", "t_ritorno": "01:45",
    "gr_mont": "PALE DI SAN MARTINO", "comuni_toc": "PRIMIERO",
}


def placemark(data=VALUES, number=None, coords="11.85,46.20 11.83,46.22"):
    props = {**data}
    if number is not None:
        props["numero"] = number
    entries = "".join(f'<SimpleData name="{key}">{value}</SimpleData>'
                      for key, value in props.items())
    return f'<Placemark><ExtendedData><SchemaData>{entries}</SchemaData></ExtendedData>' \
           f'<LineString><coordinates>{coords}</coordinates></LineString></Placemark>'


def zip_records(items):
    xml = '<?xml version="1.0"?><kml xmlns="http://www.opengis.net/kml/2.2"><Document>' \
          + "".join(items) + '</Document></kml>'
    data = BytesIO()
    with ZipFile(data, "w", ZIP_DEFLATED) as z:
        z.writestr("sentieri_tratte.kml", xml)
    return data.getvalue()


class SATTypedG0Tests(unittest.TestCase):
    def test_source_fields_are_typed_with_units_and_original_value(self):
        raw = zip_records([placemark()])
        doc = normalize_archive(raw, retrieved_at=AT)
        record = doc["records"][0]
        self.assertEqual(record["sourceIds"]["satTrailNumberReported"], "E731")
        self.assertIsNone(record["displayNameReported"])
        self.assertEqual(record["facts"]["lengthPlanimetricReportedM"]["value"], 4360)
        self.assertEqual(record["facts"]["lengthPlanimetricReportedM"]["unit"], "m")
        self.assertEqual(record["facts"]["durationOutReportedMin"]["value"], 105)
        self.assertEqual(record["facts"]["durationOutReportedMin"]["unit"], "min")
        self.assertEqual(record["facts"]["durationOutReportedMin"]["rawValue"], "01:45")
        self.assertEqual(record["originalContext"]["competentEntity"], "SAT O.C.")
        self.assertEqual(record["originalContext"]["startPlaceAsText"], "BIVIO FOSNE")
        self.assertEqual(record["originalDifficulty"]["value"], "E")
        self.assertIsNotNone(record["lengthFromSourceGeometryM"])
        self.assertEqual(record["geo"]["geometry"]["type"], "LineString")

    def test_safety_contract_no_auto_ferrata_or_accessibility(self):
        data = {**VALUES, "difficolta": "EEA-D", "denominaz": "VIA FERRATA TEST"}
        record = normalize_archive(zip_records([placemark(data)]), retrieved_at=AT)["records"][0]
        self.assertEqual(record["originalDifficulty"]["value"], "EEA-D")
        self.assertIsNone(record["officialCatalogueSubtype"])
        self.assertFalse(record["quality"]["canonicalIdentityVerified"])
        self.assertFalse(record["quality"]["traversableVerified"])
        self.assertFalse(record["quality"]["crosswalkVerified"])

    def test_duplicate_number_and_exact_duplicate_are_kept_in_review(self):
        doc = normalize_archive(zip_records([placemark(), placemark()]), retrieved_at=AT)
        self.assertEqual(doc["counts"]["sourcePlacemarks"], 2)
        self.assertEqual(doc["counts"]["uniqueNumbers"], 1)
        self.assertEqual(doc["counts"]["duplicateNumberExcess"], 1)
        self.assertEqual(doc["counts"]["exactDuplicateExcess"], 1)
        self.assertEqual(doc["unresolvedDuplicateNumbers"], {"E731": 2})
        self.assertTrue(all("duplicate_sat_number" in x["quality"]["issues"]
                            for x in doc["records"]))
        self.assertTrue(all(not x["quality"]["sourceNumberUniqueInSnapshot"]
                            for x in doc["records"]))
        self.assertEqual(len(doc["records"]), 2)

    def test_unique_code_does_not_mean_canonical_oss_identity(self):
        raw = zip_records([placemark(number="E731"), placemark(number="O302")])
        doc = normalize_archive(raw, retrieved_at=AT)
        self.assertTrue(all(x["quality"]["sourceNumberUniqueInSnapshot"]
                            for x in doc["records"]))
        self.assertFalse(doc["quality"]["osmCrosswalkVerified"])
        self.assertFalse(doc["quality"]["officialCategorySA_SAA_VFVerified"])
        self.assertFalse(doc["quality"]["publicationAllowed"])
        self.assertFalse(doc["isPublished"])
        self.assertFalse(doc["seoIndexable"])
        self.assertEqual(doc["releaseChannel"], CHANNEL)

    def test_invalid_numbers_and_difficulty_are_held_not_invented(self):
        altered = {**VALUES, "numero": "731", "difficolta": "HARD",
                   "lun_planim": "-1"}
        result = normalize_archive(zip_records([placemark(altered)]), retrieved_at=AT)
        q = result["records"][0]["quality"]
        self.assertTrue(q["requiresReview"])
        self.assertIn("number_missing_or_unrecognized", q["issues"])
        self.assertIn("technical_difficulty_missing_or_unrecognized", q["issues"])
        self.assertIn("missing_or_invalid_lun_planim", q["issues"])
        self.assertNotIn("lengthPlanimetricReportedM", result["records"][0]["facts"])
        self.assertEqual(result["records"][0]["sourceProperties"]["lun_planim"], "-1")

    def test_conserves_multiple_lines_without_invented_join(self):
        raw = zip_records([placemark(coords="11.8,46.2 11.81,46.21")])
        doc = normalize_archive(raw, retrieved_at=AT)
        self.assertEqual(doc["counts"]["validOriginalGeometries"], 1)
        self.assertEqual(doc["records"][0]["geo"]["crs"], "EPSG:4326")

    def test_rejects_invalid_or_degenerate_coordinates(self):
        self.assertIsNone(parse_line("11.8,46.2 11.8,46.2"))
        self.assertIsNone(parse_line("11.8,46.2 999,46.2"))
        self.assertIsNone(parse_line("11.8,46.2 NaN,46.2"))
        doc = normalize_archive(zip_records([placemark(coords="11.8,46.2 999,46.2")]),
                                retrieved_at=AT)
        self.assertEqual(doc["counts"]["validOriginalGeometries"], 0)
        self.assertTrue(doc["records"][0]["quality"]["requiresReview"])
        self.assertIsNone(doc["records"][0]["geo"])

    def test_reported_endpoint_range_qa_is_explicit_without_rewriting_source(self):
        moderate = {**VALUES, "quota_iniz": "1325"}
        large = {**VALUES, "numero": "O302", "quota_fine": "1490"}
        doc = normalize_archive(zip_records([placemark(moderate), placemark(large)]),
                                retrieved_at=AT)
        a, b = doc["records"]
        self.assertEqual(a["quality"]["reportedEndpointRangeExcessM"], 5)
        self.assertNotIn("reported_endpoint_outside_reported_range_over_5m",
                         a["quality"]["issues"])
        self.assertEqual(b["quality"]["reportedEndpointRangeExcessM"], 13)
        self.assertIn("reported_endpoint_outside_reported_range_over_5m",
                      b["quality"]["issues"])
        self.assertEqual(b["facts"]["elevationEndReportedM"]["value"], 1490)
        self.assertEqual(doc["counts"]["recordsWithAnyReportedEndpointOutsideReportedRange"], 2)
        self.assertEqual(doc["counts"]["recordsWithEndpointRangeExcessOver5M"], 1)
        self.assertEqual(doc["counts"]["recordsRequiringReview"], 1)

    def test_parses_zero_and_unknowns_distinctly(self):
        self.assertEqual(as_nonnegative_integer("0"), 0)
        self.assertIsNone(as_nonnegative_integer("-1"))
        self.assertIsNone(as_nonnegative_integer(""))
        self.assertEqual(as_minutes("00:00"), 0)
        self.assertIsNone(as_minutes("99:99"))
        self.assertIsNone(as_minutes("non indicato"))

    def test_archive_hash_preserved_and_deterministic(self):
        raw = zip_records([placemark()])
        first = normalize_archive(raw, retrieved_at=AT)
        second = normalize_archive(raw, retrieved_at=AT)
        self.assertEqual(first, second)
        self.assertEqual(first["sourceArchiveSha256"], sha256(raw).hexdigest())
        self.assertEqual(first["records"][0]["sourceArchiveSha256"], sha256(raw).hexdigest())
        self.assertEqual(len(first["records"][0]["sourceRecordFingerprint"]), 64)

    def test_cli_uses_offline_original_zip_without_public_output(self):
        raw = zip_records([placemark()])
        with tempfile.TemporaryDirectory() as td:
            src = Path(td) / "sat-original.zip"
            out = Path(td) / "staging"
            src.write_bytes(raw)
            script = Path(__file__).resolve().parents[1] / "scripts/normalize_sat_trails_v1.py"
            process = subprocess.run([sys.executable, str(script), "--source-zip",
                                      str(src), "--out", str(out)], text=True,
                                     capture_output=True)
            self.assertEqual(process.returncode, 0, msg=process.stderr)
            doc = json.loads((out / "sat-trails-normalized-g0.json").read_text())
            audit = json.loads((out / "sat-trails-normalization-audit-g0.json").read_text())
            self.assertEqual(len(doc["records"]), 1)
            self.assertEqual(doc["counts"], audit["counts"])
            self.assertEqual(doc["sourceArchiveSha256"], audit["sourceArchiveSha256"])
            self.assertFalse(doc["quality"]["publicationAllowed"])


if __name__ == "__main__":
    unittest.main()
