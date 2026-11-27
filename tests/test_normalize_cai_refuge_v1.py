"""CAI mapper tests on synthetic detail fields with PR8-observed shape; no network."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
script = ROOT / "scripts" / "normalize_cai_refuge_v1.py"
spec = importlib.util.spec_from_file_location("normalize_cai_refuge", script)
norm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(norm)


class CAIRefugeMapperTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rules = json.loads((ROOT / "scripts" / "cai_refuge_field_map_v1.json").read_text())
        cls.registry = json.loads((ROOT / "scripts" / "refuge_field_registry_v1.json").read_text())

    def input(self):
        return {"id_cai": 930010001, "title": "CAPANNA PROVA", "fields": [
            {"name": "posti_totali_service", "value": "16", "updated_at": "2026-04-01T09:00:00Z"},
            {"name": "posti_letto_invernali_service", "value": "0", "updated_at": None},
            {"name": "wifi_service", "value": "no"},
            {"name": "pagamento_pos_service", "value": "sì"},
            {"name": "water_certification_certification", "value": "N/D"},
            {"name": "acqua_in_rifugio_service", "value": "yes"},
            {"name": "municipality_geo", "value": "Canazei"},
            {"name": "taxCode_management_property", "value": "PRIVATE_123"},
            {"name": "contract_fee_management_property", "value": "24000"},
            {"name": "unexpectedPrivateKey", "value": "SECRET_UNMAPPED"},
        ]}

    def test_allows_parsing_without_publishing(self):
        d = norm.convert_detail(self.input(), self.rules, self.registry)
        self.assertEqual(d["status"], "RESTRICTED_STAGING_ONLY")
        self.assertEqual(d["caiId"], "930010001")
        self.assertEqual(d["identityMatchStatus"], "unresolved")
        self.assertFalse(d["summary"]["licenceApproved"])
        self.assertFalse(d["summary"]["readyForPublication"])
        values = {e["sourceField"]: e for e in d["candidateFacts"]}
        self.assertEqual(values["posti_totali_service"]["value"], 16)
        self.assertEqual(values["posti_letto_invernali_service"]["value"], 0)
        self.assertIs(values["wifi_service"]["value"], False)
        self.assertIs(values["pagamento_pos_service"]["value"], True)
        self.assertIsNone(values["water_certification_certification"]["value"])
        self.assertIs(values["acqua_in_rifugio_service"]["value"], True)
        self.assertEqual(values["municipality_geo"]["value"]["resolutionStatus"], "unresolved")
        self.assertIsNone(values["municipality_geo"]["value"]["entityId"])
        self.assertEqual(values["posti_totali_service"]["sourceUpdatedAt"], "2026-04-01T09:00:00Z")
        for e in d["candidateFacts"]:
            self.assertEqual(e["publicationStatus"], "RIGHTS_BLOCKED")
            self.assertIsNone(e["licence"])
            self.assertIsNone(e["retrievedAt"])

    def test_unknown_values_are_not_leaked(self):
        d = norm.convert_detail(self.input(), self.rules, self.registry)
        blob = json.dumps(d)
        self.assertNotIn("PRIVATE_123", blob)
        self.assertNotIn("24000", blob)
        self.assertNotIn("SECRET_UNMAPPED", blob)
        self.assertEqual(d["unmappedFields"], {"unexpectedPrivateKey": 1})
        self.assertEqual(d["blockedSensitiveFields"].get("taxCode_management_property"), 1)
        self.assertEqual(d["blockedSensitiveFields"].get("contract_fee_management_property"), 1)

    def test_sentinel_values_and_unconfirmed_boolean(self):
        self.assertIsNone(norm.normalized(-1, "positive_int"))
        self.assertIsNone(norm.normalized("sconosciuto", "reported_bool"))
        self.assertEqual(norm.normalized("0", "nonnegative_int"), 0)
        self.assertFalse(norm.normalized(0, "reported_bool"))
        self.assertTrue(norm.normalized("yes", "reported_bool"))
        self.assertIsNone(norm.normalized("2,5", "positive_int"))
        self.assertIsNone(norm.normalized("javascript:alert(1)", "https_url"))
        self.assertIsNone(norm.normalized("http://example.org", "https_url"))

    def test_duplicate_alternatives_not_overwritten(self):
        d = self.input()
        d["fields"].append({"name": "posti_totali_service", "value": "18"})
        output = norm.convert_detail(d, self.rules, self.registry)
        rows = [x for x in output["candidateFacts"] if x["fieldKeyCandidate"] == "bedsTotal"]
        self.assertEqual([x["value"] for x in rows], [16, 18])

    def test_missing_full_fields_array_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "fields"):
            norm.convert_detail({"id_cai": 930010001}, self.rules, self.registry)
        with self.assertRaisesRegex(ValueError, "id_cai"):
            norm.convert_detail({"id_cai": None, "fields": []}, self.rules, self.registry)

    def test_all_registry_targets_are_explicit_and_not_silent(self):
        existing = {f["key"] for f in self.registry["fields"]}
        for rule in self.rules["fields"]:
            self.assertIn(rule["converter"], ("positive_int", "nonnegative_int", "year",
                "reported_bool", "water_reported_not_potability", "https_url", "email",
                "name_candidate_not_id", "text", "source_text_with_rights_review"))
            if rule["target"] in existing:
                self.assertEqual(rule["canonicalStatus"], "mapped_to_existing_registry")
            else:
                self.assertEqual(rule["canonicalStatus"], "extension_requires_bibbia_review")


if __name__ == "__main__":
    unittest.main()
