"""Fail closed until every observed unmapped, non-private CAI key has a plan."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CAIUnmappedReviewPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = json.loads((ROOT / "scripts" / "cai_pilot_field_inventory_v1.json").read_text())
        cls.plan = json.loads((ROOT / "scripts" / "cai_unmapped_fields_review_plan_v1.json").read_text())
        cls.rules = json.loads((ROOT / "scripts" / "cai_refuge_field_map_v1.json").read_text())

    def test_every_unmapped_nonprivate_field_has_one_explicit_plan(self):
        expected = {x["name"] for x in self.inv["fieldNames"]
                    if x["state"] == "field_level_review_needed"}
        planned = [p["sourceField"] for p in self.plan["proposals"]]
        self.assertEqual(len(expected), 50)
        self.assertEqual(len(planned), 50)
        self.assertEqual(len(set(planned)), 50)
        self.assertEqual(set(planned), expected)

    def test_proposals_never_become_published_or_preapproved(self):
        for row in self.plan["proposals"]:
            self.assertEqual(row["status"], "PROPOSAL_ONLY_NEEDS_SOURCE_VALUE_AND_BIBBIA_REVIEW")
            self.assertEqual(row["publicationStatus"], "RIGHTS_BLOCKED")
            self.assertTrue(row["verifyOnDetail"])
            self.assertTrue(row["suggestedField"])
            self.assertTrue(row["normalization"])
            self.assertTrue(row["reviewNote"])

    def test_safety_sensitive_concepts_are_not_asserted(self):
        plan = {x["sourceField"]: x for x in self.plan["proposals"]}
        self.assertEqual(plan["water_type_certification"]["normalization"],
                         "categorical_original")
        self.assertEqual(plan["fireRegulation_certification"]["normalization"],
                         "hold_for_technical_verification")
        self.assertEqual(plan["type"]["normalization"], "categorical_original")
        self.assertEqual(plan["status"]["normalization"], "categorical_original")
        self.assertIn("non significa aperto oggi",
                      plan["status"]["reviewNote"].casefold())

    def test_private_or_internal_fields_not_in_public_proposals(self):
        forbidden = {x["name"] for x in self.inv["fieldNames"] if x["state"]
                     in ("privacy_restricted", "internal_reference")}
        proposals = {x["sourceField"] for x in self.plan["proposals"]}
        self.assertFalse(forbidden & proposals)

    def test_staging_allowlist_remains_separate(self):
        mapped = {x["sourceField"] for x in self.rules["fields"]}
        planned = {x["sourceField"] for x in self.plan["proposals"]}
        self.assertFalse(mapped & planned)


if __name__ == "__main__":
    unittest.main()
