# Demo Style: Redis vs Dragonfly + OpsView

Use this when you want to show **“Same app. More throughput. No code change.”** and tie it to the existing DevOps OpsView (streams, workers, scale-out).

---

## 🔥 Demo 1: “Same App. More Throughput. No Code Change.”

**The cleanest story.**

### Setup

- Your existing Python worker app (the one you used with Redis)
- Load generator: `scripts/load_gen.py`
- Redis on 6379, then switch to Dragonfly on 6379 (or run both on different ports and point at one)

### What You Show

1. Run workload against **Redis** (e.g. `docker compose up -d` for Redis).
2. Run load gen, note **time and ops/sec**.
3. Stop Redis, start **Dragonfly** on 6379 (`USE_DRAGONFLY=1 ./start_demo.sh` or just the backend).
4. Re-run **exact same** load gen.
5. Show **throughput jump**.

### Built into start_demo.sh

A **quick throughput run** runs automatically at startup when you set `RUN_LOAD_DEMO=1`:

```bash
# Redis: start demo + run load gen (default 20k ops, 20 workers)
RUN_LOAD_DEMO=1 ./start_demo.sh

# Dragonfly: same, but against Dragonfly
USE_DRAGONFLY=1 RUN_LOAD_DEMO=1 ./start_demo.sh
```

Optional: `LOAD_DEMO_OPS=100000 LOAD_DEMO_WORKERS=50` to make the built-in run heavier.

### Run the load manually

```bash
# From repo root, with venv active
python scripts/load_gen.py localhost 6379 100000 50
```

Default: 100k ops, 50 threads. Optional args: `[host] [port] [ops] [workers]`.

### What you say (engineers)

*“Dragonfly uses a shared-nothing architecture internally, so it avoids the global lock contention Redis hits at high core counts.”*

### What you say (execs)

*“Same API. Same code. More throughput per machine.”*

---

## ⚡ Demo 2: “Scale Without Cluster”

Redis needs clustering for serious multi-core scaling. Dragonfly scales across cores on a **single instance**.

### What you do

```bash
redis-benchmark -t set,get -n 1000000 -c 200 -P 16
```

Then: `top` or `htop`. Show **multiple CPU cores** used, high ops/sec, stable latency.

### Talking point

*“With Redis, you scale by adding shards. With Dragonfly, you scale vertically first. Fewer moving parts.”*

### Punchy moment

```bash
redis-benchmark -n 1000000 -c 500 -P 32
```

Watch CPU peg across cores. Pause. Say nothing. Let them see it.

---

## 🧠 Demo 3: Memory Efficiency Under Pressure

### What you do

Fill memory aggressively:

```bash
redis-benchmark -t set -n 5000000 -d 256
```

Then: `INFO memory` (or Dragonfly equivalent). Explain: Dragonfly’s memory layout is more compact; better allocator behavior; lower fragmentation.

**Matters for:** caching tiers, AI feature stores, session stores, rate limiting at scale.

---

## 🎯 Demo 4: “The Datastore Isn’t the Bottleneck” (OpsView + scale-out)

You already have **scale_out** / **scale_down** and workers. Use them here.

### What you do

1. Start **1 worker** (`./start_demo.sh` then `./scale_down.sh` so only worker-1).
2. Increase load (producer is already running; or run load_gen against the same Redis/Dragonfly).
3. Show **latency** or backlog.
4. **Add workers:** `./scale_out.sh 10`.
5. Show **throughput scaling** and latency improving.

### Emphasize

*“The datastore isn’t the bottleneck. We scale workers horizontally; the store keeps up.”*

Then optionally rerun Demo 1 against Dragonfly and show the store can take even more.

---

## If Your Audience Is Mixed (Engineers + Execs)

1. **1 min:** “What problem does Dragonfly solve?”
2. **2 min:** Live throughput demo (Demo 1).
3. **1 min:** CPU utilization (Demo 2, `top`/`htop`).
4. **1 min:** Cost story (below).

---

## 💰 The Cost Angle (Execs)

If one Dragonfly instance handles what normally needs:

- 3–5 Redis shards, or  
- multiple cluster nodes  

then: **fewer VMs**, less operational complexity, lower cloud bill, smaller blast radius.

**One sentence:** *“We can get Redis cluster–level performance from a single node.”*

---

## Quick reference

| Demo | Command / action | Message |
|------|------------------|--------|
| 1 – Throughput | `python scripts/load_gen.py` on Redis, then on Dragonfly | Same code, more throughput |
| 2 – Scale without cluster | `redis-benchmark -n 1000000 -c 500 -P 32` + `top` | Vertical scale, fewer shards |
| 3 – Memory | `redis-benchmark -t set -n 5000000 -d 256` + `INFO memory` | Compact layout, less fragmentation |
| 4 – OpsView | `./scale_out.sh 10` with 1 then 10 workers | Datastore isn’t the bottleneck |
