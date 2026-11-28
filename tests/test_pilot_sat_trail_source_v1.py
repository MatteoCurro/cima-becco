"""SAT G0 ZIP/KML schema probe: offline safety, provenance and no promotion."""
from hashlib import sha256
from io import BytesIO
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from zipfile import ZipFile, ZIP_DEFLATED

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from pilot_sat_trail_source_v1 import (
    SOURCE_URL, CHANNEL, audit_archive, fetch_zip, inspect_coordinates,
)

DATE = "2026-11-28T14:00:00+00:00"

KML = """<?xml version="1.0" encoding="utf-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2">
 <Document>
  <Placemark id="sat-route-1"><name>Sentiero 532</name>
   <ExtendedData><Data name="CAT"><value>SA</value></Data>
   <Data name="ref"><value>532</value></Data></ExtendedData>
   <LineString><coordinates>11.5,46.5,1120 11.51,46.51,1200</coordinates></LineString>
  </Placemark>
  <Placemark id="sat-route-2"><name>Via Ferrata X</name>
   <ExtendedData><SchemaData><SimpleData name="CLASS">VF</SimpleData>
   </SchemaData></ExtendedData>
   <MultiGeometry><LineString><coordinates>11.55,46.5 11.56,46.6</coordinates>
   </LineString></MultiGeometry>
  </Placemark>
  <Placemark><name>Invalid geometry</name>
   <LineString><coordinates>11.5,46.5 999,46.6</coordinates></LineString>
  </Placemark>
  <Placemark><name>Without geometry</name><Point>
   <coordinates>11.5,46.5</coordinates></Point></Placemark>
 </Document>
</kml>""".encode()


def zip_kml(content=KML, filename="sentieri.kml"):
    out = BytesIO()
    with ZipFile(out, "w", ZIP_DEFLATED) as z:
        z.writestr(filename, content)
    return out.getvalue()


class SATSchemaPilotTests(unittest.TestCase):
    def test_realistic_kml_extended_data_and_original_categories(self):
        raw = zip_kml()
        doc = audit_archive(raw, retrieved_at=DATE)
        self.assertEqual(doc["counts"]["sourcePlacemarks"], 4)
        self.assertEqual(doc["counts"]["validLineStringFeatures"], 2)
        self.assertEqual(doc["counts"]["invalidLineStringFeatures"], 1)
        self.assertEqual(doc["counts"]["featuresWithoutLineStrings"], 1)
        self.assertEqual(doc["files"][0]["sourcePropertyKeys"], {"CAT": 1, "CLASS": 1, "ref": 1})
        self.assertEqual(doc["files"][0]["examples"][0]["originalProperties"]["CAT"], "SA")
        self.assertEqual(doc["files"][0]["examples"][1]["originalProperties"]["CLASS"], "VF")
        self.assertEqual(doc["files"][0]["examples"][0]["kmlPlacemarkId"], "sat-route-1")

    def test_g0_never_auto_claims_cai_ferrata_or_osm_identity(self):
        d = audit_archive(zip_kml(), retrieved_at=DATE)
        self.assertEqual(d["releaseChannel"], CHANNEL)
        self.assertFalse(d["isPublished"])
        self.assertFalse(d["seoIndexable"])
        self.assertFalse(d["routeCatalogueModified"])
        self.assertEqual(d["sourceCrs"], "EPSG:4326")
        self.assertEqual(d["licence"], "ODbL 1.0")
        self.assertEqual(d["sourceDownloadUrl"], SOURCE_URL)
        self.assertFalse(d["quality"]["officialCategoryFieldVerified"])
        self.assertFalse(d["quality"]["canonicalTrailIdsAssigned"])
        self.assertFalse(d["quality"]["osmCrosswalkVerified"])
        self.assertFalse(d["quality"]["routingAllowed"])
        self.assertFalse(d["quality"]["safetyVerified"])
        self.assertTrue(all(not x["identityMatchedWithOSM"]
                            for x in d["files"][0]["examples"]))

    def test_archive_checksum_matches_input_exactly(self):
        raw = zip_kml()
        d = audit_archive(raw, retrieved_at=DATE)
        self.assertEqual(d["sourceArchiveSha256"], sha256(raw).hexdigest())
        self.assertEqual(d["archiveBytes"], len(raw))

    def test_invalid_source_zip_is_not_accepted(self):
        with self.assertRaises(ValueError):
            audit_archive(b"error from source", retrieved_at=DATE)
        with self.assertRaises(ValueError):
            audit_archive(zip_kml(b"not xml"), retrieved_at=DATE)
        with self.assertRaises(ValueError):
            audit_archive(zip_kml(filename="x.gpx"), retrieved_at=DATE)

    def test_unsafe_zip_paths_rejected_even_without_extraction(self):
        with self.assertRaisesRegex(ValueError, "Unsafe ZIP entry"):
            audit_archive(zip_kml(filename="../bad.kml"), retrieved_at=DATE)

    def test_external_entity_is_rejected(self):
        content = b'<?xml version="1.0"?><!DOCTYPE kml [<!ENTITY x SYSTEM "file:///etc/passwd">]><kml></kml>'
        with self.assertRaisesRegex(ValueError, "DTD/entity"):
            audit_archive(zip_kml(content), retrieved_at=DATE)

    def test_coordinate_precision_and_invalid_values(self):
        self.assertEqual(inspect_coordinates("11.5,46.5 11.6,46.6,1500"), (2, True))
        self.assertEqual(inspect_coordinates("11.5,46.5"), (1, False))
        self.assertFalse(inspect_coordinates("11.5,46.5 NaN,46.6")[1])
        self.assertFalse(inspect_coordinates("11.5,46.5 900,46.6")[1])

    def test_network_url_cannot_be_overridden(self):
        with self.assertRaises(ValueError):
            fetch_zip("https://evil.example.com/bad.zip")

    def test_cli_preserves_original_source_only_in_staging(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            z = root / "sat.zip"
            output = root / "staging"
            z.write_bytes(zip_kml())
            code = Path(__file__).resolve().parents[1] / "scripts/pilot_sat_trail_source_v1.py"
            process = subprocess.run([sys.executable, str(code), "--input", str(z),
                                      "--out", str(output)], text=True, capture_output=True)
            self.assertEqual(process.returncode, 0, process.stderr)
            self.assertEqual((output / "source-sat-official.kml.zip").read_bytes(), z.read_bytes())
            d = json.loads((output / "source-schema-audit-g0.json").read_text(encoding="utf-8"))
            self.assertEqual(d["counts"]["sourcePlacemarks"], 4)
            self.assertFalse(d["quality"]["publicationAllowed"])


if __name__ == "__main__":
    unittest.main()
