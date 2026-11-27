"""Test della procedura foto senza accesso alla rete Wikimedia."""
import importlib.util
from pathlib import Path
import unittest

SCRIPT=Path(__file__).resolve().parent.parent/'scripts'/'enrich_route_photos.py'
spec=importlib.util.spec_from_file_location('routephotos',SCRIPT)
photos=importlib.util.module_from_spec(spec)
spec.loader.exec_module(photos)


class PhotoTest(unittest.TestCase):
    def setUp(self):
        self.route={'name':'Via Ferrata Hans Kammerlander',
                    'coordinates':[[11.75,46.5,1100],[11.751,46.501,1120]]}
        self.page={'title':'File:Ferrata Hans Kammerlander Dolomiti.jpg',
                   'coordinates':[{'lat':46.5003,'lon':11.7503}],
                   'imageinfo':[{'width':2000,
                     'thumburl':'https://upload.wikimedia.org/wikipedia/commons/thumb/a/b/test.jpg',
                     'descriptionurl':'https://commons.wikimedia.org/wiki/File:Ferrata_Hans_Kammerlander_Dolomiti.jpg',
                     'extmetadata':{'LicenseShortName':{'value':'CC BY-SA 4.0'},
                                    'Artist':{'value':'<b>Autore</b>'}}}]}

    def test_distinctive_name(self):
        self.assertTrue(photos.matches_name('Via Ferrata Hans Kammerlander','File:Ferrata_Hans_Kammerlander.jpg'))
        self.assertFalse(photos.matches_name('Sentiero 479','File:Trullo_03.jpg'))
        self.assertFalse(photos.matches_name('Monte Bianco di Courmayeur','File:Trullo_03.jpg'))

    def test_valid_geo_and_license(self):
        photo=photos.photo_from_page(self.route,self.page)
        self.assertIsNotNone(photo)
        self.assertEqual(photo['author'],'Autore')
        self.assertEqual(photo['license'],'CC BY-SA 4.0')

    def test_reject_wrong_coordinates(self):
        self.page['coordinates']=[{'lat':40.8,'lon':17.1}]
        self.assertIsNone(photos.photo_from_page(self.route,self.page))

    def test_reject_unlicensed(self):
        self.page['imageinfo'][0]['extmetadata']['LicenseShortName']['value']='All rights reserved'
        self.assertIsNone(photos.photo_from_page(self.route,self.page))

    def test_missing_geotag_is_not_a_valid_match(self):
        del self.page['coordinates']
        self.assertIsNone(photos.photo_from_page(self.route,self.page))


if __name__=='__main__':
    unittest.main()
