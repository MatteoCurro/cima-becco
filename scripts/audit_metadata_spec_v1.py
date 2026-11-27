#!/usr/bin/env python3
"""Audit della copertura progettuale dei metadati, senza traffico di rete.

NON è un importatore: ogni voce estratta dalla Bibbia è un REQUISITO DA MAPPARE,
non un valore acquisito, verificato o pubblicabile. Il registro fonti annota
anche i fallimenti dei piloti e le licenze non confermate.
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "MODELLO_METADATI_E_LAYOUT.md"
SOURCES = ROOT / "scripts" / "metadata_source_registry_v1.json"
REFUGE = ROOT / "scripts" / "refuge_field_registry_v1.json"
EXPECTED = set(range(1, 28))

ALIASES = {
    "OSM": "osm", "WD": "wikidata", "WC": "commons",
    "WP": "wikipedia", "CAI": "cai_refuges", "SAT": "sat",
    "ISTAT": "istat", "DAIT": "dait", "OB": "openbeta",
    "METEO": "open_meteo", "OFF": "official_operator", "USR": "community",
    "GeoNames": "geonames", "INFOMONT": "cai_infomont",
    "FASI": "fasi", "OpenBeta": "openbeta", "Commons": "commons",
    "Wikidata": "wikidata", "ARPA": "regional_meteo",
}
REFUGE_ALIASES = {
    "all_sources": None, "internal": "atlas_graph",
    "review_process": None, "cai": "cai_refuges",
    "official": "official_operator", "archives": "iccd_archives",
    "geoportal": "regional_geoportal",
    "regional_agency": "regional_meteo",
    "park_authority": "park_authorities",
    "weather_provider": "open_meteo",
    "climate_provider": "open_meteo",
    "authorized_provider": "official_operator",
    "authorized_webcam_provider": "webcam_operator",
    "trails_graph": "atlas_graph",
}
for _id in (
    "osm", "sat", "wikidata", "commons", "open_meteo", "dem",
    "atlas_graph", "istat", "wikipedia",
):
    REFUGE_ALIASES[_id] = _id

SECTIONS = re.compile(r"^##\s+(\d+)\.\s+(.+?)\s*$")
TABLE = re.compile(r"^\|(.+)\|\s*$")
SEP = re.compile(r"^:?-{3,}:?$")
STRONG_BULLET = re.compile(r"^\s*-\s+\*\*(.+?)\*\*\s*:\s*(.+)$")


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def parse_sections(text):
    grouped = {}
    current = None
    for n, line in enumerate(text.splitlines(), start=1):
        match = SECTIONS.match(line)
        if match:
            current = int(match[1])
            if current in EXPECTED:
                if current in grouped:
                    raise ValueError(f"Sezione duplicata #{current}")
                grouped[current] = {"title": match[2], "line": n, "lines": []}
            continue
        if current in grouped:
            grouped[current]["lines"].append((n, line))
    missing = EXPECTED - set(grouped)
    if missing:
        raise ValueError("Bibbia senza sezioni richieste: " + str(sorted(missing)))
    return grouped


def normalize_hint(statement):
    s = statement.casefold()
    groups = [
        (r"webcam|stream|logo|stemma|foto|immagini|fotograf|topo|video|media\b", "verified_media_asset"),
        (r"meteo|temperature|precipit|neve|vento|clima|modello", "dated_time_series"),
        (r"chiusur|restrizion|diviet|allert|nidificaz|avvis|sicurezza|pericol", "dated_official_notice"),
        (r"grado|difficolt|sac.scale|uiaa|frances|ferrata.scale", "original_grade_and_scale"),
        (r"tappa|sentier|itinerar|via\s|percorso|accessi|raggiungibil|prossimit", "evidenced_typed_relation"),
        (r"quota|altezza|elevaz|prominenza|dislivello|profondità", "unit_method_datum_provenance"),
        (r"propriet|gestore|apertur|orari|prenot|prezz|mandato|sindaco|capien|posti letto", "dated_operational_fact"),
        (r"popolaz|resident|censim", "dated_admin_statistic"),
        (r"storia|biograf|etimolog|intitolaz|prima ascension|cultura|tradiz", "referenced_editorial_fact"),
        (r"coordinate|confini|geo\.|perimetro|latitudine|longitudine", "spatial_geometry_crs_provenance"),
    ]
    for pattern, rule in groups:
        if re.search(pattern, s):
            return rule
    return "typed_nullable_fact_with_field_provenance"


def rows_for_section(number, section):
    """Conserva una voce per RIGA della Bibbia; non inventa sotto-campi."""
    result = []
    for line_no, line in section["lines"]:
        m = TABLE.match(line.strip())
        if m:
            cells = [cell.strip() for cell in m[1].split("|")]
            if not cells or any(SEP.fullmatch(c.replace(" ", "")) for c in cells):
                continue
            header = cells[0].casefold()
            if header in ("campo canonico", "metadati", "tipo", "tipologia", "fonte", "modulo"):
                continue
            if not cells[0] or len(cells) < 2:
                continue
            text = cells[0]
            # Le sezioni 23/24/25 hanno una tipologia in prima colonna
            # e i veri metadati in seconda: preserviamo entrambi.
            if number in (23, 24, 25):
                text = cells[0] + ": " + cells[1]
            result.append((line_no, text, "table"))
            continue
        bullet = STRONG_BULLET.match(line)
        if bullet:
            result.append((line_no, bullet[1] + ": " + bullet[2], "bullet"))
        elif line.startswith("Campi:") or line.startswith("**Schema di una misura**:"):
            result.append((line_no, line.split(":", 1)[1].strip(), "paragraph"))
        elif number == 27 and line.startswith("Utente/consenso"):
            result.append((line_no, line.strip(), "paragraph"))
        elif line.startswith("**Identità**:"):
            result.append((line_no, line.split(":", 1)[1].strip(), "paragraph"))
        elif number == 19 and re.match(r"^\*\*(Area|Blocco|Problema)\*\*:", line):
            # Sezione boulder: tre entità figlie descritte in paragrafi,
            # non in tabelle. Non perdere questi requisiti.
            result.append((line_no, line.strip(), "paragraph"))
    return result


def compile_plan(spec_text, registry, refuge_registry):
    sections = parse_sections(spec_text)
    source_ids = {src["id"] for src in registry["sources"]}
    if len(source_ids) != len(registry["sources"]):
        raise ValueError("Duplicati nel registro fonti")
    mapping = {int(x["sectionId"]): x for x in registry["sections"]}
    if set(mapping) != EXPECTED - {1}:
        raise ValueError("Il registro fonti non copre esattamente sezioni 2-27")
    for entry in mapping.values():
        if not entry["candidates"] or any(src not in source_ids for src in entry["candidates"]):
            raise ValueError("Provider sconosciuto o lista vuota: " + str(entry))
    for f in refuge_registry["fields"]:
        for provider in f["sources"]:
            alias = REFUGE_ALIASES.get(provider, provider)
            if alias is not None and alias not in source_ids:
                raise ValueError(f"Campo rifugio {f['key']} usa provider sconosciuto {provider}")
    requirements = []
    seen = set()
    for section_num in sorted(sections):
        section = sections[section_num]
        for line, statement, form in rows_for_section(section_num, section):
            token = f"{section_num:02d}:" + hashlib.sha256(
                statement.encode("utf-8")).hexdigest()[:12]
            if token in seen:
                raise ValueError("Voce duplicata nella Bibbia: " + token)
            seen.add(token)
            candidates = list(mapping[section_num]["candidates"]) if section_num != 1 else list(source_ids)
            # Per il contratto comune tutte le fonti sono potenzialmente
            # pertinenti. Per le schede il mapping è un insieme *possibile*
            # per tipologia, mai prova che un campo esista presso la fonte.
            requirements.append({
                "requirementId": token,
                "specSection": section_num,
                "sectionTitle": section["title"],
                "specLine": line,
                "literalRequirement": statement,
                "statementFormat": form,
                "candidateSourcesForEntityKind": sorted(candidates),
                "normalizationHint": normalize_hint(statement),
                "canonicalFieldMappingStatus": "needs_field_level_mapping",
                "acquisitionStatus": "NOT_ASSERTED",
                "verificationStatus": "NOT_ASSERTED",
                "publicationStatus": "NOT_AUTHORIZED_BY_THIS_REPORT",
            })
    counts = Counter(x["specSection"] for x in requirements)
    if set(counts) != EXPECTED:
        raise ValueError("Sezioni canoniche con zero metadati: " + str(sorted(EXPECTED - set(counts))))
    hints = Counter(x["normalizationHint"] for x in requirements)
    return {
        "schemaVersion": "1.0",
        "canonicalSpec": "docs/MODELLO_METADATI_E_LAYOUT.md",
        "sourceRegistry": "scripts/metadata_source_registry_v1.json",
        "refugeRegistry": "scripts/refuge_field_registry_v1.json",
        "meaning": "Inventario integrale di requisiti editoriali: nessun numero indica dati acquisiti.",
        "sectionCount": len(counts),
        "sourceCount": len(source_ids),
        "refugeRegistryFields": len(refuge_registry["fields"]),
        "canonicalRequirementRows": len(requirements),
        "requirementsBySection": {str(k): counts[k] for k in sorted(counts)},
        "normalizationCategories": dict(sorted(hints.items())),
        "fieldsWithConfirmedAcquisitionByThisAudit": 0,
        "requirements": requirements,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--spec", type=Path, default=SPEC)
    p.add_argument("--sources", type=Path, default=SOURCES)
    p.add_argument("--refuge", type=Path, default=REFUGE)
    p.add_argument("--out", type=Path, default=ROOT / "build" / "metadata-audit" / "requirements.json")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()
    report = compile_plan(
        args.spec.read_text(encoding="utf-8"),
        read_json(args.sources),
        read_json(args.refuge),
    )
    if not args.check:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, ensure_ascii=False, indent=2,
                              sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "requirements"},
                     ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
