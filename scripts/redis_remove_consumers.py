#!/usr/bin/env python3
"""Remove extra consumers from ops:workers so only worker-1 through worker-N remain.
Called by scale_down.sh. Usage: python redis_remove_consumers.py [N] (default N=1).
"""
import os
import sys
import redis

STREAM = "ops:events"
GROUP = "ops:workers"


def main():
    n = 1
    if len(sys.argv) > 1:
        try:
            n = int(sys.argv[1])
        except ValueError:
            n = 1
    if n < 1:
        n = 1

    host = os.getenv("REDIS_HOST", "localhost")
    port = int(os.getenv("REDIS_PORT", "6379"))
    r = redis.Redis(host=host, port=port, decode_responses=True)

    # Get current consumers from Redis
    to_remove = []
    try:
        raw = r.execute_command("XINFO", "CONSUMERS", STREAM, GROUP)
        for c in raw:
            if isinstance(c, (list, tuple)) and len(c) > 1:
                name = c[1]
            elif isinstance(c, dict):
                name = c.get("name")
            else:
                continue
            if not name:
                continue
            if name.startswith("worker-"):
                try:
                    idx = int(name.split("-")[1])
                    if idx > n:
                        to_remove.append(name)
                except (ValueError, IndexError):
                    to_remove.append(name)
            else:
                to_remove.append(name)
    except Exception:
        pass

    # Remove them
    for name in to_remove:
        try:
            r.xgroup_delconsumer(STREAM, GROUP, name)
            print(f"  Removed consumer \"{name}\" from group.")
        except Exception:
            pass

    # Fallback: explicitly remove worker-(n+1) through worker-50 in case XINFO failed (no extra print)
    for i in range(n + 1, 51):
        name = f"worker-{i}"
        if name in to_remove:
            continue
        try:
            r.xgroup_delconsumer(STREAM, GROUP, name)
        except Exception:
            pass


if __name__ == "__main__":
    main()
