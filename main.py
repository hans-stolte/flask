from flask import Flask, request, jsonify, Response
from collections import deque
from datetime import datetime, timezone
from threading import Lock
import json
import uuid

app = Flask(__name__)

# --- Simple in-memory log (thread-safe) --------------------------------------
LOG_CAPACITY = 1000
_decisions = deque(maxlen=LOG_CAPACITY)
_log_lock = Lock()
_started_at = datetime.now(timezone.utc)
VERSION = "alpha-1"

def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def _decide(task: str, complexity: float) -> str:
    """Very simple demo policy."""
    if complexity > 0.8:
        return "Quantum"
    elif 0.4 < complexity <= 0.8:
        return "Hybrid"
    return "Classical"

def _log_decision(entry: dict):
    with _log_lock:
        _decisions.appendleft(entry)

# --- Routes -------------------------------------------------------------------

@app.route("/")
def home():
    return "🚀 QuantumPod Alpha is online!"

@app.route("/health")
def health():
    uptime = (datetime.now(timezone.utc) - _started_at).total_seconds()
    return jsonify({
        "status": "ok",
        "version": VERSION,
        "uptime_seconds": round(uptime, 2),
        "decisions_logged": len(_decisions)
    })

@app.route("/route", methods=["POST"])
def route_task():
    """
    Input: {"task": "portfolio_optimisation", "complexity": 0.7}
    Output: {"decision": "Quantum" | "Hybrid" | "Classical", ...}
    """
    data = request.get_json(force=True, silent=False) or {}
    task = str(data.get("task", "unspecified"))
    try:
        complexity = float(data.get("complexity", 0.5))
    except (TypeError, ValueError):
        return jsonify({"error": "complexity must be a number 0..1"}), 400

    # clamp to [0,1] so the demo is predictable
    complexity = max(0.0, min(1.0, complexity))
    decision = _decide(task, complexity)

    # log the decision
    entry = {
        "id": str(uuid.uuid4()),
        "ts": _iso(datetime.now(timezone.utc)),
        "task": task,
        "complexity": complexity,
        "decision": decision,
        "client_ip": request.headers.get("x-forwarded-for", request.remote_addr),
        "user_agent": request.headers.get("user-agent", ""),
        "path": request.path
    }
    _log_decision(entry)

    return jsonify({
        "task": task,
        "complexity": complexity,
        "decision": decision,
        "id": entry["id"],
        "ts": entry["ts"]
    })

@app.route("/decisions")
def decisions():
    """
    View recent decisions.
    Query params:
      ?limit=50      -> number of rows (default 50, max 200)
      ?format=json   -> json (default) or html
    """
    limit = request.args.get("limit", default="50")
    fmt = request.args.get("format", default="json").lower()
    try:
        limit = max(1, min(200, int(limit)))
    except ValueError:
        limit = 50

    with _log_lock:
        rows = list(list(_decisions)[:limit])

    if fmt == "html":
        # quick, tidy HTML table for demos
        head = "<tr>" + "".join(f"<th>{k}</th>" for k in ["ts","id","task","complexity","decision","client_ip"]) + "</tr>"
        body = "\n".join(
            "<tr><td>{ts}</td><td>{id}</td><td>{task}</td><td>{complexity}</td><td>{decision}</td><td>{client_ip}</td></tr>".format(**r)
            for r in rows
        )
        html = f"""
        <!doctype html><html><head><meta charset="utf-8"><title>QuantumPod Decisions</title>
        <style>
          body{{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px}}
          table{{border-collapse:collapse;width:100%}} th,td{{border:1px solid #ddd;padding:8px}}
          th{{background:#f4f6fb;text-align:left}}
        </style></head><body>
        <h2>Recent Decisions ({len(rows)})</h2>
        <p>Try <code>?limit=100</code> or <code>?format=json</code>.</p>
        <table>{head}{body}</table>
        </body></html>
        """
        return html
    else:
        return jsonify({"count": len(rows), "items": rows})

@app.route("/log")
def download_log():
    """
    Download the full in-memory log as CSV (up to LOG_CAPACITY lines).
    """
    with _log_lock:
        rows = list(_decisions)

    # CSV header + rows
    cols = ["ts","id","task","complexity","decision","client_ip","user_agent","path"]
    def gen():
        yield ",".join(cols) + "\n"
        for r in rows:
            # basic CSV escaping for commas/quotes
            def esc(v):
                s = str(v).replace('"', '""')
                return f'"{s}"'
            yield ",".join(esc(r.get(c,"")) for c in cols) + "\n"

    return Response(gen(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=quantumpod_decisions.csv"})

# --- Pretty browser tester ----------------------------------------------------

@app.route("/test")
def test_page():
    return """
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>QuantumPod Router – Live Demo</title>
<style>
  :root { --bg:#0b0f19; --card:#151b2b; --muted:#8ea0c0; --text:#e8eefc; --accent:#8ad1ff; }
  *{box-sizing:border-box;font-family:system-ui,-apple-system,Segoe UI,Roboto,Inter,Arial}
  body{margin:0;background:linear-gradient(180deg,#0b0f19,#0f1730);color:var(--text);display:grid;min-height:100dvh;place-items:center;padding:24px}
  .wrap{width:min(920px,96vw)}
  header{display:flex;gap:12px;align-items:center;margin-bottom:16px}
  .dot{height:10px;width:10px;border-radius:50%;background:#38d39f;box-shadow:0 0 12px #38d39f}
  h1{font-size:22px;margin:0}
  .card{background:var(--card);border:1px solid #27324a;border-radius:16px;padding:20px;box-shadow:0 10px 30px rgba(0,0,0,.25)}
  .grid{display:grid;gap:16px;grid-template-columns:1fr 1fr}
  label{font-size:12px;color:var(--muted);letter-spacing:.02em}
  select,input[type=number],input[type=text]{width:100%;padding:12px 14px;border:1px solid #2c3957;background:#0f1425;color:var(--text);border-radius:10px;outline:none}
  input[type=range]{width:100%}
  .kpi{display:flex;gap:10px;align-items:center;padding:10px 12px;border:1px dashed #2e3a5c;border-radius:10px;background:#0f1425}
  .kpi b{font-size:28px}
  button{padding:12px 16px;border-radius:12px;border:0;background:linear-gradient(90deg,#5ab4ff,#7fe3ff);color:#001c2e;font-weight:600;cursor:pointer}
  button:disabled{opacity:.5;cursor:not-allowed}
  .out{white-space:pre-wrap;background:#0b1222;border:1px solid #27324a;border-radius:12px;padding:14px;min-height:112px}
  .row{display:flex;gap:12px;align-items:center;justify-content:space-between}
  .muted{color:var(--muted);font-size:12px}
  .pill{padding:6px 10px;border-radius:999px;border:1px solid #33466f;background:#111b34}
  @media (max-width:720px){.grid{grid-template-columns:1fr}}
</style>
</head>
<body>
  <div class="wrap">
    <header>
      <div class="dot"></div>
      <h1>🚀 QuantumPod Router – Live Demo</h1>
      <span class="pill">/route</span>
    </header>

    <div class="card">
      <div class="grid" style="margin-bottom:16px">
        <div>
          <label>Task type</label>
          <select id="task">
            <option value="portfolio_optimisation">Portfolio optimisation</option>
            <option value="vrp_routing">Vehicle routing (VRP)</option>
            <option value="scheduling">Job scheduling</option>
            <option value="simulation">Physics simulation</option>
            <option value="inference">AI inference</option>
          </select>
        </div>
        <div>
          <label>Complexity (0–1)</label>
          <div class="kpi">
            <input id="complexity" type="range" min="0" max="1" step="0.01" value="0.75" oninput="cval.textContent=this.value">
            <b id="cval">0.75</b>
          </div>
        </div>
      </div>

      <div class="row" style="margin-bottom:12px">
        <div class="muted">Endpoint: <code>/route</code></div>
        <div class="row" style="gap:8px">
          <button id="send">Send</button>
          <button id="copycurl" title="Copy as cURL">Copy cURL</button>
          <a class="pill" href="/decisions?format=html" target="_blank" style="text-decoration:none;color:inherit">View Decisions</a>
        </div>
      </div>

      <div class="out" id="out">{ "status": "ready" }</div>
      <div class="muted" style="margin-top:8px">Try <a href="/health" target="_blank">/health</a> or download <a href="/log">/log</a>.</div>
    </div>
  </div>

<script>
const base = location.origin;

function payload(){
  return {
    task: document.getElementById('task').value,
    complexity: parseFloat(document.getElementById('complexity').value)
  };
}
function curlFor(p){
  return `curl -X POST ${base}/route -H "Content-Type: application/json" -d "{\\"task\\":\\"${p.task}\\",\\"complexity\\":${p.complexity}}"`;
}
async function call(){
  const btn = document.getElementById('send');
  const out = document.getElementById('out');
  btn.disabled = true; out.textContent = "Calling /route …";
  try{
    const res = await fetch(base + "/route", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload())
    });
    const txt = await res.text();
    out.textContent = txt;
  }catch(e){
    out.textContent = "Error: " + e;
  }finally{
    btn.disabled = false;
  }
}
document.getElementById('send').onclick = call;
document.getElementById('copycurl').onclick = async ()=>{
  await navigator.clipboard.writeText(curlFor(payload()));
  const b = document.getElementById('copycurl');
  const old = b.textContent; b.textContent = "Copied"; setTimeout(()=>b.textContent=old,900);
};
</script>
</body>
</html>
"""

# ------------------------------------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
