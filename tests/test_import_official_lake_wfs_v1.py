"""Offline contract for independent Bolzano/ARPAV WFS lake source G0 adapter."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_official_lake_wfs_v1 import (
    CHANNEL, MAX_FEATURES, PILOT_BBOX, PROVIDERS, discover_typename,
    parse_geojson, run_live, validate_geometry, wfs_urls,
)

AT = "2026-11-28T09:00:00+00:00"
OUTER = [[12.3, 46.5], [12.32, 46.5], [12.32, 46.52],
         [12.3, 46.52], [12.3, 46.5]]
ISLAND = [[12.304, 46.504], [12.306, 46.504], [12.306, 46.506],
          [12.304, 46.506], [12.304, 46.504]]


def feature(identifier="lakes.42", geometry=None, properties=None):
    return {
        "type": "Feature", "id": identifier,
        "geometry": geometry if geometry is not None else {
            "type": "Polygon", "coordinates": [OUTER],
        },
        "properties": properties if properties is not None else {
            "NOME": "Lago di prova", "CODICE": "A42", "quota": None,
        },
    }


def payload(items, crs=None):
    obj = {"type": "FeatureCollection", "features": items}
    if crs:
        obj["crs"] = {"type": "name", "properties": {"name": crs}}
    return json.dumps(obj).encode("utf-8")


CAPABILITIES = b"""<?xml version='1.0'?>
<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0" version="2.0.0">
  <wfs:FeatureTypeList>
    <wfs:FeatureType><wfs:Name>p_bz-Hydrology:Lakes</wfs:Name></wfs:FeatureType>
    <wfs:FeatureType><wfs:Name>other:Wetlands</wfs:Name></wfs:FeatureType>
  </wfs:FeatureTypeList>
</wfs:WFS_Capabilities>"""


class TestOfficialLakeWFS(unittest.TestCase):
    def test_two_independent_sources_have_verifiable_catalogue_contracts(self):
        self.assertEqual(set(PROVIDERS),
                         {"bolzano_lakes", "arpav_water_surfaces"})
        self.assertEqual(PROVIDERS["bolzano_lakes"]["licence"], "CC0 1.0")
        self.assertEqual(PROVIDERS["arpav_water_surfaces"]["licence"], "CC BY 3.0")
        self.assertEqual(PROVIDERS["arpav_water_surfaces"]["sourceScale"], "1:10000")

    def test_capabilities_requires_one_advertised_exact_type(self):
        self.assertEqual(discover_typename(CAPABILITIES, "bolzano_lakes"),
                         "p_bz-Hydrology:Lakes")
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            discover_typename(CAPABILITIES.replace(b"Lakes", b"LakesSomething"),
                              "bolzano_lakes")
        with self.assertRaisesRegex(ValueError, "missing or ambiguous"):
            discover_typename(CAPABILITIES.replace(
                b"<wfs:FeatureType><wfs:Name>other:Wetlands</wfs:Name>",
                b"<wfs:FeatureType><wfs:Name>other:Lakes</wfs:Name>"),
                "bolzano_lakes")

    def test_bounded_wfs_requests_do_not_infer_typename(self):
        for provider in PROVIDERS:
            cap, get = wfs_urls(provider, "provider-namespace:VerifiedLayer")
            self.assertIn("GetCapabilities", cap)
            self.assertIn("GetFeature", get)
            self.assertIn("VerifiedLayer", get)
            self.assertIn("4326", get)
            self.assertIn(str(MAX_FEATURES), get)
        self.assertIn("count=20", wfs_urls("bolzano_lakes", "ns:Lakes")[1])
        self.assertIn("maxFeatures=20", wfs_urls(
            "arpav_water_surfaces", "ns:water")[1])
        self.assertEqual(PILOT_BBOX, (11.15, 46.28, 12.95, 46.95))

    def test_valid_source_area_is_g0_without_unsafe_claims_or_crosswalks(self):
        for provider in PROVIDERS:
            doc, report = parse_geojson(payload([feature()]), provider, at=AT)
            self.assertEqual(report["acceptedG0"], 1)
            self.assertEqual(doc["releaseChannel"], CHANNEL)
            self.assertFalse(doc["isPublished"])
            self.assertFalse(doc["completeDataset"])
            self.assertTrue(doc["sampleOnly"])
            item = doc["entities"][0]
            self.assertIsNone(item["subtype"])
            self.assertEqual(item["sourceFeatureId"], "lakes.42")
            self.assertEqual(item["quality"]["gate"], "G0")
            self.assertFalse(item["quality"]["seoIndexable"])
            self.assertFalse(item["quality"]["subtypeConfirmed"])
            self.assertFalse(item["quality"]["osmWikidataGeonamesIdentityVerified"])
            self.assertEqual(item["geo"]["area"]["type"], "MultiPolygon")
            self.assertEqual(item["geo"]["area"]["coordinates"][0][0], OUTER)
            fact = item["facts"]["providerMappedWaterSurfaceKm2"]
            self.assertGreater(fact["value"], 0)
            self.assertEqual(fact["method"], "derived")
            self.assertEqual(fact["licence"], PROVIDERS[provider]["licence"])
            for forbidden in ("isSwimmable", "potable", "bathable",
                              "accessible_from", "slug", "elevationM"):
                self.assertNotIn(forbidden, str(item))

    def test_island_is_subtracted_and_never_filled(self):
        whole, area1 = validate_geometry({
            "type": "Polygon", "coordinates": [OUTER],
        })
        hollow, area2 = validate_geometry({
            "type": "Polygon", "coordinates": [OUTER, ISLAND],
        })
        self.assertEqual(len(hollow["coordinates"][0]), 2)
        self.assertLess(area2, area1)
        self.assertEqual(whole["coordinates"][0][0], OUTER)

    def test_unclosed_self_crossing_or_non_polygon_never_passes(self):
        errors = [
            {"type": "Polygon", "coordinates": [OUTER[:-1]]},
            {"type": "Polygon", "coordinates": [[OUTER[0], OUTER[2],
                OUTER[1], OUTER[3], OUTER[0]]]},
            {"type": "Point", "coordinates": [12.3, 46.5]},
            {"type": "Polygon", "coordinates": [OUTER, [
                [12.35, 46.5], [12.36, 46.5], [12.36, 46.51],
                [12.35, 46.51], [12.35, 46.5]]]},
            {"type": "Polygon", "coordinates": [[
                [46.5, 12.3], [46.52, 12.3], [46.52, 12.32],
                [46.5, 12.32], [46.5, 12.3]]]},
        ]
        for i, geometry in enumerate(errors):
            with self.subTest(i=i):
                doc, report = parse_geojson(payload([feature(
                    geometry=geometry)]), "bolzano_lakes", at=AT)
                self.assertEqual(report["acceptedG0"], 0)
                self.assertEqual(doc["entities"], [])
                self.assertEqual(sum(report["rejectedOrReview"].values()), 1)

    def test_source_missing_and_duplicate_ids_are_not_auto_generated(self):
        doc, report = parse_geojson(payload([feature(identifier=None)]),
                                    "bolzano_lakes", at=AT)
        self.assertEqual(report["acceptedG0"], 0)
        self.assertEqual(report["rejectedOrReview"]["missing_provider_feature_id"], 1)
        with self.assertRaisesRegex(ValueError, "Duplicate WFS feature"):
            parse_geojson(payload([feature(), feature()]),
                          "bolzano_lakes", at=AT)

    def test_wfs_limit_must_be_respected(self):
        many = [feature(str(i)) for i in range(MAX_FEATURES + 1)]
        with self.assertRaisesRegex(ValueError, "feature limit"):
            parse_geojson(payload(many), "bolzano_lakes", at=AT)

    def test_rejects_unexpected_crs_and_non_feature_collections(self):
        with self.assertRaisesRegex(ValueError, "not confirmed WGS84"):
            parse_geojson(payload([feature()], crs="EPSG:25832"),
                          "bolzano_lakes", at=AT)
        with self.assertRaisesRegex(ValueError, "FeatureCollection"):
            parse_geojson(b'{"type":"Feature","features":[]}',
                          "bolzano_lakes", at=AT)

    def test_untrusted_environment_cannot_redirect_official_provider(self):
        calls = []
        def fake_fetch(url, **kwargs):
            calls.append(url)
            if "GetCapabilities" in url:
                return CAPABILITIES
            return payload([feature()])
        with patch("import_official_lake_wfs_v1.fetch_limited", side_effect=fake_fetch):
            raw, url, cap_sha, typename = run_live("bolzano_lakes")
        self.assertEqual(typename, "p_bz-Hydrology:Lakes")
        self.assertEqual(len(cap_sha), 64)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(u.startswith(PROVIDERS["bolzano_lakes"]["endpoint"])
                            for u in calls))
        self.assertEqual(raw, payload([feature()]))
        self.assertEqual(url, calls[1])

    def test_provenance_hash_does_not_depend_on_entity_name(self):
        src = payload([feature(properties={"NOME": "Lago X"})])
        first, _ = parse_geojson(src, "arpav_water_surfaces", at=AT)
        other, _ = parse_geojson(payload([feature(properties={"NOME": "Lago Y"})]),
                                 "arpav_water_surfaces", at=AT)
        self.assertNotEqual(first["rawSha256"], other["rawSha256"])
        self.assertEqual(first["entities"][0]["sourceFeatureId"],
                         other["entities"][0]["sourceFeatureId"])
        self.assertNotIn("wikidata", first["entities"][0]["sourceIds"])


if __name__ == "__main__":
    unittest.main()
