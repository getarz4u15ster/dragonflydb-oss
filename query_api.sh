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

case "${1:-}" in
  health)
    echo "=== Health ==="
    curl -s "$BASE/health" | python3 -m json.tool
    ;;
  securities)
    echo "=== Securities ==="
    curl -s "$BASE/securities" | python3 -m json.tool
    ;;
  ticker)
    sym="${2:-AAPL}"
    echo "=== Ticker $sym (last 10) ==="
    curl -s "$BASE/ticker/$sym" | python3 -m json.tool
    ;;
  "")
    echo "=== Health ==="
    curl -s "$BASE/health" | python3 -m json.tool
    echo ""
    echo "=== Securities ==="
    curl -s "$BASE/securities" | python3 -m json.tool
    echo ""
    echo "=== Ticker AAPL (last 10) ==="
    curl -s "$BASE/ticker/AAPL" | python3 -m json.tool
    ;;
  *)
    # Treat first arg as symbol
    echo "=== Ticker $1 (last 10) ==="
    curl -s "$BASE/ticker/$1" | python3 -m json.tool
    ;;
esac
