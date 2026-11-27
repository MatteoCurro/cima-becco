"""CAI delta checkpoint correctness without any provider calls or publishing."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "scripts" / "plan_cai_refuge_delta_v1.py"
spec = importlib.util.spec_from_file_location("cai_delta", p)
delta = importlib.util.module_from_spec(spec)
spec.loader.exec_module(delta)


class CAIDeltaTests(unittest.TestCase):
    def test_strict_timestamps_with_timezone(self):
        self.assertEqual(delta.parse_time("2026-11-27T17:00:00+00:00"),
                         delta.parse_time("2026-11-27T18:00:00+01:00"))
        for value in ("2026-11-27", "2026-11-27T10:00:00", "yesterday", None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                delta.parse_time(value)

    def test_updates_not_always_fetch_all(self):
        p = {"1": "2026-11-26T10:00:00Z", "2": "2026-11-27T10:00:00Z"}
        c = {"1": "2026-11-26T10:00:00Z",
             "2": "2026-11-27T12:00:00Z",
             "3": "2026-11-27T13:00:00Z"}
        r = delta.plan_delta(p, c)
        self.assertEqual(r["summary"]["new"], 1)
        self.assertEqual(r["summary"]["updated"], 1)
        self.assertEqual(r["summary"]["unchanged"], 1)
        self.assertEqual(r["newProviderInternalIds"], ["3"])
        self.assertEqual(r["changedProviderInternalIds"], ["2"])
        self.assertEqual(r["missingIdCaiMappings"], ["2", "3"])
        self.assertFalse(r["summary"]["readyToFetchDetails"])
        self.assertFalse(r["summary"]["readyForPublication"])

    def test_complete_registry_allows_detail_planning_not_publication(self):
        p = {"1": "2026-11-26T10:00:00Z"}
        c = {"1": "2026-11-27T10:00:00Z"}
        r = delta.plan_delta(p, c, known_cai_ids={"1": "921800106"})
        self.assertTrue(r["summary"]["readyToFetchDetails"])
        self.assertEqual(r["caiIdentityCandidates"]["1"], "921800106")
        self.assertEqual(r["summary"]["readyForPublication"], False)
        self.assertEqual(r["deleteOperations"], 0)
        self.assertFalse(r["licenceApproved"])

    def test_missing_keys_are_never_deleted_even_full_snapshot(self):
        p = {"1": "2026-11-27T10:00:00Z", "2": "2026-11-27T10:00:00Z"}
        c = {"1": "2026-11-27T10:00:00Z"}
        r = delta.plan_delta(p, c, complete_snapshot=True)
        self.assertEqual(r["absentSincePreviousProviderIds"], ["2"])
        self.assertEqual(r["deleteOperations"], 0)
        self.assertEqual(r["summary"]["absentTombstonesVerified"], 0)
        self.assertFalse(r["summary"]["readyToFetchDetails"])

    def test_older_update_is_reviewed_not_overwritten(self):
        p = {"1": "2026-11-27T10:00:00Z"}
        c = {"1": "2026-11-26T10:00:00Z"}
        r = delta.plan_delta(p, c, known_cai_ids={"1": "921800106"})
        self.assertEqual(r["regressedTimestampIds"], ["1"])
        self.assertFalse(r["summary"]["readyToFetchDetails"])

    def test_bad_input_never_changes_baseline(self):
        bad = [{"1": "2026-11-27T00:00:00Z"}, {}, {"fake": "2026-11-27T00:00:00Z"},
               {"1": None}, {"0": "2026-11-27T00:00:00Z"}]
        for row in bad:
            with self.subTest(row=row), self.assertRaises(ValueError):
                delta.validate_revision_map(row)

    def test_sorting_and_consistency_are_deterministic(self):
        prior = {"10": "2026-11-26T10:00:00Z", "2": "2026-11-26T10:00:00Z"}
        cur = {"2": "2026-11-27T10:00:00Z", "10": "2026-11-27T10:00:00Z"}
        a = delta.plan_delta(prior, cur, known_cai_ids={"2": 2, "10": 10})
        b = delta.plan_delta(dict(reversed(list(prior.items()))),
                             dict(reversed(list(cur.items()))),
                             known_cai_ids={"10": 10, "2": 2})
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))
        self.assertEqual(a["changedProviderInternalIds"], ["2", "10"])

    def test_first_bootstrap_does_not_trigger_publication(self):
        r = delta.plan_delta(None, {"7": "2026-11-27T00:00:00+01:00"})
        self.assertEqual(r["newProviderInternalIds"], ["7"])
        self.assertFalse(r["publishingEnabled"])


if __name__ == "__main__":
    unittest.main()
