"""Physical trail graph pilot: test topology, separation of ferrata and route relations."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from import_trail_network_v1 import (
    BBOX,CHANNEL,build_graph,parse_way,parse_relation,query_for_bbox,
)

AT="2026-11-28T14:00:00+00:00"

def way(ident,nodes,points,tags=None):
    return {"type":"way","id":ident,"nodes":nodes,
            "geometry":[{"lon":p[0],"lat":p[1]} for p in points],
            "tags":{"highway":"path",**(tags or {})},
            "timestamp":"2026-11-28T13:50:00Z"}

def relation(ident,route,members,**tags):
    return {"type":"relation","id":ident,
            "tags":{"type":"route","route":route,**tags},
            "members":[{"type":"way","ref":wid,"role":""} for wid in members],
            "timestamp":"2026-11-28T13:55:00Z"}

def pilot():
    return {"elements":[
        # Way 11 has an interior junction at node 102.
        way(11,[101,102,103],[[12.200,46.6],[12.201,46.6],[12.202,46.6]],
            {"sac_scale":"mountain_hiking","ref":"432"}),
        way(12,[103,104],[[12.202,46.6],[12.203,46.6]]),
        way(15,[201,102],[[12.201,46.601],[12.201,46.6]]),
        # Same coordinates as node 103, but DIFFERENT OSM node ID: no join.
        way(13,[203,204],[[12.202,46.6],[12.205,46.6]]),
        # Ferrata on actual way tag (the relation alone is weaker evidence).
        way(14,[104,105],[[12.203,46.6],[12.204,46.602]],
            {"via_ferrata_scale":"B","highway":"via_ferrata"}),
        relation(200,"hiking",[11,12],network="lwn",ref="432"),
        relation(201,"via_ferrata",[11,14],name="Ferrata X"),
        relation(202,"foot",[11,13]),
        relation(203,"hiking",[11,999]),  # a missing source member
    ]}

class TestPhysicalNetworkPilot(unittest.TestCase):
    def run_stage(self,source=None,**kwargs):
        return build_graph(source or pilot(),BBOX,at=AT,**kwargs)

    def test_query_selects_physical_paths_and_hiking_foot_ferrata_relations(self):
        q=query_for_bbox(BBOX)
        self.assertIn('way["highway"',q)
        self.assertIn('way["via_ferrata_scale"]',q)
        self.assertIn('foot|hiking|via_ferrata|ferrata',q)
        self.assertIn('out meta geom;',q)
        self.assertIn('out meta;',q)
        self.assertLess(q.index("out meta geom;"),q.index('relation["type"="route"]'))
        # Relations carry only IDs, roles and metadata: no distant member geometry.
        self.assertEqual(q.count("geom;"),1)
        self.assertNotIn('bike',q)
        for invalid in [(30,12,31,13),(46,10,46.3,10.5),(47,13,46,14)]:
            with self.assertRaises(ValueError):query_for_bbox(invalid)

    def test_split_at_real_shared_osm_node_and_keep_all_geometry(self):
        d=self.run_stage()
        edges=[e for e in d["segments"] if e["sourceIds"]["osmWay"]=="way/11"]
        self.assertEqual(len(edges),2)
        self.assertEqual([(e["sourceIds"]["osmNodeStart"],e["sourceIds"]["osmNodeEnd"])
                          for e in edges],[(101,102),(102,103)])
        self.assertEqual(edges[0]["id"],"osm:way/11:span/0-1")
        self.assertEqual(edges[1]["id"],"osm:way/11:span/1-2")
        self.assertEqual(d["counts"]["junctionNodes"],3)  # 102, 103, 104
        self.assertEqual(d["counts"]["waysAccepted"],5)
        self.assertEqual(d["counts"]["graphSegments"],6)
        self.assertTrue(all(e["quality"]["topologyMethod"]=="exact_OSM_node_id" for e in d["segments"]))
        self.assertTrue(all(e["lengthM"]["value"]>0 and e["lengthM"]["licence"]=="ODbL 1.0"
                            for e in d["segments"]))

    def test_coincident_coordinate_with_distinct_id_never_makes_connection(self):
        d=self.run_stage()
        rel=next(x for x in d["routeRelations"] if x["osmRelationId"]==202)
        self.assertEqual(rel["routeType"],"foot")
        self.assertEqual(rel["topologyComponentCount"],2)
        self.assertFalse(rel["topologyContinuousInMappedWays"])
        self.assertEqual(rel["sourceCoverage"],"all_members_with_way_geometries")
        self.assertFalse(rel["canonicalItinerary"])

    def test_missing_route_way_never_gets_invented_section(self):
        d=self.run_stage()
        rel=next(x for x in d["routeRelations"] if x["osmRelationId"]==203)
        self.assertEqual(rel["missingMemberWayIds"],[999])
        self.assertEqual(rel["sourceCoverage"],"partial")
        self.assertFalse(rel["topologyContinuousInMappedWays"])
        self.assertFalse(any("999" in e["sourceIds"]["osmWay"] for e in d["segments"]))
        self.assertEqual(d["counts"]["relationsPartial"],1)
        self.assertFalse(d["isPublished"])
        self.assertFalse(d["routeCatalogueModified"])
        self.assertFalse(d["seoIndexable"])
        self.assertEqual(d["releaseChannel"],CHANNEL)

    def test_relation_ferrata_is_candidate_only_without_way_tag(self):
        d=self.run_stage()
        actual=next(e for e in d["segments"] if e["sourceIds"]["osmWay"]=="way/14")
        candidate=next(e for e in d["segments"] if e["sourceIds"]["osmWay"]=="way/11")
        self.assertEqual(actual["subtype"],"ferrata")
        self.assertEqual(actual["classificationEvidence"],"explicit_way_tag")
        self.assertFalse(actual["ferrataRelationCandidateOnly"])
        self.assertEqual(candidate["subtype"],"trail")
        self.assertTrue(candidate["ferrataRelationCandidateOnly"])
        self.assertEqual(candidate["classificationEvidence"],"route_member_candidate_only")
        self.assertIn(201,candidate["routeRelationIds"])
        self.assertEqual(d["counts"]["ferrataSegmentsExplicit"],1)
        self.assertGreaterEqual(d["counts"]["ferrataSegmentsCandidateOnly"],1)
        self.assertFalse(actual["quality"]["safetyVerified"])
        self.assertFalse(actual["quality"]["traversableVerified"])

    def test_full_original_osm_tag_provenance_survives_g0(self):
        src=pilot()
        src["elements"][0]["tags"]["cai_scale"]="E"
        src["elements"][0]["tags"]["source:ref"]="survey;CAI"
        d=self.run_stage(src)
        edge=next(x for x in d["segments"] if x["sourceIds"]["osmWay"]=="way/11")
        self.assertEqual(edge["sourceTags"]["cai_scale"],"E")
        self.assertEqual(edge["sourceTags"]["source:ref"],"survey;CAI")
        self.assertNotIn("cai_scale",edge["operationalTags"])
        self.assertEqual(edge["sourceUpdatedAt"],"2026-11-28T13:50:00Z")
        self.assertEqual(d["routeRelations"][0]["sourceUpdatedAt"],"2026-11-28T13:55:00Z")

    def test_access_restrictions_are_source_metadata_not_operational_approval(self):
        src=pilot();src["elements"][0]["tags"]["foot"]="private"
        d=self.run_stage(src)
        edge=next(x for x in d["segments"] if x["sourceIds"]["osmWay"]=="way/11")
        self.assertEqual(edge["accessStatus"],"restriction_reported")
        self.assertEqual(edge["sourceTags"]["foot"],"private")
        self.assertFalse(edge["quality"]["traversableVerified"])

    def test_geometry_source_errors_are_fail_closed(self):
        original=pilot()
        broken=deepcopy(original)
        broken["elements"][1]["nodes"]=[103]  # no fabricated vertex IDs
        result=self.run_stage(broken)
        self.assertEqual(result["counts"]["waysAccepted"],4)
        self.assertGreater(result["counts"]["dropped"]["way_not_usable_or_missing_nodes"],0)
        broken=deepcopy(original)
        broken["elements"][1]["geometry"][0]["lat"]=46.63
        with self.assertRaisesRegex(ValueError,"conflicting geometry"):
            self.run_stage(broken)
        broken=deepcopy(original)
        broken["remark"]="runtime error / truncated"
        with self.assertRaises(ValueError):self.run_stage(broken)
        with self.assertRaisesRegex(ValueError,"limit exceeded"):
            self.run_stage(max_ways=3)

    def test_deterministic_network_identity_and_no_auto_joins(self):
        one=self.run_stage()
        two=self.run_stage(deepcopy(pilot()))
        self.assertEqual(one,two)
        self.assertEqual(len({x["id"] for x in one["segments"]}),one["counts"]["graphSegments"])
        self.assertEqual(len(one["sourceSnapshotSha256"]),64)
        self.assertEqual(one["routeRelations"][0]["routeType"],"hiking")
        self.assertTrue(one["routeRelations"][0]["topologyContinuousInMappedWays"])

    def test_nonwalking_ways_are_not_imported_even_if_named_trails(self):
        bad=way(77,[700,701],[[12.2,46.6],[12.21,46.6]],
                {"highway":"motorway","name":"Sentiero CAI 1"})
        self.assertIsNone(parse_way(bad))
        tag_only=way(78,[702,703],[[12.2,46.6],[12.21,46.6]],
                {"highway":"path","name":"Via ferrata del Monte","sac_scale":"demanding_alpine_hiking"})
        self.assertEqual(tag_only["tags"]["name"],"Via ferrata del Monte")
        src={"elements":[tag_only]}
        d=self.run_stage(src)
        self.assertEqual(d["segments"][0]["subtype"],"trail")
        self.assertIsNone(parse_relation(relation(1,"bicycle",[11])))

if __name__=="__main__":unittest.main()
