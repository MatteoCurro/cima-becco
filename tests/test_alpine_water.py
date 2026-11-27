"""Controlli offline per import punti acqua; non assimilare mai una sorgente a potabile."""
from pathlib import Path
import importlib.util
import sys
import unittest

scripts=Path(__file__).resolve().parents[1]/'scripts'
sys.path.insert(0,str(scripts))
spec=importlib.util.spec_from_file_location('water',scripts/'import_alpine_water.py')
water=importlib.util.module_from_spec(spec);spec.loader.exec_module(water)

class WaterTest(unittest.TestCase):
    def test_natural_spring_potability_unknown(self):
        raw={'type':'node','id':7,'lat':46.5,'lon':12.4,'tags':{'natural':'spring','name':'Fonte Vallata'}}
        data=water.to_water(raw)
        self.assertEqual(data['potable'],'unknown')
        self.assertEqual(data['kind'],'sorgente')

    def test_drinking_water_yes_and_no_override(self):
        raw={'type':'node','id':8,'lat':46.5,'lon':12.4,'tags':{'amenity':'drinking_water'}}
        self.assertEqual(water.to_water(raw)['potable'],'yes')
        raw['tags']['drinking_water']='no'
        self.assertEqual(water.to_water(raw)['potable'],'no')

    def test_route_near_water_but_not_too_far(self):
        route={'coordinates':[[12.4,46.5,0],[12.41,46.5,0],[12.42,46.5,0]]}
        base={'name':'F','kind':'sorgente','potable':'unknown','slug':'osm-n-1'}
        near=dict(base,lat=46.5003,lng=12.41)
        far=dict(base,slug='osm-n-2',lat=46.505,lng=12.41)
        result=water.route_water(route,[near,far])
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]['slug'],near['slug'])
        self.assertLess(result[0]['distanceM'],120)

if __name__=='__main__':unittest.main()
