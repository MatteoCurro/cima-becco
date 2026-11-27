"""Coverage contract for 127 exact field *names* observed in the PR8 CAI pilot.

The fixture includes NO field values, no personal data, no media. Matching
the full observed name set prevents a silent loss of useful metadata.
"""
import json
from collections import Counter
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class CAIPilotFieldInventoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inv = json.loads((ROOT / "scripts" / "cai_pilot_field_inventory_v1.json").read_text())
        cls.rules = json.loads((ROOT / "scripts" / "cai_refuge_field_map_v1.json").read_text())
        cls.schema = json.loads((ROOT / "scripts" / "refuge_field_registry_v1.json").read_text())

    def test_all_127_observed_names_are_accounted_for(self):
        names = [x["name"] for x in self.inv["fieldNames"]]
        self.assertEqual(self.inv["totalDistinctFieldNames"], 127)
        self.assertEqual(len(names), 127)
        self.assertEqual(len(set(names)), 108)
        self.assertEqual(set(x["state"] for x in self.inv["fieldNames"]), {
            "mapped_for_restricted_staging", "field_level_review_needed",
            "internal_reference", "privacy_restricted"})

    def test_prior_mappings_are_exhaustively_linked(self):
        mapped = {r["sourceField"] for r in self.rules["fields"]}
        found = {x["name"] for x in self.inv["fieldNames"]
                 if x["state"] == "mapped_for_restricted_staging"}
        self.assertEqual(len(mapped), 47)
        self.assertEqual(mapped, found)
        self.assertEqual(Counter(x["state"] for x in self.inv["fieldNames"]), {
            "mapped_for_restricted_staging": 47,
            "field_level_review_needed": 50,
            "internal_reference": 8,
            "privacy_restricted": 22,
        })

    def test_private_fields_are_always_denied(self):
        blocked = set(self.rules["sensitiveExact"])
        prefixes = tuple(self.rules["sensitivePrefixes"])
        for field in self.inv["fieldNames"]:
            if field["state"] == "privacy_restricted":
                self.assertTrue(field["name"] in blocked or field["name"].startswith(prefixes))
        mapped = {r["sourceField"] for r in self.rules["fields"]}
        self.assertFalse(any(x["name"] in mapped for x in self.inv["fieldNames"]
                             if x["state"] == "privacy_restricted"))

    def test_cai_water_does_not_claim_drinking_water(self):
        mapped = {row["sourceField"]: row["target"] for row in self.rules["fields"]}
        self.assertEqual(mapped["acqua_in_rifugio_service"], "waterAvailableReported")
        self.assertNotEqual(mapped["acqua_in_rifugio_service"], "drinkingWater")
        self.assertEqual(mapped["camerate_superiore_4_posti_service"],
                         "largeDormitoriesAvailableReported")
        canon = {x["key"] for x in self.schema["fields"]}
        self.assertIn("drinkingWater", canon)
        self.assertIn("waterAvailableReported", canon)
        self.assertIn("largeDormitoriesAvailableReported", canon)

    def test_rights_are_not_inferred_from_field_exists(self):
        self.assertIn("No values", self.inv["scope"])
        self.assertTrue(all(set(x) == {"name", "state"}
                            for x in self.inv["fieldNames"]))
        for r in self.rules["fields"]:
            self.assertEqual(r["publicationStatus"],
                             "blocked_pending_rights_and_identity")

    def test_important_unmapped_requirements_remain_in_review(self):
        review = {x["name"] for x in self.inv["fieldNames"]
                  if x["state"] == "field_level_review_needed"}
        for field in ("type", "status", "category", "presidio_culturale_service",
                      "wc_in_camera_service", "fireRegulation_certification",
                      "instagram_contact", "facebook_contact"):
            self.assertIn(field, review)


if __name__ == "__main__":
    unittest.main()
