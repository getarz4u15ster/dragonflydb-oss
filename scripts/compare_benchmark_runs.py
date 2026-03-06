#!/usr/bin/env python3
"""
Compare two redis-benchmark run summaries (e.g. Redis vs Dragonfly).
Reads logs/benchmark_redis.json and logs/benchmark_dragonfly.json by default, or two paths as args.

Usage: python scripts/compare_benchmark_runs.py [path_a] [path_b]
  Default: logs/benchmark_redis.json logs/benchmark_dragonfly.json (from repo root)
"""
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_A = os.path.join(REPO_ROOT, "logs", "benchmark_redis.json")
DEFAULT_B = os.path.join(REPO_ROOT, "logs", "benchmark_dragonfly.json")


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
        print("Run benchmark with BENCHMARK_LABEL=redis (e.g. RUN_LOAD_DEMO=benchmark ./start_demo.sh)", file=sys.stderr)
        sys.exit(1)
    if not os.path.isfile(path_b):
        print(f"Missing: {path_b}", file=sys.stderr)
        print("Run benchmark with BENCHMARK_LABEL=dragonfly (e.g. USE_DRAGONFLY=1 RUN_LOAD_DEMO=benchmark ./start_demo.sh)", file=sys.stderr)
        sys.exit(1)

    a = load_summary(path_a)
    b = load_summary(path_b)
    label_a = a.get("label", os.path.basename(path_a))
    label_b = b.get("label", os.path.basename(path_b))

    print("--- Benchmark run comparison ---")
    print()
    print("Using logs:")
    print(f"  A: {path_a}  (run: {a.get('timestamp', 'n/a')})")
    print(f"  B: {path_b}  (run: {b.get('timestamp', 'n/a')})")
    print()
    print(f"{'Metric':<28} {label_a:>14} {label_b:>14}  Winner / ratio")
    print("-" * 72)

    if a.get("clients") != b.get("clients") or a.get("requests") != b.get("requests"):
        print("(Different clients/requests between runs; comparison may be misleading.)")
        print()

    def row(metric, val_a, val_b):
        winner = label_b if val_b > val_a else label_a
        ratio = val_b / val_a if val_a else 0
        print(f"{metric:<28} {val_a:>14.2f} {val_b:>14.2f}  {winner}  ({ratio:.2f}x)")

    row("SET requests/sec", a.get("set_requests_per_sec", 0), b.get("set_requests_per_sec", 0))
    row("GET requests/sec", a.get("get_requests_per_sec", 0), b.get("get_requests_per_sec", 0))
    row("Combined requests/sec", a.get("combined_requests_per_sec", 0), b.get("combined_requests_per_sec", 0))
    print("-" * 72)
    print()
    print("(Higher = better throughput.)")


if __name__ == "__main__":
    main()
