#!/usr/bin/env bash
# Start the POC. Demo runs from the dashboard at http://localhost:8080/dashboard
# Usage: ./start_poc.sh [redis]   — default: Dragonfly; use "redis" for Redis 7.
set -e
cd "$(dirname "$0")"

USE_REDIS=false
if [ "${1:-}" = "redis" ]; then
  USE_REDIS=true
  echo "redis" > .poc-store
  COMPOSE="docker compose -f docker-compose.yml -f docker-compose.redis.yml"
  PROFILES="--profile with-ui"
else
  echo "dragonfly" > .poc-store
  COMPOSE="docker compose"
  PROFILES="--profile with-ui --profile with-redis"
fi

STORE_NAME=$([ "$USE_REDIS" = true ] && echo "Redis" || echo "Dragonfly")
echo "Starting POC (Kafka, $STORE_NAME, bridge, producer, API, RedisInsight)..."
$COMPOSE $PROFILES up -d
echo ""
echo "POC is starting. Wait 30–60s for data, then run: ./wait_poc_ready.sh"
echo ""
echo "  Demo dashboard:  http://localhost:8080/dashboard"
echo "    (view symbols, last 10 trades, run benchmark in real time)"
echo ""
echo "  API:             http://localhost:8080"
echo "  RedisInsight:    http://localhost:5540"
if [ "$USE_REDIS" = true ]; then
  echo "    Add DB 1: host=dragonfly, port=6379 (Redis — POC data)"
  echo "    Add DB 2: host=dragonfly-alt, port=6379 (Dragonfly — compare)"
else
  echo "    Add DB 1: host=dragonfly, port=6379 (Dragonfly — POC data)"
  echo "    Add DB 2: host=redis, port=6379 (Redis — compare)"
fi
echo "  Store:           localhost:6379 ($STORE_NAME)"
echo ""
echo "Stop with: ./stop_poc.sh"
