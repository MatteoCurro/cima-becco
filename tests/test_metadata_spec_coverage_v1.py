"""Nuovi controlli di tracciabilità: riutilizzano i piloti, non rieseguono scraping."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "scripts" / "audit_metadata_spec_v1.py"
SPEC = importlib.util.spec_from_file_location("metadata_audit", PATH)
module = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)


class MetadataCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = (ROOT / "docs" / "MODELLO_METADATI_E_LAYOUT.md").read_text(encoding="utf-8")
        cls.sources = json.loads((ROOT / "scripts" / "metadata_source_registry_v1.json").read_text())
        cls.refuge = json.loads((ROOT / "scripts" / "refuge_field_registry_v1.json").read_text())
        cls.result = module.compile_plan(cls.spec, cls.sources, cls.refuge)

    def test_every_section_from_common_contract_through_community_is_counted(self):
        counts = self.result["requirementsBySection"]
        self.assertEqual(set(map(int, counts)), set(range(1, 28)))
        self.assertEqual(self.result["sectionCount"], 27)
        self.assertGreater(self.result["canonicalRequirementRows"], 100)
        self.assertEqual(sum(counts.values()), self.result["canonicalRequirementRows"])

    def test_no_acquired_data_falsely_claimed(self):
        self.assertEqual(self.result["fieldsWithConfirmedAcquisitionByThisAudit"], 0)
        for row in self.result["requirements"]:
            self.assertEqual(row["acquisitionStatus"], "NOT_ASSERTED")
            self.assertEqual(row["verificationStatus"], "NOT_ASSERTED")
            self.assertEqual(row["publicationStatus"], "NOT_AUTHORIZED_BY_THIS_REPORT")
            self.assertEqual(row["canonicalFieldMappingStatus"], "needs_field_level_mapping")

    def test_provenance_and_special_entities_covered(self):
        req = self.result["requirements"]
        for num, word in [(6, "webcam"), (14, "falesia"), (18, "sosta"),
                          (23, "Fermata"), (24, "Neve"), (25, "Logo"),
                          (26, "alertId"), (27, "licenceConsent")]:
            lines = " ".join(r["literalRequirement"] for r in req if r["specSection"] == num).casefold()
            self.assertIn(word.casefold(), lines)

    def test_source_registry_traceability_reuses_pilot_and_fails_closed(self):
        by_id = {s["id"]: s for s in self.sources["sources"]}
        self.assertEqual(len(by_id), 26)
        self.assertEqual(by_id["cai_refuges"]["status"], "release_adapter_implemented")
        self.assertEqual(by_id["cai_refuges"]["licenseGate"], "user_confirmed_reuse")
        self.assertEqual(by_id["sat"]["status"], "tested_partial_live_failure")
        self.assertEqual(by_id["regional_meteo"]["status"], "portals_access_only")
        self.assertEqual(by_id["webcam_operator"]["licenseGate"], "permission_required")
        self.assertEqual(by_id["open_meteo"]["licenseGate"], "terms_by_usage")
        self.assertEqual(by_id["commons"]["licenseGate"], "per_asset")

    def test_field_registry_and_source_registry_are_connected_without_false_mappings(self):
        self.assertEqual(self.result["refugeRegistryFields"], 80)
        self.assertEqual(len({s["sectionId"] for s in self.sources["sections"]}), 26)
        for row in self.result["requirements"]:
            self.assertTrue(row["candidateSourcesForEntityKind"])
            self.assertTrue(row["normalizationHint"])
            self.assertTrue(row["specLine"] > 0)

    def test_missing_or_unmapped_sections_are_blocking(self):
        corrupted = self.spec.replace("## 25. Webcam e multimedia", "### Webcam e multimedia")
        with self.assertRaisesRegex(ValueError, "sezioni richieste"):
            module.compile_plan(corrupted, self.sources, self.refuge)
        edited = json.loads(json.dumps(self.sources))
        edited["sections"] = [e for e in edited["sections"] if e["sectionId"] != 25]
        with self.assertRaisesRegex(ValueError, "non copre esattamente"):
            module.compile_plan(self.spec, edited, self.refuge)

    def test_unknown_provider_is_blocking(self):
        altered = json.loads(json.dumps(self.refuge))
        altered["fields"][0]["sources"] = ["unlisted_mock_provider"]
        with self.assertRaisesRegex(ValueError, "provider sconosciuto"):
            module.compile_plan(self.spec, self.sources, altered)

    def test_audit_is_deterministic(self):
        again = module.compile_plan(self.spec, self.sources, self.refuge)
        digest = lambda value: hashlib.sha256(
            json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()
        self.assertEqual(digest(again), digest(self.result))


if __name__ == "__main__":
    unittest.main()
