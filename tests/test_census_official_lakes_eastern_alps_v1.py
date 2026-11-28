"""Offline QA for multi-cell, bounded official Eastern-Alps WFS lake census."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
from urllib.parse import parse_qs, urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
from census_official_lakes_eastern_alps_v1 import (
    MAX_REQUESTS, REGION_BBOX, bbox_overlap, census, parse_wfs_hits,
    source_name, split4, wfs_census_url,
)
from import_official_lake_wfs_v1 import PROVIDERS

CAP=b"""<wfs:WFS_Capabilities xmlns:wfs="http://www.opengis.net/wfs/2.0">
<wfs:FeatureTypeList>
<wfs:FeatureType><wfs:Name>p_bz-Hydrology:Lakes</wfs:Name></wfs:FeatureType>
<wfs:FeatureType><wfs:Name>arpav:idrografia_specchio_acqua</wfs:Name></wfs:FeatureType>
</wfs:FeatureTypeList></wfs:WFS_Capabilities>"""


def records(provider):
    box=REGION_BBOX[provider]
    w,s,e,n=box
    out=[]
    for i in range(20):
        x=w+(0.24 if i%2==0 else 0.74)*(e-w)+(i//4)*0.003
        y=s+(0.25 if i%4<2 else 0.75)*(n-s)+(i//4)*0.003
        ring=[[x,y],[x+0.0008,y],[x+0.0008,y+0.0008],
              [x,y+0.0008],[x,y]]
        fid=(f"Lakes.{i+100}" if provider=="bolzano_lakes" else
             f"idrografia_specchio_acqua.{i+100}")
        props=({"ID":i+100,"CODE":f"C{i}",
                "NAME_IT":f"Lago prova {i}", "NAME_DE":f"Testsee {i}",
                "AREA":50000.0,"AREA_GEOM":50000.0,"ELEVATION":1700.0,
                "VOLUME":500000.0,"WIDTH":50.0,"LENGTH":100.0} if
               provider=="bolzano_lakes" else
               {"nome":f"Lago prova {i}","tipo":"Lago",
                "area_m2":50000.0,"hydroidspc":i+100})
        out.append({"type":"Feature","id":fid,"properties":props,
                    "geometry":{"type":"Polygon","coordinates":[ring]}})
    return out


def bbox_from_url(provider, url):
    q=parse_qs(urlsplit(url).query)
    if "bbox" not in q:
        return None
    vals=list(map(float,q["bbox"][0].split(",")[:4]))
    latlon=(PROVIDERS[provider]["wfsVersion"]=="2.0.0")
    if PROVIDERS[provider]["preferredBboxMode"]=="alternate":
        latlon=not latlon
    if latlon:
        return vals[1],vals[0],vals[3],vals[2]
    return tuple(vals)


def fake_for(provider):
    records_ = records(provider)
    requested=[]
    def fetch(url,**kwargs):
        requested.append(url)
        q=parse_qs(urlsplit(url).query)
        op=q.get("request",[""])[0]
        if op=="GetCapabilities":
            return CAP
        box=bbox_from_url(provider,url)
        data=[f for f in records_ if
              box is None or bbox_overlap({
                  "coordinates":[f["geometry"]["coordinates"]],
              },box)]
        if q.get("resultType") == ["hits"]:
            return (f'<wfs:FeatureCollection xmlns:wfs="http://www.opengis.net/wfs/2.0"'
                    f' numberMatched="{len(data)}"/>').encode()
        assert op=="GetFeature",op
        return json.dumps({"type":"FeatureCollection",
                           "features":data[:20]}).encode()
    return fetch,requested


class CensusTests(unittest.TestCase):
    def test_fixed_providers_and_alpine_bounds(self):
        self.assertEqual(set(REGION_BBOX),set(PROVIDERS))
        self.assertEqual(MAX_REQUESTS,128)
        for provider,box in REGION_BBOX.items():
            self.assertTrue(box[0]<box[2] and box[1]<box[3])
            self.assertGreater(box[1],45)

    def test_urls_use_exact_same_known_layer_and_bbox_axis(self):
        for provider in PROVIDERS:
            url=wfs_census_url(provider,"ns:"+PROVIDERS[provider]["layerSuffix"],
                               REGION_BBOX[provider])
            self.assertTrue(url.startswith(PROVIDERS[provider]["endpoint"]))
            self.assertEqual(bbox_from_url(provider,url),REGION_BBOX[provider])
            self.assertIn("4326",url)
            self.assertIn("20",url)
            hits=wfs_census_url(provider,"ns:layer",hits=True)
            self.assertIn("resultType=hits",hits)
            self.assertNotIn("bbox=",hits)

    def test_historical_wfs_and_current_wfs_counts(self):
        self.assertEqual(parse_wfs_hits(b'<wfs:FeatureCollection xmlns:wfs="x" numberMatched="456"/>'),456)
        self.assertEqual(parse_wfs_hits(b'<wfs:FeatureCollection xmlns:wfs="x" numberOfFeatures="222"/>'),222)
        self.assertIsNone(parse_wfs_hits(b'<wfs:FeatureCollection xmlns:wfs="x" numberMatched="unknown"/>'))
        self.assertIsNone(parse_wfs_hits(b'<ExceptionReport>error</ExceptionReport>'))

    def test_quadrant_partition_has_no_gaps(self):
        box=REGION_BBOX["bolzano_lakes"]
        tiles=split4(box)
        self.assertEqual(len(tiles),4)
        self.assertEqual(min(t[0] for t in tiles),box[0])
        self.assertEqual(min(t[1] for t in tiles),box[1])
        self.assertEqual(max(t[2] for t in tiles),box[2])
        self.assertEqual(max(t[3] for t in tiles),box[3])
        self.assertEqual(sum((t[2]-t[0])*(t[3]-t[1]) for t in tiles),
                         (box[2]-box[0])*(box[3]-box[1]))

    def test_twenty_paged_by_tiles_is_full_region_not_twenty_lakes(self):
        for provider in PROVIDERS:
            with self.subTest(provider=provider):
                fetch,calls=fake_for(provider)
                doc,pending,report=census(provider,fetcher=fetch,
                                  max_requests=10,max_depth=2,pause=0)
                self.assertEqual(report["requests"],5)  # parent + 4 children
                self.assertEqual(report["acceptedIndependentSourceRecordsG0"],20)
                self.assertEqual(report["requestedRegionNumberMatched"],20)
                self.assertEqual(report["sourceLayerNumberMatched"],20)
                self.assertTrue(report["regionEnumerationComplete"])
                self.assertTrue(report["regionEnumerationProvenByHits"])
                self.assertEqual(report["namedAcceptedRecords"],20)
                self.assertEqual(len({x["sourceFeatureId"] for x in doc["entities"]}),20)
                self.assertFalse(doc["isPublished"])
                self.assertFalse(doc["completeDataset"])
                self.assertEqual(sum(x["quality"]["seoIndexable"] is True
                                     for x in doc["entities"]),0)
                self.assertTrue(all(x["subtype"] is None for x in doc["entities"]))
                self.assertEqual(report["published"],0)
                self.assertGreaterEqual(len(calls),7)  # caps + 2 hits + 5 tiles

    def test_budget_exhaustion_is_detected_not_claimed_exhaustive(self):
        fetch,_=fake_for("arpav_water_surfaces")
        doc,pending,report=census("arpav_water_surfaces",fetcher=fetch,
                          max_requests=1,max_depth=3,pause=0)
        self.assertEqual(report["requests"],1)
        self.assertEqual(report["acceptedIndependentSourceRecordsG0"],20)
        self.assertFalse(report["regionEnumerationComplete"])
        self.assertFalse(report["regionEnumerationProvenByHits"])
        self.assertGreater(report["remainingUnresolvedCells"],0)

    def test_arpav_classification_never_promoted_to_kind(self):
        fetch,_=fake_for("arpav_water_surfaces")
        doc,pending,report=census("arpav_water_surfaces",fetcher=fetch,
                          max_requests=10,max_depth=2,pause=0)
        self.assertEqual(report["providerClassifications"],{"Lago":20})
        for item in doc["entities"]:
            self.assertEqual(item["providerSubtypeCandidate"],"lake")
            self.assertIsNone(item["subtype"])
            self.assertFalse(item["quality"]["officialIdentityCrosswalkVerified"])

    def test_bolzano_aliases_are_preserved_as_provider_source_evidence(self):
        fetch,_=fake_for("bolzano_lakes")
        doc,pending,report=census("bolzano_lakes",fetcher=fetch,
                          max_requests=10,max_depth=2,pause=0)
        self.assertEqual(report["namedAcceptedRecords"],20)
        self.assertEqual({v["language"] for v in doc["entities"][0]["providerNames"]},
                         {"it","de"})
        self.assertTrue(doc["entities"][0]["providerRecordCodes"]["verifiedAgainstFid"])
        self.assertNotIn("bathable",json.dumps(doc).lower())

    def test_invalid_polygon_still_preserves_source_fid_and_facts_in_g0_review(self):
        fetch,_=fake_for("bolzano_lakes")
        def broken(url,**kwargs):
            raw=fetch(url,**kwargs)
            if parse_qs(urlsplit(url).query).get("request")==["GetFeature"]:
                payload=json.loads(raw)
                for row in payload["features"]:
                    if row["id"]=="Lakes.100":
                        ring=row["geometry"]["coordinates"][0]
                        row["geometry"]["coordinates"]=[ring[:-1]]  # unclosed
                return json.dumps(payload).encode()
            return raw
        doc,pending,report=census("bolzano_lakes",fetcher=broken,
                                  max_requests=10,max_depth=2,pause=0)
        self.assertEqual(report["featuresRawDistinctSeen"],20)
        self.assertEqual(report["acceptedIndependentSourceRecordsG0"],19)
        self.assertEqual(report["sourceIdsWithGeometryReviewG0"],1)
        self.assertEqual(pending["entities"][0]["sourceFeatureId"],"Lakes.100")
        self.assertNotIn("geo",pending["entities"][0])
        self.assertIn("officialElevationReportedM",pending["entities"][0]["facts"])
        self.assertFalse(pending["entities"][0]["quality"]["seoIndexable"])
        self.assertTrue(report["regionEnumerationProvenByHits"])
        self.assertFalse(pending["isPublished"])

    def test_bogus_zero_wfs_hits_cannot_override_observed_features(self):
        fetch,_=fake_for("arpav_water_surfaces")
        def bogus(url,**kwargs):
            if parse_qs(urlsplit(url).query).get("resultType")==["hits"]:
                return (b'<wfs:FeatureCollection xmlns:wfs="x" '
                        b'numberOfFeatures="0"/>')
            return fetch(url,**kwargs)
        doc,pending,report=census("arpav_water_surfaces",fetcher=bogus,
                                  max_requests=10,max_depth=2,pause=0)
        self.assertEqual(report["featuresRawDistinctSeen"],20)
        self.assertIsNone(report["sourceLayerNumberMatched"])
        self.assertIsNone(report["requestedRegionNumberMatched"])
        self.assertEqual(len(report["hitsReliabilityWarnings"]),2)
        self.assertTrue(report["regionEnumerationComplete"])
        self.assertFalse(report["regionEnumerationProvenByHits"])

    def test_rejects_external_network_endpoints_and_excessive_work(self):
        with self.assertRaises(ValueError):
            census("unknown",fetcher=lambda url,**kw: b"",pause=0)
        with self.assertRaises(ValueError):
            census("bolzano_lakes",fetcher=lambda url,**kw:b"",
                   max_requests=MAX_REQUESTS+1,pause=0)
        with self.assertRaises(ValueError):
            census("arpav_water_surfaces",fetcher=lambda url,**kw:b"",
                   max_depth=5,pause=0)
        with self.assertRaises(ValueError):
            wfs_census_url("nonexistent","layer")

if __name__=="__main__":
    unittest.main()
