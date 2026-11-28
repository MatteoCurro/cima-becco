"""Bibbia regressions: official lake facts, independent source identity and G0."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from import_official_lake_wfs_v1 import parse_geojson
from normalize_official_lake_wfs_facts_v1 import (
    enrich_staged, audit_source_replays, review_with_osm, normalized_name,
)
from audit_official_lake_facts_v1 import run

AT = "2026-11-28T09:00:00+00:00"
RING = [[12.25,46.58],[12.26,46.58],[12.26,46.59],
        [12.25,46.59],[12.25,46.58]]
OTHER = [[12.9,46.9],[12.91,46.9],[12.91,46.91],
         [12.9,46.91],[12.9,46.9]]


def stage(provider, props=None, fid=None, ring=None):
    is_bz = provider == "bolzano_lakes"
    values = ({"ID": 7322, "CODE": "S141",
               "NAME_IT": "Lago di Misurina", "NAME_DE": "Misurinasee",
               "AREA": 700000, "AREA_GEOM": 699500,
               "VOLUME": 4000000, "ELEVATION": 1750,
               "WIDTH": 330, "LENGTH": 700, "DEPTH": None,
               "MAX_DEPTH": None, "BATHING": 1,
               "STATE_OWN": 0, "BASIN": "A.55"}
              if is_bz else
              {"nome": "LAGO DI MISURINA", "tipo": "Lago",
               "hydroidspc": 16, "codtratvp": "BL_5.24",
               "area_m2": 155373.6})
    if props:
        values.update(props)
    fid = fid or ("Lakes.7322" if is_bz else "idrografia_specchio_acqua.277")
    row = {"type": "Feature", "id": fid, "properties": values,
           "geometry": {"type": "Polygon", "coordinates": [ring or RING]}}
    raw = json.dumps({"type":"FeatureCollection","features":[row]}).encode()
    doc, rep = parse_geojson(raw, provider, at=AT)
    assert rep["acceptedG0"] == 1
    return doc


def osm_source(*, name="Lago di Misurina", subtype="lake", ring=None):
    return {
        "isPublished": False,
        "osmEntities": [{
            "displayName": name, "aliases": [],
            "subtype": subtype,
            "sourceIds": {"osm": "way/222"},
            "geo": {"area": {"type": "MultiPolygon",
                             "coordinates": [[ring or RING]]}},
        }],
    }


class OfficialFactsTest(unittest.TestCase):
    def test_bolzano_verified_field_units_and_two_languages(self):
        original = stage("bolzano_lakes")
        result, report = enrich_staged(original)
        e = result["entities"][0]
        self.assertEqual(report["normalizedFeatures"], 1)
        self.assertEqual(e["quality"]["gate"], "G0")
        self.assertFalse(e["quality"]["seoIndexable"])
        self.assertFalse(e["quality"]["officialIdentityCrosswalkVerified"])
        self.assertIsNone(e["subtype"])
        self.assertEqual(e["relations"], [])
        self.assertEqual({i["language"] for i in e["providerNames"]}, {"it","de"})
        self.assertEqual(e["providerRecordCodes"],
                         {"id":7322, "code":"S141","verifiedAgainstFid":True})
        self.assertEqual(e["providerBathingFlagRaw"],1)
        self.assertNotIn("isSwimmable",e["facts"])
        self.assertEqual(e["facts"]["officialElevationReportedM"]["unit"],"m")
        self.assertEqual(e["facts"]["officialVolumeReportedM3"]["unit"],"m3")
        self.assertEqual(e["facts"]["officialAreaReportedM2"]["unit"],"m2")
        self.assertEqual(e["facts"]["officialAreaReportedM2"]["licence"],"CC0 1.0")
        self.assertNotIn("officialDepthReportedM", e["facts"])  # null != zero
        self.assertEqual(original["entities"][0]["facts"].keys(),
                         {"providerMappedWaterSurfaceKm2"})

    def test_arpav_source_class_is_only_a_proposal(self):
        for label, candidate in [("Lago","lake"),("Invaso","reservoir"),
                                  ("Bacino artificiale","reservoir"),
                                  ("Unknown",None)]:
            doc, _ = enrich_staged(stage("arpav_water_surfaces",
                                         props={"tipo":label}))
            e=doc["entities"][0]
            self.assertEqual(e["providerWaterClassRaw"],label)
            self.assertEqual(e["providerSubtypeCandidate"],candidate)
            self.assertIsNone(e["subtype"])
            self.assertEqual(e["providerRecordCodes"]["hydroidspc"],16)
            self.assertEqual(e["facts"]["officialAreaReportedM2"]["unit"],"m2")
            self.assertEqual(e["facts"]["officialAreaReportedM2"]["licence"],
                             "CC BY 3.0")

    def test_zero_is_not_null_and_unverified_negative_is_not_published(self):
        doc = stage("bolzano_lakes",props={"VOLUME":0,"WIDTH":-1,
                                           "LENGTH":"unknown","DEPTH":None})
        result, report = enrich_staged(doc)
        facts = result["entities"][0]["facts"]
        self.assertEqual(facts["officialVolumeReportedM3"]["value"],0)
        self.assertNotIn("officialWidthReportedM",facts)
        self.assertNotIn("officialLengthReportedM",facts)
        self.assertNotIn("officialDepthReportedM",facts)
        self.assertEqual(report["numericAnomalies"],{"WIDTH":1,"LENGTH":1})
        self.assertTrue(result["entities"][0]["quality"]["needsReview"])

    def test_numeric_bool_wrong_type_never_maps(self):
        doc = stage("bolzano_lakes",props={"ELEVATION":True,"VOLUME":False})
        result, report = enrich_staged(doc)
        self.assertNotIn("officialElevationReportedM",result["entities"][0]["facts"])
        self.assertEqual(report["numericAnomalies"]["ELEVATION"],1)

    def test_fid_code_conflict_kept_in_review(self):
        doc = stage("bolzano_lakes",props={"ID":9999})
        result, report = enrich_staged(doc)
        self.assertFalse(result["entities"][0]["providerRecordCodes"]["verifiedAgainstFid"])
        self.assertEqual(report["numericAnomalies"]["id_fid_mismatch"],1)

    def test_source_g2_or_subtype_is_rejected_without_exception(self):
        doc = stage("arpav_water_surfaces")
        doc["entities"][0]["quality"]["gate"] = "G2"
        with self.assertRaisesRegex(ValueError, "bypass"):
            enrich_staged(doc)
        doc = stage("arpav_water_surfaces")
        doc["entities"][0]["subtype"] = "lake"
        with self.assertRaisesRegex(ValueError, "must not assert"):
            enrich_staged(doc)
        doc=stage("arpav_water_surfaces")
        doc["isPublished"]=True
        with self.assertRaises(ValueError):
            enrich_staged(doc)

    def test_area_disagreement_is_a_diagnostic_not_merge_authority(self):
        doc=stage("bolzano_lakes",props={"AREA":1000})
        result,_=enrich_staged(doc)
        e=result["entities"][0]
        self.assertGreater(e["providerAreaDifferencePct"],25)
        self.assertTrue(e["quality"]["providerAreaDifferenceReview"])
        self.assertIsNone(e["subtype"])

    def test_repeat_samples_stable_twice_but_not_permanently(self):
        a=stage("arpav_water_surfaces")
        b=deepcopy(a)
        audit=audit_source_replays(a,b)
        self.assertEqual(audit["sameFidCount"],1)
        self.assertTrue(audit["identifiersStableOverTwoSamples"])
        self.assertFalse(audit["longTermIdStabilityVerified"])
        b["entities"][0]["sourcePropertiesRaw"]["tipo"]="Invaso"
        audit=audit_source_replays(a,b)
        self.assertEqual(audit["conflicts"],["idrografia_specchio_acqua.277"])
        self.assertFalse(audit["identifiersStableOverTwoSamples"])

    def test_name_spatial_overlap_remains_only_a_review_candidate(self):
        official,_=enrich_staged(stage("arpav_water_surfaces"))
        report=review_with_osm(official,osm_source())
        self.assertEqual(report["exactIdentifierCrosswalks"],0)
        self.assertEqual(len(report["candidateReviews"]),1)
        c=report["candidateReviews"][0]
        self.assertTrue(c["reviewOnly"])
        self.assertFalse(c["identityVerified"])
        self.assertFalse(c["classificationDisagreement"])
        self.assertEqual(c["osmId"],"way/222")

    def test_class_disagreement_is_recorded_but_does_not_change_osm(self):
        original=osm_source(subtype="lake")
        official,_=enrich_staged(stage("arpav_water_surfaces",
                                       props={"tipo":"Invaso"}))
        report=review_with_osm(official,original)
        self.assertTrue(report["candidateReviews"][0]["classificationDisagreement"])
        self.assertEqual(original["osmEntities"][0]["subtype"],"lake")

    def test_name_alone_or_bbox_alone_do_not_create_review_pair(self):
        official,_=enrich_staged(stage("arpav_water_surfaces"))
        self.assertEqual(len(review_with_osm(
            official,osm_source(name="Lago differente")
        )["candidateReviews"]),0)
        self.assertEqual(len(review_with_osm(
            official,osm_source(ring=OTHER)
        )["candidateReviews"]),0)
        self.assertEqual(normalized_name("LÀGO dI Misurìna"),
                         "lago di misurina")

    def test_end_to_end_remains_unpublished_and_crosswalk_free(self):
        sources={p:stage(p) for p in ("bolzano_lakes","arpav_water_surfaces")}
        enriched, report=run(sources,osm_snapshot=osm_source(),
                             earlier=deepcopy(sources))
        self.assertEqual(report["g2NewEntities"],0)
        self.assertEqual(report["crossSourceLinksPublished"],0)
        self.assertEqual(report["candidateReviewCount"],2)
        for p,doc in enriched.items():
            self.assertFalse(doc["isPublished"])
            self.assertFalse(doc["entities"][0]["quality"]["seoIndexable"])
            self.assertIsNone(doc["entities"][0]["subtype"])
            replay=report["providerReports"][p]["replayConsistency"]
            self.assertTrue(replay["identifiersStableOverTwoSamples"])


if __name__=="__main__":
    unittest.main()
