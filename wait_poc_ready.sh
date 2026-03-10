#!/usr/bin/env bash
# Wait until the POC API returns at least one security (data is flowing), then print "POC ready".
# Usage: ./wait_poc_ready.sh [max_wait_seconds]
# Default max wait: 120. Exit 0 when ready, 1 on timeout.
set -e
BASE="${BASE_URL:-http://localhost:8080}"
MAX_WAIT="${1:-120}"
INTERVAL=5
elapsed=0

while [ "$elapsed" -lt "$MAX_WAIT" ]; do
  body=$(curl -s "$BASE/securities" 2>/dev/null) || true
  if [ -n "$body" ] && echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if d.get('securities') and len(d['securities'])>0 else 1)" 2>/dev/null; then
    echo "POC ready."
    exit 0
  fi
  echo "Waiting for data... (${elapsed}s / ${MAX_WAIT}s)"
  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done

echo "Timeout: no securities after ${MAX_WAIT}s. Is the POC running? Try: ./start_poc.sh"
exit 1
