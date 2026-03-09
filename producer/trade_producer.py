"""
Mock trade producer for Dragonfly Ingestion Bridge POC.
Publishes trade messages to Kafka topic 'trades' for the bridge to consume into Dragonfly.

Message schema (per CashCache discovery): flat JSON
  symbol: string (e.g. "AAPL")
  price: float (e.g. 150.25)
  quantity: integer (e.g. 100)
  timestamp: ISO8601 string
  trade_id: string (UUID)
"""
import json
import os
import random
import time
import uuid
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC_TRADES", "trades")
# Subset of symbols for POC; production tracks ~12k, with 500–1k "hot" at any time
SYMBOLS = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "WMT",
    "BAC", "HD", "DIS", "NFLX", "ADBE", "CRM", "ORCL", "CSCO", "INTC", "AMD",
]
# Delay between trades (seconds). Lower = more load on Kafka and Dragonfly.
# Default 0.1–0.5; for load testing try TRADE_DELAY_MIN=0.01 TRADE_DELAY_MAX=0.02
DELAY_MIN = float(os.getenv("TRADE_DELAY_MIN", "0.1"))
DELAY_MAX = float(os.getenv("TRADE_DELAY_MAX", "0.5"))


def connect_producer(max_attempts=30, wait_sec=2):
    """Retry until Kafka is available (e.g. after docker compose up)."""
    for attempt in range(1, max_attempts + 1):
        try:
            return KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=10,
                retry_backoff_ms=1000,
            )
        except Exception as e:
            print(f"Kafka not ready (attempt {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(wait_sec)
            else:
                raise
    raise RuntimeError("Could not connect to Kafka")


def main():
    print(f"Connecting to Kafka at {KAFKA_BOOTSTRAP}, topic '{TOPIC}'")
    producer = connect_producer()

    try:
        while True:
            symbol = random.choice(SYMBOLS)
            price = round(100 + random.random() * 500, 2)
            quantity = random.randint(10, 5000)
            timestamp = datetime.now(timezone.utc).isoformat(timespec="milliseconds") + "Z"
            trade_id = str(uuid.uuid4())
            msg = {
                "symbol": symbol,
                "price": price,
                "quantity": quantity,
                "timestamp": timestamp,
                "trade_id": trade_id,
            }
            producer.send(TOPIC, value=msg)
            producer.flush()
            print(f"Produced {symbol} @ {price} x {quantity} ({trade_id[:8]}...)")
            time.sleep(random.uniform(DELAY_MIN, DELAY_MAX))
    except KafkaError as e:
        print(f"Kafka error: {e}")
        raise
    finally:
        producer.close()


if __name__ == "__main__":
    main()
