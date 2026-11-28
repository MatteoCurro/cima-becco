"""Contratti di pubblicazione G2: identità multipla, media e testo verificati."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_settlements_wikimedia_v1 import enrich

WP_TEXT=("Alba è un centro abitato di alta montagna situato nella valle. "
         "La sua storia è legata ai percorsi tradizionali, alle attività agricole "
         "e ai collegamenti tra i piccoli insediamenti del territorio. "
         "Il nucleo conserva un patrimonio documentato di case e paesaggi alpini.")
SRC="https://www.istat.it/"
def official():
    return {
        "id":"istatid","kind":"settlement","subtype":"centro_abitato",
        "name":"Alba","slug":"alba-canazei","slugAliases":[],
        "sourceIds":{"istatLocality":"02100110002","istatMunicipality":"021001"},
        "geo":{"point":{"lat":46.468,"lng":11.78},"sourceUrl":SRC},
        "facts":{"popolazione":{"value":120,"validFrom":"2021-12-31"}},
        "relations":[{"type":"part_of","target":{"id":"muni1","name":"Canazei","kind":"municipality","slug":"canazei"},"verified":True}],
        "media":[],"quality":{"gate":"G1","seoIndexable":False},
    }
def legacy():
    return {
        "id":"osmid","kind":"settlement","subtype":"abitato_osm_non_classificato",
        "name":"Alba","slug":"alba","slugAliases":["osm-n-202"],
        "sourceIds":{"osm":"node/202","wikidata":"Q123"},
        "geo":{"point":{"lat":46.4681,"lng":11.7801}},
        "facts":{},"relations":[],"media":[],
        "quality":{"gate":"G0","seoIndexable":False},
    }
MUNICIPALITIES={"entities":[{"id":"muni1","name":"Canazei","slug":"canazei",
    "sourceIds":{"istat":"021001","wikidata":"Q999"}}]}
PEOPLE={"entities":[{"id":"person:Q55","qid":"Q55","name":"Guida Test",
      "birthPlaceQids":["Q123"],"roles":[{"category":"montagna","label":"guida alpina"}]}]}
def wb_item(*,name="Alba",lat=46.468,lon=11.78,has_photo=True,parent="Q999"):
    claims={
      "P625":[{"mainsnak":{"datavalue":{"value":{"latitude":lat,"longitude":lon}}}}],
      "P131":[{"mainsnak":{"datavalue":{"value":{"entity-type":"item","numeric-id":int(parent[1:])}}}}],
      "P31":[{"mainsnak":{"datavalue":{"value":{"entity-type":"item","numeric-id":486972}}}}],
    }
    if has_photo:claims["P18"]=[{"mainsnak":{"datavalue":{"value":"Alba.jpg"}}}]
    return {"labels":{"it":{"value":name}},"claims":claims,
            "sitelinks":{"itwiki":{"title":"Alba"}}}
def wd(_url,_params):
    return {"entities":{"Q123":wb_item()}}
def commons(_url,_params):
    return {"query":{"pages":{"1":{"title":"File:Alba.jpg","imageinfo":[{
        "thumburl":"https://upload.wikimedia.org/wikipedia/commons/thumb/a/ab/Alba.jpg/700px-Alba.jpg",
        "descriptionurl":"https://commons.wikimedia.org/wiki/File:Alba.jpg",
        "extmetadata":{"LicenseShortName":{"value":"CC BY-SA 4.0"},
                       "Artist":{"value":"Autrice documentata"},
                       "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"}}}]}}}}
def wiki(_url,_params):
    return {"query":{"pages":{"1":{"pageid":21,"pageprops":{"wikibase_item":"Q123"},
                   "extract":WP_TEXT,"images":[]}}}}
class WikiG2Tests(unittest.TestCase):
    def test_verified_match_with_istat_parent_and_people(self):
        stage={"releaseChannel":"STAGING_ISTAT21_OSM_SETTLEMENTS","isPublished":False,
               "entities":[official(),legacy()]}
        release,report=enrich(stage,MUNICIPALITIES,PEOPLE,limit=5,wd_getter=wd,
                              commons_getter=commons,wiki_getter=wiki)
        self.assertEqual(report["publishedG2"],1)
        self.assertEqual(report["withIstatExactMatch"],1)
        e=release["entities"][0]
        self.assertEqual(e["id"],"istatid")
        self.assertEqual(e["slug"],"alba-canazei")
        self.assertIn("osm-n-202",e["slugAliases"])
        self.assertEqual(e["sourceIds"]["osm"],"node/202")
        self.assertEqual(e["quality"]["gate"],"G2")
        self.assertTrue(e["quality"]["seoIndexable"])
        self.assertEqual(e["facts"]["popolazione"]["value"],120)
        self.assertEqual(e["media"][0]["sourceId"],"wikidata:Q123:P18")
        self.assertTrue(e["media"][0]["reuseAllowed"])
        self.assertEqual(e["textSources"][0]["licence"],"CC BY-SA 4.0")
        self.assertEqual(e["connectedPeople"][0]["name"],"Guida Test")
        self.assertEqual(e["connectedPeople"][0]["relationType"],"birthplace_of")

    def test_names_and_coords_are_gates_not_guesswork(self):
        stage={"releaseChannel":"STAGING_ISTAT21_OSM_SETTLEMENTS","isPublished":False,
               "entities":[official(),legacy()]}
        for changed in ({"name":"Omonimo"}, {"lat":47.8,"lon":12.3}):
            def bad_wd(url,params):
                return {"entities":{"Q123":wb_item(**changed)}}
            release,report=enrich(stage,MUNICIPALITIES,limit=2,wd_getter=bad_wd,
                commons_getter=commons,wiki_getter=wiki)
            self.assertEqual(report["publishedG2"],0)
            self.assertFalse(release["entities"])

    def test_license_and_article_qid_required(self):
        stage={"releaseChannel":"STAGING_ISTAT21_OSM_SETTLEMENTS","isPublished":False,
               "entities":[legacy()]}
        def bad_wiki(url,params):
            d=wiki(url,params);d["query"]["pages"]["1"]["pageprops"]["wikibase_item"]="Q999"
            return d
        release,_=enrich(stage,MUNICIPALITIES,limit=2,wd_getter=wd,
                          commons_getter=commons,wiki_getter=bad_wiki)
        self.assertFalse(release["entities"])

    def test_old_g2_preserved_when_wikidata_unavailable(self):
        stage={"releaseChannel":"STAGING_ISTAT21_OSM_SETTLEMENTS","isPublished":False,
               "entities":[legacy()]}
        first,_=enrich(stage,MUNICIPALITIES,limit=2,wd_getter=wd,
                        commons_getter=commons,wiki_getter=wiki)
        def failed(url,params):raise RuntimeError("temporary 503")
        second,_=enrich(stage,MUNICIPALITIES,limit=2,previous=first,wd_getter=failed,
                         commons_getter=commons,wiki_getter=wiki)
        self.assertEqual(first["entities"][0]["id"],second["entities"][0]["id"])
        self.assertEqual(second["entities"][0]["quality"]["gate"],"G2")

if __name__=="__main__":
    unittest.main()
