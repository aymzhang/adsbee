#!/usr/bin/env python3
"""EXAMPLE separate analysis of test records (reference only).

Deliberately decoupled from the station and the web GUI: it just reads the JSON
records the station produced and prints an aggregate summary (unit count, yield,
per-measurement pass/fail counts and value stats).

In production you'd point this — or a real pipeline (DB + Grafana/Metabase) — at
your CENTRAL store instead of a local folder. The station's job is to produce
records; analysis is a separate job that consumes them.

    python examples/example_analyze.py
"""

import glob
import json
import statistics
from collections import defaultdict
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"


def load_records(results_dir: Path) -> list[dict]:
    records = []
    for path in sorted(glob.glob(str(results_dir / "example_*.json"))):
        with open(path) as f:
            records.append(json.load(f))
    return records


def main():
    records = load_records(RESULTS_DIR)
    if not records:
        print(f"No records in {RESULTS_DIR}. Run a station first.")
        return

    total = len(records)
    passed = sum(1 for r in records if r.get("outcome") == "PASS")
    print(f"Units: {total}   PASS: {passed}   yield: {100 * passed / total:.1f}%\n")

    # Roll up per-measurement outcomes and numeric values across all records.
    outcomes: dict = defaultdict(lambda: defaultdict(int))
    values: dict = defaultdict(list)
    for r in records:
        for phase in r.get("phases", []):
            for name, meas in (phase.get("measurements") or {}).items():
                outcomes[name][meas.get("outcome", "UNSET")] += 1
                v = meas.get("measured_value")
                if isinstance(v, (int, float)):  # skip dimensioned (list) values
                    values[name].append(v)

    print("Per-measurement:")
    for name in sorted(outcomes):
        counts = " ".join(f"{k}={v}" for k, v in sorted(outcomes[name].items()))
        line = f"  {name:18s} {counts}"
        if values[name]:
            line += f"   mean={statistics.mean(values[name]):.4g}"
            if len(values[name]) > 1:
                line += f"  stdev={statistics.stdev(values[name]):.4g}"
        print(line)


if __name__ == "__main__":
    main()
