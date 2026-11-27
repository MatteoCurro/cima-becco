"""Test offline dell'importatore OSM; nessuna chiamata a Overpass."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parent.parent / "scripts/import_osm_routes.py"
spec = importlib.util.spec_from_file_location("import_osm_routes", SCRIPT)
osm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(osm)


def way(ref, offsets, step=0.002):
    return {"type": "way", "ref": ref, "geometry": [
        {"lon": 11.65 + step * i, "lat": 46.5} for i in offsets
    ]}


def relation(route="hiking", tags=None, members=None):
    base = {"type": "route", "route": route, "name": "Sentiero prova", "ref": "666"}
    return {"type": "relation", "id": 12345, "tags": {**base, **(tags or {})},
            "members": members if members is not None else [
                way(10, range(0, 5)), way(11, range(4, 10))
            ], "timestamp": "2026-11-27T08:00:00Z"}


class ImportOSMTest(unittest.TestCase):
    def test_hiking_metadata(self):
        result = osm.to_route(relation(tags={
            "operator": "CAI", "cai_scale": "EE", "osmc:symbol": "red:red:white_bar",
            "website": "https://example.org/sentiero-666", "wikidata": "Q123456"
        }))
        self.assertIsNotNone(result)
        self.assertEqual(result["slug"], "osm-hiking-12345")
        self.assertEqual(result["activity"], "hike")
        self.assertEqual(result["caiTrailNumber"], "666")
        self.assertEqual(result["caiDifficulty"], "EE")
        self.assertEqual(result["wikidataId"], "Q123456")
        self.assertEqual(result["officialDescriptionUrl"], "https://example.org/sentiero-666")
        self.assertGreater(result["distanceM"], 800)
        self.assertFalse(result["elevationAvailable"])

    def test_ferrata(self):
        result = osm.to_route(relation(route="via_ferrata", tags={
            "via_ferrata_scale": "3"
        }, members=[way(30, range(0, 4), 0.0005),
                    way(31, range(3, 9), 0.0005)]))
        self.assertIsNotNone(result)
        self.assertEqual(result["activity"], "ferrata")
        self.assertEqual(result["viaFerrataScale"], "3")

    def test_gap_is_rejected_without_fake_straight_link(self):
        self.assertIsNone(osm.to_route(relation(members=[
            way(10, range(0, 5)), way(11, range(7, 13))
        ])))

    def test_bicycle_only_is_excluded(self):
        self.assertIsNone(osm.to_route(relation(tags={"foot": "no", "bicycle": "designated"})))

    def test_missing_geometry_is_excluded(self):
        self.assertIsNone(osm.to_route(relation(members=[
            way(10, range(0, 5)), {"type": "way", "ref": 11}
        ])))

    def test_no_automatic_cai_attribution(self):
        result = osm.to_route(relation())
        self.assertIsNotNone(result)
        self.assertNotIn("caiTrailNumber", result)
        self.assertEqual(result["trailRef"], "666")


if __name__ == "__main__":
    unittest.main()
