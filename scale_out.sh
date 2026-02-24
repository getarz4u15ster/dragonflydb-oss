#!/usr/bin/env bash
# Scale up to N workers (worker-1 through worker-N).
# Prereq: ./start_demo.sh is already running (producer, worker-1, API, dashboard).
#
# Usage:
#   ./scale_out.sh [N]     scale to N workers total (default: 2)
#   ./scale_out.sh --demo  run fault-recovery demo: add worker-2, kill worker-1
set -e
cd "$(dirname "$0")"
VENV="${PWD}/.venv/bin"

DEMO_MODE=false
N=2

if [ "$1" = "--demo" ]; then
  DEMO_MODE=true
  N=2
elif [ -n "$1" ]; then
  N="$1"
  # Portable integer check (works in bash and sh)
  case "$N" in
    ''|*[!0-9]*) echo "Usage: $0 [N]   (N = total workers, 2-50; default 2)"; echo "       $0 --demo   (fault-recovery demo)"; exit 1 ;;
  esac
  if [ "$N" -lt 2 ] || [ "$N" -gt 50 ]; then
    echo "N must be between 2 and 50 (got $N)."
    exit 1
  fi
fi

echo "scale_out: target $N workers (use --demo for fault-recovery demo)."
echo ""

if [ ! -f .worker.pid ]; then
  if [ "$DEMO_MODE" = true ]; then
    if [ -f .worker2.pid ]; then
      echo "Demo already ran (worker-1 was killed; only worker-2 is running)."
      echo "To run the demo again: ./scale_down.sh   then   ./scale_out.sh --demo"
      echo ""
      exit 0
    fi
    echo "Error: .worker.pid not found. Run ./start_demo.sh first (need worker-1 to run the demo)."
    exit 1
  else
    # Scale-out by number: ensure worker-1 is running first (e.g. after --demo only worker-2 was left)
    if [ -f .worker2.pid ] || [ -f .worker3.pid ]; then
      echo "worker-1 not running (e.g. after --demo). Starting worker-1..."
      mkdir -p logs
      CONSUMER=worker-1 nohup "$VENV/python" worker.py >> logs/worker.log 2>&1 &
      echo $! > .worker.pid
      echo "  worker-1 started (PID $(cat .worker.pid))."
      echo ""
    else
      echo "Error: .worker.pid not found. Run ./start_demo.sh first."
      exit 1
    fi
  fi
fi

if [ "$DEMO_MODE" = true ]; then
  DELAY="${DEMO_DELAY:-6}"
  echo "=============================================="
  echo "  Scale-out + fault recovery demo"
  echo "  (Delay between steps: ${DELAY}s — set DEMO_DELAY to change)"
  echo "=============================================="
  echo ""

  echo "Step 1: Starting worker-2 (scale out)..."
  CONSUMER=worker-2 nohup "$VENV/python" worker.py >> logs/worker2.log 2>&1 &
  echo $! > .worker2.pid
  echo "        worker-2 started (PID $(cat .worker2.pid)). Two workers in group 'ops:workers'."
  echo "        Waiting ${DELAY}s so both workers consume..."
  sleep "$DELAY"
  echo ""

  echo "Step 2: Killing worker-1 (simulating failure)..."
  kill "$(cat .worker.pid)" 2>/dev/null || true
  rm -f .worker.pid
  echo "        worker-1 stopped. Its un-ACKed messages stay in Pending."
  echo "        Waiting ${DELAY}s for worker-2 to take over..."
  sleep "$DELAY"
  echo ""

  echo "Step 2b: Removing worker-1 from consumer group (so only worker-2 shows in RedisInsight)..."
  REDIS_HOST="${REDIS_HOST:-localhost}" REDIS_PORT="${REDIS_PORT:-6379}" "$VENV/python" -c "
import os, redis
r = redis.Redis(host=os.getenv('REDIS_HOST', 'localhost'), port=int(os.getenv('REDIS_PORT', 6379)), decode_responses=True)
r.xgroup_delconsumer('ops:events', 'ops:workers', 'worker-1')
print('        Removed worker-1 from group; only worker-2 should appear now.')
" 2>/dev/null || true
  echo ""

  echo "Step 3: Check the dashboard and RedisInsight"
  echo "        • Dashboard: http://localhost:8501 — incidents still updating"
  echo "        • API:      curl http://localhost:8080/incidents"
  echo "        • RedisInsight: http://localhost:5540"
  echo "          → Stream ops:events → Consumer group 'ops:workers'"
  echo "          → Show Pending entries (were on worker-1; can be claimed by others)"
  echo ""

  echo "Quick sanity check — recent incidents (API still serving):"
  curl -s http://localhost:8080/incidents 2>/dev/null | head -c 200
  echo "..."
  echo ""
  echo "Demo complete. worker-2 is still running. Stop all with: ./stop_demo.sh"
  exit 0
fi

# Scale to N workers: ensure worker-2 through worker-N are running
echo "Scaling up to $N workers (worker-1 through worker-$N)..."
started=0
i=2
while [ "$i" -le "$N" ]; do
  pidfile=".worker${i}.pid"
  logfile="logs/worker${i}.log"
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      echo "  worker-$i already running (PID $pid)."
    else
      rm -f "$pidfile"
      echo "  Starting worker-$i..."
      mkdir -p logs
      CONSUMER=worker-$i nohup "$VENV/python" worker.py >> "$logfile" 2>&1 &
      echo $! > "$pidfile"
      echo "    worker-$i started (PID $(cat "$pidfile"))."
      started=$((started + 1))
    fi
  else
    echo "  Starting worker-$i..."
    mkdir -p logs
    CONSUMER=worker-$i nohup "$VENV/python" worker.py >> "$logfile" 2>&1 &
    echo $! > "$pidfile"
    echo "    worker-$i started (PID $(cat "$pidfile"))."
    started=$((started + 1))
  fi
  i=$((i + 1))
done

echo ""
echo "Done. $N workers in group 'ops:workers' (started $started new)."
