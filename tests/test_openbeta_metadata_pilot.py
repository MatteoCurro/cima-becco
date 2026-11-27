import unittest
from scripts.pilot_openbeta_metadata import normalize

class OpenBetaMappingTest(unittest.TestCase):
    def test_bolts_not_equivalent_to_quickdraws(self):
        sample = [{
            "uuid": "a", "area_name": "Parete prova", "pathTokens": ["Italy", "Trentino"],
            "metadata": {"lat": 45.9, "lng": 10.9},
            "climbs": [{
                "uuid": "r", "name": "Prova OpenBeta", "fa": "Mario Rossi, 2001",
                "length": 21, "boltsCount": 8,
                "grades": {"french": "6a+", "yds": None, "vscale": None},
                "type": {"sport": True, "trad": False, "bouldering": False},
                "content": {"description": "Via di prova"},
                "safety": None, "pathTokens": ["Italy", "Trentino", "Area"]
            }]
        }]
        rows = normalize(sample)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["metadata"]["boltsCount"], 8)
        self.assertEqual(rows[0]["metadata"]["grades"]["french"], "6a+")
        self.assertIsNone(rows[0]["metadata"]["quickdrawsRecommended"])
        self.assertIsNone(rows[0]["metadata"]["pitchesCount"])
        self.assertEqual(rows[0]["metadata"]["pitchDetails"], [])
        self.assertEqual(rows[0]["source"]["licence"], "CC0")
        self.assertEqual(rows[0]["kind"], "climbing_route")

    def test_missing_bolts_not_zero(self):
        data = [{"uuid":"a","area_name":"A","climbs":[{"uuid":"r","name":"X",
            "boltsCount":None,"length":None,"grades":{},"type":{}}]}]
        row=normalize(data)[0]
        self.assertIsNone(row["metadata"]["boltsCount"])
        self.assertIsNone(row["metadata"]["quickdrawsRecommended"])
        self.assertIsNone(row["metadata"]["lengthM"])

    def test_negative_length_and_boulder_classification(self):
        data = [{"uuid":"z","area_name":"Block","climbs":[{
          "uuid":"z1","name":"Blocchetto","length":-1,"boltsCount":None,
          "grades":{"vscale":"V5"},"type":{"bouldering":True}}]}]
        row=normalize(data)[0]
        self.assertEqual(row["kind"], "boulder_problem")
        self.assertIsNone(row["metadata"]["lengthM"])
        self.assertEqual(row["metadata"]["grades"]["vscale"], "V5")

if __name__ == "__main__":
    unittest.main()
