"""Identity resolution: type-safe, conservative, and repeatable. No remote calls."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "scripts" / "reconcile_cai_osm_refuges_v1.py"
spec = importlib.util.spec_from_file_location("cai_identity", path)
linker = importlib.util.module_from_spec(spec)
spec.loader.exec_module(linker)


def hut(id, name, lat=46.5, lon=11.5, elevation=None):
    return {"id": "cb-" + id, "name": name, "kind": "refuge",
            "geo": {"point": {"lat": lat, "lon": lon}},
            "sourceIds": {"osm": "node/" + id},
            "facts": ({"elevationM": {"value": elevation}} if elevation else {})}


def cai(id, name, lat=46.5, lon=11.5, altitude=None, category=None):
    c = {"caiId": id, "name": name,
         "geo": {"type": "Point", "coordinates": [lon, lat]},
         "altitudeM": altitude}
    if category is not None:
        c["category"] = category
    return c


class CAIResolverTests(unittest.TestCase):
    def test_geojson_lon_lat_order_and_accents(self):
        self.assertEqual(linker.valid_geojson_point(
            {"type": "Point", "coordinates": [11.5, 46.5]}), (46.5, 11.5))
        self.assertEqual(linker.name_score("CAI BOE'", "Rifugio Boé"), 1.0)

    def test_nearby_name_agreement_yields_review_not_verified_link(self):
        r = linker.identity_candidates(
            [cai(100, "TORRANI MARIA VITTORIA", altitude=2400)],
            [hut("1", "Rifugio Maria Vittoria Torrani", elevation=2401)])
        self.assertEqual(r["summary"]["candidatePairs"], 1)
        self.assertEqual(r["summary"]["establishedLinks"], 0)
        self.assertEqual(r["candidateMatches"][0]["typeReview"], "unverified")
        self.assertFalse(r["candidateMatches"][0]["suggestions"][0]["autoMerged"])
        self.assertFalse(r["candidateMatches"][0]["linkEstablished"])

    def test_proximity_without_name_not_accepted_even_if_point_is_identical(self):
        r = linker.identity_candidates(
            [cai(100, "RIFUGIO ANTERMOIA")], [hut("1", "Rifugio Boé")])
        self.assertEqual(r["summary"]["candidatePairs"], 0)
        self.assertEqual(r["summary"]["unmatchedRecords"], 1)

    def test_far_same_name_not_linked(self):
        r = linker.identity_candidates(
            [cai(100, "RIFUGIO BOE", lat=46.5, lon=11.5)],
            [hut("1", "Rifugio Boe", lat=46.51, lon=11.5)])
        self.assertEqual(r["summary"]["candidatePairs"], 0)

    def test_excluded_bivouac_or_other_type_is_not_proposed(self):
        r = linker.identity_candidates(
            [cai(100, "FIAMME GIALLE", category="Bivacco")],
            [hut("1", "Fiamme Gialle")])
        self.assertEqual(r["summary"]["categoryStatus"]["excluded_non_refuge"], 1)
        self.assertEqual(r["summary"]["candidatePairs"], 0)
        self.assertEqual(r["unmatched"][0]["reason"], "non_refuge_type")

    def test_unknown_category_is_not_treated_as_verified_refuge(self):
        r = linker.identity_candidates([cai(100, "BOE")], [hut("1", "Boé")])
        self.assertEqual(r["candidateMatches"][0]["typeReview"], "unverified")
        self.assertEqual(r["summary"]["establishedLinks"], 0)

    def test_ambiguous_overlapping_osm_geometries_must_not_merge(self):
        r = linker.identity_candidates([cai(100, "PASSO LUSIA")], [
            hut("1", "Rifugio Passo Lusia"),
            hut("2", "Rifugio Passo Lusia", lon=11.50001)])
        self.assertEqual(r["summary"]["candidatePairs"], 2)
        self.assertEqual(r["summary"]["ambiguousRecords"], 1)
        self.assertTrue(r["candidateMatches"][0]["conflict"])
        self.assertTrue(all(not x["autoMerged"] for x in r["candidateMatches"][0]["suggestions"]))

    def test_elevation_mismatch_blocks_even_with_identical_name_and_coordinates(self):
        r = linker.identity_candidates([cai(100, "BOE", altitude=2400)],
                                       [hut("1", "Boé", elevation=1500)])
        self.assertEqual(r["summary"]["candidatePairs"], 0)

    def test_no_elevation_in_legacy_is_not_assumed_zero(self):
        r = linker.identity_candidates([cai(100, "BOE", altitude=2400)],
                                       [hut("1", "Boé")])
        self.assertEqual(r["summary"]["candidatePairs"], 1)
        self.assertIsNone(r["candidateMatches"][0]["suggestions"][0]["elevationDifferenceM"])

    def test_cai_ids_must_be_unique(self):
        with self.assertRaisesRegex(ValueError, "duplicati"):
            linker.identity_candidates([cai(100, "BOE"), cai(100, "ANTERMOIA")],
                                      [hut("1", "Boé")])

    def test_malformed_coordinates_and_missing_name(self):
        self.assertIsNone(linker.valid_geojson_point(
            {"type": "Point", "coordinates": [1000, 0]}))
        self.assertIsNone(linker.valid_geojson_point(
            {"type": "Point", "coordinates": [True, 46.5]}))
        r = linker.identity_candidates(
            [{"caiId": 100, "name": "", "geo": {"type": "Point", "coordinates": [11.5, 46.5]}}],
            [hut("1", "Boé")])
        self.assertEqual(r["unmatched"][0]["reason"], "missing_name_or_geometry")

    def test_report_stable_across_ordering_and_wrapper(self):
        records = [cai(200, "Boé"), cai(100, "Torrani Maria Vittoria", lon=11.501)]
        osms = [hut("2", "Maria Vittoria Torrani", lon=11.501),
                hut("1", "Rifugio Boé")]
        a = linker.identity_candidates(records, osms)
        b = linker.identity_candidates({"records": list(reversed(records))}, list(reversed(osms)))
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


if __name__ == "__main__":
    unittest.main()
