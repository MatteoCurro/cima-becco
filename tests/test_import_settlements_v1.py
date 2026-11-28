"""Contratti offline Blocco 4: localita ISTAT 2021 e OSM senza merge euristici."""
from __future__ import annotations

import sys
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_settlements_v1 import build, official_csvs, official_rows, locality, osm_settlement

MUNI = {"entities": [
    {"id": "municipality-1", "name": "Canazei", "slug": "canazei",
     "sourceIds": {"istat": "021001", "wikidata": "Q123"}},
]}
OSM = {"places": [
    {"kind": "borgo", "name": "Canazei", "lat": 46.47, "lng": 11.77,
     "osmUrl": "https://www.openstreetmap.org/node/101", "wikidata": "Q123"},
    {"kind": "borgo", "name": "Alba", "lat": 46.45, "lng": 11.79,
     "osmUrl": "https://www.openstreetmap.org/node/202", "wikidata": "Q456",
     "elevationM": 1500, "elevationSource": "dem"},
    {"kind": "rifugio", "name": "Non e un borgo", "lat": 46.47, "lng": 11.77,
     "osmUrl": "https://www.openstreetmap.org/node/303"},
]}
CSV = (
    "PRO_COM;LOC21_ID;TIPO_LOC;COD_LOC;NOME;CENTRO_CL\n"
    "021001;02100110001;1;10001;Canazei;1\n"
    "021001;02100120101;2;20101;Alba;0\n"
    "021001;02100130001;3;30001;Zona industriale;0\n"
    "021001;02100120102;2;20199;Codice errato;0\n"
    "021999;02199910001;1;10001;Abitato senza Comune pubblicato;0\n"
)

class SettlementImportTests(unittest.TestCase):
    def make_archive(self, folder: Path, body=CSV):
        path = folder / "R04_21.zip"
        with ZipFile(path, "w") as z:
            z.writestr("DATA/LOC_R04_21.csv", body.encode("utf-8"))
            z.writestr("DATA/SEZ_R04_21.csv", b"wrong table")
        return path

    def test_official_zip_filters_to_correct_worksheet(self):
        with tempfile.TemporaryDirectory() as folder:
            items = official_csvs(self.make_archive(Path(folder)))
            self.assertEqual(len(items), 1)
            self.assertEqual(len(official_rows(items[0][1])), 5)
            self.assertIn("LOC_R04_21.csv", items[0][0])

    def test_real_istat_utf16_tab_and_reported_altitude(self):
        # Tracciato ufficiale osservato nel pilota reale R04_21.
        header = "COD_REG\tCOD_UTS\tPRO_COM\tLOC21_ID\tTIPO_LOC\tNOME\tCENTRO_CL\tALTITUDINE (in metri slm)\n"
        row = "4\t21\t21001\t2100110001\t1\tAldino\t1\t1225\n"
        body = (header + row).encode("utf-16")
        with tempfile.TemporaryDirectory() as folder:
            path = self.make_archive(Path(folder), "")
            with ZipFile(path, "w") as z:
                z.writestr("DATA/LOC_R04_21.csv", body)
            csv_source = official_csvs(path)[0]
            parsed = official_rows(csv_source[1])
        self.assertEqual(len(parsed), 1)
        item, err = locality(parsed[0], source_url="https://www.istat.it/",
            checked_at="2026-11-28T00:00:00Z", municipality_by_code={})
        self.assertIsNone(err, {"parsed": parsed[0], "code": __import__("import_settlements_v1").code6(__import__("import_settlements_v1").value(parsed[0], "PRO_COM")), "locality": __import__("import_settlements_v1").digits(__import__("import_settlements_v1").value(parsed[0], "LOC21_ID"), 11), "subtype": __import__("import_settlements_v1").digits(__import__("import_settlements_v1").value(parsed[0], "TIPO_LOC"), 1)})
        self.assertEqual(item["sourceIds"]["istatMunicipality"], "021001")
        self.assertEqual(item["sourceIds"]["istatLocality"], "02100110001")
        self.assertEqual(item["facts"]["elevationM"]["value"], 1225)
        self.assertEqual(item["facts"]["elevationM"]["unit"], "m")
        self.assertEqual(item["elevationMethod"], "istat_reported_locality_2021")

    def test_staging_preserves_istat_and_osm_as_distinct_entities(self):
        with tempfile.TemporaryDirectory() as folder:
            doc, report = build([self.make_archive(Path(folder))], OSM, MUNI,
                                checked_at="2026-11-28T00:00:00Z")
        self.assertFalse(doc["isPublished"])
        self.assertEqual(report["seoIndexable"], 0)
        self.assertEqual(report["officialRecords"], 3)
        self.assertEqual(report["osmRecords"], 1)
        self.assertEqual(report["totalEntities"], 4)
        self.assertEqual(report["documentedMunicipalityRelations"], 2)
        self.assertEqual(report["rejected"]["not_a_settlement"], 1)
        self.assertEqual(report["rejected"]["conflicting_istat_locality_codes"], 1)
        self.assertEqual(report["rejected"]["municipality_shadow_not_a_frazione"], 1)
        self.assertEqual(len({e["id"] for e in doc["entities"]}), 4)
        self.assertEqual(len({e["slug"] for e in doc["entities"]}), 4)
        self.assertTrue(all(not x["quality"]["seoIndexable"] for x in doc["entities"]))
        self.assertTrue(all("sindacoNome" not in x["facts"] and "population" not in x["facts"]
                            for x in doc["entities"]))
        self.assertTrue(all(m == [] for m in (x["media"] for x in doc["entities"])))

    def test_census_parent_not_inherited_and_centre_not_frazione(self):
        row = official_rows(CSV.encode())[0]
        entity, error = locality(row,
            source_url="https://www.istat.it/storage/cartografia/basi_territoriali/2021/R04_21.zip",
            checked_at="2026-11-28T00:00:00Z", municipality_by_code={"021001": MUNI["entities"][0]})
        self.assertIsNone(error)
        self.assertEqual(entity["subtype"], "centro_abitato")
        self.assertTrue(entity["isMunicipalCapital"])
        self.assertEqual(entity["quality"]["gate"], "G0")
        self.assertIsNone(entity["geo"]["point"])
        rel = entity["relations"][0]
        self.assertEqual(rel["type"], "part_of")
        self.assertTrue(rel["verified"])
        self.assertEqual(entity["administrativeHierarchy"]["referenceDate"], "2021-12-31")
        self.assertNotIn("frazione", entity["subtype"])

    def test_osm_elevation_estimate_never_becomes_official_or_verified_parent(self):
        x, err = osm_settlement(OSM["places"][1],
                                checked_at="2026-11-28T00:00:00Z",
                                municipality_by_qid={"Q123": MUNI["entities"][0]})
        self.assertIsNone(err)
        self.assertEqual(x["facts"]["elevationM"]["method"], "estimated")
        self.assertEqual(x["facts"]["elevationM"]["unit"], "m")
        self.assertEqual(x["relations"], [])
        self.assertIsNone(x["parentMunicipalityId"])
        self.assertEqual(x["quality"]["gate"], "G0")
        self.assertEqual(x["slugAliases"], ["osm-n-202"])

    def test_slug_collision_with_existing_suffix_is_not_recreated(self):
        from import_settlements_v1 import unique_slug
        entities = [
            {"id": "11111111-0000-0000-0000-000000000000", "slug": "alba", "quality": {}},
            {"id": "22222222-0000-0000-0000-000000000000", "slug": "alba", "quality": {}},
            {"id": "33333333-0000-0000-0000-000000000000", "slug": "alba-1", "quality": {}},
            {"id": "44444444-0000-0000-0000-000000000000", "slug": "alba-11111111", "quality": {}},
        ]
        self.assertEqual(unique_slug(entities), 1)
        self.assertEqual(len({x["slug"] for x in entities}), len(entities))
        self.assertEqual(entities[0]["slug"], "alba-111111110000")
        self.assertTrue(entities[0]["quality"]["slugRequiresReview"])

    def test_bad_identity_rejected_instead_of_derived(self):
        row = official_rows(CSV.encode())[0].copy()
        row["loc21 id"] = ""
        entity, error = locality(row, source_url="https://www.istat.it/",
                                 checked_at="2026-11-28T00:00:00Z",
                                 municipality_by_code={})
        self.assertIsNone(entity)
        self.assertEqual(error, "invalid_istat_identity")

    def test_reproducible_ids_and_no_auto_merge_by_name(self):
        with tempfile.TemporaryDirectory() as folder:
            p = self.make_archive(Path(folder))
            first, _ = build([p], OSM, MUNI, checked_at="2026-11-28T00:00:00Z")
            second, _ = build([p], OSM, MUNI, checked_at="2026-11-28T00:00:00Z")
        self.assertEqual(first, second)
        alba = [x for x in first["entities"] if x["name"] == "Alba"]
        self.assertEqual(len(alba), 2, "ISTAT ed OSM restano distinti in staging")
        self.assertEqual(len({x["id"] for x in alba}), 2)

if __name__ == "__main__":
    unittest.main()
