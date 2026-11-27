#!/usr/bin/env python3
"""CAI refuge media candidate registry: structure only, no rights inferred.

The CAI details can contain media[] records with original_url but without
verified attribution/license. Retain their stable provider IDs and counts for
future rights-aware enrichment; never store URLs/file names/copyright
unknowns in a public artifact, and never conflate a CAI subject with an OSM
entity before identity review. No network access.
"""
from __future__ import annotations
import json
import re
from pathlib import Path
import argparse

ROOT = Path(__file__).resolve().parents[1]
UUID_RE = re.compile(r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$")
MEDIA_TYPES = {"image/jpeg", "image/png", "image/webp", "image/avif", "image/tiff"}


def convert_media(detail):
    if not isinstance(detail, dict):
        raise ValueError("CAI detail non valido")
    cai_id = detail.get("id_cai")
    if isinstance(cai_id, bool) or not isinstance(cai_id, (str, int)) or not str(cai_id).isdigit():
        raise ValueError("CAI detail senza id_cai")
    medias = detail.get("media", [])
    if not isinstance(medias, list):
        raise ValueError("CAI media deve essere array")
    candidates, seen, rejected = [], set(), []
    for i, item in enumerate(medias):
        if not isinstance(item, dict):
            rejected.append({"position": i, "reason": "invalid_shape"})
            continue
        asset_id = item.get("uuid")
        if not isinstance(asset_id, str) or not UUID_RE.fullmatch(asset_id):
            rejected.append({"position": i, "reason": "no_stable_asset_uuid"})
            continue
        asset_id = asset_id.lower()
        if asset_id in seen:
            rejected.append({"position": i, "reason": "duplicate_asset_uuid"})
            continue
        seen.add(asset_id)
        mime = item.get("mime_type")
        if mime not in MEDIA_TYPES:
            rejected.append({"position": i, "reason": "unsupported_media_type"})
            continue
        candidates.append({
            "assetId": "cai:media:" + asset_id,
            "sourceId": "cai:shelter:" + str(cai_id),
            "sourceMediaUuid": asset_id,
            "mediaType": "photo_candidate",
            "mimeType": mime,
            "providedOriginalUrl": isinstance(item.get("original_url"), str)
                                   and item["original_url"].startswith("https://"),
            "providedPreviewUrl": isinstance(item.get("preview_url"), str)
                                  and item["preview_url"].startswith("https://"),
            "subjectId": None,
            "subjectResolutionStatus": "requires_cai_osm_identity_review",
            "subjectVerification": "not_yet_verified",
            "author": None,
            "licence": None,
            "sourceRights": "not_determined",
            "embedPermission": False,
            "publicationStatus": "RIGHTS_BLOCKED",
            "mediaDownloaded": False,
            "sourceFetchedAt": None,
            "sourceUpdatedAt": None,
        })
    return {
        "schemaVersion": "1.0",
        "status": "RESTRICTED_MEDIA_CANDIDATES_ONLY",
        "caiId": str(cai_id),
        "sourceLicenceApproved": False,
        "readyToPublish": False,
        "candidates": candidates,
        "rejected": rejected,
        "summary": {
            "mediaRowsSeen": len(medias),
            "candidateImages": len(candidates),
            "rejected": len(rejected),
            "downloaded": 0,
            "licensedForPublication": 0,
            "verifiedSubjects": 0,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True,
                   help="Restricted CAI detail JSON (not a public repository file)")
    p.add_argument("--out", type=Path, default=ROOT / "build" /
                   "restricted-cai" / "media-review.json")
    args = p.parse_args()
    detail = json.loads(args.input.read_text(encoding="utf-8"))
    report = convert_media(detail)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
                        + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], sort_keys=True))


if __name__ == "__main__":
    main()
