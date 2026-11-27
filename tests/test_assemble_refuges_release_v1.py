"""OSM/CAI release join rules: type, evidence, uniqueness, no false links."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("assemble_release",ROOT/"scripts"/"assemble_refuges_release_v1.py")
assembly=importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)


def osm(id="node/1", name="Rifugio Boé", lat=46.5, lng=11.5):
    return {"id":"cb-"+id.replace("/","-"),"kind":"refuge","name":name,
            "slug":"rifugio-boe","legacyUrl":"/rifugi/osm-n-1/",
            "geo":{"point":{"lat":lat,"lng":lng}},
            "sourceIds":{"osm":id},"sources":[{"id":"osm:node:1","url":"https://www.openstreetmap.org/node/1","licence":"ODbL-1.0"}],
            "quality":{"gate":"G0","seoIndexable":False},"facts":{"elevationM":{"value":2873,"sourceId":"osm:node:1","licence":"ODbL-1.0"}},
            "media":[],"relations":[],"webcams":[]}


def cai(id="123",kind="rifugio",name="BOE'",lat=46.5,lng=11.5):
    return {"caiId":id,"name":name,"kind":kind,"slug":"cai-"+id,
            "lat":lat,"lng":lng,"subtype":"custodito",
            "originalType":"Rifugio custodito" if kind=="rifugio" else "Bivacco",
            "revision":"2026-11-27T13:00:00Z",
            "description":"Storia documentata del rifugio",
            "sourceUrl":"https://rifugi.cai.it/shelters/"+id,
            "facts":{"bedsTotal":{"value":75,"sourceId":"cai:shelter:"+id,
                                   "sourceUrl":"https://rifugi.cai.it/shelters/"+id}},
            "media":[{"id":"cai:media:a","kind":"photo","url":"https://rifugi.cai.it/media/a.jpg",
                      "sourceUrl":"https://rifugi.cai.it/shelters/"+id,
                      "author":"Archivio CAI","licence":"Riuso autorizzato",
                      "subjectVerified":True,"reuseAllowed":True}],
            "webcams":[]}


def dataset(rows):
    return {"isCompleteSnapshot":True,"records":rows,"contentSha256":"abc"}


class AssemblyTests(unittest.TestCase):
    def test_exact_spatial_unique_matches_keep_permalink_and_enrich(self):
        base={"entities":[osm()],"sourceSnapshotSha256":"osmdigest","attribution":[],"routeProximityEdges":[]}
        data,stats,review=assembly.compile_release(base,dataset([cai()]),complete=False)
        self.assertEqual(stats["mergedOSMAndCAI"],1)
        self.assertEqual(stats["newCAIRefugePages"],0)
        self.assertEqual(stats["totalRefuges"],1)
        hut=data["entities"][0]
        self.assertEqual(hut["slug"],"rifugio-boe")
        self.assertEqual(hut["legacyUrl"],"/rifugi/osm-n-1/")
        self.assertEqual(hut["sourceIds"]["cai"],"123")
        self.assertEqual(hut["facts"]["bedsTotal"]["value"],75)
        self.assertEqual(len(hut["media"]),1)
        self.assertEqual(hut["quality"]["gate"],"G1")
        self.assertEqual(len(review["strongMatches"]),1)

    def test_cai_only_distant_hut_kept_as_new_entity(self):
        base={"entities":[osm()]}
        data,stats,review=assembly.compile_release(
            base,dataset([cai(id="456",name="Rifugio Fontana",lat=46.6,lng=11.6)]),
            complete=False)
        self.assertEqual(stats["newCAIRefugePages"],1)
        self.assertEqual(stats["mergedOSMAndCAI"],0)
        new=next(e for e in data["entities"] if e["sourceIds"].get("cai")=="456")
        self.assertEqual(new["slug"],"cai-456")
        self.assertFalse(new["quality"]["seoIndexable"])
        self.assertEqual(new["geo"]["point"]["lng"],11.6)

    def test_close_mismatch_not_auto_merged(self):
        base={"entities":[osm()]}
        candidate=cai(id="456",name="Rifugio Boé Est",lat=46.50008,lng=11.5)
        data,stats,review=assembly.compile_release(base,dataset([candidate]),complete=False)
        self.assertEqual(stats["mergedOSMAndCAI"],0)
        self.assertEqual(stats["suppressedForReview"],1)
        self.assertEqual(stats["totalRefuges"],1)
        self.assertEqual(len(review["unresolvedMatches"]),1)

    def test_bivouac_not_exported_as_refuge(self):
        base={"entities":[osm()]}
        data,stats,review=assembly.compile_release(base,dataset([cai(kind="bivacco")]),complete=False)
        self.assertEqual(stats["caiBivouacsHeldForBlock2"],1)
        self.assertEqual(stats["totalRefuges"],1)
        self.assertEqual(stats["newCAIRefugePages"],0)
        self.assertTrue(review["typeConflicts"])

    def test_multiple_cai_claim_same_osm_no_auto_merge(self):
        base={"entities":[osm()]}
        rows=[cai(id="1"),cai(id="2")]
        data,stats,review=assembly.compile_release(base,dataset(rows),complete=False)
        self.assertEqual(stats["mergedOSMAndCAI"],0)
        self.assertEqual(stats["suppressedForReview"],2)
        self.assertEqual(stats["totalRefuges"],1)

    def test_noncomplete_caiprofile_never_published_as_complete(self):
        with self.assertRaisesRegex(ValueError,"campione CAI incompleto"):
            assembly.compile_release({"entities":[osm()]},
                                     {"records":[cai()],"isCompleteSnapshot":False})

    def test_no_arbitrary_name_similarity_creates_false_merge(self):
        self.assertEqual(assembly.name_score("Rifugio Antermoia","Rifugio Boé"),0)
        self.assertFalse(assembly.candidate_matches(
            cai(id="123",name="Rifugio Antermoia"),[osm()]))

    def test_deterministic_release_artifact(self):
        base={"entities":[osm()]}
        one=assembly.compile_release(base,dataset([cai()]),complete=False)
        two=assembly.compile_release(base,dataset([cai()]),complete=False)
        self.assertEqual(json.dumps(one,sort_keys=True),json.dumps(two,sort_keys=True))


if __name__=="__main__":
    unittest.main()
