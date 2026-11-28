"""SAT G1 verified reference: never confuse source identity with route safety."""
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
import json
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from publish_sat_route_source_refs_v1 import publish, canonical_hash, CHANNEL

SAT_URL="https://www.sat.tn.it/sentieri/mappa-sentieri/"
ZIP=b"PK\x03\x04an original SAT ZIP fixture"


def data(number="E630", rid=7289913):
    sat={
        "releaseChannel":"SAT_TRAILS_TYPED_SOURCE_G0_V1","isPublished":False,
        "sourceArchiveSha256":sha256(ZIP).hexdigest(),"retrievedAt":"2026-11-28T14:00:00Z",
        "quality":{"osmCrosswalkVerified":False},
        "records":[
            {"sourceIds":{"satTrailNumberReported":number},
             "quality":{"requiresReview":False},
             "originalDifficulty":{"value":"E","scale":"CAI/SAT source value",
                                   "sourceUrl":SAT_URL,"sourceId":"sat:trail-catasto-kml"},
             "originalContext":{"startPlaceAsText":"RIFUGIO A","endPlaceAsText":"PASSO B"},
             "facts":{k:{"value":100+i,"unit":u,"method":"reported","sourceUrl":SAT_URL,
                         "licence":"ODbL 1.0","retrievedAt":"2026-11-28T14:00:00Z"}
                      for i,(k,u) in enumerate((
                         ("elevationStartReportedM","m"),("elevationEndReportedM","m"),
                         ("elevationMinReportedM","m"),("elevationMaxReportedM","m"),
                         ("lengthPlanimetricReportedM","m"),("lengthInclinedReportedM","m"),
                         ("durationOutReportedMin","min"),("durationBackReportedMin","min")))}}
        ]
    }
    original={
        "elements":[{"type":"relation","id":rid,
                     "tags":{"ref":number[1:],"reg_ref":number,"route":"hiking",
                             "operator":"Società degli Alpinisti Tridentini",
                             "source":"SAT;survey:CAI","cai_scale":"E"}}]
    }
    osm={"releaseChannel":"OSM_TRAIL_PHYSICAL_GRAPH_G0_STAGING_V1",
         "isPublished":False,"sourceSnapshotSha256":canonical_hash(original),
         "bbox":[46.38,11.68,46.45,11.79],
         "routeRelations":[{"osmRelationId":rid,"routeType":"hiking"}]}
    candidate={
        "sourceIds":{"satSourceNumber":number,"osmSourceId":f"relation/{rid}"},
        "targetKind":"osm_route_relation","reviewStatus":"candidate_review",
        "quality":{"ambiguousCandidate":False},
        "osmRelationMembershipIncomplete":True,
        "geometryEvidence":{
            "satSamples":30,"osmSamples":30,
            "satWithin40mFraction":1,"osmWithin40mFraction":1,
            "satP90DistanceM":0.1,"osmP90DistanceM":0.2,
            "distanceMethod":"local_equirectangular_point_to_polyline_2d_v1",
        },
    }
    crosswalk={"releaseChannel":"TRAIL_SAT_OSM_CROSSWALK_CANDIDATES_G0_V1",
               "isPublished":False,"sourceArchiveSha256":sat["sourceArchiveSha256"],
               "osmSourceSnapshotSha256":osm["sourceSnapshotSha256"],
               "candidates":[candidate]}
    manifest={"lookup":{f"osm-hiking-{rid}":"it_46_11"}}
    return sat, ZIP, osm, original, crosswalk, manifest


class SATSourceRefReleaseTests(unittest.TestCase):
    def check(self,x):
        return publish(*x)

    def test_exact_sat_reg_ref_operator_difficulty_geometry_releases_only_source_facts(self):
        d=self.check(data())
        self.assertEqual(d["releaseChannel"],CHANNEL)
        self.assertEqual(d["counts"]["verifiedLiveSourceReferences"],1)
        self.assertEqual(len(d["records"]),1)
        r=d["records"]["osm-hiking-7289913"]
        self.assertEqual(r["sourceReference"]["number"],"E630")
        self.assertEqual(len(r["reportedFacts"]),8)
        self.assertTrue(r["identityEvidence"]["sourceReferenceVerified"])
        self.assertFalse(r["quality"]["routeContinuityVerified"])
        self.assertTrue(r["quality"]["osmRelationMembershipIncomplete"])
        self.assertFalse(r["quality"]["accessToSummitOrHutVerified"])
        self.assertFalse(r["quality"]["ferrataSubtypeVerified"])
        self.assertFalse(r["quality"]["canonicalEntityMergePerformed"])
        self.assertFalse(d["newCanonicalPagesCreated"])
        self.assertFalse(d["seoIndexable"])
        self.assertFalse(d["quality"]["routingAllowed"])

    def test_numeric_ref_alone_does_not_release_without_full_reg_ref(self):
        x=list(data());x[3]["elements"][0]["tags"].pop("reg_ref");x[2]["sourceSnapshotSha256"]=canonical_hash(x[3]);x[4]["osmSourceSnapshotSha256"]=x[2]["sourceSnapshotSha256"]
        with self.assertRaisesRegex(ValueError,"No SAT source references"):self.check(x)

    def test_source_and_operator_must_both_attest_sat(self):
        for key,val in (("source","third-party survey"),("operator","Other Club"),
                        ("cai_scale","EE")):
            x=list(data());x[3]["elements"][0]["tags"][key]=val
            x[2]["sourceSnapshotSha256"]=canonical_hash(x[3])
            x[4]["osmSourceSnapshotSha256"]=x[2]["sourceSnapshotSha256"]
            with self.subTest(key=key):
                with self.assertRaises(ValueError):self.check(x)

    def test_reported_facts_and_source_must_not_be_edited(self):
        x=list(data());x[0]["records"][0]["facts"]["lengthInclinedReportedM"]["method"]="inferred"
        with self.assertRaises(ValueError):self.check(x)
        x=list(data());x[0]["records"][0]["quality"]["requiresReview"]=True
        with self.assertRaises(ValueError):self.check(x)

    def test_nearby_but_discordant_geometry_is_held(self):
        x=list(data());x[4]["candidates"][0]["geometryEvidence"]["satWithin40mFraction"]=.80
        with self.assertRaises(ValueError):self.check(x)

    def test_duplicate_sat_code_cannot_become_second_canonical_page(self):
        x=list(data());x[0]["records"].append(deepcopy(x[0]["records"][0]))
        with self.assertRaises(ValueError):self.check(x)

    def test_missing_legacy_route_is_held_not_auto_created(self):
        x=list(data());x[5]["lookup"].clear()
        with self.assertRaises(ValueError):self.check(x)

    def test_original_snapshot_checksums_are_mandatory(self):
        x=list(data())
        with self.assertRaisesRegex(ValueError,"SAT source fingerprint"):
            self.check((x[0],b"corrupt",*x[2:]))
        x=list(data());x[3]["elements"][0]["tags"]["ref"]="wrong"
        with self.assertRaisesRegex(ValueError,"OSM source fingerprint"):self.check(x)

    def test_candidate_competitor_disqualifies_ambiguous_source(self):
        x=list(data());x[4]["candidates"].append(deepcopy(x[4]["candidates"][0]))
        with self.assertRaises(ValueError):self.check(x)

    def test_determinism(self):
        x=data();self.assertEqual(self.check(x),self.check(deepcopy(x)))


if __name__=="__main__":
    unittest.main()
