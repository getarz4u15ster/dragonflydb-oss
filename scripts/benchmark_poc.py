#!/usr/bin/env python3
"""
Benchmark the Dragonfly Ingestion Bridge POC: "last 10 trades" query latency and throughput.
Measures LRANGE trades:SYMBOL 0 9 (same as the API /ticker/<symbol>).
Run with the POC stack up so Dragonfly has trades:* keys.

Usage: python scripts/benchmark_poc.py [host] [port]
  Env: REDIS_HOST, REDIS_PORT (Dragonfly)
  Optional: BENCHMARK_QUERIES (default 10000), BENCHMARK_WARMUP (default 100)
"""
import os
import sys
import time
import redis

HOST = os.getenv("REDIS_HOST", sys.argv[1] if len(sys.argv) > 1 else "localhost")
PORT = int(os.getenv("REDIS_PORT", sys.argv[2] if len(sys.argv) > 2 else "6379"))
N_QUERIES = int(os.getenv("BENCHMARK_QUERIES", "10000"))
WARMUP = int(os.getenv("BENCHMARK_WARMUP", "100"))
KEY_PREFIX = "trades:"


def main():
    r = redis.Redis(host=HOST, port=PORT, decode_responses=True)

    # Discover tickers that have LIST data (ignore old ZSET keys from pre-LIST design)
    keys = r.keys(f"{KEY_PREFIX}*")
    tickers = [k.replace(KEY_PREFIX, "") for k in keys if r.type(k) == "list"]
    if not tickers:
        if keys:
            print(f"No LIST keys found (existing keys are wrong type, e.g. old ZSET). Flush Dragonfly and restart: docker compose down -v && ./start_poc.sh")
        else:
            print(f"No keys matching {KEY_PREFIX}* found. Start the POC first (docker compose up -d), wait ~60s, then run this.")
        sys.exit(1)
    tickers.sort()

    # Warmup
    for _ in range(WARMUP):
        sym = tickers[_ % len(tickers)]
        r.lrange(f"{KEY_PREFIX}{sym}", 0, 9)

    # Timed queries (round-robin across tickers, same as API)
    latencies_ms = []
    start = time.perf_counter()
    for i in range(N_QUERIES):
        sym = tickers[i % len(tickers)]
        key = f"{KEY_PREFIX}{sym}"
        t0 = time.perf_counter()
        r.lrange(key, 0, 9)
        t1 = time.perf_counter()
        latencies_ms.append((t1 - t0) * 1000)
    elapsed = time.perf_counter() - start

    avg_ms = sum(latencies_ms) / len(latencies_ms)
    ops_per_sec = N_QUERIES / elapsed

    print("--- POC benchmark (last 10 trades per security) ---")
    print(f"Host: {HOST}:{PORT}  Queries: {N_QUERIES}  Tickers: {len(tickers)}")
    print(f"Avg Query Latency: {avg_ms:.2f} ms")
    print(f"Throughput: {ops_per_sec:,.0f} ops/sec")
    print("---------------------------------------------------")


if __name__ == "__main__":
    main()
