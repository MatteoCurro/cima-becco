"""Publish only independently verified, unambiguous natural pass G2."""
from __future__ import annotations
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from test_natural_wikimedia_v1 import source,gn,mapped,wd_get,commons,wiki
from enrich_natural_wikimedia_v1 import enrich
from publish_natural_passes_v1 import merge,empty,check_doc

AT="2026-11-28T09:00:00Z"

def staged():
    doc,report=enrich(source(gn()),mapped(),
        wd_getter=wd_get(),commons_getter=commons,wiki_getter=wiki,at=AT)
    assert report["candidateG2"]==1
    return doc

class TestNaturalPassPublication(unittest.TestCase):
    def test_source_verified_G2_promoted_and_id_stable(self):
        original=staged()
        release,stats=merge(empty(),original)
        self.assertEqual(stats["added"],1)
        self.assertTrue(release["isPublished"])
        e=release["entities"][0]
        self.assertEqual(e["id"],original["entities"][0]["id"])
        self.assertEqual(e["slug"],"passo-delle-prove")
        self.assertTrue(e["quality"]["seoIndexable"])
        self.assertFalse(e["quality"]["needsReleaseGate"])
        self.assertEqual(e["sourceIds"]["geonames"],"100")
        check_doc(release)

    def test_refresh_keeps_an_old_verified_osm_link_if_new_batch_lacks_it(self):
        initial=staged()
        initial["entities"][0]["sourceIds"].update({
          "osm":"node/44","osmVerifiedBy":"OSM_QID_tag+GeoNames_P1566+WD_P625"})
        first,_=merge(empty(),initial)
        next_,stats=merge(first,staged())
        self.assertEqual(stats["added"],0)
        self.assertEqual(stats["refreshed"],1)
        self.assertEqual(next_["entities"][0]["sourceIds"]["osm"],"node/44")
        self.assertEqual(len(next_["entities"]),1)

    def test_bad_media_text_identity_or_altitude_never_published(self):
        original=staged()
        mutations=[
          ("wrong QID",lambda e:e["sourceIds"].update({"wikidata":"Q999"})),
          ("no author",lambda e:e["media"][0].pop("author")),
          ("no text",lambda e:e["textSources"].clear()),
          ("bad gate",lambda e:e["quality"].update({"gate":"G1"})),
          ("review altitude",lambda e:e["quality"].update({"wikiAltitudeDisagreementReview":True})),
          ("fake access",lambda e:e["relations"].append({"type":"accessible_from","verified":False})),
          ("made-up osm link",lambda e:e["sourceIds"].update({"osm":"node/1"})),
        ]
        for label,change in mutations:
            with self.subTest(label=label):
                doc=copy.deepcopy(original)
                change(doc["entities"][0])
                if label=="bad gate":
                    release,report=merge(empty(),doc)
                    self.assertEqual(report["total"],0)
                else:
                    with self.assertRaises(ValueError):
                        merge(empty(),doc)

    def test_cross_batch_qid_or_public_url_collision_blocked(self):
        first,_=merge(empty(),staged())
        second=staged()
        e=second["entities"][0]
        e["sourceIds"]["geonames"]="101"
        e["facts"]["elevationM"]["sourceId"]="geonames:101"
        e["id"]="15f60ed5-b8d0-5c50-9953-492f66902eae"
        with self.assertRaises(ValueError):
            merge(first,second)
        e["sourceIds"]["wikidata"]="Q234"
        e["facts"]["wikidataIdentityVerified"]["sourceId"]="wikidata:Q234:P1566+P625"
        e["media"][0]["sourceId"]="wikidata:Q234:P18"
        with self.assertRaises(ValueError):
            merge(first,second)

    def test_no_G2_keeps_public_catalog_without_dropping_it(self):
        first,_=merge(empty(),staged())
        batch=staged()
        batch["entities"][0]["quality"]["gate"]="G1"
        newer,report=merge(first,batch)
        self.assertEqual(report["total"],1)
        self.assertEqual(newer["entities"][0]["sourceIds"]["wikidata"],"Q123")

    def test_published_dataset_is_not_accepted_as_import_input(self):
        first,_=merge(empty(),staged())
        with self.assertRaises(ValueError):
            merge(first,first)


if __name__=="__main__":
    unittest.main()
