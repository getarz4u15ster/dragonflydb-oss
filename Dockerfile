# Dragonfly Ingestion Bridge POC — app image for bridge, producer, and query-api
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt requirements-poc.txt* ./
RUN pip install --no-cache-dir -r requirements.txt \
    && ([ -f requirements-poc.txt ] && pip install --no-cache-dir -r requirements-poc.txt || true)

COPY api_poc.py ./
COPY ingestion/ ./ingestion/
COPY producer/ ./producer/

# Ensure Python can resolve imports when running from /app
ENV PYTHONPATH=/app

# Default: run ingestion bridge (overridden by compose for producer and api)
CMD ["python", "ingestion/kafka_bridge.py"]
