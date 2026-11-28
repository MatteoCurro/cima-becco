"""Safe natural water G2 semantic publisher regression."""
from __future__ import annotations
from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
sys.path.insert(0,str(Path(__file__).resolve().parents[0]))
from test_enrich_natural_lakes_wikimedia_v1 import stages,wd,commons,wiki,AT
from enrich_natural_lakes_wikimedia_v1 import run
from publish_natural_lakes_v1 import empty,check,merge,write,read,validate

def staged():
    geom,cross=stages()
    doc,report=run(geom,cross,wd_getter=wd,
                   commons_getter=commons,wiki_getter=wiki,at=AT)
    assert report["candidateG2"]==1
    return doc

class TestLakePublisher(unittest.TestCase):
    def test_source_verified_realistic_lake_publishes_once(self):
        first=staged()
        release,stats=merge(empty(),first)
        self.assertEqual(stats["added"],1)
        self.assertEqual(stats["total"],1)
        self.assertTrue(release["isPublished"])
        e=release["entities"][0]
        self.assertTrue(e["quality"]["seoIndexable"])
        self.assertFalse(e["quality"]["needsReleaseGate"])
        self.assertEqual(e["sourceIds"]["geonames"],"100")
        self.assertEqual(e["sourceIds"]["osm"],"way/10")
        self.assertEqual(e["geo"]["area"]["type"],"MultiPolygon")
        check(release)

    def test_idempotent_refresh_and_frozen_canonical_slug(self):
        old,_=merge(empty(),staged())
        new,stats=merge(old,staged())
        self.assertEqual(stats["added"],0)
        self.assertEqual(stats["refreshed"],1)
        self.assertEqual(len(new["entities"]),1)
        changed=staged()
        changed["entities"][0]["slug"]="another-lake"
        with self.assertRaises(ValueError):
            merge(old,changed)
        changed=staged()
        changed["entities"][0]["sourceIds"]["osm"]="way/11"
        with self.assertRaises(ValueError):
            merge(old,changed)

    def test_missing_P18_itwiki_or_wrong_source_held(self):
        transforms=[
            lambda e:e["media"][0].update({"author":""}),
            lambda e:e["media"][0].update({"sourceId":"wikidata:Q999:P18"}),
            lambda e:e["textSources"].clear(),
            lambda e:e["quality"].update({"elevationConflictReview":True}),
            lambda e:e["sourceIds"].update({"wikidata":"Q222"}),
            lambda e:e["facts"]["osmMappedWaterSurfaceKm2"].update({"licence":"unknown"}),
            lambda e:e["facts"]["osmMappedWaterSurfaceKm2"].update({"value":100.0}),
            lambda e:e["geo"].update({"area":None}),
            lambda e:e["geo"]["point"].update({"lng":12.4}),
            lambda e:e["quality"].update({"geometryTopologyVerified":False}),
            lambda e:e["relations"].append({"type":"accessible_from","verified":False}),
        ]
        for i,mutate in enumerate(transforms):
            with self.subTest(case=i):
                x=staged()
                mutate(x["entities"][0])
                with self.assertRaises(ValueError):
                    merge(empty(),x)

    def test_g1_evidence_never_automatically_indicized(self):
        old,_=merge(empty(),staged())
        latest=staged()
        latest["entities"][0]["quality"]["gate"]="G1"
        new,stats=merge(old,latest)
        self.assertEqual(stats["heldG1"],1)
        self.assertEqual(new["entities"][0]["id"],old["entities"][0]["id"])
        self.assertEqual(stats["total"],1)

    def test_double_QID_or_OSM_outline_causes_release_failure(self):
        old,_=merge(empty(),staged())
        second=staged()
        e=second["entities"][0]
        e["sourceIds"]["geonames"]="101"
        e["facts"]["elevationM"]["sourceId"]="geonames:101"
        e["id"]="e58ec556-8064-5adc-94f6-95ac05f40f2e"
        e["slug"]="another-lake"
        with self.assertRaises(ValueError):
            merge(old,second)
        e["sourceIds"]["wikidata"]="Q321"
        e["facts"]["wikidataIdentityVerified"]["sourceId"]="wikidata:Q321:P1566+P625"
        e["media"][0]["sourceId"]="wikidata:Q321:P18"
        with self.assertRaises(ValueError):
            merge(old,second)

    def test_release_requires_true_published_source_state(self):
        with self.assertRaises(ValueError):
            merge(staged(),staged())
        first,_=merge(empty(),staged())
        with self.assertRaises(ValueError):
            merge(first,first)

    def test_persisted_document_validates_same_as_memory(self):
        one,_=merge(empty(),staged())
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"atlas"/"lakes.json"
            write(path,one)
            loaded=read(path)
            check(loaded)
            self.assertEqual(loaded["entities"][0]["slug"],"lago-verificato")

if __name__=="__main__":
    unittest.main()
