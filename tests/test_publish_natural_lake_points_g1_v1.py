"""G1 lake point-only release: no invented shore, no duplicated G2, only QID P18 media."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
sys.path.insert(0,str(Path(__file__).resolve().parents[0]))
from test_enrich_natural_water_geometry_v1 import originals,outline,AT
from enrich_natural_water_geometry_v1 import run as geometry_run
from import_natural_geonames_v1 import entity_from_line
from publish_natural_lake_points_g1_v1 import (build,source_gn_lakes,
                                                verified_links,CHANNEL)


def fixtures():
    osm,gn,identity=originals()
    geo,_=geometry_run(osm,gn,identity,[outline()],at=AT)
    src=gn["entities"][0]
    media={
        "id":"photo1","kind":"photo",
        "sourceId":"wikidata:Q123:P18",
        "subjectMethod":"verified_GeoNames_P1566_Wikidata_P625_P18",
        "subjectVerified":True,"reuseAllowed":True,
        "author":"Photo Author","licence":"CC BY 4.0",
        "sourceUrl":"https://commons.wikimedia.org/wiki/File:Verified_lake.jpg",
        "url":"https://upload.wikimedia.org/wikipedia/commons/0/0a/Verified_lake.jpg",
    }
    text={
        "kind":"source_excerpt_not_original_editorial",
        "sourceId":"wikipedia:it:123","sourceUrl":"https://it.wikipedia.org/wiki/Lago_verificato",
        "licence":"CC BY-SA 4.0","text":"Lago documentato e verificato. "*8,
        "method":"reported",
    }
    enrich={"releaseChannel":"NATURAL_FEATURES_G2_CANDIDATES_STAGING_V1",
            "isPublished":False,"entities":[{
                "sourceIds":{"geonames":"100","wikidata":"Q123",
                             "wikidataVerifiedBy":"P1566+P625"},
                "subtype":"lake","geo":src["geo"],"media":[media],"textSources":[text],
                "facts":{}}
            ]}
    published={"releaseChannel":"NATURAL_FEATURES_LAKES_G2",
               "isPublished":True,"entities":[]}
    return gn,identity,geo,enrich,published


class PointLakeG1Test(unittest.TestCase):
    def test_exact_source_links_produce_real_profile_and_licensed_photo(self):
        gn,identity,geo,enrich,g2=fixtures()
        doc,source=build(gn,identity,geo,enrich,g2,at=AT)
        self.assertEqual(doc["releaseChannel"],CHANNEL)
        self.assertFalse(doc["isCanonicalPublished"])
        self.assertTrue(doc["noindexFollow"])
        self.assertEqual(doc["counts"]["profiles"],1)
        self.assertEqual(doc["counts"]["withOsmGeometry"],1)
        self.assertEqual(doc["counts"]["pointOnly"],0)
        self.assertEqual(doc["counts"]["withVerifiedP18"],1)
        self.assertEqual(doc["counts"]["withVerifiedItwiki"],1)
        self.assertEqual(doc["g2Duplicated"],0)
        e=doc["entities"][0]
        self.assertEqual(e["sourceIds"]["wikidataVerifiedBy"],"P1566+P625")
        self.assertEqual(e["quality"]["gate"],"G1")
        self.assertFalse(e["quality"]["seoIndexable"])
        self.assertEqual(e["geo"]["point"],{"lat":46.501,"lng":12.301})
        self.assertEqual(e["sourceIds"]["osm"],"way/10")
        self.assertEqual(e["facts"]["osmMappedWaterSurfaceKm2"]["licence"],"ODbL 1.0")
        self.assertEqual(e["media"][0]["author"],"Photo Author")
        self.assertEqual(e["textSources"][0]["sourceId"],"wikipedia:it:123")
        self.assertFalse(e["quality"]["needsAreaGeometryReview"])
        self.assertEqual(len(source["entities"]),1)

    def test_second_exact_qid_point_without_polygon_generates_noindex_detail(self):
        gn,identity,geo,enrich,g2=fixtures()
        cols=["101","Lago senza riva","Lagosenza","", "46.61","12.40",
              "H","LK","IT","","17","01","","","","1920",
              "1920","Europe/Rome","2026-11-28"]
        second=entity_from_line("\t".join(cols),AT,(46.28,11.15,46.95,12.95))
        self.assertIsNotNone(second)
        gn["entities"].append(second)
        identity["links"].append({
            "geonameid":101,"qid":"Q124","subtype":"lake",
            "wikidataIdentityVerified":True,
            "identityMethod":"exact_P1566_P625_one_to_one",
            "coordinateDistanceKm":0.1,"coordinateGateKm":1.5,
            "wikidataUrl":"https://www.wikidata.org/wiki/Q124"})
        doc,_=build(gn,identity,geo,enrich,g2,at=AT)
        self.assertEqual(doc["counts"]["pointOnly"],1)
        self.assertEqual(doc["counts"]["withOsmGeometry"],1)
        e=next(x for x in doc["entities"] if x["sourceIds"]["geonames"]=="101")
        self.assertIsNone(e["geo"]["area"])
        self.assertIsNone(e["geo"]["areaSourceUrl"])
        self.assertNotIn("osm",e["sourceIds"])
        self.assertFalse(e["media"])
        self.assertTrue(e["quality"]["needsAreaGeometryReview"])
        self.assertEqual(e["facts"]["elevationM"]["value"],1920)
        self.assertNotIn("osmMappedWaterSurfaceKm2",e["facts"])

    def test_g2_lake_is_not_duplicated_as_point_preview(self):
        gn,identity,geo,enrich,g2=fixtures()
        g2["entities"].append({"sourceIds":{"geonames":"100","wikidata":"Q123"}})
        doc,_=build(gn,identity,geo,enrich,g2,at=AT)
        self.assertEqual(doc["entities"],[])
        self.assertEqual(doc["excludedCanonicalG2"],1)
        self.assertEqual(doc["g2Duplicated"],0)

    def test_rejects_wrong_identity_or_geometry_source(self):
        gn,identity,geo,enrich,g2=fixtures()
        for kind in ("qid","point","osm","area","wfs"):
            gg=deepcopy(gn);ii=deepcopy(identity);gr=deepcopy(geo);ee=deepcopy(enrich)
            if kind=="qid":ii["links"][0]["identityMethod"]="name_and_proximity"
            if kind=="point":gg["entities"][0]["geo"]["point"]["lat"]=46.7
            if kind=="osm":gr["geonamesLinkedEntities"][0]["sourceIds"]["osm"]="way/999"
            if kind=="area":gr["geonamesLinkedEntities"][0]["geo"]["area"]=None
            if kind=="wfs":gr["releaseChannel"]="OFFICIAL_LAKE_WFS_G0"
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                build(gg,ii,gr,ee,g2,at=AT)

    def test_ambiguous_qid_and_source_slug_are_rejected(self):
        gn,identity,geo,enrich,g2=fixtures()
        identity["links"].append(deepcopy(identity["links"][0]))
        with self.assertRaises(ValueError):
            build(gn,identity,geo,enrich,g2,at=AT)

    def test_photo_claim_never_inferred_from_name_or_other_qid(self):
        gn,identity,geo,enrich,g2=fixtures()
        altered=deepcopy(enrich)
        altered["entities"][0]["media"][0]["sourceId"]="wikidata:Q456:P18"
        d,_=build(gn,identity,geo,altered,g2,at=AT)
        self.assertEqual(d["counts"]["withVerifiedP18"],0)
        self.assertEqual(d["counts"]["profiles"],1)
        altered=deepcopy(enrich)
        altered["entities"][0]["media"][0]["reuseAllowed"]=False
        d,_=build(gn,identity,geo,altered,g2,at=AT)
        self.assertEqual(d["counts"]["withVerifiedP18"],0)


if __name__=="__main__":
    unittest.main()
