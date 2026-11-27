#!/usr/bin/env python3
"""OpenBeta metadata-only proof of concept: one page of Italian leaf areas."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

URL = "https://api.openbeta.io"
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "experiments" / "climbing-pilot"
QUERY = """
query Pilot($tokens: [String!]!, $limit: Int!, $offset: Int!) {
  areas(filter: {leaf_status: {isLeaf: true}, path_tokens: {tokens: $tokens}},
        limit: $limit, offset: $offset) {
    uuid
    area_name
    pathTokens
    metadata { lat lng }
    climbs {
      uuid name fa length boltsCount
      grades { yds vscale french }
      type { sport trad bouldering alpine tr }
      safety
      metadata { lat lng }
      content { description }
      pathTokens
    }
  }
}
"""

def normalize(data):
    records = []
    for area in data:
        for route in area.get("climbs") or []:
            grade = {k:v for k,v in (route.get("grades") or {}).items() if v}
            location = route.get("metadata") or area.get("metadata") or {}
            raw_bolts = route.get("boltsCount")
            bolts = raw_bolts if isinstance(raw_bolts, int) and not isinstance(raw_bolts,bool) and raw_bolts>=0 else None
            name = route.get("name")
            types = route.get("type") or {}
            kind = ("boulder_problem" if types.get("bouldering") else
                    "climbing_route" if types.get("sport") or types.get("trad") or types.get("alpine") or types.get("tr") else
                    "route_type_unknown")
            raw_length = route.get("length")
            length = (raw_length if isinstance(raw_length, (int, float)) and not isinstance(raw_length, bool)
                      and 0 < raw_length <= 3000 else None)
            records.append({
                "id": f"openbeta:{route.get('uuid')}",
                "name": name, "kind": kind,
                "areaId": f"openbeta:{area.get('uuid')}",
                "areaName": area.get("area_name"),
                "pathTokens": route.get("pathTokens") or area.get("pathTokens") or [],
                "geo": {"lat":location.get("lat"),"lon":location.get("lng")},
                "metadata":{
                    "grades": grade,
                    "lengthM": length,
                    "boltsCount": bolts,
                    "firstAscent": route.get("fa") or None,
                    "routeTypes": {k:v for k,v in types.items() if v},
                    "sourceDescription": (route.get("content") or {}).get("description") or None,
                    "safetyText": route.get("safety") or None,
                    "quickdrawsRecommended": None,
                    "pitchesCount": None,
                    "pitchDetails": [],
                },
                "source":{"provider":"OpenBeta","sourceId":route.get("uuid"),"licence":"CC0",
                          "url":"https://openbeta.io/climbs/"+str(route.get("uuid"))},
                "editorialStatus":"raw_unverified",
            })
    return records

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument("--fixture",type=Path)
    cli.add_argument("--country",default="Italy")
    cli.add_argument("--limit",type=int,default=25)
    args=cli.parse_args()
    if args.limit<1 or args.limit>50: cli.error("limit 1-50")
    if args.fixture:
        payload=json.loads(args.fixture.read_text(encoding="utf-8"))
    else:
        body=json.dumps({"query":QUERY,"variables":{"tokens":[args.country],"limit":args.limit,"offset":0}}).encode()
        req=Request(URL,data=body,method="POST",
            headers={"Content-Type":"application/json","Accept":"application/json",
                     "User-Agent":"CimaBecco-Research/0.1 (https://www.cimabecco.it)"})
        try:
            with urlopen(req,timeout=90) as response:
                payload=json.loads(response.read(20_000_000).decode("utf-8"))
        except (HTTPError,URLError,TimeoutError) as e:
            raise SystemExit("OpenBeta non raggiungibile: "+str(e)) from e
    if payload.get("errors"): raise SystemExit("GraphQL errors: "+json.dumps(payload["errors"])[:1500])
    areas=(payload.get("data") or {}).get("areas") or []
    records=normalize(areas)
    coverage=Counter()
    for r in records:
        for key,value in r["metadata"].items():
            if value is not None and value!=[] and value!={}: coverage[key]+=1
    report={
        "generatedAt":datetime.now(timezone.utc).isoformat(),
        "provider":"OpenBeta","countryFilter":args.country,
        "areaCount":len(areas),"recordsTotal":len(records),
        "classCounts":dict(Counter(r["kind"] for r in records)),
        "lengthKnownCount":sum(r["metadata"]["lengthM"] is not None for r in records),
        "boltsKnownCount":sum(r["metadata"]["boltsCount"] is not None for r in records),
        "metadataPresence":dict(coverage),
        "note":"Sample of first leaf areas, NOT representative of all Italy. No pitch-level data or quickdraws inferred.",
        "examples":[{"name":r["name"],"area":r["areaName"],"metadata":r["metadata"]} for r in records[:20]],
    }
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"openbeta-records.json").write_text(json.dumps({"schemaVersion":1,"records":records},ensure_ascii=False,indent=2),encoding="utf-8")
    (OUT/"openbeta-report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="examples"},ensure_ascii=False,indent=2))
    if not areas: raise SystemExit("No areas: Italy filter may differ from API hierarchy")

if __name__=="__main__":
    main()
