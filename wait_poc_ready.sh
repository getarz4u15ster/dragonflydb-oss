#!/usr/bin/env bash
# Wait until the POC API has at least one symbol with 10 trades, then print "POC ready".
# Usage: ./wait_poc_ready.sh [max_wait_seconds]
# Default max wait: 120. Exit 0 when ready, 1 on timeout.
set -e
BASE="${BASE_URL:-http://localhost:8080}"
MAX_WAIT="${1:-120}"
INTERVAL=5
elapsed=0

while [ "$elapsed" -lt "$MAX_WAIT" ]; do
  body=$(curl -s "$BASE/securities" 2>/dev/null) || true
  sym=$(echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); s=d.get('securities'); print(s[0] if s and len(s)>0 else '')" 2>/dev/null) || true
  if [ -n "$sym" ]; then
    ticker=$(curl -s "$BASE/ticker/$sym" 2>/dev/null) || true
    if [ -n "$ticker" ] && echo "$ticker" | python3 -c "import sys,json; d=json.load(sys.stdin); t=d.get('last_10_trades') or []; exit(0 if len(t)>=10 else 1)" 2>/dev/null; then
      echo "POC ready (10 trades for $sym)."
      exit 0
    fi
  fi
  echo "Waiting for 10 trades... (${elapsed}s / ${MAX_WAIT}s)"
  sleep "$INTERVAL"
  elapsed=$((elapsed + INTERVAL))
done

echo "Timeout: no symbol with 10 trades after ${MAX_WAIT}s. Is the POC running? Try: ./start_poc.sh"
exit 1
