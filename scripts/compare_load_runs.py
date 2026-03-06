#!/usr/bin/env python3
"""
Compare two load-run summaries (e.g. Redis vs Dragonfly).
Reads logs/load_redis.json and logs/load_dragonfly.json by default, or two paths as args.

Usage: python scripts/compare_load_runs.py [path_a] [path_b]
  Default: logs/load_redis.json logs/load_dragonfly.json (from repo root)
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_A = os.path.join(REPO_ROOT, "logs", "load_redis.json")
DEFAULT_B = os.path.join(REPO_ROOT, "logs", "load_dragonfly.json")


def load_summary(path):
    with open(path) as f:
        return json.load(f)


def main():
    if len(sys.argv) >= 3:
        path_a, path_b = sys.argv[1], sys.argv[2]
    else:
        path_a, path_b = DEFAULT_A, DEFAULT_B

    if not os.path.isfile(path_a):
        print(f"Missing: {path_a}", file=sys.stderr)
        print("Run load with LOAD_RUN_LABEL=redis (e.g. RUN_LOAD_DEMO=1 ./start_demo.sh)", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(path_b):
        print(f"Missing: {path_b}", file=sys.stderr)
        print("Run load with LOAD_RUN_LABEL=dragonfly (e.g. USE_DRAGONFLY=1 RUN_LOAD_DEMO=1 ./start_demo.sh)", file=sys.stderr)
        sys.exit(1)

    a = load_summary(path_a)
    b = load_summary(path_b)
    label_a = a.get("label", os.path.basename(path_a))
    label_b = b.get("label", os.path.basename(path_b))

    print("--- Load run comparison ---")
    print()
    print("Using logs:")
    print(f"  A: {path_a}  (run: {a.get('timestamp', 'n/a')})")
    print(f"  B: {path_b}  (run: {b.get('timestamp', 'n/a')})")
    print()
    print(f"{'Metric':<22} {label_a:>14} {label_b:>14}  Winner / ratio")
    print("-" * 65)

    # Same workload check
    if a.get("ops") != b.get("ops") or a.get("workers") != b.get("workers"):
        print("(Different ops/workers between runs; comparison may be misleading.)")
        print()

    elapsed_a, elapsed_b = a.get("elapsed_sec"), b.get("elapsed_sec")
    ops_a, ops_b = a.get("ops_per_sec"), b.get("ops_per_sec")

    def row(metric, val_a, val_b, higher_better=True):
        winner = label_b if (val_b > val_a) == higher_better else label_a
        ratio = val_b / val_a if val_a else 0
        print(f"{metric:<22} {val_a:>14} {val_b:>14}  {winner}  ({ratio:.2f}x)")

    row("elapsed_sec", elapsed_a, elapsed_b, higher_better=False)
    row("ops_per_sec", ops_a, ops_b, higher_better=True)
    print("-" * 65)
    print()
    print("(Lower elapsed_sec = faster. Higher ops_per_sec = better throughput.)")


if __name__ == "__main__":
    main()
