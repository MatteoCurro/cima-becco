"""Contract regression tests for source-gated summit G2 staging (offline)."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import sys
import unittest

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
from enrich_summits_wikimedia_v1 import enrich, matches_identity

ARTICLE = (
    "La Cima delle Prove è una montagna documentata nell'arco alpino. "
    "La montagna si eleva sopra un fondovalle, appartiene al sistema orografico "
    "delle Alpi e domina le vallate circostanti. "
    "La sua morfologia è caratterizzata da versanti rocciosi e creste."
)


def stage(slug="cima-delle-prove", ambiguous=False):
    return {"releaseChannel":"GEONAMES_SUMMITS_STAGING_V1","isPublished":False,
        "entities":[{
            "id":"stable-uuid","name":"Cima delle Prove","slug":slug,
            "slugAliases":["gn100-45x10"],"kind":"summit","subtype":"mountain",
            "sourceIds":{"geonames":"100"},
            "quality":{"gate":"G1","seoIndexable":False,
                       "slugRequiresReview":ambiguous},
            "geo":{"point":{"lat":46.5,"lng":12.3}},
            "facts":{"elevationM":{"value":2450,"sourceId":"geonames:100"}},
            "media":[],"relations":[],
        }]}


def crosswalk(qid="Q123"):
    return {"links":[{"geonameid":100,"qid":qid,
            "verified":True,"wdtP1566":"100",
            "identityMethod":"exact_P1566_and_P625_coordinate",
            "sourceUrl":"https://www.wikidata.org/wiki/"+qid}]}


def item(*, coord=46.5, filename="Peak photo.jpg", geonames="100",
         itwiki="Cima delle Prove", elevation="+2450", label="Probegipfel"):
    claims={
        "P1566":[{"mainsnak":{"datavalue":{"value":geonames}}}],
        "P625":[{"mainsnak":{"datavalue":{"value":{
            "latitude":coord,"longitude":12.3}}}}],
        "P31":[{"mainsnak":{"datavalue":{"value":{
            "entity-type":"item","numeric-id":8502}}}}],
        "P2044":[{"mainsnak":{"datavalue":{"value":{
            "amount":elevation,"unit":"http://www.wikidata.org/entity/Q11573"}}}}],
    }
    if filename:
        claims["P18"]=[{"mainsnak":{"datavalue":{"value":filename}}}]
    return {"claims":claims,"labels":{"de":{"value":label}},
            "sitelinks":{"itwiki":{"title":itwiki}}}


def wd(value=None):
    def getter(_url,_params):
        return {"entities":{"Q123":value if value is not None else item()}}
    return getter


def commons(_url,_params):
    return {"query":{"pages":{"1":{"title":"File:Peak photo.jpg",
        "imageinfo":[{"timestamp":"2010-01-01T00:00:00Z",
            "thumburl":"https://upload.wikimedia.org/wikipedia/thumb/peak.jpg",
            "descriptionurl":"https://commons.wikimedia.org/wiki/File:Peak_photo.jpg",
            "extmetadata":{
                "LicenseShortName":{"value":"CC BY-SA 4.0"},
                "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
                "Artist":{"value":"Autore documentato"},
                "ImageDescription":{"value":"Foto della cima"},
            }}]}}}}


def wiki(_url,_params):
    return {"query":{"pages":{"1":{"pageid":14999,
        "pageprops":{"wikibase_item":"Q123"},
        "extract":ARTICLE,"images":[]}}}}


class SummitG2Tests(unittest.TestCase):
    def call(self, raw=None, mapping=None, **kwargs):
        return enrich(raw or stage(), mapping or crosswalk(),
                      wd_getter=kwargs.get("wd_getter",wd()),
                      commons_getter=kwargs.get("commons_getter",commons),
                      wiki_getter=kwargs.get("wiki_getter",wiki),
                      retrieved_at="2026-11-28T08:00:00+00:00")

    def test_all_evidence_required_before_g2(self):
        doc, report=self.call()
        self.assertFalse(doc["isPublished"])
        self.assertEqual(doc["releaseChannel"],"GEONAMES_SUMMITS_G2_STAGING_V1")
        self.assertEqual(report["enrichedG2"],1)
        e=doc["entities"][0]
        self.assertEqual(e["id"],"stable-uuid")
        self.assertEqual(e["slugAliases"],["gn100-45x10"])
        self.assertEqual(e["sourceIds"]["wikidataVerifiedBy"],"P1566+P625")
        self.assertEqual(e["facts"]["wikidataElevationReportedM"]["value"],2450)
        self.assertEqual(e["facts"]["elevationM"]["value"],2450)
        self.assertEqual(e["quality"]["gate"],"G2")
        self.assertFalse(e["quality"]["seoIndexable"])
        self.assertTrue(e["quality"]["candidateIndexable"])
        self.assertEqual(e["media"][0]["licence"],"CC BY-SA 4.0")
        self.assertEqual(e["media"][0]["author"],"Autore documentato")
        self.assertEqual(e["media"][0]["subjectMethod"],"verified_P1566_P625_QID_P18")
        self.assertEqual(e["textSources"][0]["sourceId"],"wikipedia:it:14999")
        self.assertEqual(e["textSources"][0]["licence"],"CC BY-SA 4.0")
        self.assertEqual(e["localNames"][0]["language"],"de")
        self.assertEqual(e["localNames"][0]["value"],"Probegipfel")

    def test_mismatched_p1566_or_coordinates_are_blocked(self):
        for modified,reason in [
            (item(geonames="999"),"wikidata_P1566_mismatch"),
            (item(coord=47.5),"wikidata_P625_coordinates_conflict"),
        ]:
            with self.subTest(reason=reason):
                doc,report=self.call(wd_getter=wd(modified))
                self.assertEqual(doc["entities"],[])
                self.assertEqual(report["heldReasons"].get(reason),1)

    def test_bad_media_and_bad_article_cannot_be_published(self):
        doc, report=self.call(wd_getter=wd(item(filename="map of mountain.jpg")))
        self.assertEqual(len(doc["entities"]),0)
        self.assertEqual(report["heldReasons"]["no_P18_photo"],1)
        def wrong_wikipedia(_url,_params):
            d=wiki(_url,_params)
            d["query"]["pages"]["1"]["pageprops"]["wikibase_item"]="Q999"
            return d
        doc, report=self.call(wiki_getter=wrong_wikipedia)
        self.assertEqual(len(doc["entities"]),0)
        self.assertEqual(report["heldReasons"]["no_verified_wikipedia_excerpt"],1)

    def test_duplicate_name_requires_resolution_before_enrichment(self):
        doc,report=self.call(raw=stage(ambiguous=True))
        self.assertEqual(report["eligible"],0)
        self.assertFalse(doc["entities"])

    def test_conflicting_altitude_is_separate_and_held_for_review(self):
        doc,report=self.call(wd_getter=wd(item(elevation="+2745")))
        e=doc["entities"][0]
        self.assertEqual(e["facts"]["elevationM"]["value"],2450)
        self.assertEqual(e["facts"]["wikidataElevationReportedM"]["value"],2745)
        self.assertTrue(e["quality"]["reviewRequired"])
        self.assertTrue(e["quality"]["elevationConflictReview"])
        self.assertEqual(report["withElevationDisagreement"],1)

    def test_crosswalk_claim_required_and_one_to_one(self):
        bad=crosswalk()
        bad["links"][0]["verified"]=False
        with self.assertRaises(ValueError):
            self.call(mapping=bad)
        bad=crosswalk()
        bad["links"][0]["identityMethod"]="name_distance_guess"
        with self.assertRaises(ValueError):
            self.call(mapping=bad)

    def test_downtime_cannot_invent_page(self):
        def fail(_url,_params):
            raise RuntimeError("503 upstream")
        doc,report=self.call(wd_getter=fail)
        self.assertFalse(doc["entities"])
        self.assertEqual(report["heldReasons"]["wikidata_unavailable"],1)
        self.assertFalse(doc["isPublished"])

    def test_narrative_cannot_imply_an_access_or_first_ascent(self):
        doc,_=self.call()
        e=doc["entities"][0]
        self.assertFalse(e["relations"])
        self.assertNotIn("firstAscent",e["facts"])
        self.assertNotIn("accessible_from",e["facts"])


if __name__=="__main__":
    unittest.main()
