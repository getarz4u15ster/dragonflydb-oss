"""
Query API for Dragonfly Ingestion Bridge POC.
Exposes last 10 trades per security so CashCache can validate data in Dragonfly.
"""
import json
import os
import redis
from flask import Flask, jsonify

DRAGONFLY_HOST = os.getenv("DRAGONFLY_HOST", "localhost")
DRAGONFLY_PORT = int(os.getenv("DRAGONFLY_PORT", "6379"))
KEY_PREFIX = "trades:"

app = Flask(__name__)
r = redis.Redis(host=DRAGONFLY_HOST, port=DRAGONFLY_PORT, decode_responses=True)


def _last_n_trades(symbol: str, n: int = 10):
    key = f"{KEY_PREFIX}{symbol.upper()}"
    raw = r.zrevrange(key, 0, n - 1)
    out = []
    for s in raw:
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            out.append({"raw": s})
    return out


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/ticker/<symbol>")
@app.get("/ticker/<symbol>/last10")
def ticker_last10(symbol):
    """Return the last 10 trades for the given security (per POC requirement)."""
    trades = _last_n_trades(symbol, 10)
    return jsonify({"symbol": symbol.upper(), "last_10_trades": trades})


@app.get("/securities")
def securities():
    """List securities (tickers) that have at least one trade in Dragonfly."""
    keys = r.keys(f"{KEY_PREFIX}*")
    symbols = [k.replace(KEY_PREFIX, "") for k in keys]
    return jsonify({"securities": sorted(symbols)})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
