"""
Query API for Dragonfly Ingestion Bridge POC.
Exposes last 10 trades per security so CashCache can validate data in Dragonfly.
OpenAPI docs at /apidocs; live dashboard at /dashboard.
"""
import json
import os
import threading
import time
import redis
from flask import Flask, jsonify, Response
from flasgger import Swagger

DRAGONFLY_HOST = os.getenv("DRAGONFLY_HOST", "localhost")
DRAGONFLY_PORT = int(os.getenv("DRAGONFLY_PORT", "6379"))
KEY_PREFIX = "trades:"

app = Flask(__name__)
app.config["SWAGGER"] = {
    "title": "POC Query API",
    "description": "Last 10 trades per security. Data from Dragonfly/Redis (Kafka → bridge).",
    "uiversion": 3,
    "version": "1.0",
}
Swagger(app)

r = redis.Redis(host=DRAGONFLY_HOST, port=DRAGONFLY_PORT, decode_responses=True)

# In-API benchmark (same logic as scripts/benchmark_poc.py) for real-time dashboard
BENCHMARK_N_QUERIES = int(os.getenv("BENCHMARK_QUERIES", "10000"))
BENCHMARK_WARMUP = int(os.getenv("BENCHMARK_WARMUP", "100"))
_benchmark_state = {
    "running": False,
    "message": "Idle",
    "queries_done": 0,
    "total_queries": BENCHMARK_N_QUERIES,
    "elapsed_sec": 0,
    "avg_latency_ms": 0,
    "throughput_ops_sec": None,
    "tickers": 0,
}
_benchmark_lock = threading.Lock()


def _run_benchmark_thread():
    with _benchmark_lock:
        if _benchmark_state["running"]:
            return
        _benchmark_state["running"] = True
        _benchmark_state["message"] = "Starting…"
        _benchmark_state["queries_done"] = 0
        _benchmark_state["elapsed_sec"] = 0
        _benchmark_state["avg_latency_ms"] = 0
        _benchmark_state["throughput_ops_sec"] = None
    try:
        keys = r.keys(f"{KEY_PREFIX}*")
        tickers = [k.replace(KEY_PREFIX, "") for k in keys if r.type(k) == "list"]
        if not tickers:
            with _benchmark_lock:
                _benchmark_state["running"] = False
                _benchmark_state["message"] = "No LIST keys; start POC and wait for data."
            return
        tickers.sort()
        with _benchmark_lock:
            _benchmark_state["tickers"] = len(tickers)
            _benchmark_state["message"] = f"Warmup ({BENCHMARK_WARMUP})…"
        for i in range(BENCHMARK_WARMUP):
            sym = tickers[i % len(tickers)]
            r.lrange(f"{KEY_PREFIX}{sym}", 0, 9)
        with _benchmark_lock:
            _benchmark_state["message"] = "Running benchmark…"
        latencies_ms = []
        start = time.perf_counter()
        for i in range(BENCHMARK_N_QUERIES):
            sym = tickers[i % len(tickers)]
            t0 = time.perf_counter()
            r.lrange(f"{KEY_PREFIX}{sym}", 0, 9)
            latencies_ms.append((time.perf_counter() - t0) * 1000)
            elapsed = time.perf_counter() - start
            with _benchmark_lock:
                _benchmark_state["queries_done"] = i + 1
                _benchmark_state["elapsed_sec"] = round(elapsed, 2)
                _benchmark_state["avg_latency_ms"] = round(sum(latencies_ms) / len(latencies_ms), 2)
        elapsed = time.perf_counter() - start
        avg_ms = sum(latencies_ms) / len(latencies_ms)
        ops_per_sec = BENCHMARK_N_QUERIES / elapsed
        with _benchmark_lock:
            _benchmark_state["running"] = False
            _benchmark_state["message"] = "Done"
            _benchmark_state["queries_done"] = BENCHMARK_N_QUERIES
            _benchmark_state["elapsed_sec"] = round(elapsed, 2)
            _benchmark_state["avg_latency_ms"] = round(avg_ms, 2)
            _benchmark_state["throughput_ops_sec"] = round(ops_per_sec, 0)
    except Exception as e:
        with _benchmark_lock:
            _benchmark_state["running"] = False
            _benchmark_state["message"] = f"Error: {e!s}"


def _last_n_trades(symbol: str, n: int = 10):
    key = f"{KEY_PREFIX}{symbol.upper()}"
    try:
        raw = r.lrange(key, 0, n - 1)
    except redis.exceptions.ResponseError:
        return []
    out = []
    for s in raw:
        try:
            out.append(json.loads(s))
        except json.JSONDecodeError:
            out.append({"raw": s})
    return out


@app.get("/health")
def health():
    """
    Health check
    ---
    responses:
      200:
        description: Service is healthy
        schema:
          type: object
          properties:
            ok:
              type: boolean
              example: true
    """
    return {"ok": True}


@app.get("/ticker/<symbol>")
@app.get("/ticker/<symbol>/last10")
def ticker_last10(symbol):
    """
    Last 10 trades for a symbol
    ---
    parameters:
      - name: symbol
        in: path
        type: string
        required: true
        description: Ticker symbol (e.g. AAPL, MSFT)
    responses:
      200:
        description: Symbol and last 10 trades (newest first)
        schema:
          type: object
          properties:
            symbol:
              type: string
            last_10_trades:
              type: array
              items:
                type: object
    """
    trades = _last_n_trades(symbol, 10)
    return jsonify({"symbol": symbol.upper(), "last_10_trades": trades})


@app.get("/securities")
def securities():
    """
    List securities with at least one trade
    ---
    responses:
      200:
        description: List of ticker symbols
        schema:
          type: object
          properties:
            securities:
              type: array
              items:
                type: string
    """
    keys = r.keys(f"{KEY_PREFIX}*")
    symbols = [k.replace(KEY_PREFIX, "") for k in keys]
    return jsonify({"securities": sorted(symbols)})


@app.get("/benchmark/status")
def benchmark_status():
    """Current benchmark state (for dashboard real-time display)."""
    with _benchmark_lock:
        return jsonify(dict(_benchmark_state))


@app.post("/benchmark/start")
def benchmark_start():
    """Start the benchmark in a background thread (same as run_benchmark.sh logic)."""
    with _benchmark_lock:
        if _benchmark_state["running"]:
            return jsonify({"ok": False, "message": "Benchmark already running"}), 409
    t = threading.Thread(target=_run_benchmark_thread, daemon=True)
    t.start()
    return jsonify({"ok": True, "message": "Benchmark started"})


# Minimal live dashboard: single HTML page that polls the API
DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>POC — Last 10 Trades</title>
  <style>
    body { font-family: system-ui, sans-serif; max-width: 900px; margin: 1rem auto; padding: 0 1rem; }
    h1 { font-size: 1.25rem; }
    h2 { font-size: 1.05rem; margin-top: 1.5rem; }
    .symbols { display: flex; flex-wrap: wrap; gap: 0.5rem; margin: 0.5rem 0; }
    .symbols button { padding: 0.35rem 0.75rem; cursor: pointer; border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5; }
    .symbols button:hover, .symbols button.active { background: #e0e0e0; border-color: #888; }
    table { width: 100%; border-collapse: collapse; margin-top: 0.5rem; }
    th, td { text-align: left; padding: 0.4rem 0.6rem; border-bottom: 1px solid #eee; }
    th { background: #f9f9f9; }
    .meta { color: #666; font-size: 0.85rem; margin-top: 1rem; }
    .benchmark-box { border: 1px solid #ccc; border-radius: 6px; padding: 1rem; margin-top: 1rem; background: #fafafa; }
    .benchmark-box button { padding: 0.5rem 1rem; cursor: pointer; border-radius: 4px; background: #333; color: #fff; border: none; }
    .benchmark-box button:disabled { background: #999; cursor: not-allowed; }
    .benchmark-box .progress { height: 8px; background: #eee; border-radius: 4px; margin: 0.5rem 0; overflow: hidden; }
    .benchmark-box .progress-bar { height: 100%; background: #333; transition: width 0.2s; }
    .benchmark-box .stats { font-family: monospace; font-size: 0.9rem; margin-top: 0.5rem; }
  </style>
</head>
<body>
  <h1>POC — Last 10 trades per security</h1>
  <p>Select a symbol to see the last 10 trades (data from Query API).</p>
  <div id="symbols" class="symbols">Loading…</div>
  <div id="trades"></div>
  <p class="meta" id="meta"></p>

  <h2>Benchmark (real time)</h2>
  <div class="benchmark-box">
    <button type="button" id="benchmarkBtn">Run benchmark</button>
    <div id="benchmarkStatus" class="stats">Idle. Click to run.</div>
    <div class="progress" id="benchmarkProgress" style="display:none;"><div class="progress-bar" id="benchmarkProgressBar" style="width:0;"></div></div>
  </div>

  <script>
    const API = window.location.origin;
    let currentSymbol = null;
    let benchmarkPollTimer = null;
    function fetchJson(path) { return fetch(API + path).then(r => r.json()); }
    function renderSymbols(list) {
      const el = document.getElementById('symbols');
      el.innerHTML = list.map(s => '<button type="button" data-sym="' + s + '">' + s + '</button>').join('');
      el.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => { currentSymbol = btn.dataset.sym; btn.classList.add('active'); el.querySelectorAll('button').forEach(b => b.classList.remove('active')); btn.classList.add('active'); loadTrades(currentSymbol); });
      });
    }
    function loadTrades(sym) {
      if (!sym) return;
      fetchJson('/ticker/' + sym).then(data => {
        const trades = data.last_10_trades || [];
        let html = '<h2>' + data.symbol + ' — last ' + trades.length + ' trades</h2><table><thead><tr><th>Time</th><th>Price</th><th>Qty</th><th>Trade ID</th></tr></thead><tbody>';
        trades.forEach(t => {
          html += '<tr><td>' + (t.timestamp || t.raw || '-') + '</td><td>' + (t.price != null ? t.price : '-') + '</td><td>' + (t.quantity != null ? t.quantity : '-') + '</td><td>' + (t.trade_id || '-') + '</td></tr>';
        });
        html += '</tbody></table>';
        document.getElementById('trades').innerHTML = html;
        document.getElementById('meta').textContent = 'Fetched from ' + API + '/ticker/' + sym;
      }).catch(e => { document.getElementById('trades').innerHTML = '<p>Error: ' + e.message + '</p>'; });
    }
    function updateBenchmarkUI(data) {
      const btn = document.getElementById('benchmarkBtn');
      const status = document.getElementById('benchmarkStatus');
      const progressWrap = document.getElementById('benchmarkProgress');
      const progressBar = document.getElementById('benchmarkProgressBar');
      btn.disabled = !!data.running;
      if (data.running) {
        progressWrap.style.display = 'block';
        const pct = data.total_queries ? Math.round(100 * data.queries_done / data.total_queries) : 0;
        progressBar.style.width = pct + '%';
        status.textContent = data.message + ' — ' + data.queries_done + ' / ' + data.total_queries + ' queries · ' + data.elapsed_sec + 's · avg ' + data.avg_latency_ms + ' ms';
      } else {
        if (data.throughput_ops_sec != null) {
          progressWrap.style.display = 'block';
          progressBar.style.width = '100%';
          status.textContent = 'Done — ' + data.queries_done + ' queries in ' + data.elapsed_sec + 's · Avg latency: ' + data.avg_latency_ms + ' ms · Throughput: ' + data.throughput_ops_sec.toLocaleString() + ' ops/sec';
        } else {
          progressWrap.style.display = 'none';
          status.textContent = data.message || 'Idle. Click to run.';
        }
      }
    }
    function pollBenchmark() {
      fetchJson('/benchmark/status').then(function(data) {
        updateBenchmarkUI(data);
        if (data.running) benchmarkPollTimer = setTimeout(pollBenchmark, 200);
      });
    }
    document.getElementById('benchmarkBtn').addEventListener('click', function() {
      fetch(API + '/benchmark/start', { method: 'POST' }).then(function(r) { return r.json(); }).then(function(data) {
        if (data.ok) { updateBenchmarkUI({ running: true, message: 'Starting…', queries_done: 0, total_queries: 10000, elapsed_sec: 0, avg_latency_ms: 0 }); benchmarkPollTimer = setTimeout(pollBenchmark, 200); }
        else { document.getElementById('benchmarkStatus').textContent = data.message || 'Failed'; }
      }).catch(function(e) { document.getElementById('benchmarkStatus').textContent = 'Error: ' + e.message; });
    });
    fetchJson('/securities').then(data => {
      const list = data.securities || [];
      renderSymbols(list);
      if (list.length && !currentSymbol) { currentSymbol = list[0]; document.querySelector('.symbols button')?.classList.add('active'); loadTrades(currentSymbol); }
    }).catch(() => { document.getElementById('symbols').innerHTML = 'Could not load securities. Is the API running?'; });
    setInterval(() => { if (currentSymbol) loadTrades(currentSymbol); }, 5000);
  </script>
</body>
</html>
"""


@app.get("/dashboard")
def dashboard():
    """Serve the live dashboard (HTML page that polls the API)."""
    return Response(DASHBOARD_HTML, mimetype="text/html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
