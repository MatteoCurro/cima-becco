"""Deterministic tests for identity-backed people photos, biography, and graph links."""
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_municipality_people_v1 import enrich_profiles,portrait_candidate

def item_claim(qid):
    return {"rank":"normal","mainsnak":{"datavalue":{"value":{"entity-type":"item","id":qid}}}}
def image_claim(filename):
    return {"rank":"normal","mainsnak":{"datavalue":{"value":filename}}}
def test_item(file="Person A.jpg"):
    return {
      "claims":{
         "P31":[item_claim("Q5")],
         "P18":[image_claim(file)],
         "P19":[item_claim("Q258031")],
         "P20":[item_claim("Q111")],
         "P569":[{"mainsnak":{"datavalue":{"value":{"time":"+1970-01-01T00:00:00Z"}}}}],
         "P800":[item_claim("Q333")],
         "P793":[item_claim("Q444")],
         "P1344":[item_claim("Q555")],
         "P463":[item_claim("Q777")],
         "P742":[image_claim("La Freccia")],
       },
      "labels":{"it":{"value":"Persona Esempio"}},
      "descriptions":{"it":{"value":"alpinista delle Dolomiti"}},
      "sitelinks":{"itwiki":{"title":"Persona Esempio"}},
    }
def source(url,params):
    if "commons.wikimedia.org" in url:
        return {"query":{"pages":{"23":{"title":"File:Person A.jpg","imageinfo":[{
           "thumburl":"https://upload.wikimedia.org/commons/thumb/person.jpg",
           "descriptionurl":"https://commons.wikimedia.org/wiki/File:Person_A.jpg",
           "timestamp":"2021-01-01T00:00:00Z",
           "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
              "Artist":{"value":"Photographer A"},
              "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"}}
           }]}}}}
    if "it.wikipedia.org" in url:
        return {"query":{"pages":{"42":{"title":"Persona Esempio","pageid":42,
         "pageprops":{"wikibase_item":"Q101"},
         "extract":"Persona Esempio è una guida alpina e alpinista italiana. "
                    "Ha studiato e praticato alpinismo sulle Alpi e ha raccontato "
                    "nelle proprie pubblicazioni la storia dei percorsi alpini e "
                    "il lavoro delle guide di montagna."}}}}
    raise AssertionError("Endpoint non previsto: "+url)

class PersonProfileContract(unittest.TestCase):
    def base(self):
        return {"Q101":{"id":"person:Q101","qid":"Q101","name":"Persona Esempio",
          "roles":[{"label":"alpinista","category":"montagna"}],
          "relations":[{"type":"born_in","target":{"id":"municipality:1"},"verified":True}],
          "quality":{"gate":"G1","seoIndexable":False}}}
    def test_licensed_photo_wiki_bio_typed_claims(self):
        profiles=self.base()
        report=enrich_profiles(profiles,{"Q101":test_item()},getter=source,
          checked_at="2026-11-28T01:00:00Z")
        person=profiles["Q101"]
        self.assertEqual(report["portraitsAdded"],1)
        self.assertEqual(report["biographiesAdded"],1)
        self.assertEqual(person["media"][0]["author"],"Photographer A")
        self.assertEqual(person["media"][0]["licence"],"CC BY-SA 4.0")
        self.assertTrue(person["media"][0]["subjectVerified"])
        self.assertTrue(person["media"][0]["reuseAllowed"])
        self.assertEqual(person["textSources"][0]["sourceId"],"wikipedia:it:42")
        self.assertEqual(person["facts"]["birthDate"]["sourceId"],"wikidata:Q101:P569")
        self.assertEqual(person["birthPlaceQids"],["Q258031"])
        self.assertEqual(person["deathPlaceQids"],["Q111"])
        self.assertEqual(person["pseudonyms"],["La Freccia"])
        self.assertEqual({x["type"] for x in person["externalEntityLinks"]},
          {"notable_work","significant_event","participant_in","member_of"})
        self.assertTrue(all(x["resolution"]=="external_identity_only_not_atlas_entity"
          for x in person["externalEntityLinks"]))
        self.assertEqual(person["claim"]["status"],"not_enabled")
        self.assertIsNone(person["claim"]["verifiedUserId"])
        self.assertFalse(person["quality"]["seoIndexable"])
    def test_p18_can_be_a_monument_or_banner_not_person_avatar(self):
        for filename in (
          "Claus_Gatterer_Filmretrospektive_Banner_Bruneck_2014_b.jpg",
          "Annibale_De_Lotto_monumento_carlotti_03_firma.jpg",
          "Titian_-_Allegorie_der_Zeit_(cropped).jpg",
          "Luigi_Gillarduzzi_Hagar_und_Ismael.jpg",
          "Споруда_з_круглим_храмом.jpg",
        ):
            self.assertFalse(portrait_candidate(filename),filename)
        self.assertTrue(portrait_candidate("Valentino_Rovisi_Autoportret_1730.jpg"))
        self.assertTrue(portrait_candidate("Anna_Comarella_850_4530.jpg"))
        # The media is still archived with provenance, only avatar use is
        # disabled until manual subject review.
        profiles=self.base()
        result_item=test_item("Claus_Gatterer_Filmretrospektive_Banner.jpg")
        report=enrich_profiles(profiles,{"Q101":result_item},getter=source)
        self.assertEqual(report["portraitsAdded"],1)
        self.assertEqual(report["imagesHeldForReview"],1)
        self.assertFalse(profiles["Q101"]["media"][0]["portraitCandidate"])
        self.assertNotIn("avatarMediaId",profiles["Q101"])
    def test_wrong_biography_qid_rejected(self):
        def invalid(url,params):
            result=source(url,params)
            if "it.wikipedia.org" in url:
                result["query"]["pages"]["42"]["pageprops"]["wikibase_item"]="Q999"
            return result
        profiles=self.base()
        report=enrich_profiles(profiles,{"Q101":test_item()},getter=invalid)
        self.assertEqual(report["biographiesAdded"],0)
        self.assertFalse(profiles["Q101"].get("textSources"))
    def test_no_photographic_credit_no_image(self):
        def invalid(url,params):
            result=source(url,params)
            if "commons.wikimedia.org" in url:
                result["query"]["pages"]["23"]["imageinfo"][0]["extmetadata"]["Artist"]["value"]=""
            return result
        profiles=self.base()
        report=enrich_profiles(profiles,{"Q101":test_item()},getter=invalid)
        self.assertEqual(report["portraitsAdded"],0)
        self.assertFalse(profiles["Q101"].get("media"))
    def test_wikimedia_outage_preserves_published_verified_picture(self):
        profiles=self.base()
        profiles["Q101"]["media"]=[{
          "kind":"photo","sourceUrl":"https://commons.wikimedia.org/wiki/File:old.jpg",
          "author":"Creator","licence":"CC BY 4.0","subjectVerified":True,
          "reuseAllowed":True,"url":"https://example.org/old.jpg"}]
        def fail(url,params):
            if "commons.wikimedia.org" in url:raise TimeoutError("temporary")
            return source(url,params)
        report=enrich_profiles(profiles,{"Q101":test_item()},getter=fail)
        self.assertEqual(report["portraitsAdded"],0)
        self.assertEqual(profiles["Q101"]["media"][0]["author"],"Creator")
        self.assertTrue(any("commons" in e for e in report["errors"]))

if __name__=="__main__":unittest.main()
