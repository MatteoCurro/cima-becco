"""Public refuge release gates: no CAI/media leaks, G0 noindex, quarantine."""
from __future__ import annotations
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("refuge_release", ROOT / "scripts" / "publish_refuges_v1.py")
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)


def entity(osm="node/1", identity="cb-97206826-2947-5b36-887d-005a0d263b26",
           slug="rifugio-esempio"):
    kind, number = osm.split("/")
    origin = f"osm:{kind}:{number}"
    url = f"https://www.openstreetmap.org/{osm}"
    return {
        "id": identity, "kind": "refuge", "name": "Rifugio di prova",
        "subtype": "alpine_hut", "slug": slug, "slugAliases": ["osm-n-" + number],
        "legacyUrl": "/rifugi/osm-n-" + number + "/",
        "geo": {"point": {"lat": 46.51, "lon": 11.82, "method": "osm_node"}},
        "sourceIds": {"osm": osm, "wikidata": "Q123"},
        "facts": {"elevationM": {"value": 2201, "unit": "m", "method": "reported",
                                "licence": "ODbL-1.0", "sourceId": origin, "sourceUrl": url}},
        "relations": [
            {"type": "near", "method": "haversine", "straightLineKm": 1.5,
             "targetRef": {"kind": "locality", "name": "Paese",
                           "legacySlug": "osm-n-99", "sourceIds": {"osm": "osm:node:99"}}},
            {"type": "near", "method": "haversine", "straightLineKm": 3.0,
             "targetRef": {"kind": "mountain", "name": "Cima",
                           "sourceIds": {"geonames": "330"}}},
        ],
        "media": [{"url": "https://unlicensed.example/secret.jpg",
                   "licence": None}],
        "mediaCandidates": [{"url": "https://unlicensed.example/other.jpg"}],
        "quality": {"gate": "G0", "seoIndexable": False},
        "editorialStatus": "raw",
        "webcams": [{"stillUrlCandidate": "https://example.org/notallowed"}],
    }


def baseline(tmp, entities):
    folder = Path(tmp) / "stage"
    folder.mkdir(parents=True)
    (folder / "refuges.json").write_text(json.dumps({
        "schemaVersion": "1.0", "status": "staging_only", "sourceSnapshotSha256": "a"*64,
        "entities": entities,
    }))
    (folder / "report.json").write_text(json.dumps({
        "status": "staging_only", "snapshotSha256": "a"*64,
        "refuges": len(entities), "sourceDatasetDate": "2026-11-27",
    }))
    (folder / "review.json").write_text(json.dumps({
        "candidateDuplicates": [], "slugConflicts": [],
    }))
    (folder / "links.json").write_text(json.dumps({
        "edges": [{"type": "passes_near", "from": {"kind": "itinerary", "legacySlug": "r-1"},
                   "to": {"id": entities[0]["id"], "kind": "refuge"},
                   "distanceToPolylineM": 80, "method": "legacy_route_stops_polyline_projection",
                   "verifiedAccess": False}],
    }))
    return folder


class RefugeReleaseTests(unittest.TestCase):
    def test_public_catalogue_is_odbl_and_g0_not_seo(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = baseline(tmp, [entity()])
            result, summary = release.build_public(stage, {"sourceKeys": []}, min_count=1)
            self.assertEqual(summary["publicRecords"], 1)
            self.assertEqual(summary["quarantinedRecords"], 0)
            self.assertEqual(summary["publicRouteEdges"], 1)
            self.assertEqual(summary["publicCAIFields"], 0)
            self.assertEqual(summary["publicPhotoCount"], 0)
            self.assertEqual(summary["seoIndexable"], 0)
            item = result["entities"][0]
            self.assertFalse(item["quality"]["seoIndexable"])
            self.assertEqual(item["quality"]["gate"], "G0")
            self.assertEqual(item["sourceIds"], {"osm": "node/1"})
            self.assertEqual(item["geo"]["point"], {"lat": 46.51, "lng": 11.82})
            self.assertEqual(item["facts"]["elevationM"]["licence"], "ODbL-1.0")
            self.assertIn("OpenStreetMap contributors", result["attribution"][0]["source"])
            self.assertEqual(result["attribution"][1]["licence"], "CC-BY-4.0")
            self.assertEqual(item["relations"][0]["target"]["href"], "/borghi/osm-n-99/")
            self.assertEqual(item["relations"][1]["target"]["id"], "geonames:330")

    def test_unlicensed_photos_webcams_and_wikidata_not_exposed(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = baseline(tmp, [entity()])
            result, _ = release.build_public(stage, {"sourceKeys": []}, min_count=1)
            blob = json.dumps(result)
            for forbidden in ("unlicensed.example", "notallowed", "mediaCandidates",
                              '"wikidata": "Q123"', "stillUrlCandidate", "identity-registry"):
                self.assertNotIn(forbidden, blob)
            self.assertEqual(result["entities"][0]["media"], [])
            self.assertEqual(result["entities"][0]["webcams"], [])

    def test_source_type_quarantine_never_auto_reclassifies(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = entity()
            two = entity(osm="node/2", identity="cb-20558968-09d2-5fbd-9e81-ec7adac094c2",
                         slug="fiamme-gialle")
            stage = baseline(tmp, [one, two])
            q = {"sourceKeys": [
                {"sourceKey": "osm:node:2", "reason": "official_type_conflict_bivouac_not_refuge",
                 "evidenceUrl": "https://rifugi.cai.it/shelters/922005301"}]}
            result, summary = release.build_public(stage, q, min_count=1)
            self.assertEqual(summary["quarantinedRecords"], 1)
            self.assertEqual(summary["publicRecords"], 1)
            self.assertEqual(summary["quarantine"][0]["sourceKey"], "osm:node:2")
            self.assertNotIn("fiamme-gialle", json.dumps(result))
            self.assertEqual(summary["publicRouteEdges"], 1)

    def test_duplicate_pair_quarantines_both_sides(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = entity()
            b = entity(osm="way/2", identity="cb-20558968-09d2-5fbd-9e81-ec7adac094c2",
                       slug="rifugio-esempio-2")
            c = entity(osm="node/3", identity="cb-c4c9c82f-2f3d-5a79-a633-e9ad6f9ad17c",
                       slug="terzo-rifugio")
            stage = baseline(tmp, [a, b, c])
            review = {
                "candidateDuplicates": [
                    {"left": {"sourceKey": "osm:node:1"}, "right": {"sourceKey": "osm:way:2"},
                     "status": "manual_review_required", "autoMerged": False}],
            }
            (stage / "review.json").write_text(json.dumps(review))
            release_data, report = release.build_public(stage, {"sourceKeys": []}, min_count=1)
            self.assertEqual(report["publicRecords"], 1)
            self.assertEqual(report["quarantinedRecords"], 2)
            self.assertEqual(release_data["entities"][0]["slug"], "terzo-rifugio")
            self.assertEqual(report["publicRouteEdges"], 0)

    def test_reject_invalid_provenance_or_claimed_seo(self):
        with tempfile.TemporaryDirectory() as tmp:
            one = entity()
            one["facts"]["elevationM"]["licence"] = "UNKNOWN"
            stage = baseline(tmp, [one])
            with self.assertRaisesRegex(ValueError, "licenza"):
                release.build_public(stage, {"sourceKeys": []}, min_count=1)
            one["facts"]["elevationM"]["licence"] = "ODbL-1.0"
            one["quality"]["seoIndexable"] = True
            (stage / "refuges.json").write_text(json.dumps({
                "status": "staging_only", "sourceSnapshotSha256": "a"*64, "entities": [one]}))
            with self.assertRaisesRegex(ValueError, "indicizzata"):
                release.build_public(stage, {"sourceKeys": []}, min_count=1)

    def test_abort_empty_or_changed_baseline(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = baseline(tmp, [entity()])
            with self.assertRaisesRegex(ValueError, "meno record"):
                release.build_public(stage, {"sourceKeys": []}, min_count=400)
            report = json.loads((stage / "report.json").read_text())
            report["snapshotSha256"] = "b"*64
            (stage / "report.json").write_text(json.dumps(report))
            with self.assertRaisesRegex(ValueError, "Digest"):
                release.build_public(stage, {"sourceKeys": []}, min_count=1)

    def test_output_is_idempotent_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = baseline(tmp, [entity()])
            first, stats = release.build_public(stage, {"sourceKeys": []}, min_count=1)
            again, stats2 = release.build_public(stage, {"sourceKeys": []}, min_count=1)
            self.assertEqual(release.canonical_json(first), release.canonical_json(again))
            self.assertEqual(stats, stats2)
            self.assertEqual(stats["catalogueSha256"],
                             __import__("hashlib").sha256(release.canonical_json(first)).hexdigest())

    def test_unknown_quarantine_source_does_not_invent_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            stage = baseline(tmp, [entity()])
            record, report = release.build_public(stage, {"sourceKeys": [
                {"sourceKey": "osm:node:90", "reason": "awaiting_review",
                 "evidenceUrl": "https://www.openstreetmap.org/node/90"}]}, min_count=1)
            self.assertEqual(report["quarantinedRecords"], 0)
            self.assertEqual(len(record["entities"]), 1)


if __name__ == "__main__":
    unittest.main()
