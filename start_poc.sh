#!/usr/bin/env bash
# Start the POC with RedisInsight (Dragonfly UI at http://localhost:5540).
set -e
cd "$(dirname "$0")"
echo "Starting POC (Kafka, Dragonfly, bridge, producer, API, RedisInsight)..."
docker compose --profile with-ui up -d
echo ""
echo "POC is starting. Wait 30–60 seconds for data to flow."
echo "  API:          http://localhost:8080"
echo "  RedisInsight: http://localhost:5540  (add DB: host=dragonfly, port=6379)"
echo "  Dragonfly:    localhost:6379"
echo ""
echo "Stop with: ./stop_poc.sh"
