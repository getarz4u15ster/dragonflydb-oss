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

A **throughput run** runs automatically at startup when you set `RUN_LOAD_DEMO=1` (Python load gen) or `RUN_LOAD_DEMO=benchmark` (redis-benchmark via `scripts/run_benchmark.py`). Python default: 500k ops, 256 workers (~30–60 sec). The Python load gen can still show Redis winning; for a clearer Dragonfly win use `RUN_LOAD_DEMO=benchmark` (requires redis-benchmark on PATH, e.g. `brew install redis`). Each mode writes summary JSON to `logs/`; use the matching compare script after one run per backend.

```bash
# Python load: writes logs/load_redis.json, logs/load_dragonfly.json → compare with compare_load_runs.py
RUN_LOAD_DEMO=1 ./start_demo.sh
USE_DRAGONFLY=1 RUN_LOAD_DEMO=1 ./start_demo.sh
python scripts/compare_load_runs.py

# Benchmark: writes logs/benchmark_redis.json, logs/benchmark_dragonfly.json → compare with compare_benchmark_runs.py
RUN_LOAD_DEMO=benchmark ./start_demo.sh
USE_DRAGONFLY=1 RUN_LOAD_DEMO=benchmark ./start_demo.sh
python scripts/compare_benchmark_runs.py
```

Optional: `LOAD_DEMO_OPS=2000000` or `5000000` with 256–500 workers for heavier (longer) runs. For a quicker run: `LOAD_DEMO_OPS=200000 LOAD_DEMO_WORKERS=100`.

### Why you need enough load to see differentiation

At low throughput (e.g. ~77 ops/sec), **there is no observable difference** between Redis and Dragonfly. Both are idle. You are not CPU-, memory-, or concurrency-bound. To demonstrate real differences you need to:

- **Drive concurrency high** — enough clients/workers to saturate a core or more.
- **Push into thousands or tens of thousands of ops/sec** — so the engine is actually working.
- **Use many clients** — multi-threaded load (e.g. 100+ workers).
- **Test larger values** — `LOAD_DEMO_VALUE_SIZE=256` or `1024` (bytes per value).
- **Optionally introduce memory pressure** — fill memory and observe eviction/behavior (see Demo 3).

The built-in run uses **500k ops, 256 workers** so the demo finishes in ~30–60 sec. With the Python client, Redis may still win; for a **clear Dragonfly win** use redis-benchmark (next section).

### If you want to expose real differences

To see Dragonfly pull ahead meaningfully:

1. **Use high concurrency** — e.g. `redis-benchmark -c 100 -t get,set -n 1000000` (or `-c 200`, `-c 500`).
2. **Use multiple client threads** from the load generator — e.g. `python scripts/load_gen.py localhost 6379 500000 200` (200 workers).
3. **Push past 50k–100k ops/sec** — enough ops and workers so the server is actually saturated.
4. **Watch CPU** — pin/observe cores; Dragonfly’s strength shows when one core isn’t enough, lock contention matters, and high parallelism is required. At low concurrency, Redis is extremely efficient and can look very strong.

**redis-benchmark (same server, high concurrency):**

```bash
# Against whatever is on localhost:6379 (Redis or Dragonfly)
redis-benchmark -c 100 -t get,set -n 1000000

# Heavier: more clients, pipelining
redis-benchmark -c 200 -t get,set -n 1000000 -P 16
```

**On multi-core machines (e.g. Apple M4 Max):** you have plenty of cores. Use high `-c` in redis-benchmark and high worker count in `load_gen.py` (e.g. 100–200 workers, 500k+ ops) so both engines are under real parallel load; that’s when Dragonfly’s shared-nothing design shows up.

### How to make Dragonfly clearly win (if it’s going to)

You need a test that **forces parallelism** and **keeps the client from being the bottleneck**.

**Practical recipe:**

| Levers | Target |
|--------|--------|
| **Concurrency** | 256–2000 clients |
| **Client threads** | 8–16 (so the client can drive enough load; more is fine) |
| **Requests** | Millions (steady-state measurement) |
| **Comparison** | Same dataset and command mix on both |

**If Redis keeps winning with the Python load gen:** the client can be the bottleneck. Use **RUN_LOAD_DEMO=benchmark** so the start script runs `scripts/run_benchmark.py` (redis-benchmark), writes `logs/benchmark_redis.json` and `logs/benchmark_dragonfly.json`, then run `python scripts/compare_benchmark_runs.py`. For a heavier benchmark (e.g. more clients):

```bash
RUN_LOAD_DEMO=benchmark BENCHMARK_CLIENTS=500 ./start_demo.sh
# then same with USE_DRAGONFLY=1, then compare_benchmark_runs.py
```

**Python load_gen** (same idea: many concurrent clients, millions of ops):

```bash
# 256 workers (= 256 clients), 2M ops (4M commands: SET+GET per op), 256B value
python scripts/load_gen.py localhost 6379 2000000 256 256

# Heavier: 500 workers, 5M ops
python scripts/load_gen.py localhost 6379 5000000 500 256
```

Run the **exact same** command against Redis, note time and ops/sec; then against Dragonfly. Same dataset and command mix — that’s when Dragonfly can clearly win.

**Docker on Mac (e.g. M4):** Both backends run in a VM with limited CPU; Redis can still win at `-c 256`. Try `BENCHMARK_CLIENTS=500` or `1000` (e.g. `RUN_LOAD_DEMO=benchmark BENCHMARK_CLIENTS=500 ./start_demo.sh`) or run on Linux for a clearer Dragonfly advantage.

### Run the load manually

Works with **Redis, Dragonfly, or any Redis-compatible server.**

**Python load gen:** `python scripts/load_gen.py [host] [port] [ops] [workers] [value_size]` — set `LOAD_RUN_LABEL=redis` or `dragonfly` to write `logs/load_<label>.json` for comparison.

**Benchmark:** `LOAD_RUN_LABEL=redis python scripts/run_benchmark.py [host] [port]` (then same with `dragonfly`). Writes `logs/benchmark_<label>.json`. Compare with `python scripts/compare_benchmark_runs.py`.

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
| 1 – Throughput | `RUN_LOAD_DEMO=1` or `RUN_LOAD_DEMO=benchmark` on Redis, then Dragonfly; then `compare_load_runs.py` or `compare_benchmark_runs.py` | Same code, more throughput |
| 2 – Scale without cluster | `redis-benchmark -n 1000000 -c 500 -P 32` + `top` | Vertical scale, fewer shards |
| 3 – Memory | `redis-benchmark -t set -n 5000000 -d 256` + `INFO memory` or `python scripts/info_stats.py` | Compact layout, less fragmentation |
| 4 – OpsView | `./scale_out.sh 10` with 1 then 10 workers | Datastore isn’t the bottleneck |

**Comparison scripts:** `python scripts/compare_load_runs.py` (Python load: reads `logs/load_redis.json`, `logs/load_dragonfly.json`). `python scripts/compare_benchmark_runs.py` (benchmark: reads `logs/benchmark_redis.json`, `logs/benchmark_dragonfly.json`). Both print which files they use.

**Requests per second (no redis-cli):** `python scripts/info_stats.py [host] [port]` — works with Redis or Dragonfly.
