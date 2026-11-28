"""Fotografie storiche: non derivare l'età da upload, P180/DateTimeOriginal e diritti."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_settlement_history_v1 import enrich_historical_settlements

def release():
    return {
      "releaseChannel":"ISTAT21_OSM_SETTLEMENTS","isPublished":True,
      "entities":[{"id":"settlement:1","name":"Alba","quality":{"gate":"G2"},
        "sourceIds":{"wikidata":"Q123"},
        "textSources":[{"sourceUrl":"https://it.wikipedia.org/wiki/Alba","text":"Storia","sourceId":"wikipedia:it:1"}],
        "media":[{"kind":"photo","url":"https://commons.wikimedia.org/wiki/File:Alba.jpg",
            "sourceUrl":"https://commons.wikimedia.org/wiki/File:Alba.jpg","licence":"CC BY-SA 4.0"}]}]
    }

class HistoryTests(unittest.TestCase):
    def test_exact_subject_and_date_needed(self):
        page={"pageid":55,"filename":"Alba-1920.jpg"}
        info={"claims":{"P180":[{"mainsnak":{"datavalue":{"value":{"entity-type":"item","id":"Q123"}}}}],
                        "P571":[{"mainsnak":{"datavalue":{"value":{"time":"+1920-00-00T00:00:00Z","precision":9}}}}]}}
        asset={"url":"https://upload.wikimedia.org/wikipedia/commons/a/ab/Alba.jpg",
               "sourceUrl":"https://commons.wikimedia.org/wiki/File:Alba-1920.jpg",
               "author":"Archivio locale","licence":"CC BY-SA 4.0",
               "subjectVerified":True,"reuseAllowed":True}
        with patch("enrich_settlement_history_v1.search_depicts",return_value=[page]),\
             patch("enrich_settlement_history_v1.fetch_sdc",return_value={"M55":info}),\
             patch("enrich_settlement_history_v1.fetch_file_dates",return_value={}),\
             patch("enrich_settlement_history_v1.article_history_candidates",return_value=[]),\
             patch("enrich_settlement_history_v1.commons_pages_by_title",return_value=[]),\
             patch("enrich_settlement_history_v1.commons_files",return_value={"Alba-1920.jpg":asset}):
            doc,report=enrich_historical_settlements(release())
        self.assertEqual(report["saved"],1)
        photo=doc["entities"][0]["media"][-1]
        self.assertEqual(photo["capturedAt"],"1920")
        self.assertEqual(photo["subjectMethod"],"commons_media_info_P180_exact_settlement_QID")
        self.assertEqual(photo["historicalDateMethod"],"commons-sdc:P571")

    def test_wrong_subject_not_added(self):
        page={"pageid":55,"filename":"Alba-1920.jpg"}
        item={"claims":{"P180":[{"mainsnak":{"datavalue":{"value":{"entity-type":"item","id":"Q999"}}}}],
                        "P571":[{"mainsnak":{"datavalue":{"value":{"time":"+1920-00-00T00:00:00Z","precision":9}}}}]}}
        with patch("enrich_settlement_history_v1.search_depicts",return_value=[page]),\
             patch("enrich_settlement_history_v1.fetch_sdc",return_value={"M55":item}),\
             patch("enrich_settlement_history_v1.fetch_file_dates",return_value={}),\
             patch("enrich_settlement_history_v1.article_history_candidates",return_value=[]),\
             patch("enrich_settlement_history_v1.commons_pages_by_title",return_value=[]):
            doc,report=enrich_historical_settlements(release())
        self.assertEqual(report["saved"],0)
        self.assertEqual(len(doc["entities"][0]["media"]),1)

    def test_refuse_non_g2_release(self):
        bad=release()
        bad["releaseChannel"]="STAGING_ISTAT21_OSM_SETTLEMENTS"
        with self.assertRaises(ValueError):
            enrich_historical_settlements(bad)
if __name__=="__main__":
    unittest.main()
