"""Test della quota DEM senza chiamate di rete né dipendenza da Pillow."""
from pathlib import Path
import importlib.util
import unittest

path=Path(__file__).resolve().parents[1]/'scripts'/'enrich_alpine_elevation.py'
spec=importlib.util.spec_from_file_location('place_altitude',path)
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class AlpineElevationTests(unittest.TestCase):
    def test_estimates_only_missing_osm_elevation(self):
        places=[{'slug':'r','lng':12,'lat':46,'elevationM':2010},
                {'slug':'t','lng':12.1,'lat':46.1},
                {'slug':'u','lng':12.2,'lat':46.2}]
        calls=[]
        def fake(lng,lat):
            calls.append([lng,lat])
            return 1110.4
        result=module.patch_elevation(places,fake,limit=1)
        self.assertEqual(result['filled'],1)
        self.assertEqual(result['attempted'],1)
        self.assertEqual(places[0]['elevationM'],2010)
        self.assertEqual(places[1]['elevationM'],1110)
        self.assertEqual(places[1]['elevationSource'],'dem')
        self.assertNotIn('elevationM',places[2])
        self.assertEqual(len(calls),1)

    def test_rejects_implausible_elevation(self):
        places=[{'slug':'x','lng':12,'lat':46}]
        result=module.patch_elevation(places,lambda lng,lat:-900,limit=1)
        self.assertEqual(result['filled'],0)
        self.assertEqual(result['errors'],1)
        self.assertNotIn('elevationM',places[0])

if __name__=='__main__':unittest.main()
