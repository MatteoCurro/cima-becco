"""Tests della fonte puntuale ISTAT 2021: join, CRS, demografia senza inferenze."""
from __future__ import annotations

import io
import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from enrich_settlement_istat_geometry_v1 import (dbf_records, records_from_archive, enrich)

FIELDS = [("COD_REG","N",10),("COD_UTS","N",10),("PRO_COM","N",10),
          ("LOC_ID","N",19),("LOC","N",10),("TIPO_LOC","N",5),
          ("NOME","C",100),("CENTRO_CL","N",5),("ALTITUDINE","C",10),
          ("POP21","N",19),("FAM21","N",19),("ABI21","N",10),
          ("EDI21","N",10),("POINT_X","F",19),("POINT_Y","F",19)]
PRJ='PROJCS["WGS_1984_UTM_Zone_32N",PARAMETER["Central_Meridian",9.0]]'
BASE_ROW = {
    "COD_REG":"4","COD_UTS":"21","PRO_COM":"21001",
    "LOC_ID":"2100110001.00000000","LOC":"10001",
    "TIPO_LOC":"1","NOME":"Aldino","CENTRO_CL":"1","ALTITUDINE":"1225",
    "POP21":"934.00000000","FAM21":"320.00000000","ABI21":"401",
    "EDI21":"310","POINT_X":"6.8e+05","POINT_Y":"5.12e+06",
}
def dbf(rows):
    width=1+sum(field[2] for field in FIELDS)
    header_length=32+32*len(FIELDS)+1
    head=bytearray(header_length)
    head[0]=3
    struct.pack_into("<I",head,4,len(rows))
    struct.pack_into("<H",head,8,header_length)
    struct.pack_into("<H",head,10,width)
    for i,(key,kind,n) in enumerate(FIELDS):
        pos=32+32*i
        head[pos:pos+len(key)]=key.encode()
        head[pos+11]=ord(kind)
        head[pos+16]=n
    head[-1]=0x0d
    records=[]
    for row in rows:
        record=bytearray(b" ")
        for key,kind,n in FIELDS:
            value=str(row.get(key,""))
            data=value.rjust(n) if kind in ("N","F") else value.ljust(n)
            record.extend(data.encode()[:n])
        assert len(record)==width
        records.append(record)
    return bytes(head)+b"".join(records)+b"\x1a"

def staging():
    return {"releaseChannel":"STAGING_ISTAT21_OSM_SETTLEMENTS","isPublished":False,
            "entities":[{
                "id":"abc","slug":"aldino","name":"Aldino","subtype":"centro_abitato",
                "sourceIds":{"istatLocality":"02100110001","istatMunicipality":"021001"},
                "geo":{"point":None},"facts":{},"quality":{"gate":"G0","seoIndexable":False},
                "editorialStatus":"raw"
            }]}

class OfficialPointTests(unittest.TestCase):
    def test_dbf_header_strict_and_preserves_precision(self):
        rows=list(dbf_records(dbf([BASE_ROW])))
        self.assertEqual(len(rows),1)
        self.assertEqual(rows[0]["LOC_ID"],"2100110001.00000000")
        self.assertEqual(rows[0]["NOME"],"Aldino")

    def test_official_archive_and_crs_required(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"LocalitaPuntuali_21.zip"
            with ZipFile(path,"w") as z:
                z.writestr("LocalitàPuntuali_21/Localita_2021_Point.prj",PRJ)
                z.writestr("LocalitàPuntuali_21/Localita_2021_Point.dbf",dbf([BASE_ROW]))
            rows,digest=records_from_archive(path)
        self.assertEqual(len(rows),1)
        self.assertEqual(len(digest),64)

    def test_population_and_coordinates_only_exact_record(self):
        doc,report=enrich(staging(),[BASE_ROW],
            xy_to_lonlat=lambda x,y:(11.35,46.37),retrieved_at="2026-11-28T12:00:00Z")
        e=doc["entities"][0]
        self.assertEqual(report["counts"]["matched"],1)
        self.assertEqual(e["geo"]["point"],{"lat":46.37,"lng":11.35})
        self.assertEqual(e["geo"]["sourceCoordinateReferenceSystem"],"EPSG:32632")
        self.assertEqual(e["facts"]["popolazione"]["value"],934)
        self.assertEqual(e["facts"]["popolazione"]["validFrom"],"2021-12-31")
        self.assertEqual(e["facts"]["famiglie"]["value"],320)
        self.assertEqual(e["facts"]["abitazioni"]["value"],401)
        self.assertEqual(e["facts"]["edifici"]["value"],310)
        self.assertFalse(e["quality"]["seoIndexable"])
        self.assertEqual(e["quality"]["gate"],"G1")
        self.assertNotIn("sindacoNome",e["facts"])

    def test_name_or_subtype_mismatch_never_assigned(self):
        for changes in ({"NOME":"Aldino di Belluno"},{"TIPO_LOC":"2"},
                        {"PRO_COM":"21002"},{"LOC":"10002"}):
            row={**BASE_ROW,**changes}
            doc,report=enrich(staging(),[row],xy_to_lonlat=lambda x,y:(11.35,46.37))
            self.assertIsNone(doc["entities"][0]["geo"]["point"])
            self.assertEqual(report["counts"]["matched"],0)

    def test_zero_is_real_not_missing(self):
        row={**BASE_ROW,"POP21":"0.00000000","FAM21":""}
        doc,_=enrich(staging(),[row],xy_to_lonlat=lambda x,y:(11.35,46.37))
        e=doc["entities"][0]
        self.assertEqual(e["facts"]["popolazione"]["value"],0)
        self.assertNotIn("famiglie",e["facts"])

    def test_unrecognized_crs_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/"LocalitaPuntuali_21.zip"
            with ZipFile(path,"w") as z:
                z.writestr("LocalitàPuntuali_21/Localita_2021_Point.prj","EPSG:4326")
                z.writestr("LocalitàPuntuali_21/Localita_2021_Point.dbf",dbf([BASE_ROW]))
            with self.assertRaisesRegex(ValueError,"CRS"):
                records_from_archive(path)

if __name__=="__main__":
    unittest.main()
