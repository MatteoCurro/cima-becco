#!/usr/bin/env python3
"""Prepare incremental CAI updates from the documented updatedAt provider map.

The live probe observed a JSON object of 764 numeric *internal source keys*
and string values. Those keys are NOT id_cai. Parse timestamps strictly;
never delete missing records or overwrite good data after a fetch error.
Rights, published type and source-ID linkage remain release blockers.
No HTTP, no scheduling, no public output.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
INTERNAL_ID = re.compile(r"^[1-9]\d{0,14}$")


def parse_time(value):
    if not isinstance(value, str):
        raise ValueError("Timestamp CAI non testuale")
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Timestamp CAI non ISO-8601") from error
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("Timestamp CAI senza fuso orario")
    return dt.astimezone(timezone.utc)


def validate_revision_map(doc):
    if not isinstance(doc, dict) or not doc:
        raise ValueError("updatedAt vuoto/invalido: nessun checkpoint modificato")
    results = {}
    for internal_key, stamp in doc.items():
        if not isinstance(internal_key, str) or not INTERNAL_ID.fullmatch(internal_key):
            raise ValueError("updatedAt usa una chiave interna non valida")
        moment = parse_time(stamp)
        results[internal_key] = moment
    return results


def plan_delta(previous, current, *, complete_snapshot=False, known_cai_ids=None):
    """Return staging-only IDs. Never infer deleted from a missing key."""
    existing = validate_revision_map(previous) if previous is not None else {}
    observed = validate_revision_map(current)
    known_cai_ids = known_cai_ids or {}
    if not isinstance(known_cai_ids, dict):
        raise ValueError("Registry interno→CAI invalido")
    new_ids, newer, equal, backwards = [], [], [], []
    for key in sorted(observed, key=int):
        if key not in existing:
            new_ids.append(key)
        elif observed[key] > existing[key]:
            newer.append(key)
        elif observed[key] < existing[key]:
            backwards.append(key)
        else:
            equal.append(key)
    absent = sorted(set(existing) - set(observed), key=int)
    # Even if a verified full snapshot indicates absence, treat as
    # "needs tombstone verification" — never directly erase a published page.
    current_to_cai = {}
    for key in new_ids + newer:
        cai_id = known_cai_ids.get(key)
        current_to_cai[key] = str(cai_id) if cai_id is not None else None
    unresolved = sorted((key for key, val in current_to_cai.items() if val is None), key=int)
    return {
        "schemaVersion": "1.0",
        "source": "CAI /api/v1/shelters/updatedAt",
        "status": "RESTRICTED_STAGING_ONLY",
        "updatedAtKeyMeaning": "provider_internal_id_NOT_id_cai",
        "licenceApproved": False, "publishingEnabled": False,
        "deleteOperations": 0, "automaticContentMerge": False,
        "newProviderInternalIds": new_ids,
        "changedProviderInternalIds": newer,
        "regressedTimestampIds": backwards,
        "absentSincePreviousProviderIds": absent,
        "missingIdCaiMappings": unresolved,
        "caiIdentityCandidates": current_to_cai,
        "summary": {
            "previousRecords": len(existing),
            "currentRecords": len(observed),
            "new": len(new_ids),
            "updated": len(newer),
            "unchanged": len(equal),
            "regressed": len(backwards),
            "absent": len(absent),
            "absentTombstonesVerified": 0,
            "completeSnapshotClaimed": bool(complete_snapshot),
            "unresolvedInternalToCaiId": len(unresolved),
            "readyToFetchDetails": bool(
                not backwards and not absent and not unresolved
                and known_cai_ids and (new_ids or newer)),
            "readyForPublication": False,
        },
        "warnings": [
            "Do not resolve internal keys as CAI id_cai; use explicit registry",
            "Missing IDs may be partial API errors; never delete automatically",
            "Timestamp regressions require manual review",
            "Fetch and publication require separate rights and identity gates",
        ],
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", type=Path, required=True,
                   help="Restricted raw CAI updatedAt JSON, not a public file")
    p.add_argument("--previous", type=Path)
    p.add_argument("--identity-map", type=Path,
                   help="Restricted mapping of provider internal ID to id_cai")
    p.add_argument("--complete-snapshot", action="store_true")
    p.add_argument("--out", type=Path, default=ROOT / "build" /
                   "restricted-cai" / "delta-review.json")
    args = p.parse_args()
    previous = json.loads(args.previous.read_text()) if args.previous else None
    current = json.loads(args.current.read_text())
    identities = json.loads(args.identity_map.read_text()) if args.identity_map else None
    result = plan_delta(previous, current, complete_snapshot=args.complete_snapshot,
                        known_cai_ids=identities)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                   indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
