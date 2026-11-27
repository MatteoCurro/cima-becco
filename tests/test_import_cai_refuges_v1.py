"""CAI full catalog importer: offline fixture contract and release-safety checks."""
from pathlib import Path
import importlib.util
import json
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
spec=importlib.util.spec_from_file_location("cai_release",ROOT/"scripts"/"import_cai_refuges_v1.py")
cai=importlib.util.module_from_spec(spec)
spec.loader.exec_module(cai)
MAPPING=json.loads((ROOT/"scripts"/"cai_refuge_field_map_v1.json").read_text())
PROPOSALS=json.loads((ROOT/"scripts"/"cai_unmapped_fields_review_plan_v1.json").read_text())
UUID="8c1e2467-2b8d-4c82-a331-cd5e8622870f"


def fixture(kind="Rifugio custodito",code=921800106):
    return {"id_cai":code,"title":"BOE'","published":True,
            "deleted_at":None,"updated_at":"2026-11-27T18:00:00Z",
            "geo":{"type":"Point","coordinates":[11.824,46.505]},
            "altitude_geo":2873}


def detail(kind="Rifugio custodito",code=921800106):
    return {"id_cai":code,"title":"BOE'","fields":[
        {"name":"type","value":kind},
        {"name":"status","value":"In attività"},
        {"name":"description_geo","value":"<p>Rifugio del Sella</p>"},
        {"name":"posti_totali_service","value":"72","updated_at":"2026-11-01T00:00:00Z"},
        {"name":"wifi_service","value":"sì"},
        {"name":"acqua_in_rifugio_service","value":"yes"},
        {"name":"phone","value":"ignore me"},
        {"name":"taxCode_management_property","value":"PRIVATE_TAX_CODE"},
        {"name":"contract_fee_management_property","value":"PRIVATE_FEE"},
        {"name":"email_management_property","value":"private@example.org"},
        {"name":"openingTime_contact","value":None,"data":[{"key":"estiva"}]},
        {"name":"wc_uso_comune_service","value":"yes"},
    ],"media":[{"uuid":UUID,"mime_type":"image/jpeg",
                "original_url":"https://rifugi.cai.it/media/rifugio-boe.jpg",
                "collection_name":"images","name":"Boé panoramica",
                "custom_properties":{"author":"Mario Rossi"}}]}


class CAIReleaseTests(unittest.TestCase):
    def test_rifugio_type_and_facts_and_images(self):
        row=cai.normalize_detail(fixture(),detail(),MAPPING,PROPOSALS)
        self.assertEqual(row["kind"],"rifugio")
        self.assertEqual(row["subtype"],"custodito")
        self.assertEqual(row["caiId"],"921800106")
        self.assertEqual(row["slug"],"cai-921800106")
        self.assertEqual(row["lat"],46.505)
        self.assertEqual(row["lng"],11.824)
        self.assertEqual(row["facts"]["bedsTotal"]["value"],72)
        self.assertEqual(row["facts"]["wifi"]["value"],True)
        self.assertTrue(row["facts"]["waterAvailableReported"]["value"])
        self.assertNotIn("drinkingWater",row["facts"])
        self.assertEqual(row["facts"]["caiCatalogueStatus"]["value"],"In attività")
        self.assertTrue(row["openingScheduleStructured"])
        self.assertEqual(len(row["media"]),1)
        self.assertTrue(row["media"][0]["reuseAllowed"])
        self.assertEqual(row["media"][0]["author"],"Mario Rossi")
        s=json.dumps(row)
        for marker in ("PRIVATE_TAX_CODE","PRIVATE_FEE","private@example.org"):
            self.assertNotIn(marker,s)
        self.assertNotIn("<p>",s)

    def test_bivouac_is_not_misclassified_as_refuge(self):
        r=cai.normalize_detail(fixture(),detail(kind="Bivacco"),MAPPING,PROPOSALS)
        self.assertEqual(r["kind"],"bivacco")
        self.assertEqual(r["subtype"],"non_custodito")

    def test_other_or_unknown_type_stays_out_of_refuge_export(self):
        for kind in ("Capanna sociale","Punto d'appoggio","Tipo inedito"):
            with self.subTest(kind=kind):
                row=cai.normalize_detail(fixture(),detail(kind),MAPPING,PROPOSALS)
                self.assertNotEqual(row["kind"],"rifugio")

    def test_unpublished_or_deleted_is_not_fetched_and_not_exported(self):
        one=fixture();one["published"]=False
        second=fixture(code=921800107)
        d=cai.build_catalogue([one,second],{"921800107":detail(code=921800107)},
                              MAPPING,PROPOSALS,complete=False)
        self.assertEqual(len(d["records"]),1)
        self.assertEqual(d["records"][0]["caiId"],"921800107")

    def test_unchanged_revisions_reuse_cached_details(self):
        first=cai.build_catalogue([fixture()],{"921800106":detail()},
                                  MAPPING,PROPOSALS,complete=False)
        second=cai.build_catalogue([fixture()],{},MAPPING,PROPOSALS,first,complete=False)
        self.assertEqual(first,second)

    def test_changed_revision_needs_updated_detail_and_fails_closed(self):
        first=cai.build_catalogue([fixture()],{"921800106":detail()},
                                  MAPPING,PROPOSALS,complete=False)
        row=fixture();row["updated_at"]="2026-11-28T12:00:00Z"
        with self.assertRaisesRegex(ValueError,"Dettagli CAI mancanti"):
            cai.build_catalogue([row],{},MAPPING,PROPOSALS,first,complete=False)

    def test_incomplete_catalog_is_not_complete_release(self):
        with self.assertRaisesRegex(ValueError,"meno di 100"):
            cai.build_catalogue([fixture()],{"921800106":detail()},
                                MAPPING,PROPOSALS,complete=True)
        with self.assertRaisesRegex(ValueError,"pagination cambiata"):
            cai.fetch_catalogue(lambda url:{"unexpected":"no"})

    def test_pagination_and_duplicate_safety(self):
        def api(url):
            page=int(url.rsplit("page=",1)[1])
            return {"total":3,"data":[{"id_cai":page*100+i}
                    for i in range(2 if page==1 else 1)]}
        rows=cai.fetch_catalogue(api,page_size=2)
        self.assertEqual([x["id_cai"] for x in rows],[100,101,200])
        def dup(url):
            return {"total":2,"data":[{"id_cai":1},{"id_cai":1}]}
        with self.assertRaisesRegex(ValueError,"duplicati"):
            cai.fetch_catalogue(dup)

    def test_media_no_unsafe_urls_and_dedup(self):
        d=detail()
        d["media"].extend([
            dict(d["media"][0]),
            {"uuid":"de8e8abc-9f6c-4a87-a571-718da818b0c4","mime_type":"image/jpeg",
             "original_url":"javascript:alert('not allowed')"},
        ])
        r=cai.media_from_detail(d)
        self.assertEqual(len(r),1)
        self.assertEqual(r[0]["kind"],"photo")

    def test_empty_geo_skipped(self):
        r=fixture()
        r["geo"]={"type":"Point","coordinates":[999,46.5]}
        self.assertIsNone(cai.normalize_detail(r,detail(),MAPPING,PROPOSALS))


if __name__=="__main__":
    unittest.main()
