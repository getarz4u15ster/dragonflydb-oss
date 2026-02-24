# Redis DevOps Demo — Talk Track

Use this when walking through the demo for engineers and execs.

---

## 3) Exec view: “What’s burning right now?”

**Dashboard:**

- **Top noisy services** — live leaderboard of which services are firing the most events.
- **Active incidents** — current open incidents (service, event type, severity, last seen).
- Incidents **auto-expire after 10 minutes quiet** (TTL), so the view doesn’t become an eternal graveyard.

**In RedisInsight:** Only **hash** keys under `incident:*` have a TTL (~600 s). The stream `ops:events` and the sorted set `ops:top_noisy_services` have no TTL (they’re durable). Click an `incident:*` key to see its TTL.

---

## Talk track (engineers + execs)

- **“Streams let us take in telemetry durably.”**  
  Not best-effort like pub/sub — events are stored and replayed until processed.

- **“Consumer groups let us process it at-least-once, scale workers, and recover from worker death.”**  
  Multiple workers share the load; when one dies, its pending work can be claimed and no data is lost.

- **“We materialize the incident view into hashes with TTL, so the UI is instant.”**  
  No heavy queries — we read pre-aggregated state; TTL keeps the list from growing forever.

- **“Sorted sets give leadership an always-current ‘top offenders’ board.”**  
  The “top noisy services” leaderboard is a Redis sorted set, so it’s fast and always up to date.
