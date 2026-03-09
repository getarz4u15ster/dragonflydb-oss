#!/usr/bin/env bash
# Run curl against the POC query API. POC must be running (./start_poc.sh).
# Usage:
#   ./query_api.sh              # health + securities + ticker AAPL
#   ./query_api.sh health       # health only
#   ./query_api.sh securities   # list securities only
#   ./query_api.sh ticker AAPL  # last 10 trades for AAPL
#   ./query_api.sh AAPL         # same as ticker AAPL
set -e
BASE="${BASE_URL:-http://localhost:8080}"

# Pretty-print JSON or show a clear error if API is unreachable / returns non-JSON
run() {
  local body
  body=$(curl -s -w "\n%{http_code}" "$1") || { echo "curl failed. Is the POC running? Try: ./start_poc.sh"; return 1; }
  local code="${body##*$'\n'}"
  body="${body%$'\n'*}"
  if [ -z "$body" ]; then
    echo "Empty response from $1 — is the POC running? Try: ./start_poc.sh"
    return 1
  fi
  if [ "$code" != "200" ]; then
    echo "HTTP $code from $1"
    echo "$body" | python3 -m json.tool 2>/dev/null || echo "$body"
    return 1
  fi
  echo "$body" | python3 -m json.tool || { echo "Invalid JSON from $1"; echo "$body"; return 1; }
}

case "${1:-}" in
  health)
    echo "=== Health ==="
    run "$BASE/health"
    ;;
  securities)
    echo "=== Securities ==="
    run "$BASE/securities"
    ;;
  ticker)
    sym="${2:-AAPL}"
    echo "=== Symbol $sym (last 10 trades) ==="
    run "$BASE/ticker/$sym"
    ;;
  "")
    echo "=== Health ==="
    run "$BASE/health"
    echo ""
    echo "=== Securities ==="
    run "$BASE/securities"
    echo ""
    echo "=== Symbol AAPL (last 10 trades) ==="
    run "$BASE/ticker/AAPL"
    ;;
  *)
    # Treat first arg as symbol
    echo "=== Symbol $1 (last 10 trades) ==="
    run "$BASE/ticker/$1"
    ;;
esac
