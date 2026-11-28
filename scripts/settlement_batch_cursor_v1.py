#!/usr/bin/env python3
"""Select the next località batch using only verified successful release history.

A failed/aborted run cannot advance the cursor. The final incomplete batch
wraps to zero. When legacy history lacks an offset, restart safely at zero.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path


def next_offset(history: dict | None, batch_size: int = 80) -> int:
    if not isinstance(batch_size, int) or not (1 <= batch_size <= 1000):
        raise ValueError("Invalid batch size")
    events = (history or {}).get("events") or []
    if not isinstance(events, list):
        raise ValueError("Invalid import history")
    for event in reversed(events):
        if not isinstance(event, dict) or event.get("pipeline") != "localita" or event.get("status") != "success":
            continue
        report = event.get("report") or {}
        prev_offset = report.get("offset")
        checked = report.get("selectedCandidates")
        if not isinstance(prev_offset, int) or isinstance(prev_offset, bool) or prev_offset < 0:
            continue
        if not isinstance(checked, int) or isinstance(checked, bool) or checked < 0:
            continue
        if checked < batch_size:
            return 0
        return prev_offset + batch_size
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--history", type=Path, required=True)
    parser.add_argument("--size", type=int, default=80)
    args = parser.parse_args()
    history = json.loads(args.history.read_text(encoding="utf-8")) if args.history.exists() else None
    print(next_offset(history, args.size))


if __name__ == "__main__":
    main()
