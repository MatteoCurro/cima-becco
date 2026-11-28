#!/usr/bin/env python3
"""Audit *independent* official regional lake facts and OSM review candidates.

Accepts G0 artifacts only. Writes QA snapshots outside public/; never
promotes an official layer record to an atlas entity, G1 or G2.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from normalize_official_lake_wfs_facts_v1 import (
    enrich_staged, audit_source_replays, review_with_osm,
)

ROOT = Path(__file__).resolve().parents[1]
PROVIDERS = ("bolzano_lakes", "arpav_water_surfaces")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path, content):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def run(sources, *, osm_snapshot=None, earlier=None):
    report = {
        "releaseChannel": "OFFICIAL_LAKE_WFS_FACT_AUDIT_G0_V1",
        "isPublished": False, "seoIndexable": False, "g2NewEntities": 0,
        "crossSourceLinksPublished": 0, "providerReports": {},
        "candidateReviews": [], "sourceExamples": {},
    }
    outputs = {}
    for provider in PROVIDERS:
        doc = sources[provider]
        if doc.get("sourceProvider") != provider:
            raise ValueError("Provider/source artifact mismatch")
        enriched, facts_report = enrich_staged(doc)
        outputs[provider] = enriched
        source_report = {**facts_report, "featuresRead": len(doc.get("entities", []))}
        if earlier and provider in earlier:
            source_report["replayConsistency"] = audit_source_replays(
                earlier[provider], doc,
            )
        else:
            source_report["replayConsistency"] = None
        if osm_snapshot:
            compare = review_with_osm(enriched, osm_snapshot)
            report["candidateReviews"].extend(compare["candidateReviews"])
            source_report["possibleSamePlaceReviewOnly"] = len(compare["candidateReviews"])
            source_report["exactIdentifierCrosswalks"] = compare["exactIdentifierCrosswalks"]
        report["providerReports"][provider] = source_report
        report["sourceExamples"][provider] = [
            {
                "fid": e.get("sourceFeatureId"),
                "sourceNames": e.get("providerNames"),
                "rawClass": e.get("providerWaterClassRaw"),
                "factKeys": sorted(e.get("facts", {})),
                "sourceRecordCodes": e.get("providerRecordCodes"),
            }
            for e in enriched.get("entities", [])[:2]
        ]
    report["candidateReviews"].sort(key=lambda x: (
        x["provider"], x["officialFid"], str(x["osmId"])
    ))
    report["candidateReviewCount"] = len(report["candidateReviews"])
    return outputs, report


def main():
    p = argparse.ArgumentParser()
    for provider in PROVIDERS:
        p.add_argument("--" + provider.replace("_", "-"), type=Path, required=True)
        p.add_argument("--previous-" + provider.replace("_", "-"), type=Path)
    p.add_argument("--osm-snapshot", type=Path)
    p.add_argument("--out", type=Path,
                   default=ROOT / "build/audit-official-lake-facts-g0")
    args = p.parse_args()
    sources = {provider: read_json(getattr(args, provider)) for provider in PROVIDERS}
    previous = {}
    for provider in PROVIDERS:
        path = getattr(args, "previous_" + provider)
        if path is not None:
            previous[provider] = read_json(path)
    osm = read_json(args.osm_snapshot) if args.osm_snapshot else None
    enriched, report = run(sources, osm_snapshot=osm, earlier=previous)
    for provider, payload in enriched.items():
        write_json(args.out / (provider + "-normalized-g0.json"), payload)
    write_json(args.out / "official-lake-facts-audit.json", report)
    print(json.dumps({
        "acceptedSourceFacts": {provider: item["normalizedFeatures"]
                                for provider, item in report["providerReports"].items()},
        "candidateReviews": report["candidateReviewCount"],
        "sourceReplay": {provider: item["replayConsistency"] and
                         item["replayConsistency"]["identifiersStableOverTwoSamples"]
                         for provider, item in report["providerReports"].items()},
        "published": 0, "crossSourceLinksPublished": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
