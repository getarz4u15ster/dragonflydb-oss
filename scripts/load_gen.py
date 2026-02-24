#!/usr/bin/env python3
"""
Simple SET/GET load generator for Redis vs Dragonfly throughput demo.
Usage: python load_gen.py [host] [port] [ops] [workers]
  Default: localhost 6379 100000 50
Example: python load_gen.py localhost 6379 100000 50
"""
import os
import sys
import time
import redis
from concurrent.futures import ThreadPoolExecutor, as_completed

HOST = os.getenv("REDIS_HOST", sys.argv[1] if len(sys.argv) > 1 else "localhost")
PORT = int(os.getenv("REDIS_PORT", sys.argv[2] if len(sys.argv) > 2 else "6379"))
N = int(sys.argv[3]) if len(sys.argv) > 3 else 100_000
WORKERS = int(sys.argv[4]) if len(sys.argv) > 4 else 50

def run_worker(worker_id, indices):
    r = redis.Redis(host=HOST, port=PORT, decode_responses=True)
    for i in indices:
        r.set(f"key:{i}", "x" * 100)
        r.get(f"key:{i}")

def main():
    print(f"Load gen: {HOST}:{PORT}  ops={N}  workers={WORKERS}")
    # Partition work so each worker has its own connection and a slice of keys
    per_worker = (N + WORKERS - 1) // WORKERS
    chunks = [range(i * per_worker, min((i + 1) * per_worker, N)) for i in range(WORKERS)]
    start = time.perf_counter()
    with ThreadPoolExecutor(max_workers=WORKERS) as ex:
        list(ex.map(lambda arg: run_worker(arg[0], arg[1]), enumerate(chunks)))
    elapsed = time.perf_counter() - start
    ops_per_sec = N * 2 / elapsed  # SET + GET per op
    print(f"Time: {elapsed:.2f}s  (~{ops_per_sec:.0f} ops/sec SET+GET)")

if __name__ == "__main__":
    main()
