"""Offline checks for block 2 bivouacs, cabins and support shelters."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import assemble_shelters_release_v1 as imp


def cai(kind="bivacco", original="Bivacco", name="FIAMME GIALLE", ident="922005301", lat=46.5, lng=11.6):
    url = "https://rifugi.cai.it/shelters/" + ident
    return {
        "kind": kind, "originalType": original, "caiId": ident,
        "sourceIds": {"cai": ident}, "name": name, "lat": lat, "lng": lng,
        "sourceUrl": url, "revision": "2026-11-27T10:00:00Z",
        "facts": {
            "bedsTotal": {"value": 9, "sourceId": "cai:shelter:"+ident,
                          "sourceUrl": url, "method": "reported"},
            "waterAvailableReported": {"value": False, "sourceId": "cai:shelter:"+ident,
                                       "sourceUrl": url, "method": "reported"},
        },
        "media": [{"id": "cai:media:test", "kind": "photo",
                   "url": "https://rifugi.cai.it/media/1.jpg", "sourceUrl": url,
                   "subjectVerified": True, "reuseAllowed": True,
                   "author": "CAI", "licence": "CAI reuse"}],
    }


def osm(kind="bivacco", name="Bivacco Fiamme Gialle", url="https://www.openstreetmap.org/node/14344305435"):
    return {"kind": kind, "name": name, "slug": "osm-n-14344305435",
            "lat": 46.5, "lng": 11.60001, "osmUrl": url,
            "elevationM": 2500, "capacity": 8}


def inputs(cai_rows, osms=(), quar=(), refuges=()):
    return (
        {"isCompleteSnapshot": True, "records": cai_rows, "contentSha256": "a"*64},
        {"places": list(osms), "generatedAt": "2026-11-27"},
        {"entities": list(refuges), "quarantinedOsmIds": list(quar)},
    )


class TestShelterRelease(unittest.TestCase):
    def test_type_specific_categories_and_facts(self):
        b = imp.cai_entity(cai())
        self.assertEqual((b["kind"], b["subtype"]), ("bivouac", "fixed_bivouac"))
        self.assertEqual(b["facts"]["bedsTotal"]["value"], 9)
        self.assertEqual(b["facts"]["waterAvailableReported"]["value"], False)
        self.assertFalse(b["safety"]["waterPotabilityConfirmed"])
        self.assertFalse(b["safety"]["openingConfirmed"])
        self.assertEqual(len(b["media"]), 1)
        self.assertEqual(imp.cai_entity(cai("other", "Capanna sociale"))["subtype"], "social_cabin")
        self.assertEqual(imp.cai_entity(cai("other", "Punto d'appoggio"))["subtype"], "support_point")
        self.assertIsNone(imp.cai_entity(cai("rifugio", "Rifugio custodito")))

    def test_unique_osm_link_preserves_slug(self):
        p = inputs([cai()], [osm()])
        cat, report, review = imp.build_release(*p, min_cai=1, min_osm=1)
        self.assertEqual(report["matchedCaiOsm"], 1)
        self.assertEqual(report["publicEntities"], 1)
        merged = cat["entities"][0]
        self.assertEqual(merged["slug"], "osm-n-14344305435")
        self.assertEqual(merged["sourceIds"]["cai"], "922005301")
        self.assertEqual(merged["facts"]["bedsTotal"]["value"], 9)
        self.assertEqual(merged["factsAlternatives"][0]["key"], "bedsTotal")

    def test_wrong_refuge_tag_requires_cai_confirmation(self):
        p = inputs([cai()], [osm(kind="rifugio")], ["node/14344305435"])
        cat, report, _ = imp.build_release(*p, min_cai=1, min_osm=0)
        self.assertEqual(report["reclassifiedOsmWrongKind"], 1)
        self.assertEqual(cat["reclassifiedOsmIds"], ["node/14344305435"])
        self.assertEqual(cat["entities"][0]["kind"], "bivouac")

    def test_near_name_mismatch_is_reviewed_not_duplicated(self):
        p = inputs([cai(name="ALTRO NOME")], [osm()])
        cat, report, rev = imp.build_release(*p, min_cai=1, min_osm=1)
        self.assertEqual(report["publicEntities"], 1)
        self.assertEqual(report["caiRecordsKeptForReview"], 1)
        self.assertEqual(len(rev["unresolvedOSM"]), 1)

    def test_distant_cai_only_and_osm_bivouac_coexist(self):
        p = inputs([cai(lat=44, lng=10)], [osm()])
        cat, report, _ = imp.build_release(*p, min_cai=1, min_osm=1)
        self.assertEqual(report["publicEntities"], 2)
        self.assertEqual(report["caiOnlyPublished"], 1)

    def test_two_cai_candidates_do_not_claim_single_osm(self):
        p = inputs([cai(), cai(ident="922005302")], [osm()])
        cat, report, rev = imp.build_release(*p, min_cai=1, min_osm=1)
        self.assertEqual(report["matchedCaiOsm"], 0)
        self.assertEqual(report["caiRecordsKeptForReview"], 2)
        self.assertEqual(len(rev["unresolvedOSM"]), 2)

    def test_cai_already_used_as_refuge_stops_release(self):
        p = inputs([cai()], refuges=[{"id": "refuge", "name": "FIAMME GIALLE",
            "sourceIds": {"cai": "922005301"}, "geo": {"point": {"lat": 46.5, "lng": 11.6}}}])
        with self.assertRaisesRegex(ValueError, "già classificati"):
            imp.build_release(*p, min_cai=1, min_osm=0)

    def test_determinism_and_partial_input_block(self):
        p = inputs([cai()], [osm()])
        one = imp.build_release(*p, min_cai=1, min_osm=1)
        two = imp.build_release(*p, min_cai=1, min_osm=1)
        self.assertEqual(imp.canonical_json(one[0]), imp.canonical_json(two[0]))
        p[0]["isCompleteSnapshot"] = False
        with self.assertRaisesRegex(ValueError, "parziale"):
            imp.build_release(*p, min_cai=1, min_osm=1)

    def test_unknown_type_is_not_promoted(self):
        p = inputs([cai(kind="other", original="Non classificato")], [osm()])
        with self.assertRaisesRegex(ValueError, "Regressione"):
            imp.build_release(*p, min_cai=1, min_osm=1)


if __name__ == "__main__":
    unittest.main()
