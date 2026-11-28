"""Offline QA: natural-feature identity, OSM proof and Wikimedia G2 gates."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from resolve_natural_wikidata_v1 import reconcile,run,GN_STAGE,OSM_STAGE
from enrich_natural_wikimedia_v1 import enrich
from import_natural_geonames_v1 import entity_from_line
from import_natural_features_v1 import parse_osm

AT="2026-11-28T09:00:00Z"
TEXT=("Il Passo delle Prove è un valico documentato situato nelle Alpi italiane. "
      "La forcella separa versanti di montagna caratterizzati da una "
      "morfologia alpina complessa ed è parte del territorio montano. "
      "La denominazione geografica compare nei repertori cartografici storici.")

def gnrow(gid=100,name="Passo delle Prove",code="PASS",classification="T"):
    values=[str(gid),name,"Pass","Pass,Probenpass","46.5","12.3",
            classification,code,"IT","","17","01","","","0","2450",
            "2400","Europe/Rome","2026-11-28"]
    return "\t".join(values)

def gn(ident=100,code="PASS",cls="T"):
    e=entity_from_line(gnrow(ident,code=code,classification=cls),AT,
                       (46.1,11.2,47.1,13.0))
    assert e
    return e

def source(*rows,kind=GN_STAGE):
    return {"releaseChannel":kind,"isPublished":False,"entities":list(rows)}

def wdresult(gid=100,qid="Q123",lon=12.3,lat=46.5):
    return {"gid":{"value":str(gid)},
            "item":{"value":"http://www.wikidata.org/entity/"+qid},
            "coordinates":{"value":f"Point({lon} {lat})"}}

def osm(ident=9,qid="Q123",subtype="mountain_pass",lat=46.5,lng=12.3):
    if subtype=="mountain_pass":tags={"name":"Passo delle Prove","mountain_pass":"yes","wikidata":qid}
    else:tags={"name":"Forcella","natural":"saddle","wikidata":qid}
    return parse_osm({"id":ident,"type":"node","tags":tags,"lat":lat,"lon":lng},AT)

def mapped(qid="Q123",osm_verified=None,dist=0.0):
    return {"releaseChannel":"NATURAL_FEATURES_IDENTITY_STAGING_V1",
            "isPublished":False,"links":[{
                "geonameid":100,"qid":qid,
                "wikidataUrl":"https://www.wikidata.org/wiki/"+qid,
                "wikidataIdentityVerified":True,
                "identityMethod":"exact_P1566_P625_one_to_one",
                "coordinateDistanceKm":dist,
                "coordinateGateKm":1.5,
                "subtype":"mountain_pass",
                "osmVerified":osm_verified,
            }]}

def wditem(gid="100",lat=46.5,media="Passo delle Prove.jpg",elevation="+2450"):
    return {"claims":{
        "P1566":[{"mainsnak":{"datavalue":{"value":gid}}}],
        "P625":[{"mainsnak":{"datavalue":{"value":{"latitude":lat,"longitude":12.3}}}}],
        "P18":[{"mainsnak":{"datavalue":{"value":media}}}],
        "P2044":[{"mainsnak":{"datavalue":{"value":{
            "amount":elevation,"unit":"http://www.wikidata.org/entity/Q11573"}}}}],
    },"labels":{"de":{"value":"Probenpass"},"it":{"value":"Passo delle Prove"}},
       "sitelinks":{"itwiki":{"title":"Passo delle Prove"}}}

def wd_get(item=None):
    return lambda _url,_params: {"entities":{"Q123":item if item is not None else wditem()}}

def commons(_url,_params):
    return {"query":{"pages":{"123":{"title":"File:Passo delle Prove.jpg",
        "imageinfo":[{"timestamp":"2019-01-01T00:00:00Z",
          "thumburl":"https://upload.wikimedia.org/wikipedia/test.jpg",
          "descriptionurl":"https://commons.wikimedia.org/wiki/File:Passo_delle_Prove.jpg",
          "extmetadata":{
             "LicenseShortName":{"value":"CC BY-SA 4.0"},
             "LicenseUrl":{"value":"https://creativecommons.org/licenses/by-sa/4.0/"},
             "Artist":{"value":"Autore verificato"},
             "ImageDescription":{"value":"Fotografia del valico"},
           }}]}}}}

def wiki(_url,_params):
    return {"query":{"pages":{"55":{"pageid":55,
        "pageprops":{"wikibase_item":"Q123"},"extract":TEXT,"images":[]}}}}


class TestNaturalSourceResolution(unittest.TestCase):
    def test_exact_geonames_and_p625_proof(self):
        links,reasons=reconcile(source(gn()),[wdresult()])
        self.assertEqual(len(links),1)
        self.assertEqual(links[0]["qid"],"Q123")
        self.assertEqual(links[0]["identityMethod"],"exact_P1566_P625_one_to_one")
        self.assertEqual(sum(reasons.values()),0)

    def test_same_name_or_near_does_not_merge(self):
        links,_=reconcile(source(gn()),[wdresult(gid=999)])
        self.assertFalse(links)
        links,_=reconcile(source(gn()),[wdresult(lon=12.39)])
        self.assertFalse(links)

    def test_ambiguous_multiple_qids_and_same_qid_in_two_records_held(self):
        links,_=reconcile(source(gn()),[wdresult(),wdresult(qid="Q234")])
        self.assertFalse(links)
        links,_=reconcile(source(gn(),gn(101)),[wdresult(),wdresult(gid=101)])
        self.assertFalse(links)

    def test_osm_bridge_requires_exact_qid_subtype_and_coordinate(self):
        links,_=reconcile(source(gn()),[wdresult()],source(osm(),kind=OSM_STAGE))
        self.assertEqual(links[0]["osmVerified"],"node/9")
        for foreign in (osm(qid="Q111"),osm(subtype="saddle"),osm(lng=12.5)):
            links,_=reconcile(source(gn()),[wdresult()],source(foreign,kind=OSM_STAGE))
            self.assertIsNone(links[0]["osmVerified"])
        links,_=reconcile(source(gn()),[wdresult()],
                          source(osm(),osm(10),kind=OSM_STAGE))
        self.assertIsNone(links[0]["osmVerified"])

    def test_G0_ambiguous_slug_does_not_get_an_identity(self):
        e=gn()
        e["quality"]["gate"]="G0"
        e["quality"]["slugRequiresReview"]=True
        links,_=reconcile(source(e),[wdresult()])
        self.assertFalse(links)

    def test_unavailable_WD_batch_cannot_publish_partial_records(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw=Path(tmp)/"gn.json"
            raw.write_text(json.dumps(source(gn(),gn(101))))
            def api(ids):
                if ids==["101"]:raise RuntimeError("service unavailable")
                return {"results":{"bindings":[wdresult()]}}
            with self.assertRaises(RuntimeError):
                run(raw,Path(tmp)/"map.json",batch_size=1,max_items=2,pause=0,getter=api)
            self.assertFalse((Path(tmp)/"map.json").exists())

    def test_reject_published_and_wrong_kind_catalogs(self):
        with self.assertRaises(ValueError):
            reconcile({"releaseChannel":GN_STAGE,"isPublished":True,"entities":[]},[])
        with self.assertRaises(ValueError):
            reconcile(source(gn()),[],source(gn(),kind=OSM_STAGE))


class TestNaturalWikimedia(unittest.TestCase):
    def call(self,items=None, mapping=None, wd_getter=None,
             commons_getter=commons,wiki_getter=wiki):
        return enrich(items or source(gn()),mapping or mapped(),
                      wd_getter=wd_getter or wd_get(),
                      commons_getter=commons_getter,
                      wiki_getter=wiki_getter,at=AT)

    def test_verified_narrative_and_photo_make_only_a_G2_candidate(self):
        doc,report=self.call()
        self.assertFalse(doc["isPublished"])
        self.assertEqual(report["candidateG2"],1)
        e=doc["entities"][0]
        self.assertEqual(e["sourceIds"]["wikidataVerifiedBy"],"P1566+P625")
        self.assertEqual(e["quality"]["gate"],"G2")
        self.assertFalse(e["quality"]["seoIndexable"])
        self.assertEqual(e["media"][0]["licence"],"CC BY-SA 4.0")
        self.assertEqual(e["textSources"][0]["sourceId"],"wikipedia:it:55")
        self.assertEqual(e["facts"]["wikidataElevationReportedM"]["value"],2450)
        self.assertEqual(e["facts"]["elevationM"]["value"],2450)
        self.assertEqual(e["localNames"][0]["language"],"de")
        self.assertEqual(e["description"],TEXT)

    def test_mismatched_wd_claim_rejected_entirely(self):
        doc,report=self.call(wd_getter=wd_get(wditem(gid="201")))
        self.assertFalse(doc["entities"])
        self.assertEqual(report["heldReasons"]["wikidata_P1566_mismatch"],1)

    def test_non_photograph_or_unlicensed_photo_is_not_G2(self):
        doc,report=self.call(wd_getter=wd_get(wditem(media="Map Passo.jpg")))
        self.assertEqual(report["candidateG2"],0)
        self.assertEqual(doc["entities"][0]["quality"]["gate"],"G1")
        def no_license(_url,_params):
            val=commons(_url,_params)
            val["query"]["pages"]["123"]["imageinfo"][0]["extmetadata"].pop("Artist")
            return val
        doc,report=self.call(commons_getter=no_license)
        self.assertEqual(report["withPhoto"],0)
        self.assertEqual(report["candidateG2"],0)

    def test_wikipedia_QID_mismatch_keeps_G1(self):
        def wrong(_url,_params):
            result=wiki(_url,_params)
            result["query"]["pages"]["55"]["pageprops"]["wikibase_item"]="Q999"
            return result
        doc,report=self.call(wiki_getter=wrong)
        self.assertEqual(report["candidateG2"],0)
        self.assertEqual(report["withText"],0)

    def test_lake_without_polygon_must_remain_G1_even_with_photo(self):
        lake=gn(code="LK",cls="H")
        lake["sourceIds"]["geonames"]="100"
        lake["quality"]["areaNotVerified"]=True
        doc,report=self.call(items=source(lake))
        self.assertEqual(doc["entities"][0]["quality"]["gate"],"G1")
        self.assertTrue(doc["entities"][0]["quality"]["needsAreaGeometryReview"])
        self.assertTrue(doc["entities"][0]["quality"]["reviewRequired"])
        self.assertEqual(report["candidateG2"],0)

    def test_elevation_conflicts_remain_separate_and_blocked(self):
        doc,report=self.call(wd_getter=wd_get(wditem(elevation="+2780")))
        e=doc["entities"][0]
        self.assertEqual(e["facts"]["elevationM"]["value"],2450)
        self.assertEqual(e["facts"]["wikidataElevationReportedM"]["value"],2780)
        self.assertEqual(e["quality"]["gate"],"G1")
        self.assertTrue(e["quality"]["elevationConflictReview"])

    def test_reconcile_documented_article_altitude_before_seo(self):
        def alternative(_url,_params):
            d=wiki(_url,_params)
            d["query"]["pages"]["55"]["extract"]=(
                "Il Passo delle Prove è un valico alpino posto a quota "
                "2.390 m s.l.m. Il valico si trova lungo un'antica via "
                "di comunicazione attraverso le montagne, con sentieri "
                "e testimonianze documentate del paesaggio alpino."
            )
            return d
        doc,report=self.call(wiki_getter=alternative)
        e=doc["entities"][0]
        self.assertEqual(e["facts"]["elevationM"]["value"],2450)
        self.assertEqual(e["factsAlternatives"][0]["key"],"elevationM")
        self.assertEqual(e["factsAlternatives"][0]["fact"]["value"],2390)
        self.assertEqual(e["factsAlternatives"][0]["fact"]["licence"],"CC BY-SA 4.0")
        self.assertTrue(e["quality"]["wikiAltitudeDisagreementReview"])
        self.assertTrue(e["quality"]["reviewRequired"])
        self.assertEqual(e["quality"]["gate"],"G1")
        self.assertEqual(report["heldReasons"]["article_altitude_difference_over_45m"],1)

    def test_caption_does_not_misidentify_photo_of_a_nearby_facility(self):
        doc,_=self.call()
        caption=doc["entities"][0]["media"][0]["caption"]
        self.assertEqual(caption,"Fotografia del valico")
        self.assertNotIn("Fotografia documentata di Passo",caption)

    def test_invalid_crosswalk_fails_closed(self):
        row=mapped()
        row["links"][0]["identityMethod"]="same_name_nearest"
        with self.assertRaises(ValueError):
            self.call(mapping=row)
        row=mapped()
        row["links"][0]["wikidataUrl"]="https://www.wikidata.org/wiki/Q999"
        with self.assertRaises(ValueError):
            self.call(mapping=row)

    def test_not_inventing_access_or_water_quality(self):
        doc,_=self.call()
        e=doc["entities"][0]
        self.assertFalse(any(r["type"]=="accessible_from" for r in e["relations"]))
        self.assertNotIn("passIsOpen",e["facts"])
        self.assertNotIn("potable",e["facts"])


if __name__=="__main__":
    unittest.main()
