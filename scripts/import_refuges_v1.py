#!/usr/bin/env python3
"""Normalizza i rifugi OSM del catalogo esistente senza pubblicare o interrogare API.

Contratto: docs/MODELLO_METADATI_E_LAYOUT.md. Questa è la fase PILOTA:
- la fonte è lo snapshot locale alpine-places.json, non un fetch live;
- i link di prossimità non dimostrano attraversamento o raggiungibilità;
- l'output va in staging, NON in public/data o nelle pagine SEO.
Solo standard library, output deterministico, snapshot grezzo immutabile.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import unicodedata
from uuid import UUID, uuid5

ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = UUID("45bd9543-e579-44a2-b1fa-7b67ff889a19")
LICENCE = "ODbL-1.0"
FACT_MAP = {
    "elevationM": ("elevationM", "m"),
    "capacity": ("capacityReported", "places"),
    "operator": ("operatorReported", None),
    "openingHours": ("openingHoursReported", None),
    "website": ("website", None),
    "phone": ("phone", None),
    "email": ("email", None),
    "address": ("addressReported", None),
    "winterRoom": ("winterRoomReported", None),
    "seasonal": ("seasonalReported", None),
    "access": ("accessReported", None),
    "fee": ("feeReported", None),
}
OSM_RE = re.compile(r"^https://www\.openstreetmap\.org/(node|way|relation)/(\d+)$")
LEGACY_RE = re.compile(r"^osm-[nwr]-\d+$")


def canonical_json(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":")) + "\n").encode("utf-8")


def load(path, default=None):
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else default


def write(path, value, immutable=False):
    content = canonical_json(value)
    if path.exists():
        prior = path.read_bytes()
        if prior == content:
            return False
        if immutable:
            raise ValueError("Snapshot immutabile modificato: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(content)
    temporary.replace(path)
    return True


def slugify(value):
    flat = unicodedata.normalize("NFKD", value)
    flat = "".join(c for c in flat if not unicodedata.combining(c))
    slug = re.sub(r"[^a-z0-9]+", "-", flat.lower()).strip("-")
    return slug[:90].rstrip("-")


def haversine_km(a, b):
    lat1, lon1 = math.radians(a["lat"]), math.radians(a["lng"])
    lat2, lon2 = math.radians(b["lat"]), math.radians(b["lng"])
    h = math.sin((lat2-lat1)/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin((lon2-lon1)/2)**2
    return 6371.0088 * 2 * math.asin(min(1.0, math.sqrt(h)))


def osm_identity(place):
    match = OSM_RE.fullmatch(str(place.get("osmUrl", "")))
    if not match or not LEGACY_RE.fullmatch(str(place.get("slug", ""))):
        raise ValueError("Identità OSM invalida: " + str(place.get("slug")))
    kind, ident = match.groups()
    if place["slug"] != f"osm-{kind[0]}-{ident}":
        raise ValueError("Slug legacy discordante da ID OSM")
    return kind, ident, f"osm:{kind}:{ident}"


def coordinates(place):
    lat, lon = place.get("lat"), place.get("lng")
    if isinstance(lat, bool) or isinstance(lon, bool):
        raise ValueError("Coordinate non numeriche")
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        raise ValueError("Coordinate assenti")
    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
        raise ValueError("Coordinate fuori intervallo")


def source_ref(place):
    kind, ident, key = osm_identity(place)
    return {"key": key, "url": place["osmUrl"], "licence": LICENCE,
            "kind": kind, "osmId": ident}


def fact(value, key, url, unit=None, note=None):
    data = {"value": value, "unit": unit, "sourceId": key,
            "sourceUrl": url, "licence": LICENCE,
            "retrievedAt": None, "sourceUpdatedAt": None,
            "validFrom": None, "validUntil": None, "method": "reported",
            "confidence": None}
    if note:
        data["notes"] = note
    return data




FIELD_REGISTRY_PATH = Path(__file__).resolve().with_name("refuge_field_registry_v1.json")


def _safe_https(value):
    return isinstance(value, str) and value.startswith("https://") and " " not in value


def media_candidate(obj, kind, place, entity_id):
    """Staging-only: a file/link found in raw data is not a published asset."""
    if not isinstance(obj, dict):
        return None
    url = obj.get("url")
    page = obj.get("sourceUrl") or obj.get("sourcePage")
    if not _safe_https(url) or not _safe_https(page):
        return None
    licence = obj.get("license") or obj.get("licence")
    author = obj.get("author")
    rights_ready = bool(licence and author)
    subject_ready = bool(
        kind == "photo" and
        place.get("photoGeoCheckedAt")
    )
    status = (
        "reviewed_legacy_geo_match" if rights_ready and subject_ready else
        "subject_review_required" if rights_ready else
        "rights_and_subject_review_required"
    )
    candidate = {
        "kind": kind, "subjectId": entity_id,
        "url": url, "sourcePage": page,
        "author": author or None,
        "licence": licence or None,
        "licenceUrl": obj.get("licenseUrl") or obj.get("licenceUrl") or None,
        "status": status,
        "subjectCheckedAt": place.get("photoGeoCheckedAt") if kind == "photo" else None,
        "sourceCheckedAt": place.get("photoCheckedAt") if kind == "photo" else None,
        "origin": "legacy_alpine_places",
    }
    for source_key, output_key in (
        ("caption", "caption"), ("takenAt", "takenAt"),
        ("orientation", "orientation"), ("width", "width"),
        ("height", "height"), ("thumbnail", "thumbnail"),
    ):
        if obj.get(source_key) is not None:
            candidate[output_key] = obj[source_key]
    return candidate


def webcam_candidate(obj, entity_id):
    """Official link is only a lead; no implicit right to embed or call it live."""
    if isinstance(obj, str):
        obj = {"sourceUrl": obj}
    if not isinstance(obj, dict):
        return None
    source = obj.get("officialUrl") or obj.get("sourceUrl") or obj.get("permalink")
    if not _safe_https(source):
        return None
    return {
        "kind": "webcam", "subjectId": entity_id,
        "sourcePage": source,
        "operator": obj.get("operator"),
        "cameraDirectionDegrees": obj.get("directionDegrees"),
        "cameraCoordinates": obj.get("coordinates"),
        "visibleTarget": obj.get("visibleTarget"),
        "stillUrlCandidate": obj.get("stillUrl") if _safe_https(obj.get("stillUrl")) else None,
        "licence": obj.get("licence"),
        "permission": obj.get("permission"),
        "refreshedAt": obj.get("refreshedAt"),
        "status": "official_source_and_stream_permission_review_required",
        "isLive": False,
    }


def media_inventory(place, entity_id):
    candidates, accepted = [], []
    for kind in ("photo", "logo"):
        items = place.get(kind)
        if isinstance(items, dict):
            items = [items]
        if not isinstance(items, list):
            continue
        for item in items:
            candidate = media_candidate(item, kind, place, entity_id)
            if candidate is None:
                continue
            candidates.append(candidate)
            if candidate["status"] == "reviewed_legacy_geo_match":
                accepted.append({
                    "kind": "photo", "subjectId": entity_id,
                    "url": candidate["url"], "sourcePage": candidate["sourcePage"],
                    "author": candidate["author"], "licence": candidate["licence"],
                    "licenceUrl": candidate["licenceUrl"],
                    "subjectVerification": "legacy_explicit_commons_match",
                    "subjectCheckedAt": candidate["subjectCheckedAt"],
                })
    webcams = place.get("webcams", place.get("webcam"))
    if webcams is not None:
        if not isinstance(webcams, list):
            webcams = [webcams]
        for item in webcams:
            candidate = webcam_candidate(item, entity_id)
            if candidate:
                candidates.append(candidate)
    return candidates, accepted


def inventory_coverage(entities, raw_refuges, registry, route_links):
    """No fabricated blanks in the cards: gaps live in a field-level audit."""
    fields = registry.get("fields")
    if not isinstance(fields, list) or len(fields) != len({f.get("key") for f in fields}):
        raise ValueError("Registry dei campi canonici invalido o duplicato")
    output = []
    for entry in fields:
        target = entry.get("target", "")
        raw_key = entry.get("legacyKey")
        observed = 0
        if target == "routeProximity":
            observed = len({x["to"]["id"] for x in route_links})
        elif target == "nearbyLocalities":
            observed = sum(any(x["targetRef"]["kind"] == "locality" for x in e["relations"]) for e in entities)
        elif target == "nearbySummits":
            observed = sum(any(x["targetRef"]["kind"] == "mountain" for x in e["relations"]) for e in entities)
        elif target.startswith("mediaCandidates."):
            kind = target.partition(".")[2]
            observed = sum(any(x["kind"] == kind for x in e.get("mediaCandidates", [])) for e in entities)
        else:
            parts = target.split(".") if target else []
            for entity in entities:
                value = entity
                for part in parts:
                    if not isinstance(value, dict) or part not in value:
                        value = None
                        break
                    value = value[part]
                if value is not None and value != "" and value != [] and value != {}:
                    observed += 1
        raw_count = sum(
            raw_key in p and p[raw_key] is not None and p[raw_key] != ""
            for p in raw_refuges
        ) if raw_key else None
        output.append({
            "key": entry["key"], "group": entry["group"], "priority": entry["priority"],
            "providers": entry["sources"], "refreshPolicy": entry["refresh"],
            "recordsWithValue": observed,
            "recordsWithLegacySourceValue": raw_count,
            "state": ("staging_value_present" if observed else
                      "legacy_value_needs_review" if raw_count else
                      "not_yet_acquired"),
        })
    return {"schemaVersion": registry.get("schemaVersion"), "kind": "refuge",
            "records": len(entities),
            "fieldCount": len(fields),
            "fields": output,
            "note": "Availability counts are NOT source verification, licences or live freshness."}


def build_refuge(place, identity, snapshot_date):
    src = source_ref(place)
    name = place.get("name", "").strip()
    if len(name) < 3:
        raise ValueError("Rifugio senza nome attendibile")
    coordinates(place)
    facts = {}
    for legacy_field, (key, unit) in FACT_MAP.items():
        value = place.get(legacy_field)
        if value is None or value == "":
            continue
        if legacy_field == "elevationM":
            # Il dataset storico contiene quote DEM senza provenance del raster:
            # NON attribuirle falsamente ai tag OSM.
            if place.get("elevationSource") != "osm":
                continue
            if not isinstance(value, (int, float)) or not 0 < value < 9000:
                continue
        if legacy_field == "capacity":
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                continue
        if legacy_field == "website" and not str(value).startswith("https://"):
            continue
        note = None
        if legacy_field == "capacity":
            note = "Snapshot legacy: campo derivato da beds OSM oppure capacity; non equivale a letti verificati."
        if legacy_field in ("openingHours", "seasonal", "access"):
            note = "Dichiarazione OSM senza verifica corrente: non indica apertura o accessibilità odierna."
        facts[key] = fact(value, src["key"], src["url"], unit, note)
    media_candidates, media = media_inventory(place, identity["id"])
    kind = src["kind"]
    return {
        "id": identity["id"], "kind": "refuge", "subtype": "alpine_hut",
        "name": name, "displayName": name,
        "slug": identity["slug"], "slugAliases": [place["slug"]],
        "legacyUrl": "/rifugi/" + place["slug"] + "/",
        "geo": {"point": {"lat": place["lat"], "lon": place["lng"],
                          "method": "osm_node" if kind == "node" else "osm_feature_centre"}},
        "sourceIds": {"osm": kind + "/" + src["osmId"],
                      **({"wikidata": place["wikidata"]} if re.fullmatch(r"Q\d+", str(place.get("wikidata", ""))) else {})},
        "sources": [{"id": src["key"], "url": src["url"], "licence": LICENCE,
                     "retrievedAt": None, "snapshotDate": snapshot_date}],
        "facts": facts, "factsAlternatives": [],
        "relations": [], "media": media,
        **({"mediaCandidates": media_candidates} if media_candidates else {}),
        "restrictions": [], "alerts": [],
        "editorialStatus": "raw", "quality": {"gate": "G0", "seoIndexable": False,
            "notes": ["Identita OSM non ancora riconciliata con CAI/SAT: quality gate G0",
                      "Orari e stato di apertura non verificati in tempo reale"]},
        "weatherRef": None, "climateRef": None,
        "checkedAt": None, "updatedAt": None,
    }


def assign_identities(refuges, registry):
    previous = registry if isinstance(registry, dict) else {}
    mapping, used_slugs, conflicts = dict(previous), set(), []
    base_counts = {}
    for place in refuges:
        base = slugify(place["name"])
        base_counts[base] = base_counts.get(base, 0) + 1
    for place in sorted(refuges, key=lambda item: item["osmUrl"]):
        key = source_ref(place)["key"]
        base = slugify(place["name"])
        saved = previous.get(key)
        if saved:
            identity = {"id": saved["id"], "slug": saved["slug"]}
            if base_counts.get(base, 0) > 1 and identity["slug"] != base:
                conflicts.append({"sourceKey": key, "proposedSlug": identity["slug"],
                                  "reason": "homonymous_name_needs_editorial_review"})
        else:
            if not base:
                raise ValueError("Nome non convertibile in slug")
            slug = base
            suffix = 2
            while slug in used_slugs or any(v.get("slug") == slug for v in previous.values()):
                slug = f"{base}-{suffix}"
                suffix += 1
            if slug != base:
                conflicts.append({"sourceKey": key, "proposedSlug": slug,
                                  "reason": "homonymous_name_needs_editorial_review"})
            identity = {"id": "cb-" + str(uuid5(NAMESPACE, key)),
                        "slug": slug}
        if identity["slug"] in used_slugs:
            raise ValueError("Collisione nel registry: " + identity["slug"])
        used_slugs.add(identity["slug"])
        mapping[key] = identity
    return mapping, conflicts



def suspected_duplicates(refuges, identities):
    """Produci candidati di revisione, senza fondere due identità OSM."""
    rows = sorted(refuges, key=lambda p: source_ref(p)["key"])
    pairs = []
    for i, a in enumerate(rows):
        for b in rows[i+1:]:
            same_name = slugify(a["name"]) == slugify(b["name"])
            same_qid = bool(a.get("wikidata")) and a.get("wikidata") == b.get("wikidata")
            if not same_name and not same_qid:
                continue
            distance = haversine_km(a, b)
            if not ((same_name and distance <= 0.15) or (same_qid and distance <= 1)):
                continue
            akey = source_ref(a)["key"]
            bkey = source_ref(b)["key"]
            pairs.append({
                "left": {"id": identities[akey]["id"], "sourceKey": akey, "name": a["name"]},
                "right": {"id": identities[bkey]["id"], "sourceKey": bkey, "name": b["name"]},
                "straightLineM": round(distance * 1000),
                "evidence": "same_wikidata_qid" if same_qid else "same_normalized_name",
                "method": "haversine", "status": "manual_review_required",
                "autoMerged": False,
            })
    return pairs


def nearby_relations(refuge, items, target_kind, max_km, limit):
    matches = []
    for item in items:
        if not item.get("name") or not isinstance(item.get("lat"), (int, float)):
            continue
        if not isinstance(item.get("lng"), (int, float)):
            continue
        d = haversine_km(refuge, item)
        if d > max_km:
            continue
        target = {"kind": target_kind, "name": item["name"],
                  "sourceIds": item["sourceIds"]}
        if item.get("legacySlug"):
            target["legacySlug"] = item["legacySlug"]
        matches.append({"type": "near", "targetRef": target,
                        "straightLineKm": round(d, 3), "method": "haversine",
                        "provenance": {"refuge": "OpenStreetMap · ODbL-1.0",
                                       "target": ("GeoNames · CC-BY-4.0"
                                                  if target_kind == "mountain"
                                                  else "OpenStreetMap · ODbL-1.0")}})
    matches.sort(key=lambda link: (link["straightLineKm"], link["targetRef"]["name"]))
    return matches[:limit]


def peak_candidates(data):
    peaks = []
    folder = data / "peaks"
    for path in sorted(folder.glob("*.json")):
        if not re.fullmatch(r"-?\d+_-?\d+\.json", path.name):
            continue
        rows = load(path, [])
        for row in rows:
            if not isinstance(row, list) or len(row) < 8 or row[7] in ("MTS", "HLLS"):
                continue
            ident, name, lat, lon = row[:4]
            if not isinstance(ident, int) or not isinstance(lat, (float, int)):
                continue
            if not isinstance(lon, (float, int)) or not name:
                continue
            peaks.append({"name": name, "lat": lat, "lng": lon,
                          "sourceIds": {"geonames": str(ident)}})
    return peaks


def links_from_routes(data, refuge_by_legacy):
    manifest = load(data / "routes-manifest.json", {"tiles": []})
    links = {}
    for tile in manifest.get("tiles", []):
        for rel in tile.get("files", []):
            # Il manifest è un elenco locale verificato, non un URL remoto.
            p = Path(rel)
            if p.is_absolute() or ".." in p.parts or p.suffix != ".json":
                raise ValueError("Percorso shard non sicuro: " + str(rel))
            payload = load(data / p)
            if payload is None:
                raise ValueError("Shard citato ma assente: " + rel)
            for route in payload.get("routes", []):
                slug = route.get("slug")
                if not isinstance(slug, str) or not slug:
                    continue
                for stop in route.get("stops", []):
                    ref = refuge_by_legacy.get(stop.get("slug"))
                    dist = stop.get("distanceM")
                    if ref is None or not isinstance(dist, (int, float)):
                        continue
                    if isinstance(dist, bool) or not 0 <= dist <= 180:
                        continue
                    link = {
                        "type": "passes_near",
                        "from": {"kind": "itinerary", "legacySlug": slug},
                        "to": {"kind": "refuge", "id": ref["id"]},
                        "distanceToPolylineM": round(dist),
                        "method": "legacy_route_stops_polyline_projection",
                        "verifiedAccess": False,
                    }
                    key = (slug, ref["id"])
                    if key not in links or dist < links[key]["distanceToPolylineM"]:
                        links[key] = link
    return sorted(links.values(), key=lambda x: (x["from"]["legacySlug"], x["to"]["id"]))


def run(root=ROOT, out=None, registry_file=None, strict=False):
    root = Path(root)
    out = Path(out) if out else root / "build" / "import-refuges-v1"
    data = root / "public" / "data"
    source = load(data / "alpine-places.json")
    if not isinstance(source, dict) or not isinstance(source.get("places"), list):
        raise ValueError("Snapshot alpine-places.json assente o invalido")
    refuges = [p for p in source["places"] if p.get("kind") == "rifugio"]
    villages = [p for p in source["places"] if p.get("kind") == "borgo"]
    if not refuges:
        raise ValueError("Nessun rifugio: l'import fallisce senza cancellare i dati")
    by_source = {}
    for place in refuges:
        key = source_ref(place)["key"]
        if key in by_source:
            raise ValueError("ID OSM duplicato: " + key)
        by_source[key] = place
    registry_path = Path(registry_file) if registry_file else out / "identity-registry.json"
    existing = load(registry_path, {})
    identities, conflicts = assign_identities(refuges, existing)
    duplicate_pairs = suspected_duplicates(refuges, identities)
    entities = []
    for key, place in sorted(by_source.items()):
        entities.append(build_refuge(place, identities[key], source.get("generatedAt")))
    by_legacy = {p["slugAliases"][0]: p for p in entities}
    town_candidates = []
    for p in villages:
        coordinates(p)
        town_candidates.append({"name": p["name"], "lat": p["lat"], "lng": p["lng"],
                                "legacySlug": p["slug"],
                                "sourceIds": {"osm": source_ref(p)["key"]}})
    peaks = peak_candidates(data)
    for entity in entities:
        point = {"lat": entity["geo"]["point"]["lat"], "lng": entity["geo"]["point"]["lon"]}
        entity["relations"] = (
            nearby_relations(point, town_candidates, "locality", 12, 3) +
            nearby_relations(point, peaks, "mountain", 6, 3))
    route_links = links_from_routes(data, by_legacy)
    field_registry = load(FIELD_REGISTRY_PATH)
    if not isinstance(field_registry, dict) or field_registry.get("kind") != "refuge":
        raise ValueError("Registro rifugi obbligatorio non disponibile")
    coverage = inventory_coverage(entities, refuges, field_registry, route_links)
    # Una digest del sottoinsieme sorgente permette di rilevare aggiornamenti senza
    # spacciare la data di assemblaggio per verifica del singolo campo.
    raw = {"kind": "refuge", "sourceDataset": "public/data/alpine-places.json",
           "snapshotDate": source.get("generatedAt"),
           "licence": LICENCE, "records": [by_source[k] for k in sorted(by_source)]}
    digest = hashlib.sha256(canonical_json(raw)).hexdigest()
    status = {
        "schemaVersion": "1.0", "status": "staging_only",
        "source": "OSM snapshot legacy", "snapshotSha256": digest,
        "sourceDatasetDate": source.get("generatedAt"),
        "refuges": len(entities), "nearLocalityLinks": sum(
            x["targetRef"]["kind"] == "locality" for e in entities for x in e["relations"]),
        "nearMountainLinks": sum(
            x["targetRef"]["kind"] == "mountain" for e in entities for x in e["relations"]),
        "routeProximityLinks": len(route_links),
        "slugCollisionsReview": len(conflicts),
        "candidateDuplicatePairs": len(duplicate_pairs),
        "metadataFieldsTracked": coverage["fieldCount"],
        "media": {"photosAccepted": sum(len(e["media"]) for e in entities),
                  "photoCandidates": sum(sum(m["kind"] == "photo" for m in e.get("mediaCandidates", [])) for e in entities),
                  "logoCandidates": sum(sum(m["kind"] == "logo" for m in e.get("mediaCandidates", [])) for e in entities),
                  "webcamCandidates": sum(sum(m["kind"] == "webcam" for m in e.get("mediaCandidates", [])) for e in entities)},
        "missingElevation": sum("elevationM" not in e["facts"] for e in entities),
        "missingVerifiedOpeningStatus": len(entities),
        "searchIndexable": 0, "connectedToCai": 0,
        "warnings": ["Non e un import live; metadata snapshot preesistente",
                     "Nessuna riconciliazione automatica CAI/SAT",
                     "Nessuna raggiungibilita o apertura inferita"],
    }
    if strict and (len(entities) != len(by_source) or len({e["id"] for e in entities}) != len(entities)):
        raise ValueError("Integrita entita violata")
    if strict and len({e["slug"] for e in entities}) != len(entities):
        raise ValueError("Collisioni di permalink")
    write(out / "raw" / ("osm-refuges-" + digest + ".json"), raw, immutable=True)
    write(out / "refuges.json", {"schemaVersion": "1.0", "status": "staging_only",
                                "sourceSnapshotSha256": digest, "entities": entities})
    write(out / "links.json", {"schemaVersion": "1.0", "status": "staging_only",
                               "edges": route_links})
    write(out / "identity-registry.json", identities)
    write(out / "field-coverage.json", coverage)
    write(out / "review.json", {"slugConflicts": conflicts,
                                "candidateDuplicates": duplicate_pairs,
                                "linksRequireEntityResolution": True})
    write(out / "report.json", status)
    return status


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--root", type=Path, default=ROOT)
    p.add_argument("--out-dir", type=Path)
    p.add_argument("--registry-file", type=Path)
    p.add_argument("--strict", action="store_true")
    args = p.parse_args()
    print(json.dumps(run(args.root, args.out_dir, args.registry_file, args.strict),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
