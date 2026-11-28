#!/usr/bin/env python3
"""Summit import cursor: advance only after a committed, successful G2 release.

Use the shared import-history event contract. A failed run cannot skip a batch,
and after the final partial batch the scan restarts at the first candidate.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def next_offset(history, size=100):
    if type(size) is not int or not 1 <= size <= 500:
        raise ValueError("Invalid summit batch size")
    events=(history or {}).get("events", [])
    if not isinstance(events, list):
        raise ValueError("Invalid summit import history")
    for event in reversed(events):
        if not isinstance(event, dict) or event.get("pipeline")!="cime" or event.get("status")!="success":
            continue
        r=event.get("report") or {}
        offset,count,eligible=r.get("offset"),r.get("selectedCandidates"),r.get("eligible")
        if (type(offset) is not int or offset<0 or type(count) is not int or count<0
            or type(eligible) is not int or eligible<0):
            continue
        if count<size or offset+size>=eligible:
            return 0
        return offset+size
    return 0


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--history",type=Path,required=True)
    p.add_argument("--size",type=int,default=100)
    a=p.parse_args()
    data=json.loads(a.history.read_text()) if a.history.exists() else None
    print(next_offset(data,a.size))


if __name__=="__main__":
    main()
