# Redis DevOps Demo

**Story:** We ingest noisy DevOps telemetry, turn it into incidents, and keep an exec-friendly live view without losing data.

| Redis feature      | Role in the demo                                      |
|--------------------|--------------------------------------------------------|
| **Streams**        | Durable event ingestion (not "best effort" like pubsub) |
| **Consumer Groups**| Horizontal workers, failure recovery, pending work     |
| **Hashes + TTL**   | Incident state store (fast, simple)                    |
| **Sorted Sets**    | Live "Top noisy services" leaderboard                  |
| **Pub/Sub**        | Push updates to UI/API (optional)                      |

## Quick start

### 1. Start Redis + RedisInsight (or Dragonfly)

**Redis (default):**

```bash
docker compose up -d
```

- **Redis:** `localhost:6379`
- **RedisInsight:** http://localhost:5540 → Add DB: host `redis`, port `6379` (or `localhost:6379` from host)

**Dragonfly (Redis-compatible alternative):** [Dragonfly](https://github.com/dragonflydb/dragonfly) is a drop-in Redis-compatible store. No app code changes. **scale_out.sh** and **scale_down.sh** work the same with Dragonfly.

```bash
USE_DRAGONFLY=1 ./start_demo.sh
```

**Demo 1 (throughput) built in:** run a load at startup tuned to show Redis vs Dragonfly differentiation (200k ops, 100 workers, 256B values). See [DEMO_STYLE.md](DEMO_STYLE.md) for why light load (~77 ops/sec) shows no difference.

```bash
RUN_LOAD_DEMO=1 ./start_demo.sh              # Redis
USE_DRAGONFLY=1 RUN_LOAD_DEMO=1 ./start_demo.sh   # Dragonfly
```

**Demo 1 flow (compare Redis vs Dragonfly):**

1. `RUN_LOAD_DEMO=1 ./start_demo.sh` → Redis starts, load runs, note ops/sec.
2. `./stop_demo.sh`, then `USE_DRAGONFLY=1 RUN_LOAD_DEMO=1 ./start_demo.sh` → Dragonfly starts, same load runs, note ops/sec and compare.

**TL;DR:** Use `start_demo.sh` for everything. Set `RUN_LOAD_DEMO=1` for the comparison; optionally `LOAD_DEMO_OPS` and `LOAD_DEMO_WORKERS` for a heavier run (e.g. `LOAD_DEMO_OPS=2000000 LOAD_DEMO_WORKERS=256`).

Or start the backend only: `docker compose -f docker-compose.yml -f docker-compose.dragonfly.yml up -d`.  
Dragonfly HTTP console: http://localhost:6379. **Admin port** (status/metrics): http://localhost:9999/ and http://localhost:9999/metrics — Dragonfly only; Redis does not have this.

### 2. Python env

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the demo

**Option A – Script (easiest)**

```bash
./start_demo.sh
```

Starts Redis + RedisInsight (Docker) if needed, then producer, worker, API, and dashboard in the background. Logs: `logs/*.log`.

Stop everything (processes + stop Redis/RedisInsight containers; containers are not removed):

```bash
./stop_demo.sh
```

**Option B – Manual (4 terminals)**

| Terminal | Command |
|----------|---------|
| 1 | `python producer.py` |
| 2 | `CONSUMER=worker-1 python worker.py` |
| 3 | `python api.py` |
| 4 | `streamlit run dashboard.py` |

- **Dashboard:** http://localhost:8501  
- **API:** http://localhost:8080  
- **RedisInsight:** http://localhost:5540  

### Optional: second worker (horizontal scaling)

```bash
CONSUMER=worker-2 python worker.py
```

## Live demo: “wow” moments

### 1) Durable ingestion (not just cache)

In **RedisInsight** (http://localhost:5540): open the **ops:events** stream and show events accumulating. Data is persisted (AOF); it’s not best-effort like pub/sub.

### 2) Scale-out + fault recovery (automated)

With the demo already running (`./start_demo.sh`), you can:

**Scale up to N workers** (worker-1 through worker-N):

```bash
./scale_out.sh [N]   # default N=2; e.g. ./scale_out.sh 5 for 5 workers
```

**Run the fault-recovery demo** (add worker-2, then kill worker-1 to show recovery):

```bash
./scale_out.sh --demo
```

The demo script: (1) starts worker-2, (2) after a delay kills worker-1, (3) incidents keep updating via worker-2; no data loss.

**While it runs:** in RedisInsight → stream **ops:events** → consumer group **ops:workers** → show **Pending** (messages that were on worker-1 and can be claimed). Dashboard and API keep updating.

Tune delay (default 6s): `DEMO_DELAY=10 ./scale_out.sh --demo`

To scale back down (fewer workers):

```bash
./scale_down.sh [N]   # keep N workers (default 1). E.g. ./scale_down.sh 2 → worker-1 and worker-2
```

### 3) Full demo reset

Stop all processes and clear Redis (stream, incidents, leaderboard) so the next run starts from zero:

```bash
./demo_reset.sh
```

Then run `./start_demo.sh` for a fresh demo.

**Other Redis deployments:** The app and scripts work with any Redis-compatible server. Set `REDIS_HOST`/`REDIS_PORT` or pass host/port to scripts (e.g. `python scripts/info_stats.py myredis 6379`). See DEPLOYMENT.md → “Other Redis deployments”.

## Layout

```
redis_demo/
  docker-compose.yml            # Redis 7.4 + RedisInsight
  docker-compose.dragonfly.yml   # Override to use Dragonfly (Redis API compatible)
  requirements.txt
  start_demo.sh        # Start Redis containers + producer, worker, API, dashboard
  stop_demo.sh         # Stop all demo processes + stop (not remove) Redis/RedisInsight containers
  scale_out.sh         # Scale to N workers (e.g. ./scale_out.sh 5); --demo for fault-recovery
  scale_down.sh        # Scale to N workers (e.g. ./scale_down.sh 2 or ./scale_down.sh for 1)
  demo_reset.sh        # Stop all + clear Redis; then start_demo.sh for fresh run
  TALK_TRACK.md        # Exec view + talk track for engineers and execs
  DEMO_STYLE.md        # Redis vs Dragonfly demos (throughput, scale, memory, cost)
  scripts/load_gen.py  # SET/GET load generator (works with Redis or Dragonfly)
  scripts/info_stats.py # INFO stats / requests per sec (works with Redis or Dragonfly)
  producer.py          # Simulated events → ops:events stream
  worker.py            # Consumer group → incidents + leaderboard + pub/sub
  api.py               # /health, /stats, /top, /incidents
  dashboard.py         # Streamlit OpsView (auto-refresh)
  logs/                # Logs when using start_demo.sh
```
