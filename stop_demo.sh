#!/usr/bin/env bash
# Stop all demo processes (producer, workers, API, dashboard) and Redis containers. Does not clear Redis data.
cd "$(dirname "$0")"

echo "Stopping demo processes..."
for f in .producer.pid .api.pid .dashboard.pid; do
  if [ -f "$f" ]; then
    kill "$(cat "$f")" 2>/dev/null || true
    echo "  Stopped $(basename "$f" .pid)"
    rm -f "$f"
  fi
done
for f in .worker.pid .worker*.pid; do
  [ -f "$f" ] || continue
  kill "$(cat "$f")" 2>/dev/null || true
  label=$(basename "$f" .pid)
  [ "$label" = ".worker" ] && label="worker-1" || label="worker-${label#.worker}"
  echo "  Stopped $label"
  rm -f "$f"
done

# Stop Redis/Dragonfly + RedisInsight containers (containers stay; use start_demo to bring back)
if command -v docker >/dev/null 2>&1; then
  if docker compose version >/dev/null 2>&1; then
    if [ -n "${USE_DRAGONFLY:-}" ]; then
      echo "Stopping Dragonfly (docker compose stop)..."
      docker compose -f docker-compose.yml -f docker-compose.dragonfly.yml stop
    else
      echo "Stopping Redis containers (docker compose stop)..."
      docker compose stop
    fi
  elif docker-compose version >/dev/null 2>&1; then
    if [ -n "${USE_DRAGONFLY:-}" ]; then
      docker-compose -f docker-compose.yml -f docker-compose.dragonfly.yml stop
    else
      docker-compose stop
    fi
  fi
fi
echo "Done."
