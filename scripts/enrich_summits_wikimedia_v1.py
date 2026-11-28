#!/usr/bin/env python3
"""Enrich Cima Becco GeoNames summits into source-verified G2 dossiers (staging only).

Use the existing summit G0/G1 snapshot and independently validated P1566 map.
Recheck P1566/P625 on full Wikidata entities, then require P18 Commons with
item-level media licensing and an itwiki extract whose pageprops match the QID.
Never infer ascents, routes, openings, boundaries or photograph dates.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha1
import json
from pathlib import Path
import re

from enrich_municipalities_v1 import (
    wd_entities, claim_coord, claim_string, claim_quantity,
    commons_files, wikipedia_intro, NON_PHOTO, PHOTO_EXT
)
from enrich_settlements_wikimedia_v1 import haversine
from import_summits_v1 import read_crosswalk

ROOT = Path(__file__).resolve().parents[1]
STAGE = "GEONAMES_SUMMITS_STAGING_V1"
OUT_CHANNEL = "GEONAMES_SUMMITS_G2_STAGING_V1"
QID = re.compile(r"^Q[1-9][0-9]*$")
WIKIDATA = "https://www.wikidata.org/wiki/"
CC0 = "CC0"


def wd_fact(value, source_id, source_url, at, unit=None):
    return {
        "value": value, "unit": unit, "sourceId": source_id,
        "sourceUrl": source_url, "licence": CC0,
        "retrievedAt": at, "sourceUpdatedAt": None,
        "validFrom": None, "validUntil": None,
        "method": "reported", "confidence": 0.9,
    }


def batches(rows, size=20):
    for offset in range(0, len(rows), size):
        yield rows[offset:offset + size]


def matches_identity(base, item, qid, max_km=2.0):
    """A crosswalk is not a substitute for checking Wikidata source claims."""
    ident = base.get("sourceIds", {}).get("geonames")
    if not ident or claim_string(item, "P1566") != str(ident):
        return False, "wikidata_P1566_mismatch"
    point = claim_coord(item)
    if not point or not base.get("geo", {}).get("point"):
        return False, "wikidata_P625_missing"
    km = haversine(point, base["geo"]["point"])
    if km > max_km:
        return False, "wikidata_P625_coordinates_conflict"
    if any(
        (c.get("mainsnak") or {}).get("datavalue", {}).get("value", {}).get("numeric-id") == 5
        for c in (item.get("claims", {}).get("P31") or [])
        if isinstance((c.get("mainsnak") or {}).get("datavalue", {}).get("value"), dict)
    ):
        return False, "wikidata_human_not_summit"
    return True, None


def add_aliases(entity, item):
    names = {(entity["name"].strip().casefold(), "")}
    variants = []
    for language, data in sorted((item.get("labels") or {}).items()):
        if language not in ("it", "de", "en", "fr", "rm", "lld"):
            continue
        label = data.get("value") if isinstance(data, dict) else None
        if not label or not isinstance(label, str) or len(label) > 110:
            continue
        key = (label.strip().casefold(), language)
        if key in names or label.strip().casefold() == entity["name"].strip().casefold():
            continue
        names.add(key)
        variants.append({"value": label.strip(), "language": language,
                         "sourceUrl": WIKIDATA + entity["sourceIds"]["wikidata"]})
    entity["localNames"] = variants[:18]


def enrich(stage, crosswalk, *, max_items=80, wd_getter=None,
           commons_getter=None, wiki_getter=None, retrieved_at=None):
    if stage.get("releaseChannel") != STAGE or stage.get("isPublished") is not False:
        raise ValueError("Only the existing G0/G1 summit staging catalog is accepted")
    if not isinstance(crosswalk, dict) or not isinstance(crosswalk.get("links"), list):
        raise ValueError("Expected audited P1566/P625 crosswalk")
    qmap = {}
    inverse = {}
    for link in crosswalk["links"]:
        ident, qid = str(link.get("geonameid", "")), link.get("qid")
        if not (link.get("verified") is True
                and link.get("identityMethod") == "exact_P1566_and_P625_coordinate"
                and link.get("wdtP1566") == ident
                and QID.fullmatch(str(qid or ""))
                and link.get("sourceUrl") == WIKIDATA + qid):
            raise ValueError("Crosswalk is not P1566/P625 audited")
        if (ident in qmap and qmap[ident] != qid) or (qid in inverse and inverse[qid] != ident):
            raise ValueError("Ambiguous Wikidata to GeoNames crosswalk")
        qmap[ident] = qid
        inverse[qid] = ident

    retrieved_at = retrieved_at or datetime.now(timezone.utc).isoformat()
    bases = [e for e in stage.get("entities", []) if
             e.get("kind") == "summit"
             and e.get("quality", {}).get("gate") == "G1"
             and not e.get("quality", {}).get("slugRequiresReview")
             and e.get("sourceIds", {}).get("geonames") in qmap][:max_items]
    review = Counter()
    examples = []
    enriched = []
    held_for_review = []
    for batch in batches(bases):
        qids = [qmap[e["sourceIds"]["geonames"]] for e in batch]
        try:
            items = wd_entities(qids, getter=wd_getter)
        except Exception as err:
            review["wikidata_unavailable"] += len(batch)
            examples.append({"step": "wikidata", "error": str(err)[:160]})
            continue
        images_needed = []
        for base in batch:
            qid = qmap[base["sourceIds"]["geonames"]]
            filename = claim_string(items.get(qid, {}), "P18")
            if filename and PHOTO_EXT.search(filename) and not NON_PHOTO.search(filename):
                images_needed.append(filename)
        try:
            images = commons_files(images_needed, getter=commons_getter)
        except Exception as err:
            images = {}
            examples.append({"step": "commons", "error": str(err)[:160]})
            review["commons_unavailable"] += len(images_needed)
        for base in batch:
            ident = base["sourceIds"]["geonames"]
            qid = qmap[ident]
            item = items.get(qid) or {}
            good, reason = matches_identity(base, item, qid)
            if not good:
                review[reason] += 1
                continue
            filename = claim_string(item, "P18")
            if not filename or not PHOTO_EXT.search(filename) or NON_PHOTO.search(filename):
                review["no_P18_photo"] += 1
                continue
            image = images.get(filename.replace(" ", "_"))
            if not image or not all((
                image.get("author"), image.get("licence"),
                image.get("sourceUrl"), image.get("url"),
                image.get("reuseAllowed"), image.get("subjectVerified"),
            )):
                review["no_licensed_commons_photo"] += 1
                continue
            title = ((item.get("sitelinks") or {}).get("itwiki") or {}).get("title")
            if not title:
                review["no_itwiki_article"] += 1
                continue
            try:
                article = wikipedia_intro(title, qid, getter=wiki_getter)
            except Exception as err:
                article = None
                examples.append({"step": "wikipedia", "qid": qid, "error": str(err)[:160]})
            if not article or not article.get("text") or len(article["text"]) < 120:
                review["no_verified_wikipedia_excerpt"] += 1
                continue
            entity = deepcopy(base)
            entity["sourceIds"]["wikidata"] = qid
            entity["sourceIds"]["wikidataVerifiedBy"] = "P1566+P625"
            entity["geo"]["wikidataPointVerifiedAt"] = retrieved_at
            add_aliases(entity, item)
            entity["facts"]["wikidataIdentityVerified"] = wd_fact(
                True, "wikidata:" + qid + ":P1566+P625",
                WIKIDATA + qid, retrieved_at)
            # Wikidata P2044 is a separately reported elevation, not an overwrite
            # of GeoNames 's' surveyed or 'd' estimated altitude.
            alternative = claim_quantity(item, "P2044", "Q11573", -500, 9000)
            if alternative is not None:
                entity["facts"]["wikidataElevationReportedM"] = wd_fact(
                    round(alternative, 2), "wikidata:" + qid + ":P2044",
                    WIKIDATA + qid, retrieved_at, "m")
                first = entity["facts"].get("elevationM", {}).get("value")
                if isinstance(first, (float, int)) and abs(first - alternative) > 100:
                    entity["quality"]["elevationConflictReview"] = True
                    review["elevation_disagreement_gt_100m"] += 1
            image["retrievedAt"] = retrieved_at
            entity["media"] = [{**image,
                "id": "wikimedia:" + qid + ":P18:" + sha1(filename.encode()).hexdigest()[:12],
                "kind": "photo", "sourceId": "wikidata:" + qid + ":P18",
                "subjectMethod": "verified_P1566_P625_QID_P18",
                "subjectVerified": True, "reuseAllowed": True,
                "caption": "Fotografia documentata di " + entity["name"]}]
            article["retrievedAt"] = retrieved_at
            entity["textSources"] = [{k:v for k,v in article.items() if k!="linkedImages"}]
            entity["description"] = article["text"]
            entity["shortSummary"] = article["text"][:185]
            entity["editorialStatus"] = "enriched"
            # An altitude disagreement is a G1 review dossier, NOT G2.
            # Preserve its source-attributed facts in the staging artifact,
            # but never block the release of other independently valid cime.
            conflict = bool(entity["quality"].get("elevationConflictReview"))
            entity["quality"].update({
                "gate": "G1" if conflict else "G2",
                "candidateIndexable": not conflict,
                "seoIndexable": False, "reviewRequired": conflict,
                "photoSourceVerified": True, "textLicenseVerified": True,
                "identityMethod": "GeoNames_P1566_Wikidata_P625",
                "needsReleaseGate": True
            })
            if conflict:
                held_for_review.append(entity)
                review["altitude_conflict_held_G1"] += 1
            else:
                enriched.append(entity)
    if len(enriched) != len({e["id"] for e in enriched}):
        raise ValueError("Duplicate canonical summit IDs")
    if len(enriched) != len({e["slug"] for e in enriched}):
        raise ValueError("Duplicate summit slugs")
    result = {
        "schemaVersion": "1.0",
        "releaseChannel": OUT_CHANNEL,
        "isPublished": False,
        "generatedAt": retrieved_at,
        "entities": sorted(enriched, key=lambda e:e["id"]),
        "heldEntities": sorted(held_for_review, key=lambda e:e["id"])
    }
    report = {
        "eligible": len(bases), "enrichedG2": len(enriched),
        "heldForReviewG1": len(held_for_review),
        "quality": {"indexableNow": 0, "publishedNow": 0},
        "heldReasons": dict(sorted(review.items())),
        "reviewExamples": examples[:15],
        "withPhoto": sum(bool(e["media"]) for e in enriched),
        "withText": sum(bool(e["textSources"]) for e in enriched),
        "withElevationDisagreement": sum(
            bool(e["quality"].get("elevationConflictReview")) for e in held_for_review)
    }
    return result, report


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument("--wikidata-map", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--max-items", type=int, default=80)
    args=parser.parse_args()
    stage=json.loads(args.stage.read_text(encoding="utf-8"))
    crosswalk=json.loads(args.wikidata_map.read_text(encoding="utf-8"))
    doc, report=enrich(stage,crosswalk,max_items=args.max_items)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(doc,sort_keys=True,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    args.report.write_text(json.dumps(report,sort_keys=True,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
