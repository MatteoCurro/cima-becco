"""Controlli offline per evitare foto dei luoghi sbagliati."""
import importlib.util
import unittest
from pathlib import Path

script = Path(__file__).resolve().parent.parent / "scripts" / "enrich_alpine_photos.py"
spec = importlib.util.spec_from_file_location("enrich_alpine_photos", script)
photos = importlib.util.module_from_spec(spec)
spec.loader.exec_module(photos)

class PhotoMatchingTest(unittest.TestCase):
    def test_double_distinct_place_name(self):
        self.assertTrue(photos.title_matches_place(
            "Bivacco Antonio Marchi e Renzo Granzotto",
            "Bivacco Marchi Granzotto (Dolomiti).jpg"))
        self.assertTrue(photos.title_matches_place(
            "Cortina d'Ampezzo", "Panorama Cortina Ampezzo settembre.jpg"))
    def test_does_not_select_generic_mountain(self):
        self.assertFalse(photos.title_matches_place(
            "Bivacco Antonio Marchi e Renzo Granzotto",
            "Dolomiti di Sesto al tramonto.jpg"))
    def test_reject_short_ambiguous_village_name(self):
        self.assertFalse(photos.title_matches_place("Sesto", "Sesto Dolomiti.jpg"))
    def test_accent_and_unicode_normalization(self):
        self.assertTrue(photos.title_matches_place(
            "San Candido", "Paesaggio San Candido.jpg"))


    def test_wikipedia_image_from_exact_page_and_no_coats_of_arms(self):
        from unittest.mock import patch
        with patch.object(photos, 'request', return_value={
            'query': {'pages': {'1': {'pageimage': 'Rifugio_Locatelli.jpg'}}}
        }):
            self.assertEqual(photos.wikipedia_page_image('it', 'Rifugio Locatelli'),
                             'Rifugio_Locatelli.jpg')
        with patch.object(photos, 'request', return_value={
            'query': {'pages': {'1': {'pageimage': 'Stemma_Canazei.png'}}}
        }):
            self.assertIsNone(photos.wikipedia_page_image('it', 'Canazei'))

if __name__ == "__main__":
    unittest.main()
