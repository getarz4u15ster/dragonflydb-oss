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
echo "Waiting for at least one symbol with 10 trades (API and bridge)..."
BASE="${BASE_URL:-http://localhost:8080}"
MAX_WAIT="${POC_WAIT_MAX:-120}"
INTERVAL=5
elapsed=0
ready=0
while [ "$elapsed" -lt "$MAX_WAIT" ]; do
  body=$(curl -s "$BASE/securities" 2>/dev/null) || true
  sym=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('securities'); print(s[0] if s and len(s)>0 else '')" 2>/dev/null) || true
  if [ -n "$sym" ]; then
    ticker=$(curl -s "$BASE/ticker/$sym" 2>/dev/null) || true
    if [ -n "$ticker" ] && echo "$ticker" | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('last_10_trades') or []; exit(0 if len(t)>=10 else 1)" 2>/dev/null; then
      ready=1
      break
    fi
  fi
  echo "  ... (${elapsed}s / ${MAX_WAIT}s)"
  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done
if [ "$ready" -eq 1 ]; then
  echo "POC ready (10 trades for $sym)."
else
  echo "Timeout: no symbol with 10 trades after ${MAX_WAIT}s. Open the dashboard anyway; data may appear shortly."
fi
echo "  Query API URL:   http://localhost:8080"
echo "  API Docs URL:    http://localhost:8080/apidocs"
echo "  Dashboard URL:  http://localhost:8080/dashboard"
echo "  RedisInsight URL: http://localhost:5540"
echo "  Dragonfly admin URL: http://localhost:9999"
echo ""
if [ "$USE_REDIS" = true ]; then
  echo "  RedisInsight — Add DB 1: host=dragonfly, port=6379 (Redis — POC data)"
  echo "                 Add DB 2: host=dragonfly-alt, port=6379 (Dragonfly — compare)"
else
  echo "  RedisInsight — Add DB 1: host=dragonfly, port=6379 (Dragonfly — POC data)"
  echo "                 Add DB 2: host=redis, port=6379 (Redis — compare)"
fi
echo "  Store:           localhost:6379 ($STORE_NAME)"
echo ""
echo "Stop with: ./stop_poc.sh"
