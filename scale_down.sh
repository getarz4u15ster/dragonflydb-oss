#!/usr/bin/env bash
# Scale down to N workers (worker-1 through worker-N).
# Stops worker-{N+1}, worker-{N+2}, ... and removes them from the Redis consumer group.
#
# Usage:
#   ./scale_down.sh [N]   scale to N workers (default: 1). E.g. ./scale_down.sh 2 → keep worker-1, worker-2
set -e
cd "$(dirname "$0")"
VENV="${PWD}/.venv/bin"

N=1
if [ -n "$1" ]; then
  case "$1" in
    ''|*[!0-9]*) echo "Usage: $0 [N]   (N = number of workers to keep, 1-50; default 1)"; exit 1 ;;
  esac
  N="$1"
  if [ "$N" -lt 1 ] || [ "$N" -gt 50 ]; then
    echo "N must be between 1 and 50 (got $N)."
    exit 1
  fi
fi

echo "scale_down: target $N worker(s) (worker-1 through worker-$N)."
echo ""

if [ "$N" -eq 1 ]; then
  echo "Scaling down to single worker (worker-1)..."
  # Stop all extra workers (worker-2, worker-3, ...) by PID file
  for pidfile in .worker*.pid; do
    [ -f "$pidfile" ] || continue
    [ "$pidfile" = ".worker.pid" ] && continue
    pid=$(cat "$pidfile")
    name="${pidfile#.worker}"
    name="${name%.pid}"
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      kill -9 "$pid" 2>/dev/null || true
      echo "  Stopped worker-${name} (PID $pid)."
    else
      echo "  worker-${name} process not running (stale $pidfile)."
    fi
    rm -f "$pidfile"
  done
  # Kill any remaining worker.py processes that are not worker-1 (e.g. no pid file)
  worker1_pid=""
  [ -f .worker.pid ] && worker1_pid=$(cat .worker.pid)
  for pid in $(pgrep -f "[w]orker\.py" 2>/dev/null); do
    [ -n "$worker1_pid" ] && [ "$pid" = "$worker1_pid" ] && continue
    kill "$pid" 2>/dev/null || true
    for _ in 1 2 3 4 5; do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
    kill -9 "$pid" 2>/dev/null || true
    echo "  Stopped extra worker process (PID $pid)."
  done
  # Remove all consumers except worker-1 from Redis (so they can't re-join)
  echo "  Removing extra consumers from Redis group..."
  REDIS_HOST="${REDIS_HOST:-localhost}" REDIS_PORT="${REDIS_PORT:-6379}" "$VENV/python" "${PWD}/scripts/redis_remove_consumers.py" 1 || echo "  (Redis cleanup skipped; is Redis running?)"
else
  # N > 1: stop only worker-{N+1}, worker-{N+2}, ...
  echo "Scaling down to $N workers (worker-1 through worker-$N)..."
  i=$((N + 1))
  while [ "$i" -le 50 ]; do
    pidfile=".worker${i}.pid"
    [ -f "$pidfile" ] || { i=$((i + 1)); continue; }
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
      for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      kill -9 "$pid" 2>/dev/null || true
      echo "  Stopped worker-$i (PID $pid)."
    else
      echo "  worker-$i process not running (stale $pidfile)."
    fi
    rm -f "$pidfile"
    i=$((i + 1))
  done
  # Remove from Redis only consumers worker-{N+1}, worker-{N+2}, ...
  echo "  Removing extra consumers from Redis group..."
  REDIS_HOST="${REDIS_HOST:-localhost}" REDIS_PORT="${REDIS_PORT:-6379}" "$VENV/python" "${PWD}/scripts/redis_remove_consumers.py" "$N" || echo "  (Redis cleanup skipped; is Redis running?)"
fi

# Ensure worker-1 through worker-N are running
mkdir -p logs
i=1
while [ "$i" -le "$N" ]; do
  pidfile=".worker${i}.pid"
  logfile="logs/worker${i}.log"
  if [ "$i" -eq 1 ]; then
    pidfile=".worker.pid"
    logfile="logs/worker.log"
  fi
  if [ -f "$pidfile" ]; then
    pid=$(cat "$pidfile")
    if kill -0 "$pid" 2>/dev/null; then
      echo "  worker-$i already running (PID $pid)."
    else
      rm -f "$pidfile"
      echo "  Starting worker-$i..."
      CONSUMER=worker-$i nohup "$VENV/python" worker.py >> "$logfile" 2>&1 &
      echo $! > "$pidfile"
      echo "    worker-$i started (PID $(cat "$pidfile"))."
    fi
  else
    echo "  Starting worker-$i..."
    CONSUMER=worker-$i nohup "$VENV/python" worker.py >> "$logfile" 2>&1 &
    echo $! > "$pidfile"
    echo "    worker-$i started (PID $(cat "$pidfile"))."
  fi
  i=$((i + 1))
done

echo ""
echo "Done. $N worker(s) in group 'ops:workers'."
