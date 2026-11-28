"""Concurrent publication merge: no dropped QIDs, changed UUIDs or unsafe photos."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from merge_settlement_publication_v1 import merge_releases

def entity(qid,slug):
    return {
      "id":"stable-"+qid,"kind":"settlement","name":slug,"slug":slug,
      "sourceIds":{"wikidata":qid},
      "geo":{"point":{"lat":46.5,"lng":11.5}},
      "quality":{"gate":"G2","seoIndexable":True},
      "textSources":[{"sourceId":"wikipedia:"+qid,"licence":"CC BY-SA 4.0","text":"Geographically verified village"}],
      "media":[{"kind":"photo","sourceUrl":"https://commons.wikimedia.org/wiki/File:"+slug+".jpg",
                 "licence":"CC BY-SA 4.0","author":"Wikimedia author","reuseAllowed":True,"subjectVerified":True}],
      "slugAliases":["osm-n-100"],
    }
def release(*rows,at="2026-11-28T06:00:00Z"):
    return {"schemaVersion":"1.0","isPublished":True,
            "releaseChannel":"ISTAT21_OSM_SETTLEMENTS",
            "generatedAt":at,"entities":list(rows)}

class MergeTests(unittest.TestCase):
    def test_keeps_both_concurrent_g2_dossiers(self):
        old=release(entity("Q1","alba"))
        new=release(entity("Q2","moena"))
        out=merge_releases(old,new)
        self.assertEqual(len(out["entities"]),2)
        self.assertEqual({e["sourceIds"]["wikidata"] for e in out["entities"]},{"Q1","Q2"})
    def test_preserves_dated_historic_images(self):
        old=release(entity("Q1","alba"))
        historical={"kind":"historical_photo",
            "sourceUrl":"https://commons.wikimedia.org/wiki/File:Alba_1930.jpg",
            "author":"Archivio","licence":"CC BY-SA 4.0","reuseAllowed":True,
            "subjectVerified":True,"capturedAt":"1930",
            "historicalDateMethod":"commons-sdc:P571","subjectMethod":"commons_P180_exact"}
        old["entities"][0]["media"].append(historical)
        new=release(entity("Q1","alba"),at="2026-11-28T07:00:00Z")
        out=merge_releases(old,new)
        self.assertEqual(len(out["entities"][0]["media"]),2)
        self.assertEqual(out["entities"][0]["media"][1]["capturedAt"],"1930")
    def test_refuse_changed_permalink_or_uuid(self):
        old=release(entity("Q1","alba"))
        new=release(entity("Q1","different"))
        with self.assertRaisesRegex(ValueError,"Stable entity identity"):
            merge_releases(old,new)
    def test_refuse_duplicate_qid(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            merge_releases(release(),release(entity("Q1","alba"),entity("Q1","alba-2")))
    def test_refuse_unverified_g1_or_photo(self):
        bad=entity("Q1","alba")
        bad["quality"]["gate"]="G1"
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            merge_releases(release(),release(bad))
        bad=entity("Q1","alba")
        bad["media"][0]["reuseAllowed"]=False
        with self.assertRaisesRegex(ValueError,"Commons"):
            merge_releases(release(),release(bad))
    def test_newer_remote_preferred_on_shared_identity(self):
        old=release(entity("Q1","alba"),at="2026-11-28T09:00:00Z")
        old["entities"][0]["description"]="New facts"
        incoming=release(entity("Q1","alba"),at="2026-11-28T08:00:00Z")
        incoming["entities"][0]["description"]="Old facts"
        out=merge_releases(old,incoming)
        self.assertEqual(out["entities"][0]["description"],"New facts")

if __name__=="__main__":unittest.main()
