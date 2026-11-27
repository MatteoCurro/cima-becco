#!/usr/bin/env python3
"""One-off bounded CAI detail SHAPE audit. Never prints or stores source values.

Tests whether the PR8-discovered field names are actually populated and how
their types are encoded, including the category/type fields needed to avoid
confusing refuges with bivouacs. No database, no CMS, no raw artifact upload.
No other HTTP endpoints; no automated recurrence.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BASE = "https://rifugi.cai.it/api/v1/shelters/"
UA = "CimaBecco-MetadataShapeAudit/0.1 (https://www.cimabecco.it; educational/research)"
# Previously captured in PR8; selected for candidate matches and a bivouac.
SAMPLE_IDS = ("922005301", "922001801", "921800106", "921200201")


def shape(value):
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, str):
        return "str"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return "other"


def summarize_detail(data):
    if not isinstance(data, dict) or not isinstance(data.get("fields"), list):
        raise ValueError("Il detail CAI non contiene fields[]")
    fid = str(data.get("id_cai", ""))
    if not fid.isdigit():
        raise ValueError("id_cai non valido")
    by_field = {}
    for item in data["fields"]:
        if not isinstance(item, dict) or not isinstance(item.get("name"), str):
            continue
        key = item["name"]
        obj = by_field.setdefault(key, {"count": 0, "valueTypes": Counter(),
                                        "dataTypes": Counter(), "hasValue": 0,
                                        "hasUpdatedAt": 0})
        obj["count"] += 1
        obj["valueTypes"][shape(item.get("value"))] += 1
        obj["dataTypes"][shape(item.get("data"))] += 1
        if item.get("value") not in (None, "", [], {}):
            obj["hasValue"] += 1
        if item.get("updated_at"):
            obj["hasUpdatedAt"] += 1
    # Optional schema discovery: reveal ONLY key names and types for schedule,
    # never any dates/hours/persons or raw provider values.
    schedule_key_names = set()
    schedule_item_shapes = Counter()
    for item in data["fields"]:
        if isinstance(item, dict) and item.get("name") == "openingTime_contact":
            nested = item.get("data")
            if isinstance(nested, list):
                for child in nested[:30]:
                    schedule_item_shapes[shape(child)] += 1
                    if isinstance(child, dict):
                        schedule_key_names.update(k for k in child
                                                  if isinstance(k, str) and len(k) < 80
                                                  and k.replace("_", "").isalnum())
    media_key_names = set()
    media_custom_names = set()
    media_mimes = Counter()
    media_original_url_schemes = Counter()
    media_uuid_shapes = Counter()

    for item in (data.get("media") or [])[:12]:
        if isinstance(item, dict):
            mime = item.get("mime_type")
            media_mimes[str(mime)[:80]] += 1
            source = item.get("original_url")
            media_original_url_schemes[
                source.split(":", 1)[0].lower() if isinstance(source, str) and ":" in source
                else "missing_or_relative"
            ] += 1
            media_uuid_shapes["uuid_string" if isinstance(item.get("uuid"), str)
                              else "uuid_missing_or_other"] += 1
            media_key_names.update(k for k in item
                                   if isinstance(k, str) and len(k) < 80
                                   and k.replace("_", "").isalnum())
            custom = item.get("custom_properties")
            if isinstance(custom, dict):
                media_custom_names.update(k for k in custom
                                          if isinstance(k, str) and len(k) < 80
                                          and k.replace("_", "").isalnum())
    # Only publicly displayed structural category/status enum values;
    # no personal, contact, prices, hours, media or descriptions.
    classification = {
        item["name"]: item.get("value")
        for item in data["fields"]
        if isinstance(item, dict) and item.get("name") in ("type", "category", "status")
        and isinstance(item.get("value"), (str, int, bool))
        and len(str(item.get("value"))) < 120
    }
    # Intentionally do not copy title, field values, contact details or media URLs.
    return {"caiId": fid, "fieldEntries": len(data["fields"]),
            "publicClassificationEnums": classification,
            "openingTimeArrayElementTypes": dict(schedule_item_shapes),
            "openingTimeArrayFieldKeys": sorted(schedule_key_names),
            "mediaFieldKeys": sorted(media_key_names),
            "mediaCustomPropertyKeys": sorted(media_custom_names),
            "mediaMimeTypes": dict(sorted(media_mimes.items())),
            "mediaOriginalUrlSchemes": dict(sorted(media_original_url_schemes.items())),
            "mediaUuidShapes": dict(sorted(media_uuid_shapes.items())),
            "mediaCount": len(data.get("media") or []),
            "fields": [
                {"name": key, "count": v["count"], "valueTypes": dict(v["valueTypes"]),
                 "dataTypes": dict(v["dataTypes"]), "hasValue": v["hasValue"],
                 "hasUpdatedAt": v["hasUpdatedAt"]}
                for key, v in sorted(by_field.items())
            ], "rightsCleared": False, "publishedToAtlas": False}


def fetch_detail(code):
    if code not in SAMPLE_IDS:
        raise ValueError("CAI ID non autorizzato dal pilota")
    req = Request(BASE + code, headers={"User-Agent": UA,
                                      "Accept": "application/json"})
    with urlopen(req, timeout=35) as response:
        if response.status != 200:
            raise ValueError("HTTP " + str(response.status))
        payload = response.read(2_000_001)
        if len(payload) > 2_000_000:
            raise ValueError("CAI response oltre limite 2 MB")
    return json.loads(payload)


def summarize_updated_at(payload):
    """Only response structure, no CAI IDs/timestamps emitted."""
    if isinstance(payload, list):
        sample = payload[0] if payload else None
        return {"responseType": "array", "items": len(payload),
                "firstItemType": shape(sample),
                "firstItemKeys": sorted(sample) if isinstance(sample, dict) else []}
    if isinstance(payload, dict):
        data = payload.get("data")
        if not isinstance(data, list):
            data = payload.get("results")
        if not isinstance(data, list):
            data = []
        sample = data[0] if data else None
        numeric_keys = [key for key in payload if isinstance(key, str) and key.isdigit()]
        value_types = Counter(shape(value) for value in payload.values())
        stamp_formats = Counter()
        for value in payload.values():
            if not isinstance(value, str):
                stamp_formats["not_string"] += 1
                continue
            try:
                dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
                if dt.tzinfo is not None and dt.utcoffset() is not None:
                    stamp_formats["timezone_aware_iso"] += 1
                else:
                    stamp_formats["timezone_naive_iso"] += 1
            except ValueError:
                stamp_formats["not_iso_datetime"] += 1
        sample_value = next(iter(payload.values()), None)
        return {"responseType": "object",
                "topLevelKeyCount": len(payload),
                "numericTopLevelKeys": len(numeric_keys),
                "valueTypes": dict(sorted(value_types.items())),
                "timestampFormatCounts": dict(sorted(stamp_formats.items())),
                "firstValueObjectKeys": (sorted(sample_value)[:70]
                                         if isinstance(sample_value, dict) else []),
                "dataItems": len(data),
                "firstItemType": shape(sample),
                "firstItemKeys": sorted(sample) if isinstance(sample, dict) else []}
    return {"responseType": shape(payload), "unrecognized": True}


def probe_updated_at():
    url = BASE + "updatedAt"
    req = Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urlopen(req, timeout=35) as resp:
        if resp.status != 200:
            raise ValueError("Unexpected status " + str(resp.status))
        raw = resp.read(4_000_001)
        if len(raw) > 4_000_000:
            raise ValueError("updatedAt payload exceeds 4 MB")
    doc = json.loads(raw)
    return {"schemaVersion": "1.0", "source": url,
            "status": "ONE_OFF_SHAPE_ONLY", "fieldValuesIncluded": False,
            "rightsCleared": False, "apiResponseShape": summarize_updated_at(doc),
            "fetchedAt": datetime.now(timezone.utc).isoformat()}


def run(codes=SAMPLE_IDS):
    records, errors = [], []
    for code in codes:
        try:
            payload = fetch_detail(str(code))
            records.append(summarize_detail(payload))
        except Exception as exc:
            errors.append({"caiId": str(code), "errorType": type(exc).__name__})
    all_names = sorted({f["name"] for d in records for f in d["fields"]})
    populated = sorted({f["name"] for d in records for f in d["fields"]
                        if f["hasValue"]})
    return {
        "schemaVersion": "1.0", "status": "ONE_OFF_SHAPE_PROBE_ONLY",
        "fetchedAt": datetime.now(timezone.utc).isoformat(),
        "source": BASE, "fieldValuesIncluded": False,
        "rightsCleared": False, "mediaUrlsIncluded": False,
        "attemptedIds": list(codes), "successful": len(records),
        "fieldNames": all_names, "fieldNamesWithValues": populated,
        "summaries": records, "errors": errors,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, default=ROOT / "build" /
                   "cai-detail-shapes" / "summary.json")
    p.add_argument("--one", action="store_true",
                   help="One chosen previously-tested CAI ID, no bulk")
    p.add_argument("--updated-only", action="store_true",
                   help="Check only metadata shape of documented updatedAt endpoint")
    args = p.parse_args()
    if args.updated_only:
        result = probe_updated_at()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                          indent=2) + "\n", encoding="utf-8")
        print(json.dumps(result["apiResponseShape"], ensure_ascii=False))
        return
    result = run((SAMPLE_IDS[2],) if args.one else SAMPLE_IDS)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
                           + "\n", encoding="utf-8")
    print(json.dumps({
        "attempted": len(result["attemptedIds"]), "succeeded": result["successful"],
        "fieldNames": len(result["fieldNames"]),
        "populatedFieldNames": len(result["fieldNamesWithValues"]),
        "errors": result["errors"], "valuesExported": False,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
