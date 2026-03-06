#!/usr/bin/env python3
"""
Run redis-benchmark, parse output, and write a summary JSON for comparison.
Used when RUN_LOAD_DEMO=benchmark in start_demo.sh (or run standalone with BENCHMARK_LABEL set).

Writes logs/benchmark_<label>.json and appends to logs/benchmark_runs.log.
Requires redis-benchmark on PATH.

Usage: python scripts/run_benchmark.py [host] [port]
  Env: REDIS_HOST, REDIS_PORT, BENCHMARK_LABEL (or LOAD_RUN_LABEL), BENCHMARK_CLIENTS, BENCHMARK_REQUESTS
"""
import json
import os
import re
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(REPO_ROOT, "logs")

HOST = os.getenv("REDIS_HOST", sys.argv[1] if len(sys.argv) > 1 else "localhost")
PORT = int(os.getenv("REDIS_PORT", sys.argv[2] if len(sys.argv) > 2 else "6379"))
LABEL = os.getenv("BENCHMARK_LABEL") or os.getenv("LOAD_RUN_LABEL", "").strip()
CLIENTS = int(os.getenv("BENCHMARK_CLIENTS", "256"))
REQUESTS = int(os.getenv("BENCHMARK_REQUESTS", "2000000"))


def main():
    if not LABEL:
        print("Set BENCHMARK_LABEL or LOAD_RUN_LABEL (e.g. redis or dragonfly)", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "redis-benchmark", "-h", HOST, "-p", str(PORT),
        "-c", str(CLIENTS), "-n", str(REQUESTS), "-t", "get,set", "-q"
    ]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    stdout = result.stdout or ""
    stderr = result.stderr or ""
    if result.returncode != 0:
        print(stderr, file=sys.stderr)
        print("redis-benchmark failed", file=sys.stderr)
        sys.exit(1)

    # Parse "SET: 50000.00 requests per second" and "GET: 60000.00 requests per second"
    set_rps = get_rps = None
    for line in stdout.splitlines():
        m = re.match(r"SET:\s+([\d.]+)\s+requests per second", line, re.I)
        if m:
            set_rps = float(m.group(1))
        m = re.match(r"GET:\s+([\d.]+)\s+requests per second", line, re.I)
        if m:
            get_rps = float(m.group(1))

    if set_rps is None or get_rps is None:
        print("Could not parse benchmark output:", file=sys.stderr)
        print(stdout, file=sys.stderr)
        sys.exit(1)

    summary = {
        "label": LABEL,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "host": HOST,
        "port": PORT,
        "clients": CLIENTS,
        "requests": REQUESTS,
        "set_requests_per_sec": round(set_rps, 2),
        "get_requests_per_sec": round(get_rps, 2),
        "combined_requests_per_sec": round(set_rps + get_rps, 2),
    }

    os.makedirs(LOG_DIR, exist_ok=True)
    out_path = os.path.join(LOG_DIR, f"benchmark_{LABEL}.json")
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Summary written to {out_path}")
    print(f"  SET: {set_rps:.0f} req/s  GET: {get_rps:.0f} req/s  combined: {set_rps + get_rps:.0f} req/s")

    runs_log = os.path.join(LOG_DIR, "benchmark_runs.log")
    with open(runs_log, "a") as f:
        f.write(
            f"{summary['timestamp']}\t{LABEL}\t{CLIENTS}\t{REQUESTS}\t"
            f"{set_rps:.1f}\t{get_rps:.1f}\t{set_rps + get_rps:.1f}\n"
        )
    print(f"Appended to {runs_log}")


if __name__ == "__main__":
    main()
