import unittest
from scripts.pilot_place_weather_wikidata import extract_claims, pick
from scripts.pilot_geography_pois import normalize, haversine
from scripts.pilot_sat_trekking_stages import parse, parse_minutes

class CrossDomainPilotTest(unittest.TestCase):
    def test_population_historical_qualifier_preserved(self):
        entity={"claims":{"P1082":[{"id":"x","rank":"normal",
            "mainsnak":{"snaktype":"value","datavalue":{"value":{"amount":"+2043","unit":"1"}}},
            "qualifiers":{"P585":[{"snaktype":"value","datavalue":{"value":{"time":"+2021-12-31T00:00:00Z"}}}]}}]}}
        facts=extract_claims(entity)
        self.assertEqual(facts["population"]["value"],2043)
        self.assertIn("2021",facts["population"]["pointInTime"])
        self.assertNotIn("mayorQid",facts)

    def test_official_names_not_fused(self):
        places=[{"name":"Canazei","kind":"borgo","slug":"p1","wikidata":"Q258031"},
          {"name":"Canazei","kind":"borgo","slug":"p2","wikidata":"Q18496216"}]
        selection=pick(places)
        self.assertEqual(len(selection),2)
        self.assertNotEqual(selection[0]["wikidata"],selection[1]["wikidata"])

    def test_pois_metadata_only(self):
        peak={"type":"node","id":234,"lat":46.43,"lon":11.78,
              "tags":{"natural":"peak","name":"Cima test","ele":"2500","wikidata":"Q1"}}
        n=normalize(peak)
        self.assertEqual(n["type"],"summit")
        self.assertEqual(n["elevationM"],2500)
        self.assertNotIn("geometry",n)
        self.assertAlmostEqual(haversine((46.43,11.78),(46.43,11.78)),0)

    def test_sat_stage_table(self):
        html="""<html><table><tr><th>Tappa</th><th>Descrizione</th><th>D+</th><th>D-</th><th>Durata</th><th>Grado</th></tr>
          <tr><td>SI C01</td><td>Rifugio Bozzi – Pejo</td><td>450</td><td>1350</td><td>5.30</td><td>E</td></tr>
          <tr><td>SI C02</td><td>Pejo – Rabbi</td><td>—</td><td>500</td><td>7.15</td><td>EE</td></tr></table></html>"""
        rows=parse(html)
        self.assertEqual(len(rows),2)
        self.assertEqual(rows[0]["ascentM"],450)
        self.assertEqual(rows[0]["durationMinutes"],330)
        self.assertIsNone(rows[1]["ascentM"])
        self.assertEqual(rows[1]["difficultyOriginal"],"EE")
        self.assertEqual(parse_minutes("7.15"),435)
        self.assertIsNone(parse_minutes("7.90"))

if __name__ == "__main__":unittest.main()
