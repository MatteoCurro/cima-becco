import unittest
from scripts.pilot_climbing_metadata import normalize, category, build, slug, number, query_for

class ClimbingImportTests(unittest.TestCase):
    def test_route_does_not_infer_quickdraws(self):
        data = {"type":"node","id":1234,"lat":45.925,"lon":10.885,
            "tags":{"climbing":"route_bottom","name":"Via dei Test",
              "climbing:grade:french":"6b+","climbing:bolts":"9",
              "climbing:pitches":"2","climbing:length":"27"}}
        row = normalize(data)
        self.assertEqual(row["kind"], "climbing_route")
        self.assertEqual(row["metadata"]["boltsCount"], 9)
        self.assertEqual(row["metadata"]["pitchesCount"], 2)
        self.assertEqual(row["metadata"]["grades"]["french"], "6b+")
        self.assertIsNone(row["metadata"]["quickdrawsRecommended"])
        self.assertEqual(row["metadata"]["pitchDetails"], [])
        self.assertEqual(row["proposedSlug"], "via-dei-test")
        self.assertNotIn("geometry", row)

    def test_boolean_bolts_not_count(self):
        row = normalize({"type":"way","id":12,"center":{"lat":45.9,"lon":10.8},
            "tags":{"climbing":"route","climbing:bolts":"yes","name":"Prova"}})
        self.assertNotIn("boltsCount", row["metadata"])
        self.assertEqual(row["metadata"]["fixedProtectionReported"], "yes")
        self.assertIsNone(row["metadata"]["quickdrawsRecommended"])

    def test_gym_and_crag(self):
        self.assertEqual(category({"leisure":"sports_centre","sport":"climbing"}), "climbing_gym")
        self.assertEqual(category({"sport":"climbing","climbing":"crag"}), "crag")
        self.assertEqual(category({"sport":"climbing","climbing":"boulder"}), "boulder")

    def test_report_is_metadata_only(self):
        source = {"elements":[
          {"type":"node","id":1,"lat":45.92,"lon":10.88,
           "tags":{"name":"Parete Uno","climbing":"crag","climbing:orientation":"S"}},
          {"type":"node","id":2,"lat":45.921,"lon":10.882,
           "tags":{"name":"Via Uno","climbing":"route_bottom","climbing:bolts":"6",
                   "climbing:grade:french":"5c"}}
        ]}
        rows, report = build(source, (45.8,10.7,46,11), "fixture")
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["routeCount"], 1)
        self.assertEqual(report["routeBoltsCountAvailable"], 1)
        self.assertEqual(report["routeQuickdrawsAvailable"], 0)
        self.assertEqual(report["types"]["crag"], 1)

    def test_title_and_numbers(self):
        self.assertEqual(slug("Placche di Baoné - Arco"), "placche-di-baone-arco")
        self.assertIsNone(number("yes", integer=True))
        self.assertEqual(number("0", integer=True), 0)
        self.assertIn('nwr["climbing"]', query_for((45.87,10.82,45.99,11.03)))

if __name__ == "__main__":
    unittest.main()
