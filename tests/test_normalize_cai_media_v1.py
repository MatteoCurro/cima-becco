"""No unsourced CAI image should become a published hero/logo or leak URL."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
source=ROOT/"scripts"/"normalize_cai_media_v1.py"
spec=importlib.util.spec_from_file_location("cai_media", source)
media=importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)

UUID="5b8cd267-0e50-4204-b37b-3d912e7290a6"


class CAIMediaTests(unittest.TestCase):
    def sample(self):
        return {"id_cai": 921800106, "title": "Rifugio example",
                "media": [
                    {"uuid": UUID, "mime_type": "image/jpeg",
                     "original_url": "https://example.org/SECRET_ORIGINAL.jpg?token=secret",
                     "preview_url": "https://example.org/SECRET_PREVIEW.jpg",
                     "name": "PRIVATE_PERSON", "file_name": "private_photo.jpg",
                     "custom_properties": {"author": "PRIVATE_AUTHOR"}},
                    {"uuid": UUID, "mime_type": "image/png"},
                    {"uuid": "not_uuid", "mime_type": "image/jpeg"},
                    {"uuid": "70296ab9-88e5-40c8-bf55-a715ec978252",
                     "mime_type": "application/pdf"},
                ]}

    def test_collects_only_safe_candidates_no_media_urls_or_authors(self):
        result=media.convert_media(self.sample())
        self.assertEqual(result["summary"]["mediaRowsSeen"], 4)
        self.assertEqual(result["summary"]["candidateImages"], 1)
        self.assertEqual(result["summary"]["rejected"], 3)
        self.assertEqual(result["summary"]["downloaded"], 0)
        self.assertEqual(result["summary"]["licensedForPublication"], 0)
        self.assertEqual(result["summary"]["verifiedSubjects"], 0)
        candidate=result["candidates"][0]
        self.assertEqual(candidate["assetId"], "cai:media:"+UUID)
        self.assertEqual(candidate["sourceId"], "cai:shelter:921800106")
        self.assertEqual(candidate["publicationStatus"], "RIGHTS_BLOCKED")
        self.assertTrue(candidate["providedOriginalUrl"])
        self.assertFalse(candidate["mediaDownloaded"])
        self.assertFalse(candidate["embedPermission"])
        self.assertIsNone(candidate["author"])
        self.assertIsNone(candidate["licence"])
        self.assertIsNone(candidate["subjectId"])
        blob=json.dumps(result)
        for forbidden in ("SECRET_ORIGINAL", "SECRET_PREVIEW", "PRIVATE_PERSON",
                          "PRIVATE_AUTHOR", "private_photo.jpg", "token=secret"):
            self.assertNotIn(forbidden, blob)

    def test_identical_asset_uuid_does_not_get_duplicate_entities(self):
        result=media.convert_media(self.sample())
        self.assertEqual(result["rejected"][0]["reason"], "duplicate_asset_uuid")

    def test_absent_media_is_no_candidate_not_an_error(self):
        r=media.convert_media({"id_cai": 10})
        self.assertEqual(r["summary"]["mediaRowsSeen"], 0)
        self.assertEqual(r["candidates"], [])

    def test_malformed_media_and_subject_identity_rejected(self):
        for obj in ({"id_cai": None, "media": []}, {"id_cai": 10, "media": {}},
                    {"id_cai": False, "media": []}):
            with self.subTest(obj=obj), self.assertRaises(ValueError):
                media.convert_media(obj)

    def test_unsupported_webcam_video_not_implicitly_published(self):
        doc={"id_cai": 10, "media": [{"uuid": UUID, "mime_type": "video/mp4"}]}
        r=media.convert_media(doc)
        self.assertEqual(r["summary"]["candidateImages"], 0)
        self.assertEqual(r["rejected"][0]["reason"], "unsupported_media_type")


if __name__ == "__main__":
    unittest.main()
