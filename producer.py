"""
Simulated DevOps events producer → Redis Streams (durable, not best-effort).
"""
import os
import json
import random
import time
from datetime import datetime, timezone
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

STREAM_KEY = "ops:events"
SERVICES = ["api-gateway", "auth", "payments", "search", "inventory", "billing", "deploy", "kafka", "db", "cdn"]
EVENT_TYPES = ["latency_spike", "error_rate", "cpu_high", "mem_pressure", "deploy_failed", "db_conn_exhausted"]


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    print(f"Producing events to stream '{STREAM_KEY}' on {REDIS_HOST}:{REDIS_PORT}")
    while True:
        service = random.choice(SERVICES)
        event_type = random.choice(EVENT_TYPES)

        # Make "bad" events happen more often for a few services (demo effect)
        bias = 1.0
        if service in ("payments", "db"):
            bias = 1.8

        severity = random.choices(
            population=[1, 2, 3, 4, 5],
            weights=[35, 30, 20, 10, 5],
            k=1,
        )[0]

        if random.random() < (0.15 * bias):
            severity = min(5, severity + 2)

        payload = {
            "ts": now_iso(),
            "service": service,
            "event_type": event_type,
            "severity": severity,
            "message": f"{service} reported {event_type} (sev={severity})",
        }

        # XADD supports field/value pairs; store JSON string as one field for simplicity
        event_id = r.xadd(STREAM_KEY, {"payload": json.dumps(payload)})

        print(f"XADD {STREAM_KEY} -> {event_id} {payload['message']}")
        time.sleep(0.25)


if __name__ == "__main__":
    main()
