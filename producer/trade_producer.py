"""
Mock trade producer for Dragonfly Ingestion Bridge POC.
Publishes trade messages to Kafka topic 'trades' for the bridge to consume into Dragonfly.
"""
import json
import os
import random
import time
from datetime import datetime, timezone

from kafka import KafkaProducer
from kafka.errors import KafkaError

KAFKA_BOOTSTRAP = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC_TRADES", "trades")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", "V", "WMT"]


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
            ticker = random.choice(TICKERS)
            price = round(100 + random.random() * 500, 2)
            volume = random.randint(10, 5000)
            ts = int(datetime.now(timezone.utc).timestamp())
            msg = {"ticker": ticker, "price": price, "volume": volume, "timestamp": ts}
            producer.send(TOPIC, value=msg)
            producer.flush()
            print(f"Produced {ticker} @ {price} x {volume}")
            time.sleep(random.uniform(0.1, 0.5))
    except KafkaError as e:
        print(f"Kafka error: {e}")
        raise
    finally:
        producer.close()


if __name__ == "__main__":
    main()
