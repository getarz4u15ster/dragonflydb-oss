#!/usr/bin/env bash
# Scale the POC ingestion bridge back to 1 instance.
#
# Usage: ./scale_down_poc.sh
#
# Prereq: POC is running.
set -e
cd "$(dirname "$0")"
. ./poc_compose.sh

echo "scale_down_poc: scaling ingestion-bridge back to 1 instance."
$COMPOSE $PROFILES up -d --scale ingestion-bridge=1
echo ""
echo "Done. One ingestion-bridge instance."
echo "Check: $COMPOSE $PROFILES ps"
