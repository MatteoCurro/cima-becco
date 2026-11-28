"""Offline pilot of historic municipal images. No filename-only auto-publication."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_municipality_history_v1 import (
  parse_history_date,recorded_history_date,sdc_depicts_exact,enrich_historical,
  article_history_candidates,safe_historical_scene)
def claim_item(qid,rank="normal"):
  return {"rank":rank,"mainsnak":{"datavalue":{"value":{"entity-type":"item","id":qid}}}}
def claim_date(d):
  return {"mainsnak":{"datavalue":{"value":{"time":d}}}}
def release():
  return {"releaseChannel":"ISTAT_DAIT_MUNICIPALITIES","isPublished":True,
    "entities":[{"name":"Canazei","sourceIds":{"istat":"022039","wikidata":"Q12345",
     "wikidataVerifiedBy":"P635"},"media":[]}]}
def getter(url,params):
  if params.get("list")=="search":
    return {"query":{"search":[{"title":"File:Canazei 1912.jpg","pageid":101},
         {"title":"File:Other town 1911.jpg","pageid":102},
         {"title":"File:Canazei 1901.jpg","pageid":103}]}}
  if params.get("action")=="wbgetentities":
    return {"entities":{
      "M101":{"claims":{"P180":[claim_item("Q12345")],
                          "P571":[claim_date("+1912-01-01T00:00:00Z")]}},
      "M102":{"claims":{"P180":[claim_item("Q99999")],
                          "P571":[claim_date("+1911-01-01T00:00:00Z")]}},
      "M103":{"claims":{"P180":[claim_item("Q12345")],
                          "P571":[claim_date("+2011-01-01T00:00:00Z")]}}
    }}
  if params.get("iiprop")=="extmetadata":
    return {"query":{"pages":{str(i):{
      "title":"File:"+name,"imageinfo":[{"extmetadata":{}}]} for i,name in
      [(101,"Canazei 1912.jpg"),(102,"Other town 1911.jpg"),(103,"Canazei 1901.jpg")]}}}
  if params.get("iiprop")=="url|extmetadata|timestamp":
    return {"query":{"pages":{
      "101":{"title":"File:Canazei 1912.jpg","imageinfo":[{
        "thumburl":"https://upload.wikimedia.org/thumb/canazei-1912.jpg",
        "descriptionurl":"https://commons.wikimedia.org/wiki/File:Canazei_1912.jpg",
        "timestamp":"2024-01-01T00:00:00Z",
        "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
          "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
          "Artist":{"value":"Archive photographer"}}}]}}}}
  raise AssertionError(params)
class HistoryContract(unittest.TestCase):
  def test_date_precision_and_exclusions(self):
    self.assertEqual(parse_history_date("+1912-00-00T00:00:00Z"),"1912")
    self.assertEqual(parse_history_date("+1930-08-00T00:00:00Z"),"1930-08")
    self.assertIsNone(parse_history_date("old picture around 1912"))
    self.assertIsNone(parse_history_date("+2010-02-01T00:00:00Z"))
    self.assertIsNone(parse_history_date("+1770-01-01T00:00:00Z"))
  def test_college_before_after_cannot_be_dated_as_single_1960_scene(self):
    self.assertFalse(safe_historical_scene(
      {"descriptionText":"Longarone (BL) prima e dopo il disastro del Vajont del 1963"},"1960"))
    self.assertTrue(safe_historical_scene(
      {"descriptionText":"Pirago, hamlet of Longarone before Vajont dam disaster"},"1961"))
  def test_exact_depicts_and_date_not_upload(self):
    self.assertTrue(sdc_depicts_exact({"claims":{"P180":[claim_item("Q12345") ]}},"Q12345"))
    self.assertFalse(sdc_depicts_exact({"claims":{"P180":[claim_item("Q999")]}},"Q12345"))
    self.assertEqual(recorded_history_date({"claims":{}},{}),(None,None))
  def test_pilot_emits_only_verified_historic_photos(self):
    doc,report=enrich_historical(release(),getter=getter,checked_at="2026-11-28")
    self.assertEqual(report["imagesSaved"],1)
    self.assertEqual(report["historicalMunicipalities"],1)
    items=doc["entities"][0]["media"]
    self.assertEqual(len(items),1)
    self.assertEqual(items[0]["capturedAt"],"1912-01-01")
    self.assertEqual(items[0]["historicalDateMethod"],"commons-sdc:P571")
    self.assertEqual(items[0]["subjectMethod"],"commons_media_info_P180_exact_municipality_QID")
    self.assertEqual(items[0]["author"],"Archive photographer")
    self.assertEqual(items[0]["licence"],"CC BY-SA 4.0")
  def test_article_photo_candidate_needs_same_QID_and_full_name(self):
    doc=release()["entities"][0]
    doc["textSources"]=[{"sourceUrl":"https://it.wikipedia.org/wiki/Canazei"}]
    def wiki(url,params):
      return {"query":{"pages":{"42":{"pageprops":{"wikibase_item":"Q12345"},
        "images":[{"title":"File:Canazei panorama 1930.jpg"},
                  {"title":"File:Canazei-Stemma.svg"},
                  {"title":"File:Trento old view.jpg"},
                  {"title":"File:Canazei map 1930.jpg"}]}}}}
    self.assertEqual(article_history_candidates(doc,getter=wiki),["Canazei panorama 1930.jpg"])
    def other(url,params):
      result=wiki(url,params)
      result["query"]["pages"]["42"]["pageprops"]["wikibase_item"]="Q99999"
      return result
    self.assertEqual(article_history_candidates(doc,getter=other),[])
  def test_outage_does_not_erase_prior_photos(self):
    doc=release()
    doc["entities"][0]["media"]=[{"kind":"historical_photo","sourceUrl":"https://commons.wikimedia.org/wiki/File:old"}]
    def fail(url,params):raise TimeoutError("temporaneo")
    updated,report=enrich_historical(doc,getter=fail)
    self.assertEqual(len(updated["entities"][0]["media"]),1)
    self.assertEqual(len(report["errors"]),1)
if __name__=="__main__":unittest.main()
