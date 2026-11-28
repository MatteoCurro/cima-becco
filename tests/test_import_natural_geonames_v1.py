"""Offline contract test for GeoNames natural features as an OSM outage-safe source."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from zipfile import ZipFile

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from import_natural_geonames_v1 import entity_from_line,load_dump,run,CODES

AT="2026-11-28T00:00:00+00:00"
BBOX=(46.3,11.1,47.1,13.0)

def row(ident,name,code,feature_class,ele="",dem="",lat=46.7,lon=12.0):
    values=[str(ident),name,name.replace(" ",""),"",
            str(lat),str(lon),feature_class,code,"IT","","17","01","","",
            "0",str(ele),str(dem),"Europe/Rome","2026-11-01"]
    assert len(values)==19
    return "\t".join(values)


class GeoNamesFeatureTest(unittest.TestCase):
    def test_each_exact_feature_type(self):
        for idx,(feature,(subtype,classification)) in enumerate(CODES.items()):
            with self.subTest(feature=feature):
                item=entity_from_line(row(100+idx,"Nome documentato "+str(idx),
                                               feature,classification,ele=2300),AT,BBOX)
                self.assertIsNotNone(item)
                self.assertEqual(item["subtype"],subtype)
                self.assertEqual(item["facts"]["elevationM"]["licence"],"CC BY 4.0")
                self.assertFalse(item["quality"]["seoIndexable"])
                self.assertFalse(item["media"])
                self.assertEqual(item["sourceIds"]["geonames"],str(100+idx))

    def test_dem_does_not_replace_declared_elevation(self):
        e=entity_from_line(row(150,"Passo Locale","PASS","T",ele=1890,dem=1810),AT,BBOX)
        self.assertEqual(e["facts"]["elevationM"]["value"],1890)
        self.assertEqual(e["facts"]["elevationM"]["method"],"reported")
        e=entity_from_line(row(151,"Passo Locale","PASS","T",ele="",dem=1810),AT,BBOX)
        self.assertEqual(e["facts"]["elevationM"]["value"],1810)
        self.assertEqual(e["facts"]["elevationM"]["method"],"estimated")
        e=entity_from_line(row(152,"Passo Locale","PASS","T",ele="-1",dem="-9999"),AT,BBOX)
        self.assertNotIn("elevationM",e["facts"])

    def test_unrelated_unbounded_and_springs_not_imported(self):
        self.assertIsNone(entity_from_line(row(201,"Sorgente","SPRG","H"),AT,BBOX))
        self.assertIsNone(entity_from_line(row(202,"Passo","PASS","T",lat=45),AT,BBOX))
        self.assertIsNone(entity_from_line(row(203,"Passo","PASS","H"),AT,BBOX))
        self.assertIsNone(entity_from_line(row(204,"Passo","PASS","T").replace("\tIT\t","\tAT\t"),AT,BBOX))

    def test_name_conflicts_are_held_as_G0(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"IT.zip"
            with ZipFile(source,"w") as zipfile:
                zipfile.writestr("IT.txt","\n".join([
                    row(101,"Passo dello Stesso Nome","PASS","T"),
                    row(102,"Passo dello Stesso Nome","PASS","T")]))
            result=run(source,BBOX,Path(tmp)/"out")
            self.assertEqual(result["staged"],2)
            self.assertEqual(result["collisionGroups"],1)
            doc=json.loads((Path(tmp)/"out/features-geonames.json").read_text())
            self.assertTrue(all(e["quality"]["gate"]=="G0" for e in doc["entities"]))
            self.assertTrue(all(not e["quality"]["seoIndexable"] for e in doc["entities"]))

    def test_zip_snapshots_and_identifiers_are_stable(self):
        with tempfile.TemporaryDirectory() as tmp:
            source=Path(tmp)/"IT.zip"
            with ZipFile(source,"w") as zipfile:
                zipfile.writestr("IT.txt","\n".join([
                    row(101,"Lago Esempio","LK","H"),
                    row(102,"Valle Esempio","VAL","T")]))
            result=run(source,BBOX,Path(tmp)/"stage")
            self.assertEqual(len(result["sourceSnapshot"]["sha256"]),64)
            self.assertTrue((Path(tmp)/"stage/raw/geonames-features.json").exists())
            doc=json.loads((Path(tmp)/"stage/features-geonames.json").read_text())
            self.assertFalse(doc["isPublished"])
            self.assertEqual(len({e["sourceIds"]["geonames"] for e in doc["entities"]}),2)
            row_id=doc["entities"][0]["id"]
            result2=run(source,BBOX,Path(tmp)/"stage2")
            doc2=json.loads((Path(tmp)/"stage2/features-geonames.json").read_text())
            self.assertEqual(doc2["entities"][0]["id"],row_id)
            self.assertEqual(result2["crossSourceMerges"],0)


if __name__=="__main__":
    unittest.main()
