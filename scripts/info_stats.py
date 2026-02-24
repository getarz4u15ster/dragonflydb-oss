#!/usr/bin/env python3
"""Print Redis/Dragonfly INFO stats (e.g. instantaneous_ops_per_sec, total_commands_processed).
Works with Redis, Dragonfly, or any Redis-compatible server. No redis-cli needed.
Usage: python scripts/info_stats.py [host] [port]  (default: localhost 6379)
"""
import os
import sys
import redis

host = os.getenv("REDIS_HOST", sys.argv[1] if len(sys.argv) > 1 else "localhost")
port = int(os.getenv("REDIS_PORT", sys.argv[2] if len(sys.argv) > 2 else "6379"))

r = redis.Redis(host=host, port=port, decode_responses=True)
info = r.info("stats")

print("--- INFO stats ---")
for k, v in sorted(info.items()):
    print(f"  {k}: {v}")
print("---")
print("Requests/sec (instantaneous):", info.get("instantaneous_ops_per_sec", "n/a"))
print("Total commands processed:", info.get("total_commands_processed", "n/a"))
