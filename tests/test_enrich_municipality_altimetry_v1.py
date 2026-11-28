"""No inferred municipality altitude; ISTAT 2021 join audited by ID."""
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from enrich_municipality_altimetry_v1 import rows_from_source,attach_altimetry
from enrich_municipalities_v1 import claim_quantity

def publication():
    def record(code):
        return {"id":"e"+code,"name":"Comune","kind":"municipality",
         "sourceIds":{"istat":code},"facts":{}}
    return {"releaseChannel":"ISTAT_DAIT_MUNICIPALITIES","entities":[record("022039"),record("025016")]}
class AltimetricContracts(unittest.TestCase):
    def test_csv_2021_no_geographic_name_join(self):
        raw=b"Codice Comune;Altitudine minima DEM (m);Altitudine massima DEM (m);Altitudine media DEM (m)\n022039;1100;3152;1680\n025016;1020;3240;1780\n"
        release,report=attach_altimetry(publication(),raw,retrieved_at="2026-11-28")
        self.assertEqual(report["matched"],2)
        e=release["entities"][0]
        self.assertEqual(e["facts"]["altitudineTerritorioMinM"]["value"],1100)
        self.assertEqual(e["facts"]["altitudineTerritorioMaxM"]["value"],3152)
        self.assertEqual(e["facts"]["altitudineTerritorioMediaM"]["unit"],"m")
        self.assertEqual(e["facts"]["altitudineTerritorioMinM"]["sourceUpdatedAt"],"2021-12-31")
        self.assertNotIn("quotaCentroM",e["facts"])
    def test_bad_table_blocked(self):
        with self.assertRaises(ValueError):
            rows_from_source(b"Comune;Quota\nCanazei;1500\n")
    def test_conflicting_altitudes_not_committed(self):
        raw=b"Codice Comune;Altitudine minima;Altitudine massima\n022039;3900;1000\n"
        release,report=attach_altimetry(publication(),raw)
        self.assertEqual(report["metricsAdded"],0)
        self.assertNotIn("altitudineTerritorioMinM",release["entities"][0]["facts"])
    def test_no_merge_by_name_and_historical_code(self):
        raw=b"Codice Comune;Altitudine minima\n999999;1000\n"
        release,report=attach_altimetry(publication(),raw)
        self.assertEqual(report["matched"],0)
        self.assertEqual(report["metricsAdded"],0)
    def test_wikidata_unit_rejected(self):
        def claim(unit,amount):
            return {"mainsnak":{"datavalue":{"value":{"amount":amount,"unit":unit}}}}
        item={"claims":{"P2044":[claim("http://www.wikidata.org/entity/Q11573","+1486")]}}
        self.assertEqual(claim_quantity(item,"P2044","Q11573",-5,4800),1486)
        item["claims"]["P2044"]=[claim("http://www.wikidata.org/entity/Q712226","+1486")]
        self.assertIsNone(claim_quantity(item,"P2044","Q11573",-5,4800))
if __name__=="__main__": unittest.main()
