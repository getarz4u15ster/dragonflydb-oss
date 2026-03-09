#!/usr/bin/env bash
# Stop the POC (containers are stopped but not removed, so RedisInsight keeps its config).
set -e
cd "$(dirname "$0")"
. ./poc_compose.sh
echo "Stopping POC (including RedisInsight)..."
$COMPOSE $PROFILES stop
echo "POC stopped. Containers are kept so you don't have to reconfigure RedisInsight."
echo "To remove containers and volumes, run: $COMPOSE $PROFILES down -v"
