"""
Consumer group processor: stream → incidents (hashes+TTL) + leaderboard (sorted set) + pub/sub.
Durable stream processing + failure recovery.
"""
import os
import json
import hashlib
from datetime import datetime, timezone
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

STREAM_KEY = "ops:events"
GROUP = "ops:workers"
CONSUMER = os.getenv("CONSUMER", "worker-1")

INCIDENT_TTL_SECONDS = 60 * 10  # incidents auto-expire if quiet for 10 min
NOISY_ZSET = "ops:top_noisy_services"
PUBSUB_CHANNEL = "ops:updates"  # optional push to UI/API


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def incident_id(service: str, event_type: str) -> str:
    # stable-ish incident key for demo: one incident per (service, event_type)
    key = f"{service}:{event_type}"
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:10]


def ensure_group(r: redis.Redis) -> None:
    try:
        r.xgroup_create(STREAM_KEY, GROUP, id="$", mkstream=True)
    except redis.exceptions.ResponseError as e:
        if "BUSYGROUP" in str(e):
            return
        raise


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    ensure_group(r)

    print(f"Worker {CONSUMER} reading {STREAM_KEY} as group {GROUP}")
    while True:
        # Read up to N new messages, block up to 2 seconds
        resp = r.xreadgroup(
            groupname=GROUP,
            consumername=CONSUMER,
            streams={STREAM_KEY: ">"},
            count=20,
            block=2000,
        )

        if not resp:
            continue

        for _stream, messages in resp:
            for msg_id, fields in messages:
                try:
                    payload = json.loads(fields["payload"])
                    service = payload["service"]
                    event_type = payload["event_type"]
                    sev = int(payload["severity"])

                    inc_id = incident_id(service, event_type)
                    inc_key = f"incident:{inc_id}"

                    # Incident state in a hash (fast + simple); TTL so it auto-expires after 10 min quiet
                    pipe = r.pipeline()
                    pipe.hset(
                        inc_key,
                        mapping={
                            "incident_id": inc_id,
                            "service": service,
                            "event_type": event_type,
                            "status": "OPEN",
                            "max_severity": max(sev, int(r.hget(inc_key, "max_severity") or 0)),
                            "last_seen": payload["ts"],
                            "updated_at": now_iso(),
                            "message": payload["message"],
                        },
                    )
                    pipe.expire(inc_key, INCIDENT_TTL_SECONDS)
                    pipe.execute()

                    # Track top noisy services
                    r.zincrby(NOISY_ZSET, 1, service)

                    # Publish update (nice for live UI)
                    r.publish(
                        PUBSUB_CHANNEL,
                        json.dumps(
                            {
                                "type": "incident_update",
                                "incident_id": inc_id,
                                "service": service,
                                "event_type": event_type,
                                "severity": sev,
                                "ts": payload["ts"],
                            }
                        ),
                    )

                    # Ack message after successful processing
                    r.xack(STREAM_KEY, GROUP, msg_id)

                except Exception as e:
                    # Don't ack on failure: message stays pending, can be recovered
                    print(f"Error processing {msg_id}: {e}")


if __name__ == "__main__":
    main()
