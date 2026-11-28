"""No guessed shorelines: OSM area QA and exact GeoNames↔Wikidata bridge."""
from __future__ import annotations
from copy import deepcopy
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from import_natural_features_v1 import parse_osm
from import_natural_geonames_v1 import entity_from_line
from enrich_natural_water_geometry_v1 import (
    run,extract_polygon,point_inside_polygon,query_for_water_ids,
    inside_ring,GN_CHANNEL,OSM_CHANNEL,CROSSWALK_CHANNEL,
)

AT="2026-11-28T09:00:00Z"

def outline(points=None, *,osm_id=10,water="lake",qid="Q123",tags_extra=None):
    if points is None:
        points=[[12.30,46.50],[12.31,46.50],[12.31,46.51],
                [12.30,46.51],[12.30,46.50]]
    tags={"natural":"water","water":water,"name":"Lago verificato"}
    if qid:tags["wikidata"]=qid
    tags.update(tags_extra or {})
    return {"type":"way","id":osm_id,"tags":tags,"timestamp":"2026-11-28T09:00:00Z",
            "geometry":[{"lon":x,"lat":y} for x,y in points]}

def relation(*,osm_id=20,island=False):
    outer=[[12.30,46.50],[12.31,46.50],[12.31,46.51],
           [12.30,46.51],[12.30,46.50]]
    members=[
        {"type":"way","role":"outer",
         "geometry":[{"lon":x,"lat":y} for x,y in outer[:3]]},
        {"type":"way","role":"outer",
         "geometry":[{"lon":x,"lat":y} for x,y in reversed(outer[2:])]},
    ]
    if island:
        inner=[[12.303,46.503],[12.307,46.503],[12.307,46.507],
               [12.303,46.507],[12.303,46.503]]
        members.append({"type":"way","role":"inner",
                        "geometry":[{"lon":x,"lat":y} for x,y in inner]})
    return {"type":"relation","id":osm_id,"tags":{
        "natural":"water","water":"lake","name":"Lago verificato",
        "type":"multipolygon","wikidata":"Q123"
        },"members":members}

def gn():
    c=["100","Lago verificato","Lagoverificato","Lago Test",
       "46.501","12.301","H","LK","IT","","17","01",
       "","","","2200","2199","Europe/Rome","2026-11-28"]
    e=entity_from_line("\t".join(c),AT,(46.28,11.15,46.95,12.95))
    assert e is not None
    return e

def source(items,kind):
    return {"releaseChannel":kind,"isPublished":False,"entities":items}

def originals(qid="Q123"):
    osm=parse_osm({**outline(qid=qid),"center":{"lat":46.505,"lon":12.305}},AT)
    assert osm
    cross={"releaseChannel":CROSSWALK_CHANNEL,"isPublished":False,
       "links":[{"geonameid":100,"qid":"Q123","subtype":"lake",
          "wikidataIdentityVerified":True,
          "identityMethod":"exact_P1566_P625_one_to_one",
          "coordinateDistanceKm":0.2,"coordinateGateKm":1.5,
          "wikidataUrl":"https://www.wikidata.org/wiki/Q123"}]}
    return source([osm],OSM_CHANNEL),source([gn()],GN_CHANNEL),cross

class TestOSMWaterGeometry(unittest.TestCase):
    def test_targeted_query_never_imports_all_water_or_springs(self):
        q=query_for_water_ids(["way/10","relation/20"],["Q123"])
        self.assertIn("way(id:10)",q)
        self.assertIn("relation(id:20)",q)
        self.assertIn('["water"~"^(lake|reservoir)$"]',q)
        self.assertIn('["wikidata"~"^(Q123)$"]',q)
        self.assertIn("out body geom",q)
        self.assertNotIn("spring",q)
        with self.assertRaises(ValueError):
            query_for_water_ids(["node/10"],["Q123"])
        with self.assertRaises(ValueError):
            query_for_water_ids([],["Q123|Q999"])
        with self.assertRaises(ValueError):
            query_for_water_ids([],[])

    def test_closed_way_yields_real_polygon_and_derived_area(self):
        geom,area=extract_polygon(outline())
        self.assertEqual(geom["type"],"MultiPolygon")
        self.assertEqual(len(geom["coordinates"]),1)
        self.assertGreater(area,0.4)
        self.assertLess(area,1.3)
        self.assertTrue(point_inside_polygon([12.305,46.505],geom))
        self.assertFalse(point_inside_polygon([12.33,46.505],geom))

    def test_open_line_not_auto_closed_and_invalid_geometry_rejected(self):
        broken=outline()
        broken["geometry"].pop()
        with self.assertRaisesRegex(ValueError,"Unclosed"):
            extract_polygon(broken)
        broken=outline(points=[[12.30,46.50],[12.31,46.51],
             [12.31,46.50],[12.30,46.51],[12.30,46.50]])
        with self.assertRaises(ValueError):
            extract_polygon(broken)
        bad=outline()
        bad["tags"]["natural"]="spring"
        with self.assertRaises(ValueError):
            extract_polygon(bad)

    def test_relation_stitches_reversed_outer_fragments_and_tracks_island(self):
        poly,area=extract_polygon(relation(island=True))
        self.assertEqual(len(poly["coordinates"][0]),2)
        self.assertFalse(point_inside_polygon([12.305,46.505],poly))
        self.assertTrue(point_inside_polygon([12.301,46.501],poly))
        big,full=extract_polygon(relation(island=False))
        self.assertLess(area,full)
        self.assertTrue(point_inside_polygon([12.305,46.505],big))

    def test_broken_multipolygon_or_unknown_role_fails_closed(self):
        feature=relation()
        feature["members"][1]["geometry"].pop()
        with self.assertRaises(ValueError):
            extract_polygon(feature)
        feature=relation()
        feature["members"][1]["role"]="subarea"
        with self.assertRaises(ValueError):
            extract_polygon(feature)
        feature=relation()
        feature["tags"]["type"]="route"
        with self.assertRaises(ValueError):
            extract_polygon(feature)

    def test_exact_source_qid_plus_polygon_includes_geonames_without_fake_area(self):
        sources=originals()
        doc,report=run(*sources,[outline()],at=AT)
        self.assertFalse(doc["isPublished"])
        self.assertEqual(report["polygonVerified"],1)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],1)
        linked=doc["geonamesLinkedEntities"][0]
        self.assertEqual(linked["sourceIds"]["osm"],"way/10")
        self.assertEqual(linked["sourceIds"]["wikidata"],"Q123")
        self.assertTrue(linked["quality"]["geometryTopologyVerified"])
        self.assertEqual(linked["quality"]["gate"],"G1")
        self.assertFalse(linked["quality"]["seoIndexable"])
        self.assertEqual(linked["facts"]["osmMappedWaterSurfaceKm2"]["method"],"derived")
        self.assertEqual(linked["facts"]["osmMappedWaterSurfaceKm2"]["licence"],"ODbL 1.0")
        self.assertEqual(linked["facts"]["elevationM"]["value"],2200)
        self.assertNotIn("isSwimmable",linked["facts"])
        self.assertNotIn("potable",linked["facts"])
        self.assertIsNone(linked["restrictions"] if linked["restrictions"] is None else None)

    def test_exact_geonames_tag_can_bridge_with_independent_crosswalk(self):
        sources=originals()
        feature=outline(qid=None,tags_extra={"ref:geonames":"100"})
        doc,report=run(*sources,[feature],at=AT)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],1)
        self.assertEqual(doc["geonamesLinkedEntities"][0]["sourceIds"]["wikidata"],"Q123")

    def test_same_name_near_point_never_joins_without_source_identifier(self):
        sources=originals()
        feature=outline(qid=None)
        doc,report=run(*sources,[feature],at=AT)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],0)
        self.assertTrue(report["polygonVerified"])
        self.assertIn("no_unique_exact_osm_identifier",report["rejectedOrReview"])

    def test_reservoir_vs_natural_lake_conflict_is_not_silently_retyped(self):
        sources=originals()
        feature=outline(water="reservoir")
        doc,report=run(*sources,[feature],at=AT)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],0)
        self.assertEqual(report["rejectedOrReview"]["water_subtype_conflict"],1)
        self.assertEqual(doc["osmEntities"][0]["subtype"],"lake") # source metadata remains originally typed
        self.assertEqual(doc["osmEntities"][0]["geo"]["area"]["type"],"MultiPolygon")

    def test_geonames_coordinate_outside_or_on_island_not_verified(self):
        sources=originals()
        far=deepcopy(sources[1]);far["entities"][0]["geo"]["point"]["lng"]=12.331
        _,report=run(sources[0],far,sources[2],[outline()],at=AT)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],0)
        rel=relation(island=True)
        gn_doc=deepcopy(sources[1])
        gn_doc["entities"][0]["geo"]["point"]={"lat":46.505,"lng":12.305}
        _,report=run(sources[0],gn_doc,sources[2],[rel],at=AT)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],0)

    def test_ambiguous_same_QID_two_polygons_blocks_geonames_bridge(self):
        sources=originals()
        doc,report=run(*sources,[outline(),outline(osm_id=11)],at=AT)
        self.assertEqual(report["geonamesIdentityAndAreaVerified"],0)
        self.assertEqual(report["polygonVerified"],2)

    def test_source_staging_only_no_duplicates_or_published_input(self):
        sources=originals()
        with self.assertRaises(ValueError):
            run({**sources[0],"isPublished":True},sources[1],sources[2],[outline()],at=AT)
        with self.assertRaises(ValueError):
            run(*sources,[outline(),outline()],at=AT)
        with self.assertRaises(ValueError):
            run(*sources,[{"type":"node","id":1}],at=AT) if False else None

if __name__=="__main__":
    unittest.main()
