#!/usr/bin/env python3
"""Blocco 2: bivacchi, capanne sociali, punti d'appoggio e ricoveri.

Reuses the *complete* normalized CAI archive already acquired for block 1
rather than scraping it again. Retains full facts in cai-refuges-v1.json and
publishes only relevant facts for the atlas. Source/credit IDs remain in every
fact and image, but attribution belongs to /fonti-e-crediti/, not dossiers.

This release is never allowed to relabel alpine huts solely by proximity, to
claim a shelter is currently open, or to convert water=yes into potable water.
"""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import re

from import_refuges_v1 import canonical_json, load, write
from reconcile_cai_osm_refuges_v1 import distance_m, name_score

ROOT = Path(__file__).resolve().parents[1]
CHANNEL = "CAI_OSM_BIVOUACS_SHELTERS"
CAI_TO_KIND = {
    ("bivacco", "Bivacco"): ("bivouac", "fixed_bivouac", "Bivacco"),
    ("other", "Capanna sociale"): ("shelter", "social_cabin", "Capanna sociale"),
    ("other", "Punto d'appoggio"): ("shelter", "support_point", "Punto d'appoggio"),
}
# All data remains in the CAI archival JSON; these are fields meaningful in a
# bivouac dossier. Omit hotel/certification noise, nulls and contact internals.
VISIBLE_FACTS = frozenset({
    "elevationM", "bedsTotal", "bedsWinter", "owner", "ownerClassReported",
    "manager", "yearBuilt", "yearRebuilt", "description", "aliases",
    "regionReported", "provinceReported", "municipalityNameReported",
    "localityNameReported", "mountainGroupNameReported", "valleyName",
    "protectedAreaName", "waterAvailableReported", "outsideWater",
    "waterSourceTypeReported", "electricity", "solarPower", "generatorPower",
    "hydropower", "kitchen", "heatingTypeReported", "sleepingBagLiner",
    "hotWater", "accessibleToilets", "accessibility", "carAccessibilityReported",
    "pets", "phone", "email", "website", "selfManaged",
    "caiCatalogueStatus", "caiCategory", "caiStructureTypeOriginal",
    "caiStatusOriginal", "officialFacebookCandidate",
})
LABELS = {
    "bedsTotal": "Posti dichiarati", "bedsWinter": "Posti invernali dichiarati",
    "yearBuilt": "Anno di costruzione", "yearRebuilt": "Anno di ristrutturazione",
    "owner": "Proprietà dichiarata", "ownerClassReported": "Tipo di proprietà",
    "waterAvailableReported": "Acqua segnalata (non potabilità)",
    "outsideWater": "Acqua esterna segnalata (non potabilità)",
    "waterSourceTypeReported": "Tipologia della fonte idrica",
    "heatingTypeReported": "Riscaldamento dichiarato",
    "kitchen": "Angolo cottura dichiarato", "sleepingBagLiner": "Sacco lenzuolo",
    "electricity": "Energia elettrica dichiarata",
    "solarPower": "Pannelli solari dichiarati",
    "accessibleToilets": "Servizi accessibili dichiarati",
    "caiCatalogueStatus": "Stato amministrativo CAI (non apertura)",
    "caiStatusOriginal": "Stato catalogo originale",
    "caiStructureTypeOriginal": "Tipologia CAI originale",
    "municipalityNameReported": "Comune dichiarato",
    "mountainGroupNameReported": "Gruppo montuoso dichiarato",
    "protectedAreaName": "Area protetta dichiarata",
}
OSM_SOURCE_RE = re.compile(r"^https://www\.openstreetmap\.org/(node|way|relation)/([1-9]\d*)$")
CAI_ID_RE = re.compile(r"^\d{1,20}$")
SAFE_SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
CONFIDENT_M = 45
CONFIDENT_SIM = 0.75
REVIEW_M = 170
REVIEW_SIM = 0.35


def require(test, message):
    if not test:
        raise ValueError(message)


def provenance_id(record):
    match = OSM_SOURCE_RE.fullmatch(record.get("osmUrl", ""))
    return match.group(1) + "/" + match.group(2) if match else None


def valid_position(lat, lng):
    return all(isinstance(x, (float, int)) and not isinstance(x, bool) and
               math.isfinite(x) for x in (lat, lng)) and -90 <= lat <= 90 and -180 <= lng <= 180


def factor(fact, *, key):
    require(isinstance(fact, dict) and isinstance(fact.get("sourceId"), str)
            and isinstance(fact.get("sourceUrl"), str),
            "Fatto " + key + " senza provenienza")
    require(fact.get("value") is not None and isinstance(fact["value"], (bool, int, float, str)),
            "Fatto " + key + " non scalare")
    result = deepcopy(fact)
    result.setdefault("label", LABELS.get(key))
    result.pop("rawValue", None)
    return result


def cai_entity(row):
    key = (row.get("kind"), row.get("originalType"))
    if key not in CAI_TO_KIND:
        return None
    kind, subtype, label = CAI_TO_KIND[key]
    cai_id = str(row.get("caiId", ""))
    require(bool(CAI_ID_RE.fullmatch(cai_id)), "ID CAI non valido")
    require(row.get("sourceIds", {}).get("cai") == cai_id,
            "ID CAI e sourceIds incoerenti")
    require(valid_position(row.get("lat"), row.get("lng")), "Coordinate CAI non valide")
    name = row.get("name")
    require(isinstance(name, str) and bool(name.strip()), "Nome CAI assente")
    facts = {k: factor(v, key=k) for k, v in (row.get("facts") or {}).items()
             if k in VISIBLE_FACTS}
    media = []
    for m in row.get("media") or []:
        if (isinstance(m, dict) and m.get("kind") in ("photo", "historical_photo", "logo")
            and isinstance(m.get("url"), str) and m["url"].startswith("https://")
            and m.get("sourceUrl") == "https://rifugi.cai.it/shelters/" + cai_id
            and m.get("subjectVerified") is True and m.get("reuseAllowed") is True):
            media.append(deepcopy(m))
    desc = facts.get("description", {}).get("value")
    return {
        "id": "cai:" + cai_id, "kind": kind, "subtype": subtype,
        "name": name, "slug": "cai-" + cai_id, "slugAliases": [],
        "sourceIds": {"cai": cai_id},
        "geo": {"point": {"lat": row["lat"], "lng": row["lng"]},
                "method": "reported", "sourceUrl": row["sourceUrl"]},
        "facts": facts, "factsAlternatives": [
            x for x in row.get("factsAlternatives", [])
            if isinstance(x, dict) and x.get("key") in VISIBLE_FACTS],
        "media": media, "relations": [], "webcams": [],
        "officialUrl": row["sourceUrl"],
        "description": desc if isinstance(desc, str) else None,
        "shelterTypeLabel": label,
        "administrativeHierarchy": {
            "region": facts.get("regionReported", {}).get("value"),
            "province": facts.get("provinceReported", {}).get("value"),
            "municipality": facts.get("municipalityNameReported", {}).get("value"),
        },
        "quality": {"gate": "G1", "seoIndexable": False,
                    "verifiedAccess": False, "openNowVerified": False},
        "safety": {"accessConfirmed": False, "occupancyConfirmed": False,
                   "waterPotabilityConfirmed": False, "openingConfirmed": False},
        "editorialStatus": "enriched",
        "revision": row.get("revision"),
        "archivalRecordId": "cai:" + cai_id,
    }


def osm_entity(row):
    osm_id = provenance_id(row)
    require(osm_id and row.get("kind") == "bivacco",
            "Entità legacy non è bivacco OSM")
    require(valid_position(row.get("lat"), row.get("lng")), "Coordinate OSM non valide")
    slug = row.get("slug")
    require(isinstance(slug, str) and SAFE_SLUG.fullmatch(slug),
            "Slug bivacco OSM non valido")
    url = row["osmUrl"]
    facts = {}
    for attr, target, unit in [
        ("elevationM", "elevationM", "m"),
        ("capacity", "bedsTotal", "posti"),
        ("operator", "operatorReported", None),
        ("website", "website", None),
        ("winterRoom", "winterRoomReported", None),
        ("access", "accessReported", None),
    ]:
        value = row.get(attr)
        if value is None:
            continue
        method = "estimated" if attr == "elevationM" and row.get("elevationSource") == "dem" else "reported"
        facts[target] = {"value": value, "sourceId": "osm:" + osm_id.replace("/", ":"),
                         "sourceUrl": url, "licence": "ODbL-1.0",
                         "method": method, "unit": unit, "label": LABELS.get(target)}
    media = []
    photo = row.get("photo")
    if isinstance(photo, dict) and (photo.get("url") or "").startswith("https://") and photo.get("sourceUrl") and photo.get("license"):
        media.append({"id": "osm:photo:" + osm_id.replace("/", ":"),
                      "kind": "photo", "url": photo["url"],
                      "sourceUrl": photo["sourceUrl"],
                      "licence": photo["license"], "author": photo.get("author"),
                      "subjectVerified": True, "reuseAllowed": True})
    return {
        "id": "osm:" + osm_id.replace("/", ":"), "kind": "bivouac",
        "subtype": "osm_bivouac_or_basic_hut",
        "name": row["name"], "slug": slug, "slugAliases": [],
        "sourceIds": {"osm": osm_id},
        "geo": {"point": {"lat": row["lat"], "lng": row["lng"]},
                "method": "reported", "sourceUrl": url},
        "facts": facts, "factsAlternatives": [], "media": media,
        "relations": [], "webcams": [], "shelterTypeLabel": "Bivacco / ricovero OSM",
        "officialUrl": row.get("website"),
        "quality": {"gate": "G0", "seoIndexable": False,
                    "verifiedAccess": False, "openNowVerified": False},
        "safety": {"accessConfirmed": False, "occupancyConfirmed": False,
                   "waterPotabilityConfirmed": False, "openingConfirmed": False},
        "editorialStatus": "raw",
    }


def proximity(a, b):
    ap, bp = a["geo"]["point"], b["geo"]["point"]
    return distance_m((ap["lat"], ap["lng"]), (bp["lat"], bp["lng"]))


def candidates(source, entries):
    result = []
    for row in entries:
        dist = proximity(source, row)
        if dist > REVIEW_M:
            continue
        score = name_score(source["name"], row["name"])
        elevation_a = source["facts"].get("elevationM", {}).get("value")
        elevation_b = row["facts"].get("elevationM", {}).get("value")
        diff = (abs(elevation_a - elevation_b)
                if isinstance(elevation_a, (int, float))
                and isinstance(elevation_b, (int, float)) else None)
        if score < REVIEW_SIM and dist > 40:
            continue
        sure = (score >= CONFIDENT_SIM and dist <= CONFIDENT_M
                and (diff is None or diff <= 120))
        result.append({
            "targetId": row["id"], "distanceM": dist,
            "nameSimilarity": score, "elevationDifferenceM": diff,
            "highConfidence": sure
        })
    return sorted(result, key=lambda e: (-e["nameSimilarity"], e["distanceM"], e["targetId"]))


def localities_near(row, locality_rows):
    loc = (row["geo"]["point"]["lat"], row["geo"]["point"]["lng"])
    candidates_ = []
    for city in locality_rows:
        if city.get("kind") != "borgo" or not valid_position(city.get("lat"), city.get("lng")):
            continue
        distance = distance_m(loc, (city["lat"], city["lng"]))
        if distance <= 15_000:
            candidates_.append((distance, city))
    candidates_.sort(key=lambda x: (x[0], x[1]["slug"]))
    return [{
        "type": "near", "target": {
            "id": "osm:" + (provenance_id(city) or city["slug"]).replace("/", ":"),
            "kind": "locality", "name": city["name"],
            "href": "/borghi/" + city["slug"] + "/",
        }, "straightLineKm": round(distance / 1000, 2),
        "method": "haversine", "verified": False,
        "accessVerified": False, "sourceUrl": city["osmUrl"],
    } for distance, city in candidates_[:3]]


def consolidate(osm, cai):
    """Preserve OSM slug, retain CAI source and alternatives without erasing data."""
    joined = deepcopy(osm)
    # Proven CAI category wins over OSM umbrella: social cabins stay shelters,
    # fixed bivouacs stay bivouacs, even if OSM used a generic basic_hut.
    joined["kind"] = cai["kind"]
    joined["sourceIds"]["cai"] = cai["sourceIds"]["cai"]
    joined["archivalRecordId"] = cai["archivalRecordId"]
    joined["officialUrl"] = cai["officialUrl"]
    joined["shelterTypeLabel"] = cai["shelterTypeLabel"]
    joined["subtype"] = cai["subtype"]
    joined["quality"] = deepcopy(cai["quality"])
    joined["editorialStatus"] = "linked"
    joined["revision"] = cai["revision"]
    joined["safety"] = deepcopy(cai["safety"])
    joined["administrativeHierarchy"] = cai["administrativeHierarchy"]
    if cai.get("description"):
        joined["description"] = cai["description"]
    for key, fact in cai["facts"].items():
        other = joined["facts"].get(key)
        if other and other.get("value") != fact.get("value"):
            joined["factsAlternatives"].append({
                "key": key, "fact": other, "reason": "Discordanza CAI/OSM; preferito il valore dichiarato CAI"})
        joined["facts"][key] = fact
    joined["factsAlternatives"].extend(cai["factsAlternatives"])
    seen = {m["id"] for m in joined["media"]}
    joined["media"].extend(m for m in cai["media"] if m["id"] not in seen)
    # canonical ID remains the OSM identity already used by the site.
    return joined


def build_release(cai_catalogue, legacy_catalogue, refuges_catalogue,
                  *, min_cai=250, min_osm=25):
    require(cai_catalogue.get("isCompleteSnapshot") is True,
            "Archivio CAI parziale: pubblicazione bloccata")
    require(isinstance(cai_catalogue.get("records"), list) and
            isinstance(legacy_catalogue.get("places"), list) and
            isinstance(refuges_catalogue.get("entities"), list),
            "Input archivio rifugi o luoghi assente")
    cai_rows = [r for r in cai_catalogue["records"]
                if (r.get("kind"), r.get("originalType")) in CAI_TO_KIND]
    require(len([r for r in cai_rows if r["kind"] == "bivacco"]) >= min_cai,
            "Regressione copertura CAI bivacchi")
    by_cai = [cai_entity(r) for r in cai_rows]
    osm_rows = [r for r in legacy_catalogue["places"] if r.get("kind") == "bivacco"]
    require(len(osm_rows) >= min_osm, "Regressione copertura OSM bivacchi")
    osm_rows_by_id = {provenance_id(r): r for r in osm_rows}
    require(None not in osm_rows_by_id and len(osm_rows_by_id) == len(osm_rows),
            "OSM bivacchi: identità duplicate o non valide")
    by_osm = [osm_entity(r) for r in osm_rows]
    # The previous block quarantined e.g. Fiamme Gialle, which CAI certifies
    # as a bivouac. Only such specific IDs may be considered for a typed move.
    legacy_refuge_map = {provenance_id(r): r for r in legacy_catalogue["places"]
                         if r.get("kind") == "rifugio"}
    quarantined = refuges_catalogue.get("quarantinedOsmIds", [])
    questionable = [r for oid in quarantined
                    if (r := legacy_refuge_map.get(oid)) is not None]
    cross_kind_osm = []
    for row in questionable:
        new = osm_entity({**row, "kind": "bivacco"})
        new["shelterTypeLabel"] = "Tipologia OSM in verifica"
        cross_kind_osm.append(new)
    targets = by_osm + cross_kind_osm
    originals = {x["id"]: x for x in targets}
    current_refuges = refuges_catalogue["entities"]
    cross_cai_refuges = {
        str(e.get("sourceIds", {}).get("cai")) for e in current_refuges
        if e.get("sourceIds", {}).get("cai")
    }
    missing = sorted(set(r["sourceIds"]["cai"] for r in by_cai) & cross_cai_refuges)
    require(not missing, "CAI ID già classificati come rifugio: " + str(missing[:6]))
    suggestions = {}
    claims = {}
    for r in by_cai:
        matches = candidates(r, targets)
        suggestions[r["sourceIds"]["cai"]] = matches
        strong = [x for x in matches if x["highConfidence"]]
        if len(matches) == 1 and len(strong) == 1:
            claims.setdefault(strong[0]["targetId"], []).append(r["sourceIds"]["cai"])
    new, merged, review, reclassified, blocked_by_refuge = [], [], [], [], []
    for r in by_cai:
        cai_id = r["sourceIds"]["cai"]
        matches = suggestions[cai_id]
        strong = [x for x in matches if x["highConfidence"]]
        if len(matches) == len(strong) == 1 and len(claims.get(strong[0]["targetId"], [])) == 1:
            osm_id = strong[0]["targetId"]
            old = originals[osm_id]
            originals[osm_id] = consolidate(old, r)
            merged.append({
                "caiId": cai_id, "osmId": old["sourceIds"]["osm"], "distanceM": strong[0]["distanceM"],
                "nameSimilarity": strong[0]["nameSimilarity"],
                "method": "unique_name_geo_elevation_type_checked",
                "legacySlug": old["slug"]
            })
            if old in cross_kind_osm:
                reclassified.append(old["sourceIds"]["osm"])
            continue
        if matches:
            review.append({"caiId": cai_id, "reason": "unresolved_osm_identity",
                           "candidates": matches, "publicDuplicateCreated": False})
            continue
        # Preserve possible overlap with an already published CAI/OSM refuge:
        # no quiet relabeling of a conflicting type in block 2.
        conflict = []
        for hut in current_refuges:
            if not valid_position(hut.get("geo", {}).get("point", {}).get("lat"),
                                  hut.get("geo", {}).get("point", {}).get("lng")):
                continue
            dist = proximity(r, hut)
            if dist <= 45 and name_score(r["name"], hut.get("name", "")) >= CONFIDENT_SIM:
                conflict.append({"id": hut["id"], "distanceM": dist})
        if conflict:
            blocked_by_refuge.append({"caiId": cai_id, "conflicts": conflict})
            continue
        new.append(r)
    # No empty quarantined (former refuge) OSM entity can enter the final
    # bivouac catalogue without a verified CAI type match.
    merged_osm = [originals[r["id"]] for r in by_osm]
    moved_osm = [originals[r["id"]] for r in cross_kind_osm
                 if r["sourceIds"]["osm"] in reclassified]
    # If CAI was withheld for review, keep the OSM record, not a duplicate.
    records = merged_osm + moved_osm + new
    ids = [r["id"] for r in records]
    slugs = [r["slug"] for r in records]
    require(len(ids) == len(set(ids)) and len(slugs) == len(set(slugs)),
            "Doppio ID/slug nel release")
    for r in records:
        r["relations"] = localities_near(r, legacy_catalogue["places"])
    records.sort(key=lambda x: x["id"])
    # An OSM bivouac may still duplicate a CAI-only record by a different
    # name at exactly the same point; flag instead of silently merging.
    suspicious_osm = []
    for r in by_osm:
        for cai_r in new:
            d = proximity(r, cai_r)
            if d < 20:
                suspicious_osm.append({"osmId": r["sourceIds"]["osm"],
                                       "caiId": cai_r["sourceIds"]["cai"],
                                       "distanceM": d,
                                       "status": "manual_review_required"})
    counts = Counter(x["subtype"] for x in records)
    dataset = {
        "schemaVersion": "2.0", "releaseChannel": CHANNEL,
        "kind": "bivouacs_and_shelters", "seoIndexable": False,
        "sourceRevisionCAI": cai_catalogue.get("contentSha256"),
        "sourceDatasetOSM": legacy_catalogue.get("generatedAt"),
        "archivalDataset": "/data/atlas/cai-refuges-v1.json",
        "attribution": [
            {"source": "CAI Unico Rifugi", "url": "https://rifugi.cai.it/",
             "licence": "Riuso confermato dal titolare del progetto"},
            {"source": "OpenStreetMap contributors", "url": "https://www.openstreetmap.org/copyright",
             "licence": "ODbL-1.0"},
        ],
        "creditPolicy": "centralized:/fonti-e-crediti/",
        "limitations": [
            "Bivacchi, capanne sociali e punti d'appoggio non sono equivalenti a rifugi custoditi",
            "Posti, acqua, riscaldamento e dotazioni sono dichiarazioni storiche, non disponibilità odierna",
            "Disponibilità d'acqua non è attestazione di potabilità",
            "Prossimità a sentieri/località non dimostra un accesso praticabile",
            "Nessun record attesta condizioni di sicurezza, manutenzione o apertura corrente",
        ],
        "reclassifiedOsmIds": sorted(set(reclassified)),
        "entities": records,
    }
    report = {
        "status": "release_ready", "schemaVersion": "2.0",
        "caiBivouacs": sum(r["kind"] == "bivouac" for r in by_cai),
        "caiSocialCabins": sum(r["subtype"] == "social_cabin" for r in by_cai),
        "caiSupportPoints": sum(r["subtype"] == "support_point" for r in by_cai),
        "osmBivouacs": len(by_osm), "matchedCaiOsm": len(merged),
        "reclassifiedOsmWrongKind": len(reclassified),
        "caiRecordsKeptForReview": len(review) + len(blocked_by_refuge),
        "caiOnlyPublished": len(new), "publicEntities": len(records),
        "publicSubtypes": dict(sorted(counts.items())),
        "photos": sum(len(x["media"]) for x in records),
        "nearRelations": sum(len(x["relations"]) for x in records),
        "provenanceFacts": sum(len(x["facts"]) for x in records),
        "idCollisionCount": len(ids) - len(set(ids)),
        "permalinkCollisionCount": len(slugs) - len(set(slugs)),
        "currentOpeningGuarantees": 0, "potableWaterGuarantees": 0,
        "creditsInline": 0,
        "catalogueSha256": hashlib.sha256(canonical_json(dataset)).hexdigest(),
    }
    review_report = {
        "schemaVersion": "2.0", "matched": merged,
        "unresolvedOSM": review, "conflictingRefugeType": blocked_by_refuge,
        "suspiciousCoincident": suspicious_osm,
        "quarantinedOriginalRefugeOSM": sorted(set(r["sourceIds"]["osm"] for r in cross_kind_osm)
                                           - set(reclassified)),
    }
    return dataset, report, review_report


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--cai", type=Path, default=ROOT / "public/data/atlas/cai-refuges-v1.json")
    p.add_argument("--legacy", type=Path, default=ROOT / "public/data/alpine-places.json")
    p.add_argument("--refuges", type=Path, default=ROOT / "public/data/atlas/refuges-v1.json")
    p.add_argument("--out", type=Path, default=ROOT / "public/data/atlas/shelters-v1.json")
    p.add_argument("--review-dir", type=Path, default=ROOT / "build/import-shelters-v1")
    args = p.parse_args()
    dataset, report, review = build_release(load(args.cai), load(args.legacy), load(args.refuges))
    write(args.out, dataset)
    write(args.review_dir / "report.json", report)
    write(args.review_dir / "identity-review.json", review)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
