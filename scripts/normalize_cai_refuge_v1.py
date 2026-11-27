#!/usr/bin/env python3
"""CAI detail -> restricted staging candidate facts (no network, no publication).

Reuse the already-tested PR8 API shape fields[]; never infer authorization to
republish. Unknown field names are reported for review but raw values are not
copied into publicly shareable audit reports. Input snapshots must remain in
restricted staging until license/privacy clearance.
"""
from __future__ import annotations
import argparse
from collections import Counter
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
RULES = ROOT / "scripts" / "cai_refuge_field_map_v1.json"
FIELD_REGISTRY = ROOT / "scripts" / "refuge_field_registry_v1.json"


def normalized(value, converter):
    if value is None:
        return None
    if converter in ("positive_int", "nonnegative_int", "year"):
        if isinstance(value, bool):
            return None
        if not isinstance(value, (int, str)):
            return None
        text = str(value).strip()
        if not re.fullmatch(r"-?\d+", text):
            return None
        n = int(text)
        if converter == "positive_int":
            return n if n > 0 else None
        if converter == "nonnegative_int":
            return n if n >= 0 else None
        return n if 1000 <= n <= 2100 else None
    if converter in ("reported_bool", "water_reported_not_potability"):
        if isinstance(value, bool):
            return value
        if value in (0, 1) and isinstance(value, int):
            return bool(value)
        if not isinstance(value, str):
            return None
        c = value.strip().casefold()
        if c in ("yes", "sì", "si", "true", "1"):
            return True
        if c in ("no", "false", "0"):
            return False
        return None
    if not isinstance(value, str):
        return None
    text = " ".join(value.split())
    if not text or text.casefold() in ("n.d.", "n/a", "unknown", "-1"):
        return None
    if converter == "https_url":
        return text if text.startswith("https://") and " " not in text and len(text) < 400 else None
    if converter == "email":
        return text if len(text) <= 160 and re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", text) else None
    if converter == "name_candidate_not_id":
        return {"label": text[:240], "resolutionStatus": "unresolved", "entityId": None}
    if converter in ("text", "source_text_with_rights_review"):
        return text[:5000]
    raise ValueError("Converter non implementato: " + converter)


def convert_detail(doc, rules, registry):
    if not isinstance(doc, dict) or not str(doc.get("id_cai", "")).isdigit():
        raise ValueError("Dettaglio CAI senza id_cai stabile")
    if not isinstance(doc.get("fields"), list):
        raise ValueError("Dettaglio CAI senza fields[] (non inferire dall'elenco ridotto)")
    code = str(doc["id_cai"])
    rule_by_name = {f["sourceField"]: f for f in rules["fields"]}
    if len(rule_by_name) != len(rules["fields"]):
        raise ValueError("Mapping CAI con sorgenti duplicate")
    known = {field["key"] for field in registry["fields"]}
    prefix = tuple(rules["sensitivePrefixes"])
    blocked = Counter()
    unmapped = Counter()
    converted = []
    for field in doc["fields"]:
        if not isinstance(field, dict) or not isinstance(field.get("name"), str):
            unmapped["INVALID_FIELD_SHAPE"] += 1
            continue
        source_name = field["name"]
        if source_name in rules["sensitiveExact"] or source_name.startswith(prefix):
            blocked[source_name] += 1
            continue
        rule = rule_by_name.get(source_name)
        if rule is None:
            # Non includere valori ignoti (potrebbero essere dati privati).
            unmapped[source_name] += 1
            continue
        is_known = rule["target"] in known
        if is_known != (rule["canonicalStatus"] == "mapped_to_existing_registry"):
            raise ValueError("Contraddizione con field registry: " + source_name)
        value = normalized(field.get("value"), rule["converter"])
        converted.append({
            "sourceField": source_name, "fieldKeyCandidate": rule["target"],
            "value": value, "valueStatus": "parsed" if value is not None else "unknown_or_invalid",
            "unit": "m" if rule["target"] == "elevationM" else "places" if rule["target"] in (
                "bedsTotal", "bedsWinter", "managerBeds") else None,
            "sourceId": "cai:shelter:" + code,
            "sourceUrl": "https://rifugi.cai.it/api/v1/shelters/" + code,
            "licence": None, "licenseGate": "requires_review",
            "retrievedAt": None, "sourceUpdatedAt": field.get("updated_at"),
            "validFrom": None, "validUntil": None,
            "method": "reported", "confidence": None,
            "canonicalStatus": rule["canonicalStatus"],
            "publicationStatus": "RIGHTS_BLOCKED",
            "notes": rule.get("notes"),
        })
    return {
        "schemaVersion": "1.0", "kind": "refuge", "status": "RESTRICTED_STAGING_ONLY",
        "sourceId": "cai:shelter:" + code,
        "caiId": code,
        "identityMatchStatus": "unresolved",
        "candidateFacts": converted,
        "blockedSensitiveFields": dict(sorted(blocked.items())),
        "unmappedFields": dict(sorted(unmapped.items())),
        "summary": {
            "candidateFacts": len(converted),
            "parsedCandidateValues": sum(x["valueStatus"] == "parsed" for x in converted),
            "unmappedFieldOccurrences": sum(unmapped.values()),
            "sensitiveFieldOccurrences": sum(blocked.values()),
            "licenceApproved": False,
            "readyForPublication": False,
        },
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path, required=True, help="File locale RISERVATO, non commit")
    p.add_argument("--output", type=Path, default=ROOT / "build" / "restricted-cai" / "candidate-facts.json")
    args = p.parse_args()
    doc = json.loads(args.input.read_text(encoding="utf-8"))
    rules = json.loads(RULES.read_text(encoding="utf-8"))
    registry = json.loads(FIELD_REGISTRY.read_text(encoding="utf-8"))
    output = convert_detail(doc, rules, registry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
                           encoding="utf-8")
    print(json.dumps(output["summary"], ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
