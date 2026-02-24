#!/usr/bin/env bash
# Full demo reset: stop all processes and clear Redis (stream, incidents, leaderboard).
# After this, run ./start_demo.sh for a fresh demo run.
set -e
cd "$(dirname "$0")"
VENV="${PWD}/.venv/bin"

echo "Demo reset..."
echo ""

echo "Stopping all demo processes..."
for f in .producer.pid .worker.pid .worker2.pid .api.pid .dashboard.pid; do
  [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null && echo "  Stopped $(basename $f .pid)" && rm -f "$f" || true
done
echo "  All stopped."
echo ""

echo "Clearing Redis (ops:events, incident:*, ops:top_noisy_services, etc.)..."
REDIS_HOST="${REDIS_HOST:-localhost}" REDIS_PORT="${REDIS_PORT:-6379}" "$VENV/python" -c "
import os, redis
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), decode_responses=True)
r.flushdb()
print('  Redis DB cleared.')
" 2>/dev/null || { echo "  Could not clear Redis (is it running?)."; exit 1; }

echo ""
echo "Demo reset complete. Run ./start_demo.sh to start fresh."
