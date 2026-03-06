#!/usr/bin/env bash
# Start Redis containers + all demo components in background. Run from repo root.
set -e
cd "$(dirname "$0")"
VENV="${PWD}/.venv/bin"

# Start Redis (or Dragonfly if USE_DRAGONFLY=1) + RedisInsight if not already running
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    if [ -n "${USE_DRAGONFLY:-}" ]; then
      echo "Starting Dragonfly (docker compose with dragonfly override)..."
      docker compose -f docker-compose.yml -f docker-compose.dragonfly.yml up -d
    else
      echo "Starting Redis containers (docker compose up -d)..."
      docker compose up -d
    fi
    echo "  Waiting for server to be ready..."
    sleep 3
    # Demo 1: optional throughput run (RUN_LOAD_DEMO=1 or RUN_LOAD_DEMO=benchmark)
    if [ -n "${RUN_LOAD_DEMO:-}" ]; then
      echo ""
      if [ "${RUN_LOAD_DEMO}" = "benchmark" ]; then
        echo "Demo 1: redis-benchmark (same command for Redis or Dragonfly)..."
        [ -n "${USE_DRAGONFLY:-}" ] && export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-dragonfly}" || export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-redis}"
        export BENCHMARK_CLIENTS="${BENCHMARK_CLIENTS:-256}"
        export BENCHMARK_REQUESTS="${BENCHMARK_REQUESTS:-2000000}"
        "$VENV/python" scripts/run_benchmark.py localhost 6379 || true
      else
        echo "Demo 1: throughput run (Python load gen)..."
        LOAD_OPS="${LOAD_DEMO_OPS:-500000}"
        LOAD_WORKERS="${LOAD_DEMO_WORKERS:-256}"
        LOAD_VAL="${LOAD_DEMO_VALUE_SIZE:-256}"
        export LOAD_VALUE_SIZE="$LOAD_VAL"
        [ -n "${USE_DRAGONFLY:-}" ] && export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-dragonfly}" || export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-redis}"
        "$VENV/python" scripts/load_gen.py localhost 6379 "$LOAD_OPS" "$LOAD_WORKERS" || true
      fi
      echo ""
    fi
  elif docker-compose version >/dev/null 2>&1; then
    if [ -n "${USE_DRAGONFLY:-}" ]; then
      echo "Starting Dragonfly..."
      docker-compose -f docker-compose.yml -f docker-compose.dragonfly.yml up -d
    else
      echo "Starting Redis containers..."
      docker-compose up -d
    fi
    sleep 3
    if [ -n "${RUN_LOAD_DEMO:-}" ]; then
      echo ""
      if [ "${RUN_LOAD_DEMO}" = "benchmark" ]; then
        echo "Demo 1: redis-benchmark..."
        [ -n "${USE_DRAGONFLY:-}" ] && export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-dragonfly}" || export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-redis}"
        export BENCHMARK_CLIENTS="${BENCHMARK_CLIENTS:-256}"
        export BENCHMARK_REQUESTS="${BENCHMARK_REQUESTS:-2000000}"
        "$VENV/python" scripts/run_benchmark.py localhost 6379 || true
      else
        echo "Demo 1: throughput run..."
        LOAD_OPS="${LOAD_DEMO_OPS:-500000}"
        LOAD_WORKERS="${LOAD_DEMO_WORKERS:-256}"
        LOAD_VAL="${LOAD_DEMO_VALUE_SIZE:-256}"
        export LOAD_VALUE_SIZE="$LOAD_VAL"
        [ -n "${USE_DRAGONFLY:-}" ] && export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-dragonfly}" || export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-redis}"
        "$VENV/python" scripts/load_gen.py localhost 6379 "$LOAD_OPS" "$LOAD_WORKERS" || true
      fi
      echo ""
    fi
  else
    echo "Docker Compose not found; assuming Redis/Dragonfly is already running on localhost:6379"
  fi
else
  echo "Docker not found; assuming Redis/Dragonfly is already running on localhost:6379"
  if [ -n "${RUN_LOAD_DEMO:-}" ]; then
    echo ""
    if [ "${RUN_LOAD_DEMO}" = "benchmark" ]; then
      echo "Demo 1: redis-benchmark..."
      [ -n "${USE_DRAGONFLY:-}" ] && export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-dragonfly}" || export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-redis}"
      export BENCHMARK_CLIENTS="${BENCHMARK_CLIENTS:-256}"
      export BENCHMARK_REQUESTS="${BENCHMARK_REQUESTS:-2000000}"
      "$VENV/python" scripts/run_benchmark.py localhost 6379 || true
    else
      echo "Demo 1: throughput run..."
      LOAD_OPS="${LOAD_DEMO_OPS:-500000}"
      LOAD_WORKERS="${LOAD_DEMO_WORKERS:-256}"
      export LOAD_VALUE_SIZE="${LOAD_DEMO_VALUE_SIZE:-256}"
      [ -n "${USE_DRAGONFLY:-}" ] && export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-dragonfly}" || export LOAD_RUN_LABEL="${LOAD_RUN_LABEL:-redis}"
      "$VENV/python" scripts/load_gen.py localhost 6379 "$LOAD_OPS" "$LOAD_WORKERS" || true
    fi
    echo ""
  fi
fi
echo ""

mkdir -p logs
echo "Starting producer..."
nohup "$VENV/python" producer.py >> logs/producer.log 2>&1 &
echo $! > .producer.pid

echo "Starting worker..."
CONSUMER=worker-1 nohup "$VENV/python" worker.py >> logs/worker.log 2>&1 &
echo $! > .worker.pid

echo "Starting API..."
nohup "$VENV/python" api.py >> logs/api.log 2>&1 &
echo $! > .api.pid

sleep 1
echo "Starting dashboard..."
nohup "$VENV/streamlit" run dashboard.py --server.headless true >> logs/dashboard.log 2>&1 &
echo $! > .dashboard.pid

echo ""
echo "Demo running."
echo "  Dashboard: http://localhost:8501"
echo "  API:       http://localhost:8080"
if [ -z "${USE_DRAGONFLY:-}" ]; then
  echo "  RedisInsight: http://localhost:5540"
else
  echo "  Dragonfly HTTP console: http://localhost:6379"
fi
echo ""
echo "Logs: logs/*.log   Stop: ./stop_demo.sh"
