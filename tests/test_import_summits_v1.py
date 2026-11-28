"""Contract and offline regression tests for the GeoNames summit staging importer."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/import_summits_v1.py"
spec = importlib.util.spec_from_file_location("summits_pilot", SCRIPT)
imp = importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)


class SummitImporterTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name)
        self.data = self.base / "peaks"
        self.data.mkdir()
        self.rows = [
            [11, "Monte Prova", 46.50, 12.30, 2700, "s", "IT", "MT"],
            [12, "Monte Prova", 46.60, 12.32, 2620, "d", "IT", "PK"],
            [13, "Gruppo di Prova", 46.70, 12.34, 2500, "d", "IT", "MTS"],
            [14, "Cima Serena", 46.55, 12.38, 2800, "d", "IT", "PK"],
            [15, "Picco Altrove", 49.0, 12.0, 2200, "s", "IT", "MT"],
            [16, "Invalid code", 46.5, 12.5, 1200, "s", "IT", "LK"],
        ]
        self.write(self.data / "index.json", {
            "tile": 5, "cells": {"45_10": 6}, "top": [], "total": 6})
        self.write(self.data / "45_10.json", self.rows)
        self.photos = self.data / "photos.json"
        self.write(self.photos, {
            "photos": {"gn14-45x10": [
                "https://upload.wikimedia.org/example.jpg",
                "https://commons.wikimedia.org/wiki/File:Example.jpg",
                "Archivio", "CC BY-SA 4.0"]}})

    def write(self, path, value):
        path.write_text(json.dumps(value), encoding="utf-8")

    def pilot(self, **overrides):
        opts = {
            "peak_dir": self.data,
            "bbox": (46, 11, 47, 13),
            "out": self.base / "stage", "limit": 10,
            "photo_file": self.photos, "min_count": 1,
        }
        opts.update(overrides)
        report = imp.build(**opts)
        entities = json.loads((opts["out"] / "summits.json").read_text())["entities"]
        return report, entities

    def test_geonames_ids_and_legacy_slugs_are_stable(self):
        _, entities = self.pilot()
        self.assertEqual(len(entities), 4)
        self.assertEqual(len({e["id"] for e in entities}), 4)
        target = next(e for e in entities if e["name"] == "Cima Serena")
        self.assertEqual(target["slug"], "cima-serena")
        self.assertEqual(target["slugAliases"], ["gn14-45x10"])
        self.assertEqual(target["sourceIds"]["geonames"], "14")
        self.assertEqual(target["geo"]["point"]["lng"], 12.38)
        self.assertEqual(target["facts"]["elevationM"]["method"], "estimated")
        self.assertEqual(target["facts"]["elevationM"]["licence"], "CC BY 4.0")
        self.assertEqual(target["quality"]["gate"], "G1")
        self.assertFalse(target["quality"]["seoIndexable"])
        self.assertEqual(target["media"], [])
        self.assertFalse(target["mediaCandidates"][0]["subjectVerified"])
        self.assertFalse(target["mediaCandidates"][0]["reuseAllowed"])
        self.assertEqual(target["id"], imp.create_entity(
            self.rows[3], checked_at="2026-11-28T00:00:00Z",
            tile_size=5)["id"])

    def test_duplicates_stay_noindex_and_reviewable(self):
        report, entities = self.pilot()
        dupe = [e for e in entities if e["name"] == "Monte Prova"]
        self.assertEqual(len(dupe), 2)
        self.assertEqual(len(set(e["slug"] for e in dupe)), 2)
        self.assertTrue(all(e["quality"]["slugRequiresReview"] for e in dupe))
        self.assertTrue(all(e["quality"]["gate"] == "G0" for e in dupe))
        self.assertEqual(report["ambiguousSlugs"], 2)
        self.assertEqual(report["published"], 0)
        self.assertEqual(report["indexable"], 0)

    def test_group_not_confused_with_peak_or_area_polygon(self):
        _, entities = self.pilot()
        e = next(e for e in entities if e["kind"] == "mountain_group")
        self.assertEqual(e["subtype"], "mountain_group")
        self.assertIsNone(e["geo"]["area"])
        self.assertEqual(e["quality"]["gate"], "G0")
        self.assertTrue(e["quality"]["groupAreaNotVerified"])

    def test_source_snapshot_sha_and_staging_only(self):
        report, _ = self.pilot()
        self.assertIn("45_10.json", report["sourceSnapshotsSha256"])
        self.assertTrue((self.base / "stage/raw/geonames-candidates.json").exists())
        self.assertTrue((self.base / "stage/review.json").exists())
        self.assertFalse(json.loads(
            (self.base / "stage/summits.json").read_text())["isPublished"])

    def test_wikidata_needs_exact_verified_p1566(self):
        path = self.base / "crosswalk.json"
        self.write(path, {"links": [{
            "geonameid": 14, "qid": "Q12345", "wdtP1566": "14",
            "verified": True,
            "sourceUrl": "https://www.wikidata.org/wiki/Q12345"}]})
        _, entities = self.pilot(crosswalk=path)
        e = next(x for x in entities if x["name"] == "Cima Serena")
        self.assertEqual(e["sourceIds"]["wikidata"], "Q12345")
        self.assertFalse(e["quality"]["seoIndexable"])
        self.write(path, {"links": [{
            "geonameid": 14, "qid": "Q12345", "wdtP1566": "15",
            "verified": True,
            "sourceUrl": "https://www.wikidata.org/wiki/Q12345"}]})
        with self.assertRaises(ValueError):
            imp.read_crosswalk(path)

    def test_near_is_not_an_access_route(self):
        ref = self.base / "refuges.json"
        self.write(ref, {"entities": [
            {"id": "verified-hut", "kind": "refuge",
             "slug": "rifugio-prova", "name": "Rifugio Prova",
             "geo": {"point": {"lat": 46.501, "lng": 12.301}},
             "quality": {"gate": "G2"}},
            {"id": "raw-hut", "kind": "refuge",
             "slug": "rifugio-incerto", "name": "Rifugio Incerto",
             "geo": {"point": {"lat": 46.501, "lng": 12.301}},
             "quality": {"gate": "G0"}}
        ]})
        _, entities = self.pilot(catalogs=[("refuges", ref)])
        summit = next(e for e in entities if e["sourceIds"]["geonames"] == "11")
        self.assertEqual(len(summit["relations"]), 1)
        relation = summit["relations"][0]
        self.assertEqual(relation["type"], "near")
        self.assertFalse(relation["verified"])
        self.assertFalse(relation["accessVerified"])
        self.assertGreater(relation["straightLineKm"], 0)

    def test_invalid_rows_rejected_without_invention(self):
        self.assertFalse(imp.valid_row([99, "Cima", float("nan"), 12, 2000, "s", "IT", "PK"]))
        self.assertFalse(imp.valid_row([99, "Cima", 46, 12, -1, "unknown", "IT", "PK"]))
        self.assertFalse(imp.valid_row([99, "Cima", 46, 12, 2000, "s", "IT", "LK"]))
        no_elevation = imp.create_entity(
            [99, "Cima Invisibile", 46.3, 12.2, -1, "d", "IT", "PK"],
            checked_at="2026-11-28T00:00:00Z", tile_size=5)
        self.assertNotIn("elevationM", no_elevation["facts"])

    def test_empty_filtered_dataset_fails_quality_floor(self):
        with self.assertRaises(ValueError):
            self.pilot(country="FR", min_count=1)


if __name__ == "__main__":
    unittest.main()
