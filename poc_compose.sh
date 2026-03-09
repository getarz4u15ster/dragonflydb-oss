# Shared compose file selection and profiles for POC scripts.
# Source after: cd "$(dirname "$0")"
# If we started with ./start_poc.sh redis, use Redis override so stop/scale match.
if [ -f .poc-store ] && [ "$(cat .poc-store)" = "redis" ]; then
  COMPOSE="docker compose -f docker-compose.yml -f docker-compose.redis.yml"
  PROFILES="--profile with-ui"
else
  COMPOSE="docker compose"
  PROFILES="--profile with-ui --profile with-redis"
fi
