#!/usr/bin/env bash
# Scale the POC ingestion bridge to N instances (Kafka consumer group shares partitions).
# Ensure the Kafka topic has enough partitions first, then scale bridge containers.
#
# Usage:
#   ./scale_out_poc.sh [N]   scale to N bridge instances (default: 2)
#
# Prereq: POC is running (./start_poc.sh or docker compose --profile with-ui up -d).
set -e
cd "$(dirname "$0")"
. ./poc_compose.sh

N=2
if [ -n "$1" ]; then
  case "$1" in
    ''|*[!0-9]*) echo "Usage: $0 [N]   (N = number of ingestion-bridge instances, 2-10; default 2)"; exit 1 ;;
  esac
  N="$1"
  if [ "$N" -lt 2 ] || [ "$N" -gt 10 ]; then
    echo "N must be between 2 and 10 (got $N)."
    exit 1
  fi
fi

echo "scale_out_poc: ensuring topic 'trades' has enough partitions, then scaling to $N bridge(s)."
echo ""

# Ensure topic exists with enough partitions so multiple consumers get work
PARTITIONS=$((N > 4 ? N : 4))
echo "Step 1: Topic 'trades' with ${PARTITIONS} partition(s)..."
$COMPOSE $PROFILES exec -T kafka kafka-topics --create --topic trades --partitions "$PARTITIONS" --replication-factor 1 --bootstrap-server localhost:9092 2>/dev/null || true
$COMPOSE $PROFILES exec -T kafka kafka-topics --alter --topic trades --partitions "$PARTITIONS" --bootstrap-server localhost:9092 2>/dev/null || true
echo ""

echo "Step 2: Scaling ingestion-bridge to $N instance(s)..."
$COMPOSE $PROFILES up -d --scale ingestion-bridge="$N"
echo ""
echo "Done. $N ingestion-bridge instance(s) in consumer group 'dragonfly-bridge'."
echo "Check: $COMPOSE $PROFILES ps"
