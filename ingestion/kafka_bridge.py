"""
Dragonfly Ingestion Bridge — consume trades from Kafka, store last 10 per security in Dragonfly.
Data model: LIST per symbol. LPUSH (newest at head) then LTRIM 0 9 — simplest "last 10" pattern.

Accepts CashCache schema: symbol, price, quantity, timestamp (ISO8601), trade_id.
Also accepts legacy: ticker, volume for backward compatibility.
"""
import json
import os
import signal
import sys
import time

import redis
from kafka import KafkaConsumer
from kafka.errors import KafkaError

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC_TRADES", "trades")
DRAGONFLY_HOST = os.getenv("DRAGONFLY_HOST", "localhost")
DRAGONFLY_PORT = int(os.getenv("DRAGONFLY_PORT", "6379"))
LAST_N = 10  # "Last 10 trades" per security (per discovery: no longer window for POC)

KEY_PREFIX = "trades:"


def make_key(symbol: str) -> str:
    return f"{KEY_PREFIX}{symbol.upper()}"


def connect_consumer(max_attempts=30, wait_sec=2):
    """Retry until Kafka is available (e.g. after docker compose up)."""
    for attempt in range(1, max_attempts + 1):
        try:
            return KafkaConsumer(
                TOPIC,
                bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                value_deserializer=lambda m: json.loads(m.decode("utf-8")),
                auto_offset_reset="latest",
                group_id="dragonfly-bridge",
            )
        except Exception as e:
            print(f"Kafka not ready (attempt {attempt}/{max_attempts}): {e}", file=sys.stderr)
            if attempt < max_attempts:
                time.sleep(wait_sec)
            else:
                raise
    raise RuntimeError("Could not connect to Kafka")


def main():
    print(f"Connecting to Kafka {KAFKA_BOOTSTRAP}, topic '{TOPIC}'")
    consumer = connect_consumer()

    print(f"Connecting to Dragonfly at {DRAGONFLY_HOST}:{DRAGONFLY_PORT}")
    r = redis.Redis(host=DRAGONFLY_HOST, port=DRAGONFLY_PORT, decode_responses=True)

    running = True

    def shutdown(*_):
        nonlocal running
        running = False

    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    try:
        for message in consumer:
            if not running:
                break
            try:
                trade = message.value
                # CashCache schema: symbol; legacy: ticker
                symbol = trade.get("symbol") or trade.get("ticker")
                if not symbol:
                    continue
                key = make_key(symbol)
                value = json.dumps(trade)
                r.lpush(key, value)
                r.ltrim(key, 0, LAST_N - 1)
            except (redis.RedisError, json.JSONDecodeError) as e:
                print(f"Bridge error: {e}", file=sys.stderr)
    except KafkaError as e:
        print(f"Kafka error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        consumer.close()


if __name__ == "__main__":
    main()
