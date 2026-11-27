"""Test offline altimetria Terrarium, senza chiamate a server esterni."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch
from PIL import Image

SCRIPT = Path(__file__).resolve().parent.parent / 'scripts' / 'enrich_elevation.py'
spec = importlib.util.spec_from_file_location('enrich_elevation', SCRIPT)
dem = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dem)


class ElevationTest(unittest.TestCase):
    def test_pixel_decode(self):
        # R=128, G=1, B=0 -> elevazione +1 m.
        fake = Image.new('RGB', (256, 256), (128, 1, 0))
        with patch.object(dem, 'load_tile', return_value=fake):
            self.assertAlmostEqual(dem.pixel(0, 0), 1)

    def test_samples_keep_endpoints(self):
        pts = [[11.55 + i * 0.0003, 46.55, 0] for i in range(1000)]
        selected = dem.samples(pts)
        self.assertEqual(selected[0], 0)
        self.assertEqual(selected[-1], 999)
        self.assertLessEqual(len(selected), 211)

    def test_gain_loss(self):
        self.assertEqual(dem.gain_loss([1000] * 8), (0, 0))
        gain, loss = dem.gain_loss([1000, 1010, 1020, 1030, 1020, 1010, 1000], smooth=1)
        self.assertGreater(gain, 20)
        self.assertGreater(loss, 20)

    def test_fill_elevation_and_keep_xy(self):
        coords = [[11.55 + i * 0.001, 46.55, 0] for i in range(12)]
        route = {'slug': 'osm-hiking-test', 'coordinates': [p[:] for p in coords],
                 'gainM': 0, 'lossM': 0, 'elevationAvailable': False}
        with patch.object(dem, 'elevation', side_effect=lambda lon, lat: 1200 + (lon-11.55)*1200):
            self.assertTrue(dem.enrich(route))
        self.assertTrue(route['elevationAvailable'])
        self.assertEqual(route['elevationSource'], 'terrain')
        self.assertTrue(all(a[:2] == b[:2] for a, b in zip(route['coordinates'], coords)))
        self.assertGreater(route['coordinates'][-1][2], route['coordinates'][0][2])
        self.assertFalse(dem.enrich(route))


if __name__ == '__main__':
    unittest.main()
