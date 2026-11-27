"""Test offline dell'atlante alpino e dei passaggi lungo le tracce GPX."""
from pathlib import Path
import importlib.util
import unittest

script=Path(__file__).resolve().parent.parent/'scripts'/'import_alpine_places.py'
spec=importlib.util.spec_from_file_location('alpine_places',script)
atlas=importlib.util.module_from_spec(spec)
spec.loader.exec_module(atlas)


class AlpinePlacesTest(unittest.TestCase):
    def test_osm_rifugio_and_its_source(self):
        raw={'type':'node','id':321,'lat':46.55,'lon':12.4,
             'tags':{'name':'Rifugio delle Prove','tourism':'alpine_hut','ele':'2004 m'}}
        item=atlas.parse_item(raw)
        self.assertEqual(item['kind'],'rifugio')
        self.assertEqual(item['elevationM'],2004)
        self.assertEqual(item['osmUrl'],'https://www.openstreetmap.org/node/321')

    def test_six_disjoint_import_cells_cover_the_pilot(self):
        cells=atlas.alpine_cells()
        self.assertEqual(len(cells),6)
        self.assertAlmostEqual(min(cell[0] for cell in cells),atlas.BBOX[0])
        self.assertAlmostEqual(min(cell[1] for cell in cells),atlas.BBOX[1])
        self.assertAlmostEqual(max(cell[2] for cell in cells),atlas.BBOX[2])
        self.assertAlmostEqual(max(cell[3] for cell in cells),atlas.BBOX[3])
        self.assertTrue(all(c[0]<c[2] and c[1]<c[3] for c in cells))

    def test_osm_metadata_from_official_tags(self):
        raw={'type':'node','id':321,'lat':46.55,'lon':12.4,
             'tags':{'name':'Rifugio delle Prove','tourism':'alpine_hut','ele':'2004 m',
                     'beds':'40','operator':'CAI','opening_hours':'Jun-Sep',
                     'phone':'+390000000','wikimedia_commons':'File:Example Hut.jpg',
                     'description:it':'Rifugio in quota'}}
        item=atlas.parse_item(raw)
        self.assertEqual(item['capacity'],40)
        self.assertEqual(item['commonsFile'],'Example Hut.jpg')
        self.assertEqual(item['operator'],'CAI')
        self.assertEqual(item['openingHours'],'Jun-Sep')

    def test_bad_osm_item_rejected(self):
        self.assertIsNone(atlas.parse_item({'type':'node','id':1,'lat':46.5,'lon':12.4,
                                              'tags':{'tourism':'alpine_hut'}}))
        self.assertIsNone(atlas.sanitize_url('javascript:alert(1)'))

    def test_near_route_and_outside_route(self):
        points=[[12.400,46.500,1000],[12.405,46.500,1100],
                [12.410,46.500,1200],[12.415,46.500,1000]]
        route={'coordinates':points,'loop':False}
        hut={'slug':'osm-n-321','name':'Rifugio A','kind':'rifugio','lng':12.410,'lat':46.5001}
        village={'slug':'osm-n-123','name':'Borgo B','kind':'borgo','lng':12.500,'lat':46.5}
        found=atlas.route_stops(route,[hut,village])
        self.assertEqual(len(found),1)
        self.assertEqual(found[0]['slug'],hut['slug'])
        self.assertIn(found[0]['relation'],('passaggio','arrivo'))

    def test_far_off_path_is_not_a_stop(self):
        route={'coordinates':[[12.4,46.5,0],[12.41,46.5,0]],'loop':False}
        hut={'slug':'osm-n-123','name':'Rifugio lontano','kind':'rifugio','lng':12.405,'lat':46.509}
        self.assertEqual(atlas.route_stops(route,[hut]),[])


if __name__=='__main__':
    unittest.main()
