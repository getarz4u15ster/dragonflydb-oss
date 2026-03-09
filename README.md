# Dragonfly Ingestion Bridge POC

**Deliverable for CashCache:** A self-contained package that demonstrates ingestion from Kafka into Dragonfly, a data model that supports **"last 10 trades" per security**, and a way to query and validate the data.

---

## What this POC does

1. **Ingestion** — Trade messages flow from a Kafka topic into Dragonfly via a small ingestion bridge.
2. **Storage** — Dragonfly holds one sorted set per security (e.g. `trades:AAPL`), keeping only the last 10 trades by timestamp.
3. **Validation** — You can query Dragonfly via REST API or `redis-cli` and see data per security.

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

Or without RedisInsight: `docker compose up -d`

This starts:

- **Zookeeper** (Confluent) on port 2181  
- **Kafka** (Confluent) on port 9092  
- **Dragonfly** on port 6379 (Redis protocol)  
- **Ingestion bridge** — consumes from Kafka and writes to Dragonfly (retries until Kafka is up)  
- **Trade producer** — mock trades into Kafka topic `trades`  
- **Query API** — HTTP API on port 8080  
- **RedisInsight** (optional) — start with `--profile with-ui` to get a GUI at http://localhost:5540 (see "Dragonfly UI" below).

Wait 30–60 seconds for Kafka to be ready and for the producer/bridge to connect and stream data. Then validate with the commands below.

### Dragonfly UI (optional): RedisInsight

**RedisInsight** works with Dragonfly (Redis-compatible). Use it to browse keys (`trades:AAPL`, etc.), run commands, and view memory.

**1. Start RedisInsight** (with or after the POC):

```bash
docker compose --profile with-ui up -d
# Or to add only RedisInsight to an already-running POC:
docker compose --profile with-ui up -d redisinsight
```

**2. Open RedisInsight in your browser:** http://localhost:5540

**3. Add Dragonfly as a database.** RedisInsight runs in a Docker container and connects to Dragonfly over the Docker network, so use the **service name** as the host (not `localhost`):

| Field        | Value        |
|-------------|--------------|
| **Host**    | `dragonfly`  |
| **Port**    | `6379`       |
| **Username**| *(leave empty)* |
| **Password**| *(leave empty)* |

**Connection URL** (if RedisInsight asks for a URL instead):

```
redis://dragonfly:6379
```

No username or password is configured for this POC.

**Why `dragonfly` and not `localhost`?** RedisInsight runs inside a container. From that container, `localhost` is the RedisInsight container itself, not Dragonfly. The hostname `dragonfly` is the Docker Compose service name and resolves to the Dragonfly container on the same network.

**4. After connecting:** You'll see keys like `trades:AAPL`, `trades:MSFT`. Click a key to view the sorted set (last 10 trades), or use the CLI/Workbench to run `ZREVRANGE trades:AAPL 0 9`.

**Dragonfly admin port** (metrics/health only, no key browser): http://localhost:9999 and http://localhost:9999/metrics

### Scale out (optional)

You can run **multiple ingestion-bridge** instances so they share the Kafka topic (consumer group).

```bash
./scale_out_poc.sh [N]   # scale to N bridge instances (default 2)
./scale_down_poc.sh      # scale back to 1 bridge
```

The scale-out script ensures the `trades` topic has enough partitions, then scales the bridge.

### Simulating load on Dragonfly

**Does scaling out create more load?** Yes, but only a bit. More bridge instances consume from Kafka in parallel, so more writes (ZADD, ZREMRANGEBYRANK) hit Dragonfly. Total write rate is still limited by the **trade producer**, which by default sends about 2–10 trades/sec.

**Ways to simulate load:**

1. **Faster producer (write load)** — Run the producer with a shorter delay so more trades flow into Dragonfly:
   ```bash
   docker compose run --rm -e TRADE_DELAY_MIN=0.01 -e TRADE_DELAY_MAX=0.02 trade-producer
   ```
   Or set env in `docker-compose.yml` for the `trade-producer` service (e.g. `TRADE_DELAY_MIN: "0.01"`, `TRADE_DELAY_MAX: "0.02"`). Lower delay = more writes/sec to Dragonfly.

2. **Read load** — The benchmark script hammers Dragonfly with read queries (ZREVRANGE):
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

### Option A — REST API (recommended)

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

Example response shape:

```json
{
  "ticker": "AAPL",
  "last_10_trades": [
    {"ticker": "AAPL", "price": 185.22, "volume": 200, "timestamp": 1710000012},
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

### Option B — Benchmark (query latency + throughput)

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

### Option C — redis-cli (directly against Dragonfly)

If you have `redis-cli` on your host (e.g. `brew install redis` on Mac):

**Last 10 trades for AAPL (newest first):**

```bash
redis-cli -h localhost -p 6379 ZREVRANGE trades:AAPL 0 9
```

**List keys for all securities:**

```bash
redis-cli -h localhost -p 6379 KEYS "trades:*"
```

**Count of trades stored for a security:**

```bash
redis-cli -h localhost -p 6379 ZCARD trades:AAPL
```

You should see up to 10 entries per security; the bridge keeps only the last 10 by timestamp.

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
| `trades:AAPL` | ZSET | One sorted set per security. Score = trade timestamp, value = trade JSON. Only the last 10 (by score) are kept. |

The ingestion bridge runs `ZADD` for each consumed trade and then `ZREMRANGEBYRANK` so that at most 10 members remain per key. Queries use `ZREVRANGE` to get the last 10 (newest first).

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
Dockerfile              # Image for bridge, producer, and API
requirements.txt        # redis, flask
requirements-poc.txt    # kafka-python
ingestion/kafka_bridge.py   # Kafka consumer → Dragonfly ZSET (last 10 per ticker)
producer/trade_producer.py  # Mock trade producer → Kafka topic "trades"
api_poc.py              # GET /ticker/<symbol>, /securities, /health
scripts/benchmark_poc.py    # Benchmark last-10-trades query latency + throughput
start_poc.sh            # Start POC with RedisInsight (docker compose --profile with-ui up -d)
stop_poc.sh             # Stop POC (docker compose down; use -v to remove volumes)
run_benchmark.sh        # Run benchmark (uses .venv if present)
query_api.sh            # Curl the API (health, securities, ticker; pretty-printed JSON)
scale_out_poc.sh        # Scale ingestion-bridge to N instances (Kafka consumer group)
scale_down_poc.sh       # Scale ingestion-bridge back to 1
README.md               # This file — setup, run, and validate the POC
.gitignore
```

---

This README is intended for the CashCache DevOps engineer: follow the steps above to set up, run, and validate the POC on your infrastructure.
