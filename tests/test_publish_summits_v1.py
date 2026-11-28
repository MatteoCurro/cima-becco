"""Offline G2 summit release: semantic merge, zero fake SEO and stable aliases."""
import copy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from publish_summits_v1 import merge, empty_release, append_history, validate_doc

UUID="598ed681-d801-59c9-927a-a5c59c708fcc"
UUID2="edc30af1-3d6b-5ba6-aee8-a5076b09c4b2"
TEXT=("La cima documentata delle Alpi offre un riferimento geografico "
      "per gli itinerari che attraversano le vallate e le creste "
      "circostanti secondo una ricostruzione documentale verificata.")

def example(gn="100",qid="Q123",slug="cima-delle-prove",uid=UUID):
    return {"id":uid,"kind":"summit","subtype":"mountain",
            "name":"Cima delle Prove","slug":slug,
            "slugAliases":["gn"+gn+"-45x10"],
            "sourceIds":{"geonames":gn,"wikidata":qid,
                         "wikidataVerifiedBy":"P1566+P625"},
            "geo":{"point":{"lat":46.5,"lng":12.3}},
            "facts":{"elevationM":{"value":2450,"unit":"m","sourceId":"geonames:"+gn}},
            "description":TEXT,"quality":{"gate":"G2",
                    "slugRequiresReview":False,"reviewRequired":False,
                    "seoIndexable":False,"candidateIndexable":True},
            "relations":[{"type":"near","verified":False,"accessVerified":False}],
            "media":[{"kind":"photo","sourceUrl":"https://commons.wikimedia.org/wiki/File:Peak.jpg",
                      "url":"https://upload.wikimedia.org/test.jpg",
                      "licence":"CC BY 4.0","author":"Archivista",
                      "sourceId":"wikidata:"+qid+":P18",
                      "subjectMethod":"verified_P1566_P625_QID_P18",
                      "reuseAllowed":True,"subjectVerified":True}],
            "textSources":[{"text":TEXT,"licence":"CC BY-SA 4.0",
                            "sourceId":"wikipedia:it:100",
                            "sourceUrl":"https://it.wikipedia.org/wiki/Cima_delle_Prove"}]}

def staged(entities):
    return {"schemaVersion":"1.0","releaseChannel":"GEONAMES_SUMMITS_G2_STAGING_V1",
            "isPublished":False,"generatedAt":"2026-11-28T07:00:00+00:00",
            "entities":entities}


class TestSummitPublication(unittest.TestCase):
    def test_promote_and_preserve_legacy_slug(self):
        doc,report=merge(empty_release(),staged([example()]))
        self.assertEqual(report["added"],1)
        e=doc["entities"][0]
        self.assertTrue(doc["isPublished"])
        self.assertTrue(e["quality"]["seoIndexable"])
        self.assertFalse(e["quality"]["needsReleaseGate"])
        self.assertIn("gn100-45x10",e["slugAliases"])
        validate_doc(doc,staging=False)

    def test_merge_is_idempotent_and_keeps_previous_data(self):
        first,_=merge(empty_release(),staged([example()]))
        second,report=merge(first,staged([example()]))
        self.assertEqual(report["total"],1)
        self.assertEqual(report["refreshed"],1)
        self.assertEqual(first["entities"][0]["id"],second["entities"][0]["id"])
        self.assertEqual(second["entities"][0]["slugAliases"],["gn100-45x10"])

    def test_conflicting_source_id_or_qid_never_merged(self):
        first,_=merge(empty_release(),staged([example()]))
        with self.assertRaises(ValueError):
            merge(first,staged([example(qid="Q234")]))
        with self.assertRaises(ValueError):
            merge(first,staged([example(slug="another-cima")]))

    def test_duplicate_qid_across_release_batches_is_blocked(self):
        first,_=merge(empty_release(),staged([example()]))
        with self.assertRaises(ValueError):
            merge(first,staged([example(gn="101",qid="Q123",slug="another",uid=UUID2)]))

    def test_cross_source_legacy_slug_alias_cannot_redirect_another_peak(self):
        bad=example()
        bad['slugAliases']=['gn101-45x10']
        with self.assertRaises(ValueError):
            merge(empty_release(),staged([bad]))

    def test_bad_photo_or_missing_text_never_promoted(self):
        base=example()
        for mutation in ("photo","text","ambiguity","no_alt","inferred_access"):
            ent=copy.deepcopy(base)
            if mutation=="photo":
                ent["media"][0]["subjectVerified"]=False
            if mutation=="text":
                ent["textSources"]=[]
            if mutation=="ambiguity":
                ent["quality"]["slugRequiresReview"]=True
            if mutation=="no_alt":
                ent["facts"]={}
            if mutation=="inferred_access":
                ent["relations"][0]["accessVerified"]=True
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    merge(empty_release(),staged([ent]))

    def test_history_advances_after_proven_success_only(self):
        h=append_history(None,{"offset":0,"selectedCandidates":100,"eligible":1884},"run-123",at="2026-11-28T00:00:00Z")
        self.assertEqual(h["events"][0]["report"]["offset"],0)
        self.assertEqual(len(append_history(h,{"offset":0,"selectedCandidates":100,"eligible":1884},"run-123")["events"]),1)
        # A different workflow ID must not double-count the same consecutive batch.
        self.assertEqual(len(append_history(h,{"offset":0,"selectedCandidates":100,"eligible":1884},"run-124")["events"]),1)
        advanced=append_history(h,{"offset":100,"selectedCandidates":100,"eligible":1884},"run-125")
        self.assertEqual(len(advanced["events"]),2)
        # A future cycle can revisit a source offset after making real progress.
        self.assertEqual(len(append_history(advanced,{"offset":0,"selectedCandidates":100,"eligible":1884},"run-126")["events"]),3)
        with self.assertRaises(ValueError):
            append_history(None,{"offset":0,"selectedCandidates":0,"eligible":1884},"run-124")
        with self.assertRaises(ValueError):
            append_history(None,None,"run-125")

    def test_one_bad_existing_record_fails_safely(self):
        first,_=merge(empty_release(),staged([example()]))
        first["entities"][0]["quality"]["seoIndexable"]=False
        with self.assertRaises(ValueError):
            merge(first,staged([example()]))


if __name__=="__main__":
    unittest.main()
