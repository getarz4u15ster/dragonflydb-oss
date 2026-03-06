#!/usr/bin/env python3
"""
SET/GET load generator for Redis vs Dragonfly throughput demo.
Works with Redis, Dragonfly, or any Redis-compatible server.

To see real differentiation between Redis and Dragonfly, use high concurrency
and enough ops to push into thousands+ ops/sec (see DEMO_STYLE.md).

Usage: python load_gen.py [host] [port] [ops] [workers] [value_size]
  Default: localhost 6379 100000 50 100
  Env: REDIS_HOST, REDIS_PORT, LOAD_VALUE_SIZE (bytes)
  Env: LOAD_RUN_LABEL (e.g. redis, dragonfly) — write summary to logs/load_<label>.json and append to logs/load_runs.log
"""
import json
import os
import sys
import time
import redis
from concurrent.futures import ThreadPoolExecutor

HOST = os.getenv("REDIS_HOST", sys.argv[1] if len(sys.argv) > 1 else "localhost")
PORT = int(os.getenv("REDIS_PORT", sys.argv[2] if len(sys.argv) > 2 else "6379"))
N = int(sys.argv[3]) if len(sys.argv) > 3 else 100_000
WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 else 50
VALUE_SIZE = int(os.getenv("LOAD_VALUE_SIZE", sys.argv[5] if len(sys.argv) > 5 else "100"))
RUN_LABEL = os.getenv("LOAD_RUN_LABEL", "").strip()

def run_worker(worker_id, indices):
    r = redis.Redis(host=HOST, port=PORT, decode_responses=True)
    payload = "x" * VALUE_SIZE
    for i in indices:
        r.set(f"key:{i}", payload)
        r.get(f"key:{i}")

def main():
    print(f"Load gen: {HOST}:{PORT}  ops={N}  workers={WORKERS}  value_size={VALUE_SIZE}B")
    per_worker = (N + WORKERS - 1) // WORKERS
    chunks = [range(i * per_worker, min((i + 1) * per_worker, N)) for i in range(WORKERS)]
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(lambda arg: run_worker(arg[0], arg[1]), enumerate(chunks)))
    elapsed = time.perf_counter() - start
    ops_per_sec = N * 2 / elapsed  # SET + GET per op
    print(f"Time: {elapsed:.2f}s  (~{ops_per_sec:.0f} ops/sec SET+GET)")

    if RUN_LABEL:
        total_commands = N * 2
        summary = {
            "label": RUN_LABEL,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "host": HOST,
            "port": PORT,
            "ops": N,
            "workers": WORKERS,
            "value_size": VALUE_SIZE,
            "elapsed_sec": round(elapsed, 2),
            "ops_per_sec": round(ops_per_sec, 1),
            "total_commands": total_commands,
        }
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
        os.makedirs(log_dir, exist_ok=True)
        summary_path = os.path.join(log_dir, f"load_{RUN_LABEL}.json")
        with open(summary_path, "w") as f:
            json.dump(summary, f, indent=2)
        print(f"Summary written to {summary_path}")
        runs_log = os.path.join(log_dir, "load_runs.log")
        with open(runs_log, "a") as f:
            f.write(f"{summary['timestamp']}\t{RUN_LABEL}\t{N}\t{WORKERS}\t{elapsed:.2f}\t{ops_per_sec:.0f}\n")
        print(f"Appended to {runs_log}")

if __name__ == "__main__":
    main()
