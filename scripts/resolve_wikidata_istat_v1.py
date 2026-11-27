#!/usr/bin/env python3
"""Resolver ausiliario del blocco COMUNI: OSM Wikidata QID -> Wikidata P635.

L'ISTAT resta la fonte primaria. Fallimenti SPARQL non generano associazioni
euristiche. Nessun aggiornamento in public/data, nessuna modifica ai borghi.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
API = "https://query.wikidata.org/sparql"
USER_AGENT = "CimaBecco-MunicipalitiesPilot/1.0 (https://www.cimabecco.it)"
QID = re.compile(r"Q[1-9]\d*")
CODE = re.compile(r"\d{6}")

def qids_from_osm(data):
    return sorted({row["wikidata"] for row in data.get("places", [])
                   if row.get("kind") == "borgo" and
                   isinstance(row.get("wikidata"), str) and QID.fullmatch(row["wikidata"])})

def query_codes(qids, request=None):
    if not qids:
        return []
    if any(not QID.fullmatch(q) for q in qids):
        raise ValueError("QID non valida")
    values = " ".join("wd:" + q for q in qids)
    query = ("SELECT ?item ?code WHERE { VALUES ?item { " + values +
             " } ?item wdt:P635 ?code. } LIMIT " + str(len(qids) * 6))
    uri = API + "?" + urlencode({"query": query, "format": "json"})
    req = Request(uri, headers={"User-Agent": USER_AGENT, "Accept": "application/sparql-results+json"})
    if request is None:
        request = urlopen
    with request(req, timeout=55) as handle:
        data = json.load(handle)
    records = []
    for hit in data.get("results", {}).get("bindings", []):
        item = str(hit.get("item", {}).get("value", "")).rsplit("/", 1)[-1]
        code = str(hit.get("code", {}).get("value", ""))
        if item in qids and CODE.fullmatch(code):
            records.append({"wikidata": item, "istatCode": code,
                            "sourceId": "wikidata:" + item + ":P635",
                            "sourceUrl": "https://www.wikidata.org/wiki/" + item,
                            "method": "reported"})
    return records

def resolve(data, batch=80, pause=0.75, request=None):
    ids = qids_from_osm(data)
    found = []
    errors = []
    for offset in range(0, len(ids), batch):
        part = ids[offset:offset + batch]
        try:
            found.extend(query_codes(part, request=request))
        except Exception as exc:
            errors.append({"offset": offset, "count": len(part), "error": str(exc)[:220]})
        if pause and offset + batch < len(ids):
            time.sleep(pause)
    unique = {(r["wikidata"], r["istatCode"]): r for r in found}
    return {"source": API, "property": "P635", "qidsExamined": len(ids),
            "associations": sorted(unique.values(), key=lambda r: (r["istatCode"], r["wikidata"])),
            "errors": errors}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--osm", type=Path, default=ROOT / "public/data/alpine-places.json")
    p.add_argument("--out", type=Path, default=ROOT / "build/import-municipalities-v1/wikidata-resolver.json")
    p.add_argument("--batch", type=int, default=80)
    args = p.parse_args()
    if args.batch not in range(1, 121):
        p.error("batch 1..120")
    result = resolve(json.loads(args.osm.read_text(encoding="utf-8")), batch=args.batch)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "associations"}, ensure_ascii=False))
    if result["errors"]:
        raise SystemExit("Wikidata P635 non completo: pilot review, niente associazioni parziali")

if __name__ == "__main__":
    main()
