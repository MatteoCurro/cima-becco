"""Fixture deterministiche per Wikimedia: P635, P18/P94, imageinfo, itwiki QID."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_municipalities_v1 import (
    query_national_istat_qids,commons_files,wikipedia_intro,choose_candidates,enrich
)

QID="Q12345"
CODE="022039"
def wd_claim(value):
    return {"rank":"normal","mainsnak":{"datavalue":{"value":value}}}
def imageinfo():
    return {"query":{"pages":{"1":{"title":"File:Canazei.jpg","imageinfo":[{
      "thumburl":"https://upload.wikimedia.org/thumb/a.jpg",
      "descriptionurl":"https://commons.wikimedia.org/wiki/File:Canazei.jpg",
      "timestamp":"2026-01-01T00:00:00Z",
      "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
                     "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
                     "Artist":{"value":"<a href='#'>Fotografo</a>"}}}]}}}}

def fake_getter(url, params):
    if "sparql" in url:
        return {"results":{"bindings":[
          {"item":{"value":"http://www.wikidata.org/entity/"+QID},"code":{"value":CODE}}
        ]}}
    if "wikidata.org/w/api.php" in url:
        return {"entities":{QID:{"claims":{
          "P635":[wd_claim(CODE)],"P18":[wd_claim("Canazei.jpg")],
          "P625":[wd_claim({"latitude":46.477,"longitude":11.771})],
          "P856":[wd_claim("https://www.comune.canazei.tn.it")]},
          "sitelinks":{"itwiki":{"title":"Canazei"}}}}}
    if "commons.wikimedia" in url:return imageinfo()
    if "wikipedia" in url:
        return {"query":{"pages":{"20":{"pageid":20,"pageprops":{"wikibase_item":QID},
          "extract":"Canazei è un comune del Trentino noto per il contesto delle Dolomiti e per i passi che collegano la valle ai comprensori montani. Nel territorio si sviluppano tradizioni ladine e attività legate alla montagna e al turismo, con una storia documentata dal patrimonio culturale alpino."}}}}
    raise RuntimeError(url)

def archive():
    return {"schemaVersion":"1.0","releaseChannel":"ISTAT_DAIT_MUNICIPALITIES_STAGING",
      "isPublished":False,"retrievedAt":"2026-11-27T21:00:00Z","entities":[{
       "id":"m1","kind":"municipality","subtype":"italian_municipality",
       "name":"Canazei","slug":"canazei","slugAliases":[],
       "sourceIds":{"istat":CODE},"geo":{"point":None,"area":None},
       "facts":{"sindacoNome":{"value":"Persona","sourceId":"dait:mayors:1","sourceUrl":"https://dait.interno.gov.it/"}},
       "administrativeHierarchy":{"region":"Trentino-Alto Adige","province":"Trento","provinceAbbreviation":"TN"},
       "relations":[],"media":[],"editorialStatus":"raw",
       "quality":{"gate":"G0","seoIndexable":False}
      }]}

class MunicipalMediaTests(unittest.TestCase):
    def test_sparql_unique_code_and_qid(self):
        crosswalk,issues=query_national_istat_qids(getter=fake_getter)
        self.assertEqual(crosswalk[CODE],QID)
        self.assertEqual(issues,[])
    def test_photograph_rejects_unlicensed(self):
        photo=commons_files(["Canazei.jpg"],getter=fake_getter)["Canazei.jpg"]
        self.assertEqual(photo["licence"],"CC BY-SA 4.0")
        self.assertEqual(photo["author"],"Fotografo")
        def bad_getter(url,params):
            payload=imageinfo()
            payload["query"]["pages"]["1"]["imageinfo"][0]["extmetadata"].pop("Artist")
            return payload
        self.assertEqual(commons_files(["Canazei.jpg"],getter=bad_getter),{})
    def test_heraldry_svg_uses_commons_raster_thumbnail_and_cannot_be_photo(self):
        def svg_getter(url,params):
            return {"query":{"pages":{"200":{
              "title":"File:Stemma di Canazei.svg","imageinfo":[{
                "url":"https://upload.wikimedia.org/coat.svg",
                "thumburl":"https://upload.wikimedia.org/thumb/coat.svg.png",
                "descriptionurl":"https://commons.wikimedia.org/wiki/File:Stemma_di_Canazei.svg",
                "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
                  "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
                  "Artist":{"value":"Autore stemma"}}}]}}}}
        self.assertEqual(commons_files(["Stemma di Canazei.svg"],getter=svg_getter),{})
        approved=commons_files(["Stemma di Canazei.svg"],getter=svg_getter,allow_svg=True)
        self.assertEqual(approved["Stemma_di_Canazei.svg"]["url"],
                         "https://upload.wikimedia.org/thumb/coat.svg.png")
        def no_raster(url,params):
            d=svg_getter(url,params)
            del d["query"]["pages"]["200"]["imageinfo"][0]["thumburl"]
            return d
        self.assertEqual(commons_files(["Stemma di Canazei.svg"],getter=no_raster,allow_svg=True),{})
    def test_wikipedia_must_confirm_same_qid(self):
        self.assertTrue(wikipedia_intro("Canazei",QID,getter=fake_getter)["text"])
        self.assertIsNone(wikipedia_intro("Canazei","Q999",getter=fake_getter))
    def test_G2_requires_real_media_and_sourced_text(self):
        release,report=enrich(archive(),{CODE:QID},getter=fake_getter,max_new=10,
          retrieved_at="2026-11-27T21:00:00Z")
        self.assertEqual(report["publishedG2"],1)
        self.assertEqual(report["newMedia"],1)
        e=release["entities"][0]
        self.assertTrue(e["quality"]["seoIndexable"])
        self.assertEqual(e["sourceIds"]["wikidata"],QID)
        self.assertEqual(e["geo"]["point"]["lat"],46.477)
        self.assertTrue(e["media"][0]["sourceUrl"].startswith("https://commons.wikimedia.org"))
        self.assertEqual(e["textSources"][0]["licence"],"CC BY-SA 4.0")
    def test_fail_closed_on_wrong_municipality_qid(self):
        def bad_getter(url,params):
            payload=fake_getter(url,params)
            if "wikidata.org/w/api.php" in url:
                payload["entities"][QID]["claims"]["P635"]=[wd_claim("999999")]
            return payload
        release,report=enrich(archive(),{CODE:QID},getter=bad_getter,max_new=10)
        self.assertEqual(report["publishedG2"],0)
        self.assertEqual(report["newMedia"],0)
        self.assertTrue(any("p635_mismatch" in x for x in report["failures"]))
    def test_no_seo_without_photo_and_text(self):
        def bad_getter(url,params):
            if "commons.wikimedia" in url:return {"query":{"pages":{}}}
            return fake_getter(url,params)
        release,report=enrich(archive(),{CODE:QID},getter=bad_getter,max_new=10)
        self.assertEqual(report["publishedG2"],0)

if __name__=="__main__":
    unittest.main()
