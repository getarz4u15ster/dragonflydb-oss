"""
Exec-friendly read API: stats, top noisy services, active incidents.
"""
import os
import redis
from flask import Flask, jsonify

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))

NOISY_ZSET = "ops:top_noisy_services"

app = Flask(__name__)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/stats")
def stats():
    # stream group info + pending counts
    try:
        groups = r.xinfo_groups("ops:events")
    except Exception:
        groups = []
    return jsonify({"groups": groups})


@app.get("/top")
def top():
    top_result = r.zrevrange(NOISY_ZSET, 0, 9, withscores=True)
    return jsonify([{"service": s, "events": int(score)} for s, score in top_result])


@app.get("/incidents")
def incidents():
    keys = r.keys("incident:*")
    incidents_list = []
    for k in keys:
        data = r.hgetall(k)
        incidents_list.append(data)
    # sort most recent first
    incidents_list.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return jsonify(incidents_list[:50])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
