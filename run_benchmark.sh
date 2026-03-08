#!/usr/bin/env bash
# Run the POC benchmark (query latency + throughput). POC should be running with data flowing.
set -e
cd "$(dirname "$0")"
VENV="${PWD}/.venv"
if [ -d "$VENV" ] && [ -x "$VENV/bin/python" ]; then
  export PATH="${VENV}/bin:${PATH}"
  "$VENV/bin/python" scripts/benchmark_poc.py "$@"
else
  python3 scripts/benchmark_poc.py "$@"
fi
