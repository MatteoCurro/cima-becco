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
    # Intentionally do not copy title, field values, contact details or media URLs.
    return {"caiId": fid, "fieldEntries": len(data["fields"]),
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
    args = p.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2)
                           + "\n", encoding="utf-8")
    print(json.dumps({
        "attempted": len(SAMPLE_IDS), "succeeded": result["successful"],
        "fieldNames": len(result["fieldNames"]),
        "populatedFieldNames": len(result["fieldNamesWithValues"]),
        "errors": result["errors"], "valuesExported": False,
    }, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
