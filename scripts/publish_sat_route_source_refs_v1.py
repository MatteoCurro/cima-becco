#!/usr/bin/env python3
"""Publish only source-identity-aligned SAT facts onto EXISTING OSM route pages.

G1 informational enrichment, not route geometries, route safety or ferrata
classification. Explicit gate: original SAT E/O code == OSM reg_ref, SAT
operator/source, difficulty exact, unique identities and bidirectional
geometry consistency. Uses immutable GitHub Actions pilot snapshots.
"""
from __future__ import annotations

import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "build/trail-sat-verified-references-v1.json"
CHANNEL = "SAT_VERIFIED_ROUTE_SOURCE_REFERENCE_G1_V1"
SOURCE_PAGE = "https://www.sat.tn.it/sentieri/mappa-sentieri/"
SAT_OP = "Società degli Alpinisti Tridentini"
METRIC_NAMES = {
    "elevationStartReportedM", "elevationEndReportedM",
    "elevationMinReportedM", "elevationMaxReportedM",
    "lengthPlanimetricReportedM", "lengthInclinedReportedM",
    "durationOutReportedMin", "durationBackReportedMin",
}
SLUG = re.compile(r"^osm-hiking-[1-9][0-9]*$")


def canonical_hash(source):
    return sha256(json.dumps(source, ensure_ascii=False, sort_keys=True,
                            separators=(",", ":")).encode("utf-8")).hexdigest()


def publish(sat, sat_zip, osm, osm_source, candidates, manifest):
    if (sat.get("releaseChannel") != "SAT_TRAILS_TYPED_SOURCE_G0_V1" or
        osm.get("releaseChannel") != "OSM_TRAIL_PHYSICAL_GRAPH_G0_STAGING_V1" or
        candidates.get("releaseChannel") != "TRAIL_SAT_OSM_CROSSWALK_CANDIDATES_G0_V1"):
        raise ValueError("Wrong source audit channels; no G1 publishing")
    if any(x.get("isPublished") is not False for x in (sat, osm, candidates)):
        raise ValueError("Only original G0 source audits accepted")
    if not (sha256(sat_zip).hexdigest() == sat.get("sourceArchiveSha256") ==
            candidates.get("sourceArchiveSha256")):
        raise ValueError("SAT source fingerprint mismatch")
    if not (canonical_hash(osm_source) == osm.get("sourceSnapshotSha256") ==
            candidates.get("osmSourceSnapshotSha256")):
        raise ValueError("OSM source fingerprint mismatch")
    if (not isinstance(manifest.get("lookup"), dict) or
        not isinstance(sat.get("records"), list) or
        not isinstance(candidates.get("candidates"), list) or
        not isinstance(osm_source.get("elements"), list)):
        raise ValueError("Incomplete source manifest or audit")
    if sat.get("quality", {}).get("osmCrosswalkVerified") is not False:
        raise ValueError("SAT source snapshot has unexpected crosswalk status")

    sat_numbers = Counter(r.get("sourceIds", {}).get("satTrailNumberReported")
                          for r in sat["records"])
    sat_by_number = {
        r["sourceIds"]["satTrailNumberReported"]: r
        for r in sat["records"] if r.get("sourceIds", {}).get("satTrailNumberReported")
    }
    raw_relations = {
        f"relation/{r['id']}": r for r in osm_source["elements"]
        if r.get("type") == "relation" and type(r.get("id")) is int
    }
    route_type = {f"relation/{r['osmRelationId']}": r.get("routeType")
                  for r in osm["routeRelations"]}
    candidates_by_sat = Counter(
        x["sourceIds"]["satSourceNumber"] for x in candidates["candidates"]
        if x.get("reviewStatus") != "geometry_conflict")
    candidates_by_osm = Counter(
        x["sourceIds"]["osmSourceId"] for x in candidates["candidates"]
        if x.get("reviewStatus") != "geometry_conflict")

    accepted = {}
    deferred = []
    held = Counter()
    for candidate in candidates["candidates"]:
        ids = candidate.get("sourceIds") or {}
        number = ids.get("satSourceNumber")
        relation_id = ids.get("osmSourceId")
        if (candidate.get("targetKind") != "osm_route_relation" or
            candidate.get("reviewStatus") == "geometry_conflict"):
            held["geometry_or_source_type_not_validated"] += 1
            continue
        if (not isinstance(number, str) or sat_numbers[number] != 1 or
            not isinstance(relation_id, str) or
            candidates_by_sat[number] != 1 or candidates_by_osm[relation_id] != 1):
            held["non_unique_identity"] += 1
            continue
        row = sat_by_number[number]
        relation = raw_relations.get(relation_id)
        if (not relation or row.get("quality", {}).get("requiresReview") or
            route_type.get(relation_id) != "hiking"):
            held["source_quality_or_relation_type"] += 1
            continue
        tags = relation.get("tags") or {}
        original_difficulty = (row.get("originalDifficulty") or {}).get("value")
        if not (tags.get("reg_ref") == number and
                tags.get("operator") == SAT_OP and
                isinstance(tags.get("source"), str) and
                tags["source"].startswith("SAT;") and
                tags.get("cai_scale") == original_difficulty):
            held["original_tag_identity_or_difficulty_conflict"] += 1
            continue
        m = candidate.get("geometryEvidence") or {}
        if not (m.get("satSamples", 0) >= 8 and m.get("osmSamples", 0) >= 8 and
                min(m.get("satWithin40mFraction", 0),
                    m.get("osmWithin40mFraction", 0)) >= .9 and
                max(m.get("satP90DistanceM", 1e9),
                    m.get("osmP90DistanceM", 1e9)) <= 20):
            held["incomplete_or_inconsistent_geometry"] += 1
            continue
        if candidate.get("quality", {}).get("ambiguousCandidate"):
            held["ambiguous_candidate"] += 1
            continue
        slug = "osm-hiking-" + relation_id.split("/")[-1]
        if not SLUG.fullmatch(slug):
            held["invalid_route_slug"] += 1
            continue
        if slug not in manifest["lookup"]:
            deferred.append({"satRef":number, "osmRelationId":relation_id,
                             "reason":"catalog_route_not_present"})
            continue
        if slug in accepted:
            raise ValueError("Duplicate route source reference; fail closed")

        # Public G1 contains only valuable verified source facts, no KML,
        # raw OSM geometry, internal review queue or new canonical ID.
        facts = {
            k: v for k, v in row.get("facts", {}).items()
            if k in METRIC_NAMES and isinstance(v, dict) and
            isinstance(v.get("value"), (float, int)) and
            v.get("method") == "reported" and v.get("sourceUrl") == SOURCE_PAGE
        }
        if len(facts) != 8:
            held["source_facts_incomplete"] += 1
            continue
        accepted[slug] = {
            "routeSlug": slug,
            "sourceReference": {"sourceId": "SAT", "number": number,
                                "sourceUrl": SOURCE_PAGE, "licence": "ODbL 1.0",
                                "retrievedAt": sat.get("retrievedAt"),
                                "officialCatalogueSubtype": None},
            "identityEvidence": {
                "osmRelationId": relation_id,
                "osmSourceUrl": "https://www.openstreetmap.org/" + relation_id,
                "osmOriginalRegRef": tags["reg_ref"],
                "operatorOriginal": tags["operator"],
                "osmSourceReported": tags["source"],
                "originalDifficultyExact": True,
                "geometryComparison": m,
                "method": "exact_sat_reg_ref_operator_source_difficulty_and_bilateral_geometry_v1",
                "sourceReferenceVerified": True,
            },
            "originalDifficulty": row["originalDifficulty"],
            "sourceContext": row.get("originalContext"),
            "reportedFacts": facts,
            "quality": {
                "gate": "G1", "seoIndexable": False,
                "satSourceReferenceVerified": True,
                "osmRelationMembershipIncomplete": candidate.get("osmRelationMembershipIncomplete"),
                "osmRelationOperationallyVerified": False,
                "routeContinuityVerified": False,
                "traversableVerified": False, "ferrataSubtypeVerified": False,
                "accessToSummitOrHutVerified": False,
                "canonicalEntityMergePerformed": False,
            },
        }
    if not accepted:
        raise ValueError("No SAT source references passed strict G1 verification")
    return {
        "schemaVersion":"1.0",
        "releaseChannel": CHANNEL,
        "isPublished": True,
        "newCanonicalPagesCreated": False,
        "seoIndexable": False,
        "routeCatalogueModified": False,
        "sourceName": "Società degli Alpinisti Tridentini",
        "sourceArchiveSha256": sat["sourceArchiveSha256"],
        "osmSourceSnapshotSha256": osm["sourceSnapshotSha256"],
        "bbox": osm["bbox"],
        "sourceRetrievalTimestamp": sat.get("retrievedAt"),
        "quality": {"gate": "G1", "sourceIdentityReferenceVerified": True,
                    "safetyVerified": False, "routingAllowed": False,
                    "ferrataSubtypeVerified": False, "newPermalinksAllowed": False},
        "counts": {
            "verifiedLiveSourceReferences": len(accepted),
            "verifiedButNoLiveRoute": len(deferred),
            "heldForReview": sum(held.values()),
        },
        "records": dict(sorted(accepted.items())),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--sat", required=True, type=Path)
    p.add_argument("--sat-zip", required=True, type=Path)
    p.add_argument("--osm", required=True, type=Path)
    p.add_argument("--osm-source", required=True, type=Path)
    p.add_argument("--crosswalk", required=True, type=Path)
    p.add_argument("--manifest", required=True, type=Path)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--publish", action="store_true",
                   help="Required if writing under public/; never creates new URL")
    args = p.parse_args()
    if (ROOT/"public") in args.out.resolve().parents and not args.publish:
        raise ValueError("Public release requires explicit --publish")
    doc = publish(
        json.loads(args.sat.read_text(encoding="utf-8")), args.sat_zip.read_bytes(),
        json.loads(args.osm.read_text(encoding="utf-8")),
        json.loads(args.osm_source.read_text(encoding="utf-8")),
        json.loads(args.crosswalk.read_text(encoding="utf-8")),
        json.loads(args.manifest.read_text(encoding="utf-8")),
    )
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc, ensure_ascii=False, sort_keys=True,
                                  separators=(",", ":")) + "\n", encoding="utf-8")
    print(json.dumps(doc["counts"], ensure_ascii=False, sort_keys=True))


if __name__=="__main__":
    try:
        main()
    except (ValueError, OSError) as exc:
        sys.exit(str(exc))
