"""No G0 regional WFS records may masquerade as G2 lake entities or URLs."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))
from test_normalize_official_lake_wfs_facts_v1 import stage
from normalize_official_lake_wfs_facts_v1 import enrich_staged
from publish_natural_lake_census_map_v1 import build, source_to_map_record, PUBLIC_CHANNEL
from import_official_lake_wfs_v1 import CHANNEL, PROVIDERS


def fixtures():
    source={}
    held={}
    registry={
        "releaseChannel":"OFFICIAL_LAKE_CENSUS_SOURCE_REGISTRY_G0_V1",
        "isPublished":False,"providers":{},
    }
    for provider in sorted(PROVIDERS):
        src,_=enrich_staged(stage(provider))
        source[provider]=src
        review=deepcopy(src)
        review["entities"]=[]
        review["geometryReviewOnly"]=True
        held[provider]=review
        registry["providers"][provider]={
            "validPolygons":1,"geometryReviewOnly":0,"observedSourceIds":1
        }
    return source,held,registry


class CensusMapTest(unittest.TestCase):
    def test_catalog_is_only_map_and_has_no_canonical_entities(self):
        source,held,registry=fixtures()
        output=build(source,held,registry)
        self.assertEqual(output["releaseChannel"],PUBLIC_CHANNEL)
        self.assertTrue(output["sourceOnlyCatalogue"])
        self.assertFalse(output["individualPagesAllowed"])
        self.assertFalse(output["isPublishedG2"])
        self.assertFalse(output["seoIndexable"])
        self.assertTrue(output["sourceRecordsAreNotDeduplicatedPhysicalLakes"])
        self.assertEqual(output["shownPolygons"],2)
        self.assertEqual(output["canonicalAtlasEntitiesAdded"],0)
        self.assertEqual(output["crossSourceIdentityLinksAdded"],0)
        self.assertTrue(output["sourcePreviewPagesNoindexAllowed"])
        self.assertEqual(output["sourcePreviewsReady"],2)
        for row in output["records"]:
            self.assertTrue(row["previewOnly"])
            self.assertTrue(row["previewNoindex"])
            self.assertRegex(row["previewSlug"],r"^[a-z0-9]+(?:-[a-z0-9]+)*-[a-f0-9]{7}$")
            self.assertNotIn(row["sourceFeatureId"],row["previewSlug"])
            self.assertNotIn("sameAs",row)
        for row in output["records"]:
            self.assertEqual(row["qualityGate"],"G0")
            self.assertFalse(row["canonicalSubtypeVerified"])
            self.assertFalse(row["seoIndexable"])
            self.assertIn(row["provider"],PROVIDERS)
            self.assertIsNotNone(row["geom"])
            self.assertGreater(row["derivedMappedKm2"],0)
            self.assertNotIn("slug",row)
            self.assertNotIn("relations",row)
            self.assertNotIn("media",row)
            self.assertNotIn("geo",row)
            self.assertNotIn("bathable",json.dumps(row).lower())
            self.assertTrue(row["sourceKey"].endswith(row["sourceFeatureId"]))

    def test_provider_names_and_classes_not_promoted(self):
        source,held,registry=fixtures()
        out=build(source,held,registry)
        bz=next(x for x in out["records"] if x["provider"]=="bolzano_lakes")
        ar=next(x for x in out["records"] if x["provider"]=="arpav_water_surfaces")
        self.assertEqual({n["lang"] for n in bz["names"]},{"it","de"})
        self.assertEqual(bz["name"],"Lago di Misurina")
        self.assertEqual(bz["agencyReportedElevationM"],1750)
        self.assertEqual(ar["rawClass"],"Lago")
        self.assertFalse(ar["canonicalSubtypeVerified"])
        self.assertEqual(bz["agencyReportedVolumeM3"],4000000)
        self.assertEqual(bz["agencyReportedWidthM"],330)
        self.assertEqual(bz["agencyReportedLengthM"],700)
        self.assertIsNone(bz["municipalityReported"])
        self.assertNotIn("subtype",ar)

    def test_held_geometry_has_count_but_never_polygon_or_point(self):
        source,held,registry=fixtures()
        provider="arpav_water_surfaces"
        entry=deepcopy(held[provider]["entities"])
        self.assertEqual(entry,[])
        held[provider]["entities"]=[{
            "sourceFeatureId":"idrografia_specchio_acqua.999",
            "quality":{"gate":"G0","seoIndexable":False},
            "sourcePropertiesRaw":{"nome":"Specchio non cartografabile"},
        }]
        registry["providers"][provider]["geometryReviewOnly"]=1
        registry["providers"][provider]["observedSourceIds"]=2
        out=build(source,held,registry)
        self.assertEqual(out["shownPolygons"],2)
        self.assertEqual(out["geometryPendingReview"],1)
        self.assertFalse(any("999" in x["sourceKey"] for x in out["records"]))

    def test_rejects_bad_gate_canonical_subtype_or_relations(self):
        source,held,registry=fixtures()
        for name, value in (
            ("quality",{"gate":"G2","seoIndexable":True}),
            ("subtype","lake"),
            ("relations",[{"type":"near","target":"a"}]),
        ):
            changed=deepcopy(source)
            changed["bolzano_lakes"]["entities"][0][name]=value
            with self.subTest(name=name),self.assertRaises(ValueError):
                build(changed,held,registry)

    def test_rejects_wrong_source_counts_or_cross_provider_identity(self):
        source,held,registry=fixtures()
        bad=deepcopy(registry)
        bad["providers"]["bolzano_lakes"]["observedSourceIds"]=2
        with self.assertRaises(ValueError):
            build(source,held,bad)
        broken=deepcopy(source)
        broken["arpav_water_surfaces"]["entities"][0]["sourceIds"]={
            "bolzano_lakes":"Lakes.7322",
        }
        with self.assertRaises(ValueError):
            build(broken,held,registry)

    def test_rejects_false_area_and_invalid_geom(self):
        source,held,registry=fixtures()
        bad=deepcopy(source)
        bad["bolzano_lakes"]["entities"][0]["facts"]["providerMappedWaterSurfaceKm2"]["value"]=1e12
        with self.assertRaises(ValueError):
            build(bad,held,registry)
        bad=deepcopy(source)
        bad["arpav_water_surfaces"]["entities"][0]["geo"]["area"]={"type":"Point","coordinates":[1,2]}
        with self.assertRaises(ValueError):
            build(bad,held,registry)

    def test_rejects_pseudo_name_or_duplicate_homonym_uses_stable_suffix(self):
        source,held,registry=fixtures()
        p="arpav_water_surfaces"
        bad=deepcopy(source)
        bad[p]["entities"][0]["providerNames"]=[{"language":"it","value":"N.D."}]
        blank=build(bad,held,registry)
        r=next(x for x in blank["records"] if x["provider"]==p)
        self.assertIsNone(r["previewSlug"])
        self.assertFalse(r["previewOnly"])
        # Same source FID and name give a stable URL even after refresh.
        a=build(source,held,registry)
        b=build(deepcopy(source),deepcopy(held),deepcopy(registry))
        self.assertEqual([x["previewSlug"] for x in a["records"]],
                         [x["previewSlug"] for x in b["records"]])

    def test_missing_name_keeps_null_and_no_invented_name(self):
        source,held,registry=fixtures()
        source["arpav_water_surfaces"]["entities"][0]["providerNames"]=[]
        out=build(source,held,registry)
        e=next(e for e in out["records"] if e["provider"]=="arpav_water_surfaces")
        self.assertIsNone(e["name"])
        self.assertIsNone(e["previewSlug"])
        self.assertFalse(e["previewOnly"])
        self.assertEqual(e["names"],[])
        self.assertFalse(out["individualPagesAllowed"])


if __name__=="__main__":
    unittest.main()
