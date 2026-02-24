# Deployment Guide — Redis DevOps Demo

## Useful URLs

| Service        | URL                      | Description |
|----------------|--------------------------|-------------|
| **Dashboard**  | http://localhost:8501    | Streamlit OpsView — top noisy services, stream/worker health, active incidents (auto-refresh) |
| **API**        | http://localhost:8080    | REST API — health, stats, top, incidents |
| **RedisInsight** | http://localhost:5540  | Redis GUI — inspect streams, keys, consumer groups |

### API endpoints

| Endpoint    | URL                       | Description |
|------------|---------------------------|-------------|
| Health     | http://localhost:8080/health   | Liveness check |
| Top noisy  | http://localhost:8080/top      | Top 10 services by event count |
| Incidents  | http://localhost:8080/incidents| Active incidents (last 50) |
| Stats      | http://localhost:8080/stats    | Stream consumer group info + pending |

### Redis / Dragonfly

| Resource | Connection |
|----------|------------|
| **Redis** | `localhost:6379` (or host `redis`, port `6379` from Docker network) |
| **Dragonfly** | Same port `6379` when using `USE_DRAGONFLY=1`; HTTP console at http://localhost:6379 |

---

## Deploy

### 1. Start infrastructure

**Redis (default):**

```bash
docker compose up -d
```

**Dragonfly (Redis-compatible):** Use the override and env so start/stop scripts use Dragonfly:

```bash
USE_DRAGONFLY=1 ./start_demo.sh
```

To start only the backend: `docker compose -f docker-compose.yml -f docker-compose.dragonfly.yml up -d`

**Scale out/down** (`./scale_out.sh`, `./scale_down.sh`) work the same with Dragonfly—no changes needed.

### 2. Python environment

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Run the demo

**Option A — Script (all in background)**

```bash
./start_demo.sh
```

Starts Redis + RedisInsight (Docker) if available, then producer, worker, API, and dashboard. Logs: `logs/*.log`. Stop processes and stop (not remove) containers with:

```bash
./stop_demo.sh
```

**Option B — Manual (separate terminals)**

| Terminal | Command |
|----------|---------|
| 1 | `python producer.py` |
| 2 | `CONSUMER=worker-1 python worker.py` |
| 3 | `python api.py` |
| 4 | `streamlit run dashboard.py` |

**Optional — second worker**

```bash
CONSUMER=worker-2 python worker.py
```

---

## Live demo: scale-out + fault recovery

Best way to automate the “scale out + fault recovery” moment:

1. Start the full stack: `./start_demo.sh`
2. Scale up: `./scale_out.sh [N]` (e.g. `./scale_out.sh 5` for 5 workers), or run the fault-recovery demo: `./scale_out.sh --demo`

The script will:

| Step | Action | What to show |
|------|--------|--------------|
| 1 | Start worker-2 | Two consumers in group `ops:workers` |
| 2 | Kill worker-1 | Simulate failure; its messages go to Pending |
| 3 | — | Incidents still update (worker-2); dashboard/API keep working |

**In RedisInsight:** Stream **ops:events** → Consumer group **ops:workers** → open **Pending** to see messages that were on worker-1 (and can be claimed by another consumer).

**Slower run (e.g. for narration):** `DEMO_DELAY=10 ./scale_out.sh --demo`

**Scale back down** to N workers (default 1):

```bash
./scale_down.sh [N]   # e.g. ./scale_down.sh 2 to keep 2 workers, or ./scale_down.sh for 1
```

**Full demo reset** (stop all processes and clear Redis for a fresh run):

```bash
./demo_reset.sh
```

Then run `./start_demo.sh` again.

`./stop_demo.sh` stops all processes but does not clear Redis.

---

## RedisInsight setup

1. Open http://localhost:5540  
2. Add database: **Host** `localhost` (or `redis` if from another container), **Port** `6379`  
3. Use to inspect: `ops:events` stream, `incident:*` hashes, `ops:top_noisy_services` sorted set, consumer group `ops:workers`

---

## Environment variables

| Variable    | Default    | Description        |
|-------------|------------|--------------------|
| `REDIS_HOST` | `localhost` | Redis host        |
| `REDIS_PORT` | `6379`      | Redis port        |
| `CONSUMER`   | `worker-1`  | Worker consumer name |
