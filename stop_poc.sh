#!/usr/bin/env bash
# Stop the POC (containers are stopped but not removed, so RedisInsight keeps its config).
set -e
cd "$(dirname "$0")"
echo "Stopping POC (including RedisInsight)..."
docker compose --profile with-ui stop
echo "POC stopped. Containers are kept so you don't have to reconfigure RedisInsight."
echo "To remove containers and volumes, run: docker compose --profile with-ui down -v"
