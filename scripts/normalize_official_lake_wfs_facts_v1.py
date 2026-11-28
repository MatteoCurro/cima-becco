#!/usr/bin/env python3
"""Normalize official lake WFS records WITHOUT promoting identities or SEO.

Inputs are provider-specific G0 staging samples from import_official_lake_wfs_v1.
This is an independent evidence stream, not a replacement of GeoNames/OSM.
Bibbia §§1,5,30–31. All units explicitly sourced; no inferred lake access,
bathing conditions, permanence of water or canonical cross-source relation.
"""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
from hashlib import sha256
import json
import math
from pathlib import Path
import re
import unicodedata

from import_official_lake_wfs_v1 import CHANNEL, PROVIDERS

FACT_FIELDS = {
    "bolzano_lakes": {
        "AREA": ("officialAreaReportedM2", "m2"),
        "AREA_GEOM": ("providerGeometryAreaReportedM2", "m2"),
        "VOLUME": ("officialVolumeReportedM3", "m3"),
        "ELEVATION": ("officialElevationReportedM", "m"),
        "WIDTH": ("officialWidthReportedM", "m"),
        "LENGTH": ("officialLengthReportedM", "m"),
        "DEPTH": ("officialDepthReportedM", "m"),
        "MAX_DEPTH": ("officialMaxDepthReportedM", "m"),
    },
    "arpav_water_surfaces": {
        "area_m2": ("officialAreaReportedM2", "m2"),
    },
}
MAX_METRIC_VALUE = {
    "m2": 400_000_000,
    "m3": 40_000_000_000,
    "m": 100_000,
}
# A source classification may inform review; it does NOT become the
# canonical subtype, which requires the full source/identity gate.
ARPAV_CLASS_SUGGESTIONS = {
    "lago": "lake",
    "invaso": "reservoir",
    "bacino artificiale": "reservoir",
}


def _fact(value, unit, source_id, source_url, licence, at, *,
          notes=None, confidence=0.85):
    return {
        "value": value, "unit": unit, "method": "reported",
        "sourceId": source_id, "sourceUrl": source_url,
        "licence": licence, "retrievedAt": at, "sourceUpdatedAt": None,
        "confidence": confidence, "notes": notes,
    }


def _number(raw, unit):
    if type(raw) not in (int, float) or not math.isfinite(raw):
        raise ValueError("Source numeric field is not a finite number")
    if raw < 0 or raw > MAX_METRIC_VALUE[unit]:
        raise ValueError("Source numeric field outside plausible declared-unit bounds")
    return raw


def _name(raw):
    if type(raw) is not str:
        return None
    raw = " ".join(raw.strip().split())
    return raw if 1 <= len(raw) <= 180 else None


def enrich_staged(source_doc):
    if not isinstance(source_doc, dict) or source_doc.get("releaseChannel") != CHANNEL:
        raise ValueError("Expected independent official WFS G0 source channel")
    if source_doc.get("isPublished") is not False or not source_doc.get("sampleOnly"):
        raise ValueError("Source must remain non-public and explicitly sampled")
    provider = source_doc.get("sourceProvider")
    if provider not in PROVIDERS:
        raise ValueError("Unknown official WFS provider")
    result = deepcopy(source_doc)
    source_url = PROVIDERS[provider]["sourceUrl"]
    licence = PROVIDERS[provider]["licence"]
    at = source_doc.get("retrievedAt")
    if not isinstance(at, str) or not at:
        raise ValueError("Official evidence has no retrievedAt")
    invalid = Counter()
    classifications = Counter()
    for entity in result.get("entities", []):
        quality = entity.get("quality", {})
        if quality.get("gate") != "G0" or quality.get("seoIndexable") is not False:
            raise ValueError("Official source entity attempted to bypass quality gate")
        if entity.get("subtype") is not None or entity.get("relations"):
            raise ValueError("G0 official feature must not assert a subtype or relations")
        props = entity.get("sourcePropertiesRaw", {})
        if not isinstance(props, dict):
            raise ValueError("Source evidence attributes missing")
        fid = entity.get("sourceFeatureId")
        if not isinstance(fid, str) or not fid:
            raise ValueError("Missing WFS FID")
        prefix = provider + ":" + fid
        facts = entity.setdefault("facts", {})
        for source_field, (canonical, unit) in FACT_FIELDS[provider].items():
            raw = props.get(source_field)
            if raw is None:
                continue
            try:
                val = _number(raw, unit)
            except ValueError:
                invalid[source_field] += 1
                quality["needsReview"] = True
                continue
            facts[canonical] = _fact(
                val, unit, prefix + ":" + source_field, source_url, licence, at,
                notes=("Provider-reported lake metric; does not replace GeoNames or OSM"
                       if source_field != "AREA_GEOM" else
                       "Provider-supplied geometric area; not a separate survey"),
            )
        names = []
        if provider == "bolzano_lakes":
            for key, lang in (("NAME_IT", "it"), ("NAME_DE", "de")):
                value = _name(props.get(key))
                if value:
                    names.append({"value": value, "language": lang,
                                  "sourceUrl": source_url, "sourceId": prefix + ":" + key})
            code = _name(props.get("CODE"))
            numeric_id = props.get("ID")
            # ID + CODE are source-specific evidence; no cross-source join.
            entity["providerRecordCodes"] = {
                "id": numeric_id if type(numeric_id) is int and numeric_id > 0 else None,
                "code": code,
                "verifiedAgainstFid": (
                    type(numeric_id) is int and fid == "Lakes." + str(numeric_id)
                ),
            }
            if not entity["providerRecordCodes"]["verifiedAgainstFid"]:
                quality["needsReview"] = True
                invalid["id_fid_mismatch"] += 1
            # BATHING is a *raw source flag*, not an assertion of public
            # bathing permission, up-to-date testing or water quality.
            entity["providerBathingFlagRaw"] = (
                props.get("BATHING") if type(props.get("BATHING")) is int else None
            )
            entity["providerBasinCodeRaw"] = _name(props.get("BASIN"))
            entity["providerStateOwnershipCodeRaw"] = (
                props.get("STATE_OWN") if type(props.get("STATE_OWN")) is int else None
            )
        else:
            val = _name(props.get("nome"))
            if val:
                names.append({"value": val, "language": "it",
                              "sourceUrl": source_url, "sourceId": prefix + ":nome"})
            classification = _name(props.get("tipo"))
            entity["providerWaterClassRaw"] = classification
            entity["providerSubtypeCandidate"] = (
                ARPAV_CLASS_SUGGESTIONS.get(classification.casefold())
                if classification else None
            )
            hydro_id = props.get("hydroidspc")
            entity["providerRecordCodes"] = {
                "hydroidspc": hydro_id if type(hydro_id) is int and hydro_id >= 0 else None,
                "codtratvp": _name(props.get("codtratvp")),
                "verifiedAgainstFid": False,
            }
            classifications[classification or "unknown"] += 1
        entity["providerNames"] = names
        entity["quality"]["providerFactsNormalized"] = True
        entity["quality"]["officialIdentityCrosswalkVerified"] = False
        entity["quality"]["seoIndexable"] = False
        entity["quality"]["gate"] = "G0"
        entity["subtype"] = None
        # Independent agency-area vs source polygon area comparison is
        # diagnostic ONLY, not an authority hierarchy or an auto-merge.
        official = facts.get("officialAreaReportedM2", {}).get("value")
        mapped = facts.get("providerMappedWaterSurfaceKm2", {}).get("value")
        if official and mapped is not None:
            deviation = abs(mapped * 1_000_000 - official) / official * 100
            entity["providerAreaDifferencePct"] = round(deviation, 2)
            if deviation > 25:
                quality["providerAreaDifferenceReview"] = True
        if any(k.lower().startswith(("isswimmable", "potability",
                                     "accessible_from", "bathable"))
               for k in facts):
            raise ValueError("Forbidden implied access/water-safety fact")
    return result, {
        "provider": provider, "normalizedFeatures": len(result.get("entities", [])),
        "numericAnomalies": dict(invalid),
        "sourceClassifications": dict(classifications),
        "g2Released": 0, "crossSourceLinksPromoted": 0,
    }


def audit_source_replays(first_doc, second_doc):
    """Two repeat responses can establish short-term consistency, NOT permanence."""
    if first_doc.get("sourceProvider") != second_doc.get("sourceProvider"):
        raise ValueError("Cannot compare snapshots from different agencies")
    def keyed(d):
        out = {}
        for entry in d.get("entities", []):
            fid = entry["sourceFeatureId"]
            if fid in out:
                raise ValueError("Duplicate feature ID in repeated source sample")
            out[fid] = entry
        return out
    earlier, later = keyed(first_doc), keyed(second_doc)
    shared = sorted(earlier.keys() & later.keys())
    unchanged = 0
    conflicts = []
    for fid in shared:
        old, new = earlier[fid], later[fid]
        # Presence/name/codes/facts must be stable across requests; timestamps
        # and source URL query differences are ignored by design.
        stable_fields = ("sourcePropertiesRaw",)
        same = all(old.get(field) == new.get(field) for field in stable_fields)
        if same:
            unchanged += 1
        else:
            conflicts.append(fid)
    return {
        "provider": first_doc.get("sourceProvider"),
        "firstSample": len(earlier), "secondSample": len(later),
        "sameFidCount": len(shared), "sameFidAndAttributes": unchanged,
        "conflicts": conflicts, "identifiersStableOverTwoSamples": (
            not conflicts and len(earlier) == len(later) == len(shared)
        ),
        "longTermIdStabilityVerified": False,
        "crossSourceIdentityVerified": False, "seoIndexable": False,
    }


def normalized_name(value):
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFKD", value.casefold())
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+", value))


def bbox(geo):
    area = geo.get("area") or {}
    if area.get("type") != "MultiPolygon":
        return None
    points = [pt for polygon in area.get("coordinates", [])
              for ring in polygon for pt in ring]
    if not points:
        return None
    return (min(x for x, y in points), min(y for x, y in points),
            max(x for x, y in points), max(y for x, y in points))


def overlaps(a, b):
    return a and b and max(a[0], b[0]) < min(a[2], b[2]) and \
        max(a[1], b[1]) < min(a[3], b[3])


def review_with_osm(official_doc, osm_snapshot):
    """Generate NON-identity review suggestions; do not alter either source.

    A matching name and intersecting bounding box are clues, not evidence
    for publishing a crosswalk (Bibbia §5). No 'same_as' is emitted.
    """
    if osm_snapshot.get("isPublished") is not False:
        raise ValueError("Expected original non-public OSM G1 snapshot")
    osm = osm_snapshot.get("osmEntities", [])
    candidates = []
    for ent in official_doc.get("entities", []):
        names = {normalized_name(v.get("value")) for v in ent.get("providerNames", [])}
        names.discard("")
        area = bbox(ent.get("geo", {}))
        if not area or not names:
            continue
        for other in osm:
            other_names = {normalized_name(other.get("displayName"))}
            other_names.update(normalized_name(v.get("value"))
                               for v in other.get("aliases", [])
                               if isinstance(v, dict))
            other_names.discard("")
            if not names.intersection(other_names):
                continue
            if not overlaps(area, bbox(other.get("geo", {}))):
                continue
            candidates.append({
                "provider": official_doc["sourceProvider"],
                "officialFid": ent["sourceFeatureId"],
                "osmId": other.get("sourceIds", {}).get("osm"),
                "name": next(iter(sorted(names.intersection(other_names)))),
                "officialSourceClass": ent.get("providerWaterClassRaw"),
                "osmSubtype": other.get("subtype"),
                "classificationDisagreement": (
                    bool(ent.get("providerSubtypeCandidate")) and
                    ent["providerSubtypeCandidate"] != other.get("subtype")
                ),
                "reviewOnly": True, "identityVerified": False,
                "evidence": "normalised_name_and_bounding_box_intersection_ONLY",
            })
    return {
        "candidateReviews": sorted(candidates, key=lambda x: (x["provider"], x["officialFid"], str(x["osmId"]))),
        "exactIdentifierCrosswalks": 0,
        "published": 0,
        "nameAndSpatialEvidenceNotSufficient": True,
    }
