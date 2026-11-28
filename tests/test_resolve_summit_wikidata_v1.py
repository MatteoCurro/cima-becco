"""Offline tests for conservative GeoNames -> Wikidata P1566/P625 linking."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts/resolve_summit_wikidata_v1.py"
spec=importlib.util.spec_from_file_location("summit_wd",SCRIPT)
wd=importlib.util.module_from_spec(spec)
spec.loader.exec_module(wd)


def entity(ident, lat=46.5, lng=12.3, kind="summit"):
    return {"sourceIds":{"geonames":str(ident)},
            "geo":{"point":{"lat":lat,"lng":lng}},"kind":kind}


def result(gid, qid, lon=12.3, lat=46.5):
    return {"gid":{"value":str(gid)},
            "item":{"value":"https://www.wikidata.org/entity/"+qid},
            "coordinates":{"value":f"Point({lon} {lat})"}}


class SummitWikidataTest(unittest.TestCase):
    def test_verified_exact_claim_and_coordinates(self):
        links,reasons=wd.verify([result(100,"Q123")],[entity(100)])
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]["wdtP1566"],"100")
        self.assertEqual(links[0]["qid"],"Q123")
        self.assertTrue(links[0]["verified"])
        self.assertEqual(sum(reasons.values()),0)

    def test_distance_is_not_an_identity_resolver(self):
        # Different ID, even same coordinates, stays unmatched.
        links,reasons=wd.verify([result(101,"Q123")],[entity(100)])
        self.assertFalse(links)
        self.assertEqual(reasons["unrecognized_id_or_qid"],1)
        links,reasons=wd.verify([result(100,"Q123",lon=10.0)],[entity(100)])
        self.assertFalse(links)
        self.assertEqual(reasons["coordinate_disagreement"],1)

    def test_ambiguous_and_duplicated_claims_are_held(self):
        rows=[result(100,"Q123"),result(100,"Q456")]
        links,reasons=wd.verify(rows,[entity(100)])
        self.assertFalse(links)
        self.assertEqual(reasons["ambiguous_qid_for_geonames"],1)
        links,reasons=wd.verify([result(100,"Q123"),
                                  result(101,"Q123",12.3,46.5)],
                                [entity(100),entity(101)])
        self.assertFalse(links)
        self.assertEqual(reasons["ambiguous_geonames_for_qid"],2)

    def test_non_geolocated_claim_cannot_pass(self):
        item=result(100,"Q123")
        del item["coordinates"]
        links,reasons=wd.verify([item],[entity(100)])
        self.assertFalse(links)
        self.assertEqual(reasons["wd_coordinates_missing"],1)

    def test_group_center_is_only_provisional_and_limited(self):
        links,_=wd.verify([result(100,"Q123",lon=12.36)],
                          [entity(100,kind="mountain_group")])
        self.assertEqual(len(links),1)
        links,_=wd.verify([result(100,"Q123",lon=14)],
                          [entity(100,kind="mountain_group")])
        self.assertFalse(links)

    def test_bounded_batch_offline_and_network_failure_reporting(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"summits.json"
            output=Path(tmp)/"wikidata-map.json"
            source.write_text(json.dumps({"isPublished":False,
                "releaseChannel":"GEONAMES_SUMMITS_STAGING_V1",
                "entities":[entity(100),entity(101)]}),encoding="utf-8")
            def api(ids):
                if ids==["101"]:
                    raise RuntimeError("temporarily unavailable")
                return {"results":{"bindings":[result(100,"Q123")]}}
            report=wd.run(source,output,max_items=2,batch_size=1,pause=0,getter=api)
            self.assertEqual(report["matched"],1)
            self.assertEqual(report["heldReasons"]["source_unavailable"],1)
            self.assertFalse(report["isPublished"])
            self.assertTrue(output.exists())
            self.assertEqual(len(json.loads(output.read_text())["links"]),1)
            self.assertEqual(json.loads(
                output.with_name("summit-wikidata-report.json").read_text())["attempted"],2)

    def test_reject_published_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            src=Path(tmp)/"data.json"
            src.write_text(json.dumps({"isPublished":True,
                "releaseChannel":"GEONAMES_SUMMITS_STAGING_V1"}))
            with self.assertRaises(ValueError):
                wd.run(src,Path(tmp)/"out.json",pause=0,getter=lambda _: {})

    def test_query_parameters_safe(self):
        self.assertIn('VALUES ?gid { "100" "102" }',wd.query_text(["100","102"]))
        with self.assertRaises(ValueError):
            wd.query_text(["100", "1}; DROP ALL"])

if __name__=="__main__":
    unittest.main()
