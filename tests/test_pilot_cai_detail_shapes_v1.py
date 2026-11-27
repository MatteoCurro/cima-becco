"""Offline proof that CAI detail shape probes do NOT export field values."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
p = ROOT / "scripts" / "pilot_cai_detail_shapes_v1.py"
spec = importlib.util.spec_from_file_location("cai_shape_probe", p)
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)


class ShapeProbeTests(unittest.TestCase):
    def test_values_and_media_urls_never_leave_the_prober(self):
        payload = {"id_cai": 921800106, "title": "DO NOT EXPORT NAME",
                   "media": [{"url": "PRIVATE_URL_DO_NOT_EXPORT"}],
                   "fields": [
                       {"name": "email_management_property", "value": "private@example.org",
                        "data": {"pii": "PRIVATE_NAME"}, "updated_at": "2026-11-27"},
                       {"name": "posti_totali_service", "value": 42, "data": {"x": 123}},
                       {"name": "wifi_service", "value": False},
                       {"name": "openingTime_contact", "value": None,
                        "data": [{"start_date": "PRIVATE_DAY", "end_date": "PRIVATE_DAY_2"}]},
                   ]}
        result = probe.summarize_detail(payload)
        self.assertEqual(result["caiId"], "921800106")
        self.assertEqual(result["mediaCount"], 1)
        self.assertEqual(result["fieldEntries"], 4)
        blob = json.dumps(result)
        for sensitive in ("private@example.org", "PRIVATE_NAME",
                          "PRIVATE_URL_DO_NOT_EXPORT", "DO NOT EXPORT NAME"):
            self.assertNotIn(sensitive, blob)
        byname = {x["name"]: x for x in result["fields"]}
        self.assertEqual(byname["posti_totali_service"]["hasValue"], 1)
        self.assertEqual(byname["posti_totali_service"]["valueTypes"], {"number": 1})
        self.assertEqual(byname["wifi_service"]["valueTypes"], {"bool": 1})
        self.assertEqual(byname["openingTime_contact"]["hasValue"], 0)
        self.assertEqual(result["openingTimeArrayElementTypes"], {"object": 1})
        self.assertEqual(result["openingTimeArrayFieldKeys"],
                         ["end_date", "start_date"])
        self.assertNotIn("PRIVATE_DAY", blob)
        self.assertFalse(result["rightsCleared"])
        self.assertFalse(result["publishedToAtlas"])

    def test_unsupported_record_shape_fails_without_output(self):
        with self.assertRaisesRegex(ValueError, "fields"):
            probe.summarize_detail({"id_cai": 921800106, "data": None})
        with self.assertRaisesRegex(ValueError, "id_cai"):
            probe.summarize_detail({"id_cai": "bad", "fields": []})

    def test_updated_at_structure_summary_never_contains_ids_or_dates(self):
        sample = [{"id_cai": 123456789, "updated_at": "SECRET_TIMESTAMP",
                   "contact": "secret@example.org"}]
        result = probe.summarize_updated_at(sample)
        self.assertEqual(result["responseType"], "array")
        self.assertEqual(result["items"], 1)
        self.assertEqual(result["firstItemKeys"],
                         ["contact", "id_cai", "updated_at"])
        blob = json.dumps(result)
        self.assertNotIn("123456789", blob)
        self.assertNotIn("SECRET_TIMESTAMP", blob)
        self.assertNotIn("secret@example.org", blob)
        obj = probe.summarize_updated_at({"data": sample, "total": 1})
        self.assertEqual(obj["responseType"], "object")
        self.assertEqual(obj["dataItems"], 1)

    def test_audit_disallows_arbitrary_remote_ids(self):
        with self.assertRaisesRegex(ValueError, "non autorizzato"):
            probe.fetch_detail("123456789")


if __name__ == "__main__":
    unittest.main()
