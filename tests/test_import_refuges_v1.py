"""Contratti offline del primo importatore canonico: nessuna richiesta di rete."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "import_refuges_v1.py"
SPEC = importlib.util.spec_from_file_location("import_refuges_v1", SCRIPT)
importer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(importer)


def fixture(root):
    data = root / "public" / "data"
    (data / "routes-tiles").mkdir(parents=True)
    (data / "peaks").mkdir()
    places = {
        "generatedAt": "2026-11-27",
        "source": "OpenStreetMap · ODbL 1.0",
        "places": [
            {"kind": "rifugio", "name": "Rifugio Dolomia", "slug": "osm-n-100",
             "osmUrl": "https://www.openstreetmap.org/node/100",
             "lat": 46.5, "lng": 11.5, "elevationM": 2110, "elevationSource": "osm",
             "capacity": 16, "openingHours": "Jun-Sep", "wikidata": "Q123",
             "operator": "Cooperativa A",
             "photo": {"url": "https://example.org/a.jpg"}},
            {"kind": "rifugio", "name": "Rifugio Dolomia", "slug": "osm-w-200",
             "osmUrl": "https://www.openstreetmap.org/way/200",
             "lat": 46.51, "lng": 11.52, "elevationM": 2333, "elevationSource": "dem",
             "capacity": 0},
            {"kind": "borgo", "name": "Villaggio Vicino", "slug": "osm-n-300",
             "osmUrl": "https://www.openstreetmap.org/node/300",
             "lat": 46.502, "lng": 11.501},
        ],
    }
    (data / "alpine-places.json").write_text(json.dumps(places), encoding="utf-8")
    (data / "peaks" / "45_10.json").write_text(
        json.dumps([[1234, "Monte Esempio", 46.503, 11.502, 2512, "s", "IT", "PK"]]),
        encoding="utf-8")
    (data / "routes-manifest.json").write_text(json.dumps({
        "tiles": [{"files": ["routes-tiles/tile.json"]}]}), encoding="utf-8")
    (data / "routes-tiles" / "tile.json").write_text(json.dumps({
        "routes": [{"slug": "osm-hiking-123", "stops": [
            {"slug": "osm-n-100", "kind": "rifugio", "distanceM": 75, "relation": "passaggio"},
            {"slug": "osm-w-200", "kind": "rifugio", "distanceM": 220},
            {"slug": "osm-n-100", "kind": "rifugio", "distanceM": 50}]}]
    }), encoding="utf-8")
    return data


class RefugeImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = fixture(self.root)
        self.out = self.root / "stage"

    def test_complete_staging_and_semantic_relations(self):
        report = importer.run(self.root, self.out, strict=True)
        self.assertEqual(report["refuges"], 2)
        self.assertEqual(report["nearLocalityLinks"], 2)
        self.assertEqual(report["nearMountainLinks"], 2)
        self.assertEqual(report["routeProximityLinks"], 1)
        self.assertEqual(report["missingElevation"], 1)
        self.assertEqual(report["searchIndexable"], 0)
        catalogue = json.loads((self.out / "refuges.json").read_text())["entities"]
        self.assertEqual(len({e["id"] for e in catalogue}), 2)
        self.assertEqual(len({e["slug"] for e in catalogue}), 2)
        osm = next(e for e in catalogue if e["sourceIds"]["osm"] == "node/100")
        dem = next(e for e in catalogue if e["sourceIds"]["osm"] == "way/200")
        self.assertIn("elevationM", osm["facts"])
        self.assertNotIn("elevationM", dem["facts"])
        self.assertNotIn("capacityReported", dem["facts"])
        self.assertFalse(osm["quality"]["seoIndexable"])
        self.assertEqual(osm["legacyUrl"], "/rifugi/osm-n-100/")
        self.assertEqual(osm["facts"]["openingHoursReported"]["validUntil"], None)
        self.assertEqual(osm["facts"]["openingHoursReported"]["retrievedAt"], None)
        self.assertFalse(osm["media"])  # foto senza autore/licenza scartata
        self.assertEqual(osm["relations"][0]["type"], "near")
        self.assertEqual(osm["relations"][0]["method"], "haversine")
        edges = json.loads((self.out / "links.json").read_text())["edges"]
        self.assertEqual(edges[0]["type"], "passes_near")
        self.assertEqual(edges[0]["distanceToPolylineM"], 50)
        self.assertFalse(edges[0]["verifiedAccess"])
        self.assertEqual(edges[0]["to"]["id"], osm["id"])
        self.assertEqual(len(list((self.out / "raw").glob("osm-refuges-*.json"))), 1)

    def test_repeat_is_byte_identical_and_preserves_permalink_on_rename(self):
        importer.run(self.root, self.out, strict=True)
        targets = ("refuges.json", "links.json", "report.json", "identity-registry.json")
        original = {f: (self.out / f).read_bytes() for f in targets}
        importer.run(self.root, self.out, strict=True)
        self.assertEqual(original, {f: (self.out / f).read_bytes() for f in targets})
        catalog = json.loads(original["refuges.json"])["entities"]
        prev = next(e for e in catalog if e["sourceIds"]["osm"] == "node/100")
        data_file = self.data / "alpine-places.json"
        data = json.loads(data_file.read_text())
        data["places"][0]["name"] = "Rifugio Dolomia - Nuovo Nome"
        data_file.write_text(json.dumps(data), encoding="utf-8")
        importer.run(self.root, self.out, strict=True)
        current = json.loads((self.out / "refuges.json").read_text())["entities"]
        now = next(e for e in current if e["sourceIds"]["osm"] == "node/100")
        self.assertEqual((prev["id"], prev["slug"]), (now["id"], now["slug"]))
        self.assertEqual(now["name"], "Rifugio Dolomia - Nuovo Nome")
        self.assertEqual(len(list((self.out / "raw").glob("osm-refuges-*.json"))), 2)

    def test_unknown_location_is_not_automatically_municipality(self):
        importer.run(self.root, self.out, strict=True)
        for e in json.loads((self.out / "refuges.json").read_text())["entities"]:
            self.assertNotIn("administrativeHierarchy", e)
            self.assertFalse(any(x["type"] == "located_in" for x in e["relations"]))
            self.assertFalse(any(x["type"] == "accessible_from" for x in e["relations"]))

    def test_same_name_and_spatial_overlap_are_reviewed_not_merged(self):
        file = self.data / "alpine-places.json"
        doc = json.loads(file.read_text())
        doc["places"][1]["lat"] = 46.500005
        doc["places"][1]["lng"] = 11.500005
        file.write_text(json.dumps(doc), encoding="utf-8")
        report = importer.run(self.root, self.out, strict=True)
        self.assertEqual(report["candidateDuplicatePairs"], 1)
        entity = json.loads((self.out / "refuges.json").read_text())["entities"]
        self.assertEqual(len({x["id"] for x in entity}), 2)
        review = json.loads((self.out / "review.json").read_text())
        candidate = review["candidateDuplicates"][0]
        self.assertEqual(candidate["evidence"], "same_normalized_name")
        self.assertFalse(candidate["autoMerged"])
        self.assertEqual(candidate["status"], "manual_review_required")

    def test_equal_wikidata_identifier_is_only_a_merge_candidate(self):
        file = self.data / "alpine-places.json"
        doc = json.loads(file.read_text())
        doc["places"][1]["name"] = "Capanna su altro lato"
        doc["places"][1]["wikidata"] = "Q123"
        doc["places"][1]["lat"] = 46.5005
        doc["places"][1]["lng"] = 11.5005
        file.write_text(json.dumps(doc), encoding="utf-8")
        importer.run(self.root, self.out, strict=True)
        review = json.loads((self.out / "review.json").read_text())
        self.assertEqual(len(review["candidateDuplicates"]), 1)
        self.assertEqual(review["candidateDuplicates"][0]["evidence"], "same_wikidata_qid")

    def test_duplicate_osm_id_aborts_before_writing(self):
        file = self.data / "alpine-places.json"
        doc = json.loads(file.read_text())
        doc["places"].append(dict(doc["places"][0]))
        file.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "duplicato"):
            importer.run(self.root, self.out, strict=True)
        self.assertFalse((self.out / "refuges.json").exists())

    def test_manifest_traversal_is_blocked(self):
        f = self.data / "routes-manifest.json"
        f.write_text(json.dumps({"tiles": [{"files": ["../../secrets.json"]}]}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "non sicuro"):
            importer.run(self.root, self.out, strict=True)

    def test_raw_snapshot_never_silently_overwritten(self):
        importer.run(self.root, self.out, strict=True)
        raw = next((self.out / "raw").glob("*.json"))
        raw.write_text("changed", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "immutabile"):
            importer.run(self.root, self.out, strict=True)

    def test_invalid_urls_and_missing_coordinates_fail(self):
        file = self.data / "alpine-places.json"
        doc = json.loads(file.read_text())
        doc["places"][0]["osmUrl"] = "javascript:alert(1)"
        file.write_text(json.dumps(doc), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Identità OSM invalida"):
            importer.run(self.root, self.out, strict=True)

    def test_zero_and_false_are_not_interpreted_as_absent(self):
        self.assertEqual(importer.fact(False, "s", "https://example.org")["value"], False)
        self.assertEqual(importer.fact(0, "s", "https://example.org")["value"], 0)
        self.assertIsNone(importer.fact(None, "s", "https://example.org")["value"])


if __name__ == "__main__":
    unittest.main()
