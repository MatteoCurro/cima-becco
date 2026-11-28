"""Lake G2 gate: source polygon + P1566/P625 + Commons P18 + itwiki QID."""
from __future__ import annotations
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
sys.path.insert(0,str(Path(__file__).resolve().parents[0]))
from test_enrich_natural_water_geometry_v1 import originals,outline
from test_natural_wikimedia_v1 import wditem,commons,wiki
from enrich_natural_water_geometry_v1 import run as geometry_run
from enrich_natural_lakes_wikimedia_v1 import run,lake_candidates,OUT

AT="2026-11-28T09:00:00Z"

def stages():
    return geometry_run(*originals(),[outline()],at=AT)[0],originals()[2]

def wd(_url,_params):
    return {"entities":{"Q123":wditem(gid="100",lat=46.501,elevation="+2200")}}

class TestNaturalLakesG2(unittest.TestCase):
    def call(self,geo=None,cross=None,wd_getter=wd,commons_getter=commons,wiki_getter=wiki):
        first,links=stages()
        return run(geo or first,cross or links,at=AT,
                   wd_getter=wd_getter,commons_getter=commons_getter,
                   wiki_getter=wiki_getter)

    def test_full_exact_source_and_licensed_media_make_only_G2_staging(self):
        d,r=self.call()
        self.assertEqual(d["releaseChannel"],OUT)
        self.assertFalse(d["isPublished"])
        self.assertEqual(r["geometryVerified"],1)
        self.assertEqual(r["candidateG2"],1)
        self.assertEqual(r["published"],0)
        e=d["entities"][0]
        self.assertEqual(e["quality"]["gate"],"G2")
        self.assertFalse(e["quality"]["seoIndexable"])
        self.assertTrue(e["quality"]["geometryTopologyVerified"])
        self.assertEqual(e["geo"]["area"]["type"],"MultiPolygon")
        self.assertEqual(e["facts"]["osmMappedWaterSurfaceKm2"]["method"],"derived")
        self.assertEqual(e["facts"]["elevationM"]["value"],2200)
        self.assertEqual(e["facts"]["wikidataElevationReportedM"]["value"],2200)
        self.assertEqual(e["sourceIds"]["wikidata"],"Q123")
        self.assertEqual(e["sourceIds"]["osm"],"way/10")
        self.assertEqual(e["media"][0]["licence"],"CC BY-SA 4.0")
        self.assertEqual(e["textSources"][0]["sourceId"],"wikipedia:it:55")

    def test_missing_photo_or_text_cannot_be_G2(self):
        doc,r=self.call(commons_getter=lambda *_:{"query":{"pages":{}}})
        self.assertEqual(r["candidateG2"],0)
        self.assertEqual(doc["entities"][0]["quality"]["gate"],"G1")
        doc,r=self.call(wiki_getter=lambda *_:{"query":{"pages":{}}})
        self.assertEqual(r["candidateG2"],0)
        self.assertEqual(doc["entities"][0]["quality"]["gate"],"G1")

    def test_geometry_provenance_cannot_be_painted_on_a_different_lake(self):
        geo,links=stages()
        for mutation in (
            lambda e:e["sourceIds"].update({"wikidata":"Q999"}),
            lambda e:e["sourceIds"].update({"osm":"way/999"}),
            lambda e:e["quality"].update({"geometryTopologyVerified":False}),
            lambda e:e["facts"]["osmMappedWaterSurfaceKm2"].update({"licence":"unknown"}),
            lambda e:e["geo"].update({"area":None}),
            lambda e:e["geo"]["point"].update({"lng":12.40}),
        ):
            altered=deepcopy(geo)
            mutation(altered["geonamesLinkedEntities"][0])
            with self.assertRaises(ValueError):
                lake_candidates(altered,links)

    def test_geo_type_conflict_and_duplicate_water_identity_blocked(self):
        geo,links=stages()
        altered=deepcopy(geo)
        altered["geonamesLinkedEntities"][0]["subtype"]="reservoir"
        with self.assertRaises(ValueError):
            lake_candidates(altered,links)
        altered=deepcopy(geo)
        altered["geonamesLinkedEntities"].append(deepcopy(altered["geonamesLinkedEntities"][0]))
        with self.assertRaises(ValueError):
            lake_candidates(altered,links)

    def test_unverified_or_published_geometry_is_not_accepted(self):
        geo,links=stages()
        altered=deepcopy(geo)
        altered["releaseChannel"]="GEONAMES_NATURAL_FEATURES_STAGING_V1"
        with self.assertRaises(ValueError):
            lake_candidates(altered,links)
        altered=deepcopy(geo)
        altered["isPublished"]=True
        with self.assertRaises(ValueError):
            lake_candidates(altered,links)
        altered=deepcopy(geo)
        altered["sourceSha256"]="not SHA256"
        with self.assertRaises(ValueError):
            lake_candidates(altered,links)

    def test_wd_P1566_disagreement_rejects_just_that_identity(self):
        def wrong(_url,_params):
            return {"entities":{"Q123":wditem(gid="999",lat=46.501,elevation="+2200")}}
        doc,r=self.call(wd_getter=wrong)
        self.assertEqual(doc["entities"],[])
        self.assertEqual(r["candidateG2"],0)
        self.assertEqual(r["heldReasons"]["wikidata_P1566_mismatch"],1)

    def test_documented_altitude_conflict_holds_G1_without_overwriting(self):
        def other(_url,_params):
            return {"entities":{"Q123":wditem(gid="100",lat=46.501,elevation="+2480")}}
        doc,r=self.call(wd_getter=other)
        e=doc["entities"][0]
        self.assertEqual(e["quality"]["gate"],"G1")
        self.assertTrue(e["quality"]["reviewRequired"])
        self.assertEqual(e["facts"]["elevationM"]["value"],2200)
        self.assertEqual(e["facts"]["wikidataElevationReportedM"]["value"],2480)
        self.assertEqual(r["candidateG2"],0)

    def test_unrelated_water_usage_or_access_never_inferred(self):
        doc,_=self.call()
        e=doc["entities"][0]
        self.assertFalse(any(x["type"]=="accessible_from" for x in e["relations"]))
        for disallowed in ("potable","isSwimmable","bathing","lakeAccess"):
            self.assertNotIn(disallowed,e["facts"])

if __name__=="__main__":
    unittest.main()
