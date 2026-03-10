# Dragonfly Ingestion Bridge POC

**Deliverable:** A self-contained deployable package that demonstrates ingestion from Kafka into Dragonfly, and a data model that supports **"last 10 trades" per security**, including a way to query and validate the data.

---

## What this POC does

1. **Ingestion** — Trade messages flow from a Kafka topic into Dragonfly via a small ingestion bridge.
2. **Storage** — The store (Dragonfly or Redis) holds one LIST per security (e.g. `trades:AAPL`), keeping only the last 10 trades (LPUSH + LTRIM).
3. **Validation** — You can query Dragonfly via REST API or `redis-cli` and see data per security.

---

## Requirements (from discovery)

This POC is aligned with CashCache’s answers from discovery:

| Topic | Requirement | How the POC addresses it |
|-------|-------------|---------------------------|
| **Trade message schema** | Flat JSON: `symbol` (string), `price` (float), `quantity` (integer), `timestamp` (ISO8601 string), `trade_id` (UUID) | Producer emits this schema. Bridge accepts it and stores full JSON in Dragonfly. |
| **Ingestion rate** | ~50k eps average; spikes to 500k eps; no backpressure to Kafka, low frontend latency | Bridge uses Kafka consumer (pull-based), so it does not push back to Kafka. Scale bridge instances and topic partitions to handle throughput; Dragonfly supports high write/read rates. This POC runs at low rate for demos; production would scale partitions + bridges. |
| **Symbol scale** | ~12k symbols globally; 500–1k “hot” at any time | Data model is one LIST per symbol (`trades:SYMBOL`); scales to 12k+ keys. Mock producer uses a subset of symbols for the demo. |
| **Retention** | Last 10 trades per symbol only (no longer window for POC) | Bridge runs `LPUSH` then `LTRIM 0 9` so at most 10 elements per key (newest at head). |
| **Frontend / query** | REST API from mobile app → backend → data store; &lt;1 ms from data store | This repo’s Query API is the backend: it talks to Dragonfly over the Redis protocol. Use `./run_benchmark.sh` to measure latency (typically sub‑ms). |
| **Client library** | Backend will query Dragonfly via Redis-compatible client; &lt;1 ms target | **Recommended:** Use the official Redis client for your stack. Examples: **Python** [redis-py](https://github.com/redis/redis-py), **Node** [ioredis](https://github.com/redis/ioredis) or [node-redis](https://github.com/redis/node-redis), **Go** [go-redis](https://github.com/redis/go-redis), **Java** [Jedis](https://github.com/redis/jedis) or [Lettuce](https://github.com/lettuce-io/lettuce-core). All are Dragonfly-compatible. This POC’s API uses **redis-py**. |

---

## Prerequisites

- **Docker** and **Docker Compose** (v2+), installed and running on your machine.

---

## Step 1 — Set up the environment

1. Clone or unpack this repo and go to the project root:
   ```bash
   cd /path/to/redis_demo
   ```

2. Ensure no other services are using **port 6379** (Dragonfly) or **9092** (Kafka). Stop any existing Redis/Kafka containers if needed.

---

## Step 2 — Start the POC

From the project root, run:

```bash
./start_poc.sh
```

To use **Redis 7** instead of Dragonfly as the in-memory store (same scripts, same ports, same API):

```bash
./start_poc.sh redis
```

The choice is saved (in `.poc-store`); `./stop_poc.sh` and the scale scripts use the same store automatically. All commands (query API, benchmark, redis-cli, RedisInsight) work the same—host `dragonfly`, port 6379.

Or without RedisInsight: `docker compose up -d`

This starts:

- **Zookeeper** (Confluent) on port 2181  
- **Kafka** (Confluent) on port 9092  
- **Dragonfly** on port 6379 (Redis protocol)  
- **Ingestion bridge** — consumes from Kafka and writes to Dragonfly (retries until Kafka is up)  
- **Trade producer** — mock trades into Kafka topic `trades`  
- **Query API** — HTTP API on port 8080  
- **RedisInsight** (optional) — start with `--profile with-ui` to get a GUI (see "Dragonfly UI" below).

### URLs at a glance

| Service / endpoint | URL |
|--------------------|-----|
| **Demo dashboard** | **http://localhost:8080/dashboard** |
| Query API (base) | http://localhost:8080 |
| API docs (Swagger) | http://localhost:8080/apidocs |
| Health | http://localhost:8080/health |
| Securities | http://localhost:8080/securities |
| Ticker (e.g. AAPL) | http://localhost:8080/ticker/AAPL |
| RedisInsight | http://localhost:5540 |
| Dragonfly admin | http://localhost:9999 |
| Dragonfly metrics | http://localhost:9999/metrics |

Wait 30–60 seconds for Kafka to be ready and for the producer/bridge to connect and stream data.

**Demo flow (dashboard-first):** Run the same story every time:

1. **Start** — `./start_poc.sh` (or `./start_poc.sh redis`).
2. **Wait until ready** — `./wait_poc_ready.sh` (prints "POC ready" when data is flowing).
3. **Open the dashboard** — http://localhost:8080/dashboard  
   From the dashboard you can:
   - **View symbols and last 10 trades** — Click a symbol to see live trade data (auto-refreshes).
   - **Run the benchmark** — Click "Run benchmark" to see latency and throughput in real time.
4. **Optional: scale the bridge** — In a terminal, `./scale_out_poc.sh 2`, then run the benchmark again from the dashboard to compare.
5. **Optional: inspect the store** — Open [RedisInsight](http://localhost:5540) to browse keys and run Redis commands.

### Dragonfly UI (optional): RedisInsight

**RedisInsight** works with Dragonfly (Redis-compatible). Use it to browse keys (`trades:AAPL`, etc.), run commands, and view memory.

**1. Start RedisInsight** (with or after the POC):

```bash
docker compose --profile with-ui up -d
# Or to add only RedisInsight to an already-running POC:
docker compose --profile with-ui up -d redisinsight
```

**2. Open RedisInsight in your browser:** see **RedisInsight** in the [URLs table](#urls-at-a-glance) above.

**3. Add the POC store and (optionally) the other store.** You can add both Dragonfly and Redis so you can compare. Use the **service name** as the host (not `localhost`).

**When you ran `./start_poc.sh` (Dragonfly as main store):**

| Alias (optional) | Host        | Port  |
|------------------|-------------|-------|
| Dragonfly (POC)  | `dragonfly` | `6379` |
| Redis (compare)  | `redis`     | `6379` |

**When you ran `./start_poc.sh redis` (Redis as main store):**

| Alias (optional) | Host             | Port  |
|------------------|------------------|-------|
| Redis (POC)     | `dragonfly`      | `6379` |
| Dragonfly (compare) | `dragonfly-alt` | `6379` |

Leave **Username** and **Password** empty. Connection URL examples: `redis://dragonfly:6379`, `redis://redis:6379`, `redis://dragonfly-alt:6379`.

**Why service names and not `localhost`?** RedisInsight runs inside a container; from there, `localhost` is RedisInsight itself. The hostnames above are Docker Compose service names and resolve to the right container on the same network.

**4. After connecting:** You'll see keys like `trades:AAPL`, `trades:MSFT`. Click a key to view the list (last 10 trades, newest at index 0), or use the CLI/Workbench to run `LRANGE trades:AAPL 0 9`.

**Dragonfly admin** (metrics/health only, no key browser): see **Dragonfly admin** and **Dragonfly metrics** in the [URLs table](#urls-at-a-glance) above.

### Scale out (optional)

You can run **multiple ingestion-bridge** instances so they share the Kafka topic (consumer group).

```bash
./scale_out_poc.sh [N]   # scale to N bridge instances (default 2)
./scale_down_poc.sh      # scale back to 1 bridge
```

The scale-out script ensures the `trades` topic has enough partitions, then scales the bridge.

### Simulating load on Dragonfly

**Does scaling out create more load?** Yes, but only a bit. More bridge instances consume from Kafka in parallel, so more writes (LPUSH, LTRIM) hit Dragonfly. Total write rate is still limited by the **trade producer**, which by default sends about 2–10 trades/sec.

**Ways to simulate load:**

1. **Faster producer (write load)** — Run the producer with a shorter delay so more trades flow into Dragonfly:
   ```bash
   docker compose run --rm -e TRADE_DELAY_MIN=0.01 -e TRADE_DELAY_MAX=0.02 trade-producer
   ```
   Or set env in `docker-compose.yml` for the `trade-producer` service (e.g. `TRADE_DELAY_MIN: "0.01"`, `TRADE_DELAY_MAX: "0.02"`). Lower delay = more writes/sec to Dragonfly.

2. **Read load** — The benchmark script hammers Dragonfly with read queries (LRANGE):
   ```bash
   ./run_benchmark.sh
   ```
   Use `BENCHMARK_QUERIES=100000 ./run_benchmark.sh` for a longer run. This measures latency and throughput for the "last 10 trades" query.

3. **Scale bridges + faster producer** — Scale out the ingestion bridge (e.g. `./scale_out_poc.sh 4`) and run a faster producer so more messages are consumed and written to Dragonfly in parallel.

4. **Generic load (optional)** — If you have `redis-benchmark` installed (e.g. `brew install redis`), you can stress Dragonfly with arbitrary commands:
   ```bash
   redis-benchmark -h localhost -p 6379 -t set,get,zadd,zrange -n 100000 -c 50
   ```

---

## Step 3 — Validate: query data per security

### Option A — Dashboard (recommended)

Open the **demo dashboard:** [http://localhost:8080/dashboard](http://localhost:8080/dashboard)

- **Symbols and last 10 trades** — Click a symbol to see live data (auto-refreshes every 5s).
- **Benchmark** — Click "Run benchmark" to run the same benchmark as `./run_benchmark.sh` and watch progress and results in real time.

No terminal needed for the core demo. For API docs (Swagger) and raw endpoints, see the [URLs table](#urls-at-a-glance) above.

### Option B — REST API (curl / query_api.sh)

**List securities that have data:**

```bash
curl -s http://localhost:8080/securities
```

**Get last 10 trades for a security (e.g. AAPL):**

```bash
curl -s http://localhost:8080/ticker/AAPL
```

or explicitly:

```bash
curl -s http://localhost:8080/ticker/AAPL/last10
```

Example response shape (schema matches discovery: symbol, price, quantity, timestamp ISO8601, trade_id):

```json
{
  "symbol": "AAPL",
  "last_10_trades": [
    {"symbol": "AAPL", "price": 185.22, "quantity": 200, "timestamp": "2025-03-07T14:30:00.123Z", "trade_id": "550e8400-e29b-41d4-a716-446655440000"},
    ...
  ]
}
```

**Health check:**

```bash
curl -s http://localhost:8080/health
```

Or use the helper script (runs curl and pretty-prints JSON):

```bash
./query_api.sh              # health + securities + ticker AAPL
./query_api.sh health       # health only
./query_api.sh securities   # list securities
./query_api.sh ticker AAPL  # last 10 trades for AAPL
./query_api.sh MSFT         # last 10 trades for MSFT
```

| What you run | Endpoint | Curl equivalent |
|--------------|----------|------------------|
| `./query_api.sh` (no args) | health, securities, ticker AAPL | `curl -s http://localhost:8080/health`<br>`curl -s http://localhost:8080/securities`<br>`curl -s http://localhost:8080/ticker/AAPL` |
| `./query_api.sh health` | Health only | `curl -s http://localhost:8080/health` |
| `./query_api.sh securities` | List of symbols | `curl -s http://localhost:8080/securities` |
| `./query_api.sh ticker AAPL` | Last 10 trades for AAPL | `curl -s http://localhost:8080/ticker/AAPL` |
| `./query_api.sh MSFT` | Last 10 trades for MSFT | `curl -s http://localhost:8080/ticker/MSFT` |

### Option C — Benchmark (script: run_benchmark.sh)

With the POC running and data flowing (so Dragonfly has `trades:*` keys), run:

```bash
./run_benchmark.sh
```

The script uses `.venv` if present (with `redis` installed); otherwise it uses `python3`. Optional: `BENCHMARK_QUERIES=50000 ./run_benchmark.sh` or pass host/port: `./run_benchmark.sh localhost 6379`.

Example output:

```
--- POC benchmark (last 10 trades per security) ---
Host: localhost:6379  Queries: 10000  Tickers: 10
Avg Query Latency: 0.15 ms
Throughput: 6,653 ops/sec
---------------------------------------------------
```

### Option D — redis-cli (directly against Dragonfly)

If you have `redis-cli` on your host (e.g. `brew install redis` on Mac). These commands mirror what the query API does.

**Last 10 trades for a symbol (same as `GET /ticker/AAPL`):**

```bash
redis-cli -h localhost -p 6379 LRANGE trades:AAPL 0 9
```

Use any symbol in place of `AAPL` (e.g. `trades:MSFT`, `trades:GOOGL`).

**List keys for all securities:**

```bash
redis-cli -h localhost -p 6379 KEYS "trades:*"
```

**Count of trades stored for a security:**

```bash
redis-cli -h localhost -p 6379 LLEN trades:AAPL
```

You should see up to 10 entries per security; the bridge keeps only the last 10 (LPUSH + LTRIM).

---

## Step 4 — Stop the POC

```bash
./stop_poc.sh
```

To also remove the Dragonfly data volume:

```bash
./stop_poc.sh -v
```

---

## Data model (Dragonfly)

| Key           | Type | Description |
|---------------|------|--------------|
| `trades:AAPL` | LIST | One list per symbol. Newest trade at index 0 (LPUSH). Value = full trade JSON (`symbol`, `price`, `quantity`, `timestamp`, `trade_id`). Bridge runs `LPUSH` then `LTRIM 0 9` so at most 10 elements are kept. |

This is the simplest "last 10" pattern: no scores, insertion order is recency. Queries use `LRANGE key 0 9` to get the last 10 (newest first).

---

## Troubleshooting

| Issue | What to do |
|-------|------------|
| No data in `/ticker/AAPL` or `trades:AAPL` | Wait 30–60 s after `up -d`; the producer and bridge need to start. Try `curl http://localhost:8080/securities` again. |
| `Connection refused` to Kafka or Dragonfly | Ensure all containers are up: `docker compose ps`. Check logs: `docker compose logs ingestion-bridge` and `docker compose logs trade-producer`. |
| Port 6379 or 9092 in use | Stop the process using that port or change the compose ports. |

---

## File layout

```
docs/architecture.drawio # Architecture diagram (draw.io): Kafka → Bridge → Dragonfly → API
docker-compose.yml      # Zookeeper, Kafka, Dragonfly, ingestion-bridge, trade-producer, query-api
docker-compose.redis.yml # Override: use Redis 7 instead of Dragonfly (./start_poc.sh redis)
poc_compose.sh          # Shared compose selection for stop/scale (reads .poc-store)
Dockerfile              # Image for bridge, producer, and API
requirements.txt        # redis, flask
requirements-poc.txt    # kafka-python
ingestion/kafka_bridge.py   # Kafka consumer → Dragonfly LIST (LPUSH + LTRIM 0 9 per symbol)
producer/trade_producer.py  # Mock trade producer → Kafka topic "trades"
api_poc.py              # GET /ticker/<symbol>, /securities, /health
scripts/benchmark_poc.py    # Benchmark last-10-trades query latency + throughput
start_poc.sh            # Start POC with RedisInsight; optional: start_poc.sh redis for Redis 7
stop_poc.sh             # Stop POC (uses same store as start; use down -v to remove volumes)
wait_poc_ready.sh       # Wait until API returns securities, then print "POC ready"
run_benchmark.sh        # Run benchmark (uses .venv if present)
query_api.sh            # Curl the API (health, securities, ticker; pretty-printed JSON)
scale_out_poc.sh        # Scale ingestion-bridge to N instances (Kafka consumer group)
scale_down_poc.sh       # Scale ingestion-bridge back to 1
README.md               # This file — setup, run, and validate the POC
.gitignore
```

---

This README is intended for the DevOps engineer: follow the steps above to set up, run, and validate the POC on your infrastructure.
