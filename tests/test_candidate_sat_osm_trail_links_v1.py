"""SAT-OSM graph crosswalk G0: require geometry + reference evidence, no false IDs."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from candidate_sat_osm_trail_links_v1 import (
    build_candidates, ref_tokens, comparison, CHANNEL,
)

BBOX = [46.38, 11.68, 46.45, 11.79]
COORDS = [[11.715,46.390],[11.718,46.393],[11.721,46.396],[11.724,46.400]]


def sat(number="E630",coords=None):
    return {
        "releaseChannel":"SAT_TRAILS_TYPED_SOURCE_G0_V1",
        "isPublished":False, "sourceUrl":"https://www.sat.tn.it/sentieri/mappa-sentieri/",
        "sourceArchiveSha256":"a"*64,
        "quality":{"osmCrosswalkVerified":False},
        "records":[record(number,coords)],
    }


def record(number="E630",coords=None):
    return {
        "sourceIds":{"satTrailNumberReported":number},
        "sourceRecordFingerprint":number.lower().ljust(64,"f"),
        "geo":{"geometry":{"type":"LineString","coordinates":coords or COORDS}},
        "quality":{"requiresReview":False},
    }


def segment(way=45,ref="630",coords=None):
    return {
        "sourceIds":{"osmWay":f"way/{way}"},
        "sourceTags":{"ref":ref},
        "geometry":{"type":"LineString","coordinates":coords or COORDS},
    }


def relation(relation_id=100,ref="630",way=45,missing=None):
    return {
        "osmRelationId":relation_id,"ref":ref,"routeType":"hiking",
        "members":[{"osmWayId":way,"role":""}],
        "missingMemberWayIds":missing or [],
        "sourceUrl":f"https://www.openstreetmap.org/relation/{relation_id}",
    }


def osm(ref="630", coords=None, missing=None):
    return {
        "releaseChannel":"OSM_TRAIL_PHYSICAL_GRAPH_G0_STAGING_V1",
        "isPublished":False, "bbox":BBOX,
        "sourceSnapshotSha256":"b"*64,
        "segments":[segment(ref=ref,coords=coords)],
        "routeRelations":[relation(ref=ref,missing=missing)],
    }


class TestSATOSMCrosswalkG0(unittest.TestCase):
    def test_numeric_ref_and_real_matching_geometry_is_only_candidate(self):
        d=build_candidates(sat(),osm(missing=[9999]))
        self.assertGreaterEqual(d["counts"]["relationCandidates"],1)
        route=next(c for c in d["candidates"] if c["targetKind"]=="osm_route_relation")
        self.assertEqual(route["sourceIds"]["satSourceNumber"],"E630")
        self.assertEqual(route["referenceEvidence"]["method"],"numeric_only_ref")
        self.assertEqual(route["reviewStatus"],"candidate_review")
        self.assertTrue(route["osmRelationMembershipIncomplete"])
        self.assertEqual(route["missingMemberWayIds"],[9999])
        self.assertFalse(route["quality"]["crosswalkVerified"])
        self.assertFalse(route["quality"]["routeContinuityVerified"])
        self.assertFalse(d["quality"]["publicationAllowed"])

    def test_full_exact_ref_strong_review_not_automatic_identity(self):
        src=osm("E630")
        src["segments"][0]["sourceTags"]["ref"]=None
        d=build_candidates(sat(),src)
        self.assertEqual(d["counts"]["candidatesTotal"],1)
        c=d["candidates"][0]
        self.assertEqual(c["reviewStatus"],"strong_review")
        self.assertFalse(c["quality"]["canonicalIdentityVerified"])
        self.assertFalse(c["quality"]["crosswalkVerified"])
        self.assertEqual(d["counts"]["candidateCrosswalksVerified"],0)

    def test_geometry_conflict_is_not_a_connection(self):
        remote=[[11.77,46.43],[11.775,46.432],[11.78,46.434]]
        d=build_candidates(sat(),osm(coords=remote))
        conflicts=[x for x in d["candidates"] if x["reviewStatus"]=="geometry_conflict"]
        self.assertTrue(conflicts)
        self.assertTrue(all(not c["quality"]["crosswalkVerified"] for c in conflicts))
        self.assertFalse(any(c["reviewStatus"]=="strong_review" for c in conflicts))

    def test_number_without_geometry_no_candidate(self):
        other=[[11.715,46.395],[11.715,46.395]]
        doc=sat(coords=other)
        doc["records"][0]["geo"]=None
        x=build_candidates(doc,osm())
        self.assertEqual(x["counts"]["candidatesTotal"],0)
        self.assertEqual(x["counts"]["satOutsideOrInsufficientOverlap"],1)

    def test_sat_duplicate_number_held_entirely(self):
        x=sat()
        x["records"].append(deepcopy(x["records"][0]))
        d=build_candidates(x,osm())
        self.assertEqual(d["counts"]["satDuplicateRefHeld"],2)
        self.assertEqual(d["counts"]["candidatesTotal"],0)

    def test_ambiguous_competing_osm_targets_are_not_promoted(self):
        graph=osm("E630")
        graph["segments"].append(segment(way=46,ref=None))
        graph["routeRelations"].append(relation(101,"E630",46))
        graph["segments"][0]["sourceTags"]["ref"]=None
        d=build_candidates(sat(),graph)
        self.assertEqual(d["counts"]["candidatesTotal"],2)
        self.assertEqual(d["counts"]["ambiguousCandidates"],2)
        self.assertTrue(all(c["quality"]["ambiguousCandidate"] for c in d["candidates"]))
        self.assertTrue(all(c["reviewStatus"]=="ambiguous_review" for c in d["candidates"]))

    def test_sat_e_vs_o_prefix_is_not_equal_even_if_same_digits(self):
        graph=osm("E630")
        graph["segments"][0]["sourceTags"]["ref"]=None
        o=sat("O630")
        d=build_candidates(o,graph)
        self.assertEqual(d["counts"]["candidatesTotal"],0)
        self.assertEqual(d["counts"]["satNoRefMatch"],1)

    def test_references_reject_ranges_and_incidental_names(self):
        self.assertEqual(ref_tokens("E630; 630, 630A"),{"E630","630","630A"})
        self.assertEqual(ref_tokens("630-631;E630-631;trail 630"),{"630"})
        self.assertEqual(ref_tokens("a nice trail"),set())

    def test_bbox_and_ferrata_do_not_claim_access(self):
        graph=osm()
        graph["routeRelations"][0]["routeType"]="via_ferrata"
        d=build_candidates(sat(),graph)
        c=next(c for c in d["candidates"] if c["targetKind"]=="osm_route_relation")
        self.assertTrue(c["relationFerrataOnly"])
        self.assertFalse(c["quality"]["ferrataSubtypeVerified"])
        self.assertFalse(c["quality"]["accessibleFromVerified"])
        self.assertEqual(d["releaseChannel"],CHANNEL)
        self.assertFalse(d["routeCatalogueModified"])
        self.assertFalse(d["seoIndexable"])

    def test_incompatible_sources_fail_closed(self):
        changed=sat()
        changed["quality"]["osmCrosswalkVerified"]=True
        with self.assertRaises(ValueError):build_candidates(changed,osm())
        changed=osm()
        changed["sourceSnapshotSha256"]=None
        with self.assertRaises(ValueError):build_candidates(sat(),changed)

    def test_deterministic_outputs(self):
        self.assertEqual(build_candidates(sat(),osm()),build_candidates(deepcopy(sat()),deepcopy(osm())))


if __name__=="__main__":
    unittest.main()
