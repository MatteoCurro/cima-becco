"""Stage-only import contracts for alpine passes, lakes, valleys and viewpoints."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts/import_natural_features_v1.py"
spec=importlib.util.spec_from_file_location("natural_feature_import",SCRIPT)
imp=importlib.util.module_from_spec(spec)
spec.loader.exec_module(imp)


def item(ident,name,tags,**kwargs):
    return {"type":"node","id":ident,"lat":46.5,"lon":12.1,
            "tags":{"name":name,**tags},**kwargs}


class TestNaturalFeaturesPilot(unittest.TestCase):
    def test_query_bounded_and_does_not_repeat_water_sources(self):
        q=imp.query_for_bbox((46.4,11.5,46.6,12.4))
        self.assertIn('"natural"="saddle"',q)
        self.assertIn('"mountain_pass"="yes"',q)
        self.assertIn('"waterway"="waterfall"',q)
        self.assertIn('"water"~"^(lake|reservoir)$"',q)
        self.assertNotIn('["natural"="spring"]',q)
        self.assertNotIn('["amenity"="drinking_water"]',q)
        with self.assertRaises(ValueError):
            imp.query_for_bbox((0,0,1,1))

    def test_all_subtypes_exact_tags(self):
        names=[
            ("pass",{"mountain_pass":"yes"},"mountain_pass"),
            ("saddle",{"natural":"saddle"},"saddle"),
            ("valley",{"natural":"valley"},"valley"),
            ("lake",{"natural":"water","water":"lake"},"lake"),
            ("reservoir",{"natural":"water","water":"reservoir"},"reservoir"),
            ("waterfall",{"waterway":"waterfall"},"waterfall"),
            ("viewpoint",{"tourism":"viewpoint"},"viewpoint"),
        ]
        for ix,(_,tags,expected) in enumerate(names):
            with self.subTest(expected=expected):
                e=imp.parse_osm(item(100+ix,"Nome alpino "+str(ix),tags),"2026-11-28T00:00:00Z")
                self.assertEqual(e["subtype"],expected)
                self.assertFalse(e["quality"]["seoIndexable"])
                self.assertFalse(e["relations"])
                self.assertEqual(e["facts"]["osmFeatureTag"]["licence"],"ODbL 1.0")

    def test_unnamed_or_unrelated_not_auto_classified(self):
        self.assertIsNone(imp.parse_osm(item(1,"",{"natural":"valley"}),"time"))
        self.assertIsNone(imp.parse_osm(item(2,"Fontana",{"natural":"spring"}),"time"))
        self.assertIsNone(imp.parse_osm(item(3,"Acqua",{"natural":"water","water":"pond"}),"time"))
        self.assertIsNone(imp.parse_osm(item(4,"Baita",{"tourism":"alpine_hut"}),"time"))

    def test_way_center_is_not_polygon_or_access(self):
        e=imp.parse_osm({"type":"way","id":1234,
                         "center":{"lat":46.6,"lon":12.2},
                         "tags":{"name":"Lago della Prova","natural":"water","water":"lake","ele":"2030"}},
                        "2026-11-28T00:00:00Z")
        self.assertIsNone(e["geo"]["area"])
        self.assertEqual(e["geo"]["method"],"osm_element_center")
        self.assertTrue(e["quality"]["perimeterNotVerified"])
        self.assertEqual(e["facts"]["elevationM"]["value"],2030)
        self.assertEqual(e["sourceIds"]["osm"],"way/1234")
        self.assertIn("osm-w-1234",e["slugAliases"])

    def test_waterfall_height_is_not_elevation(self):
        e=imp.parse_osm(item(5,"Cascata Bona",{"waterway":"waterfall","height":"70 m"}),"time")
        self.assertEqual(e["facts"]["waterfallDropM"]["value"],70)
        self.assertNotIn("elevationM",e["facts"])
        self.assertIsNone(imp.numeric_meters("30 ft",maximum=1000))
        self.assertIsNone(imp.numeric_meters("20-30",maximum=1000))
        self.assertIsNone(imp.numeric_meters("-1",maximum=1000))

    def test_explicit_language_and_wikidata_unverified_candidate(self):
        e=imp.parse_osm(item(6,"Passo Test",{
            "mountain_pass":"yes","name:de":"Testpass","wikidata":"Q123"}),"time")
        self.assertEqual(e["sourceIds"]["wikidataCandidate"],"Q123")
        self.assertFalse(e["quality"]["wikidataIdentityVerified"])
        self.assertEqual(e["localNames"][0]["language"],"de")

    def test_stable_uuid_and_conflicting_names_held_noindex(self):
        a=item(7,"Forcella omonima",{"natural":"saddle"})
        b=item(8,"Forcella omonima",{"natural":"saddle"})
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"staging"
            count=imp.run([a,b],cell=2,out=out)
            self.assertEqual(count,2)
            doc=json.loads((out/"features.json").read_text())
            self.assertFalse(doc["isPublished"])
            self.assertTrue(all(x["quality"]["gate"]=="G0" for x in doc["entities"]))
            self.assertTrue(all(x["quality"]["slugRequiresReview"] for x in doc["entities"]))
            self.assertEqual(len({x["id"] for x in doc["entities"]}),2)
            self.assertEqual(len({x["slug"] for x in doc["entities"]}),2)
            report=json.loads((out/"report.json").read_text())
            self.assertEqual(report["slugCollisionGroups"],1)
            self.assertEqual(report["seoIndexable"],0)
            self.assertEqual(report["published"],0)
            self.assertTrue(report["reusedWaterCatalog"])

    def test_reference_id_stable_through_name_change(self):
        a=item(7,"Forcella antica",{"natural":"saddle"})
        b=item(7,"Forcella moderna",{"natural":"saddle"})
        self.assertEqual(imp.parse_osm(a,"time")["id"],imp.parse_osm(b,"time")["id"])
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                imp.run([a,b],cell=1,out=Path(d))

    def test_near_does_not_attest_access(self):
        raw=item(50,"Passo vicino",{"mountain_pass":"yes"})
        with tempfile.TemporaryDirectory() as d:
            cat=Path(d)/"refuges.json"
            cat.write_text(json.dumps({"entities":[{
                "id":"refuge1","name":"Rifugio vicino","kind":"refuge","slug":"rifugio-vicino",
                "geo":{"point":{"lat":46.505,"lng":12.102}},
                "quality":{"gate":"G2"}}
            ]}))
            count=imp.run([raw],cell=1,out=Path(d)/"out",catalogs=[("refuges",cat)])
            self.assertEqual(count,1)
            doc=json.loads((Path(d)/"out/features.json").read_text())
            relation=doc["entities"][0]["relations"][0]
            self.assertEqual(relation["type"],"near")
            self.assertFalse(relation["verified"])
            self.assertFalse(relation["accessVerified"])

    def test_source_checksum_and_no_live_writes(self):
        with tempfile.TemporaryDirectory() as d:
            out=Path(d)/"stage"
            imp.run([item(100,"Lago A",{"natural":"water","water":"lake"})],
                    cell=0,out=out)
            report=json.loads((out/"report.json").read_text())
            self.assertEqual(len(report["overpassSha256"]),64)
            self.assertTrue((out/"raw/osm-features.json").exists())


if __name__=="__main__":
    unittest.main()
