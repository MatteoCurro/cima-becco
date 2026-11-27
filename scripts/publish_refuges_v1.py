#!/usr/bin/env python3
"""Release the first Cima Becco refuge DATASET, OSM-only, without CAI/media.

Input is the reviewed deterministic importer staging output. This intentionally
does not publish a CAI-derived field, an unlicensed image, a webcam, a raw
snapshot, a candidate duplicate, or an unverified SEO page. It produces a
versioned static JSON data product consumed by future Atlas UI adapters.

The existing site's alpine-places.json remains the sole UI writer; this
publisher never edits it or changes permalink/SEO behaviour.

The generated JSON is OSM-derived under ODbL with GeoNames CC BY attribution
for nearby peak references. Review ODbL requirements for derived databases.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import re

from import_refuges_v1 import canonical_json, load, write

ROOT = Path(__file__).resolve().parents[1]
ID_RE = re.compile(r"^cb-[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
OSM_RE = re.compile(r"^(node|way|relation)/[1-9]\d*$")
SOURCE_RE = re.compile(r"^osm:(node|way|relation):[1-9]\d*$")
SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_FACT_KEYS = {
    "elevationM", "capacityReported", "operatorReported",
    "openingHoursReported", "website", "phone", "email",
    "addressReported", "winterRoomReported", "seasonalReported",
    "accessReported", "feeReported",
}


def require(condition, error):
    if not condition:
        raise ValueError(error)


def source_key(record):
    source = record.get("sourceIds", {}).get("osm", "")
    require(isinstance(source, str) and bool(OSM_RE.fullmatch(source)),
            "ID OSM non valido")
    return "osm:" + source.replace("/", ":", 1)


def validate_fact(key, item, origin):
    require(key in VALID_FACT_KEYS, "Campo OSM non autorizzato alla release: " + key)
    require(isinstance(item, dict) and item.get("sourceId") == origin,
            "Provenienza del fatto non OSM")
    require(item.get("licence") == "ODbL-1.0", "Fatto con licenza non consentita")
    require(item.get("method") == "reported", "Fatto non misurato dalla fonte")
    require(isinstance(item.get("sourceUrl"), str) and
            item["sourceUrl"].startswith("https://www.openstreetmap.org/"),
            "Link di provenienza non OSM")
    val = item.get("value")
    require(val is not None and isinstance(val, (str, int, float, bool)), "Valore inadatto")
    require(not isinstance(val, float) or math.isfinite(val), "Valore infinito")
    return {
        "value": val, "unit": item.get("unit"),
        "sourceId": origin, "sourceUrl": item["sourceUrl"],
        "licence": "ODbL-1.0", "method": "reported",
        "sourceUpdatedAt": item.get("sourceUpdatedAt"),
        "validFrom": item.get("validFrom"), "validUntil": item.get("validUntil"),
        "notes": item.get("notes"),
    }


def validated_relation(rel):
    require(isinstance(rel, dict) and rel.get("type") == "near" and
            rel.get("method") == "haversine",
            "Relazione geografica non tipizzata")
    ref = rel.get("targetRef", {})
    require(isinstance(ref, dict) and ref.get("kind") in {"locality", "mountain"},
            "Destinazione relazione non ammessa")
    name = ref.get("name")
    require(isinstance(name, str) and bool(name.strip()), "Relazione senza nome")
    dist = rel.get("straightLineKm")
    require(isinstance(dist, (float, int)) and not isinstance(dist, bool) and
            math.isfinite(dist) and 0 <= dist <= 20,
            "Distanza prossimità non valida")
    sources = ref.get("sourceIds", {})
    if ref["kind"] == "locality":
        key = sources.get("osm", "")
        require(isinstance(key, str) and bool(SOURCE_RE.fullmatch(key)),
                "Località senza ID OSM")
        legacy_slug = ref.get("legacySlug")
        require(isinstance(legacy_slug, str) and bool(SAFE_SLUG.fullmatch(legacy_slug)),
                "Località con permalink non valido")
        target = {"id": key, "kind": "locality", "name": name,
                  "href": "/borghi/" + legacy_slug + "/"}
        source_url = "https://www.openstreetmap.org/" + key.split(":")[1] + "/" + key.split(":")[2]
    else:
        ident = sources.get("geonames", "")
        require(isinstance(ident, str) and ident.isdigit(),
                "Montagna senza GeoNames ID")
        target = {"id": "geonames:" + ident, "kind": "mountain", "name": name}
        source_url = "https://www.geonames.org/" + ident
    return {
        "type": "near", "target": target,
        "straightLineKm": dist, "method": "haversine",
        "sourceUrl": source_url, "verified": False,
        "accessVerified": False,
    }


def build_public(source_dir, exclusions, *, min_count=400):
    source_dir = Path(source_dir)
    raw = load(source_dir / "refuges.json")
    report = load(source_dir / "report.json")
    review = load(source_dir / "review.json")
    links = load(source_dir / "links.json")
    require(all(isinstance(obj, dict) for obj in (raw, report, review, links)),
            "Staging incompleto")
    require(raw.get("status") == "staging_only" and report.get("status") == "staging_only",
            "Input non è lo staging originale")
    require(raw.get("sourceSnapshotSha256") == report.get("snapshotSha256"),
            "Digest dataset incoerente")
    records = raw.get("entities")
    require(isinstance(records, list) and report.get("refuges") == len(records),
            "Numero rifugi diverso dal report")
    require(len(records) >= min_count, "Regressione copertura OSM: meno record del minimo")
    require(isinstance(exclusions, dict) and isinstance(exclusions.get("sourceKeys"), list),
            "Registro quarantena obbligatorio")
    quarantine = {}
    for rule in exclusions["sourceKeys"]:
        require(isinstance(rule, dict) and bool(SOURCE_RE.fullmatch(str(rule.get("sourceKey", "")))),
                "Chiave quarantena invalida")
        require(bool(rule.get("reason")) and bool(rule.get("evidenceUrl")),
                "Quarantena senza motivo o provenienza")
        quarantine[rule["sourceKey"]] = rule["reason"]
    duplicate_pairs = review.get("candidateDuplicates", [])
    require(isinstance(duplicate_pairs, list), "Coda duplicati assente")
    for pair in duplicate_pairs:
        require(pair.get("autoMerged") is False and
                pair.get("status") == "manual_review_required",
                "Merge automatico inatteso")
        for side in ("left", "right"):
            ident = pair.get(side, {}).get("sourceKey")
            require(bool(SOURCE_RE.fullmatch(str(ident))), "Duplicato senza ID OSM")
            quarantine[ident] = "potential_duplicate_identity"
    published, excluded = [], []
    all_seen_ids, all_seen_slugs, all_source_keys = set(), set(), set()
    for item in records:
        require(isinstance(item, dict), "Rifugio non oggetto")
        key = source_key(item)
        require(key not in all_source_keys, "Fonte OSM duplicata")
        all_source_keys.add(key)
        entity_id = item.get("id")
        slug = item.get("slug")
        require(isinstance(entity_id, str) and bool(ID_RE.fullmatch(entity_id)),
                "ID canonico invalido")
        require(isinstance(slug, str) and bool(SAFE_SLUG.fullmatch(slug)),
                "Slug canonico invalido")
        require(entity_id not in all_seen_ids and slug not in all_seen_slugs,
                "Collisione identificatore o slug")
        all_seen_ids.add(entity_id)
        all_seen_slugs.add(slug)
        require(item.get("kind") == "refuge" and item.get("quality", {}).get("gate") == "G0",
                "Quality gate diverso da G0 senza approvazione")
        require(item.get("quality", {}).get("seoIndexable") is False,
                "Una scheda G0 non può essere indicizzata")
        if key in quarantine:
            excluded.append({"sourceKey": key, "reason": quarantine[key]})
            continue
        point = item.get("geo", {}).get("point", {})
        lat, lon = point.get("lat"), point.get("lon")
        require(all(isinstance(v, (float, int)) and not isinstance(v, bool) and
                    math.isfinite(v) for v in (lat, lon)) and
                -90 <= lat <= 90 and -180 <= lon <= 180,
                "Coordinate WGS84 non valide")
        orig = "https://www.openstreetmap.org/" + key.split(":")[1] + "/" + key.split(":")[2]
        facts = {
            field: validate_fact(field, value, key)
            for field, value in item.get("facts", {}).items()
        }
        relations = [validated_relation(link) for link in item.get("relations", [])]
        aliases = item.get("slugAliases", [])
        require(isinstance(aliases, list) and all(
            isinstance(s, str) and bool(SAFE_SLUG.fullmatch(s)) for s in aliases),
            "Aliases invalidi")
        # No CAI/individual media. No Wikimedia photo is shipped by this release.
        published.append({
            "id": entity_id, "kind": "refuge", "name": item["name"],
            "subtype": item.get("subtype"),
            "slug": slug, "slugAliases": aliases,
            "legacyUrl": item.get("legacyUrl"),
            "geo": {"point": {"lat": lat, "lng": lon},
                    "method": point.get("method"), "sourceUrl": orig},
            "sourceIds": {"osm": item["sourceIds"]["osm"]},
            "sources": [{"id": key, "url": orig, "licence": "ODbL-1.0"}],
            "facts": facts, "relations": relations,
            "editorialStatus": "raw", "quality": {
                "gate": "G0", "seoIndexable": False,
                "description": "Identità OSM non riconciliata con fonti ufficiali",
            },
            "media": [], "webcams": [], "alerts": [],
        })
    require(len(excluded) <= max(3, len(records) // 20),
            "Quarantena troppo ampia: revisione obbligatoria")
    require(len(published) >= min_count - max(3, min_count // 20),
            "Troppi record esclusi per una pubblicazione integra")
    ids = {r["id"] for r in published}
    public_links = []
    for link in links.get("edges", []):
        if link.get("to", {}).get("id") not in ids:
            continue
        require(link.get("type") == "passes_near" and
                link.get("verifiedAccess") is False and
                isinstance(link.get("distanceToPolylineM"), (int, float)) and
                0 <= link["distanceToPolylineM"] <= 180,
                "Relazione percorso non verificabile")
        public_links.append({
            "type": "passes_near", "from": link["from"],
            "to": link["to"], "distanceToPolylineM": link["distanceToPolylineM"],
            "method": link["method"], "verifiedAccess": False,
        })
    public_links.sort(key=lambda x: (x["from"]["legacySlug"], x["to"]["id"]))
    published.sort(key=lambda x: x["id"])
    catalogue = {
        "schemaVersion": "1.0",
        "releaseChannel": "OSM_ONLY_G0",
        "sourceSnapshotSha256": raw["sourceSnapshotSha256"],
        "sourceDatasetDate": report.get("sourceDatasetDate"),
        "kind": "refuge", "seoIndexable": False,
        "attribution": [
            {"source": "OpenStreetMap contributors", "licence": "ODbL-1.0",
             "url": "https://www.openstreetmap.org/copyright",
             "datasetTerms": "https://opendatacommons.org/licenses/odbl/"},
            {"source": "GeoNames", "licence": "CC-BY-4.0",
             "url": "https://www.geonames.org/about.html",
             "scope": "nearby mountain references only"},
        ],
        "rightsNotice": (
            "Derived geographic data: ODbL attribution/share-alike obligations apply; "
            "GeoNames nearby mountain references require CC BY attribution. "
            "No CAI data, copyrighted photographs, logos or webcam media are included."
        ),
        "limitations": [
            "G0: OSM-sourced facts are not independently verified",
            "No current opening, access/safety guarantee or route reachability",
            "Nearby relations are linear distance; passes_near is not a walked route",
            "No new indexable pages are generated from this dataset",
        ],
        "entities": published, "routeProximityEdges": public_links,
    }
    public_blob = canonical_json(catalogue)
    local_report = {
        "schemaVersion": "1.0", "status": "release_ready_osm_only",
        "sourceSnapshotSha256": raw["sourceSnapshotSha256"],
        "sourceRecords": len(records),
        "publicRecords": len(published),
        "quarantinedRecords": len(excluded),
        "quarantineReasons": dict(sorted(Counter(x["reason"] for x in excluded).items())),
        "quarantine": sorted(excluded, key=lambda x: x["sourceKey"]),
        "publicRouteEdges": len(public_links),
        "publicNearRelations": sum(len(r["relations"]) for r in published),
        "publicPhotoCount": 0, "publicCAIFields": 0,
        "publicWebcamCount": 0, "seoIndexable": 0,
        "catalogueSha256": hashlib.sha256(public_blob).hexdigest(),
        "qualityGate": "G0_catalogue_and_map_only",
        "licences": ["ODbL-1.0", "CC-BY-4.0 (GeoNames mountain refs)"],
    }
    return catalogue, local_report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source-dir", type=Path,
                   default=ROOT / "build" / "import-refuges-v1")
    p.add_argument("--dist-dir", type=Path,
                   default=ROOT / "dist")
    p.add_argument("--quarantine-file", type=Path,
                   default=ROOT / "scripts" / "refuges_release_quarantine_v1.json")
    p.add_argument("--report-dir", type=Path,
                   default=ROOT / "build" / "release-refuges-v1")
    p.add_argument("--min-records", type=int, default=400)
    args = p.parse_args()
    catalogue, report = build_public(
        args.source_dir, load(args.quarantine_file), min_count=args.min_records
    )
    write(args.dist_dir / "data" / "atlas" / "refuges-v1.json", catalogue)
    write(args.report_dir / "report.json", report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
