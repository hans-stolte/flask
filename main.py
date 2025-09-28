import os, uuid, json
from datetime import datetime, timezone
from flask import Flask, request, jsonify, Response
from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker, scoped_session
from sqlalchemy import String, DateTime, Float

# ------------------------------------------------------------------------------
# Flask
# ------------------------------------------------------------------------------
app = Flask(__name__)
VERSION = "alpha-2"

# ------------------------------------------------------------------------------
# Database (Postgres preferred; SQLite fallback for local/dev)
# ------------------------------------------------------------------------------
DB_URL = os.getenv("DATABASE_URL", "sqlite:///data.db")

# Railway Postgres usually needs this param for SQLAlchemy 2.x style URLs
# (SQLAlchemy accepts both postgres:// and postgresql://, normalize if needed)
if DB_URL.startswith("postgres://"):
    DB_URL = DB_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DB_URL, pool_pre_ping=True)

class Base(DeclarativeBase):
    pass

class Decision(Base):
    __tablename__ = "decisions"
    id: Mapped[str]         = mapped_column(String(40), primary_key=True)
    ts: Mapped[datetime]    = mapped_column(DateTime(timezone=True), index=True)
    task: Mapped[str]       = mapped_column(String(200), index=True)
    complexity: Mapped[float] = mapped_column(Float)
    decision: Mapped[str]   = mapped_column(String(32), index=True)
    client_ip: Mapped[str]  = mapped_column(String(64), default="")
    user_agent: Mapped[str] = mapped_column(String(500), default="")
    path: Mapped[str]       = mapped_column(String(200), default="/route")

# create tables if they don't exist
Base.metadata.create_all(engine)

SessionLocal = scoped_session(sessionmaker(bind=engine, expire_on_commit=False))

# ------------------------------------------------------------------------------
# Core decision policy
# ------------------------------------------------------------------------------
def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()

def _decide(task: str, complexity: float) -> str:
    if complexity > 0.8:
        return "Quantum"
    elif 0.4 < complexity <= 0.8:
        return "Hybrid"
    return "Classical"

# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------
@app.route("/")
def home():
    return "🚀 QuantumPod Alpha is online!"

@app.route("/health")
def health():
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        with SessionLocal() as s:
            count = s.query(Decision).count()
        status = "ok"
    except Exception as e:
        status = f"db_error: {e.__class__.__name__}"
        count = None
    return jsonify({
        "status": status,
        "version": VERSION,
        "db_url_scheme": DB_URL.split("://", 1)[0],
        "decisions_logged": count
    })

@app.route("/route", methods=["POST"])
def route_task():
    """
    Input: {"task": "portfolio_optimisation", "complexity": 0.7}
    Output: {"decision": "...", "id": "...", "ts": "...", ...}
    """
    data = request.get_json(force=True) or {}
    task = str(data.get("task", "unspecified"))
    try:
        complexity = float(data.get("complexity", 0.5))
    except (TypeError, ValueError):
        return jsonify({"error": "complexity must be a number 0..1"}), 400

    # clamp for demo predictability
    complexity = max(0.0, min(1.0, complexity))
    decision = _decide(task, complexity)

    entry = Decision(
        id=str(uuid.uuid4()),
        ts=datetime.now(timezone.utc),
        task=task,
        complexity=complexity,
        decision=decision,
        client_ip=request.headers.get("x-forwarded-for", request.remote_addr),
        user_agent=request.headers.get("user-agent", "")[:500],
        path=request.path
    )
    with SessionLocal() as s:
        s.add(entry)
        s.commit()

    return jsonify({
        "task": task,
        "complexity": complexity,
        "decision": decision,
        "id": entry.id,
        "ts": _iso(entry.ts)
    })

@app.route("/decisions")
def decisions():
    """
    Query params:
      ?limit=50         (max 200)
      ?format=json|html (default json)
      ?task=...         (optional filter)
      ?since=ISO8601    (optional, e.g. 2025-09-28T00:00:00Z)
    """
    limit = request.args.get("limit", "50")
    fmt   = request.args.get("format", "json").lower()
    taskf = request.args.get("task")
    since = request.args.get("since")

    try:
        limit = max(1, min(200, int(limit)))
    except ValueError:
        limit = 50

    with SessionLocal() as s:
        q = s.query(Decision)
        if taskf:
            q = q.filter(Decision.task == taskf)
        if since:
            try:
                dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
                q = q.filter(Decision.ts >= dt)
            except Exception:
                pass
        rows = q.order_by(Decision.ts.desc()).limit(limit).all()

    items = [
        {
            "ts": _iso(r.ts), "id": r.id, "task": r.task,
            "complexity": r.complexity, "decision": r.decision,
            "client_ip": r.client_ip
        } for r in rows
    ]

    if fmt == "html":
        head = "<tr>" + "".join(f"<th>{k}</th>" for k in ["ts","id","task","complexity","decision","client_ip"]) + "</tr>"
        body = "\n".join(
            f"<tr><td>{i['ts']}</td><td>{i['id']}</td><td>{i['task']}</td>"
            f"<td>{i['complexity']}</td><td>{i['decision']}</td><td>{i['client_ip']}</td></tr>"
            for i in items
        )
        html = f"""<!doctype html><html><head><meta charset="utf-8">
        <title>QuantumPod Decisions</title>
        <style>body{{font-family:system-ui,Segoe UI,Roboto,Arial;margin:20px}}
        table{{border-collapse:collapse;width:100%}}th,td{{border:1px solid #ddd;padding:8px}}
        th{{background:#f4f6fb;text-align:left}}</style></head><body>
        <h2>Recent Decisions ({len(items)})</h2>
        <p>Filters: <code>?task=…</code> <code>?since=ISO</code> <code>?limit=…</code></p>
        <table>{head}{body}</table></body></html>"""
        return html
    else:
        return jsonify({"count": len(items), "items": items})

@app.route("/log")
def download_log():
    """
    Stream the full log as CSV (ordered newest first).
    """
    cols = ["ts","id","task","complexity","decision","client_ip","user_agent","path"]

    def esc(v):  # basic CSV escaping
        s = str(v).replace('"', '""')
        return f'"{s}"'

    def gen():
        yield ",".join(cols) + "\n"
        with SessionLocal() as s:
            for r in s.query(Decision).order_by(Decision.ts.desc()):
                row = [r.ts.isoformat(), r.id, r.task, r.complexity, r.decision, r.client_ip, r.user_agent, r.path]
                yield ",".join(esc(x) for x in row) + "\n"

    return Response(gen(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=quantumpod_decisions.csv"})

# ---------- Pretty /test page (unchanged from your last version) --------------
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
function payload(){ return { task: document.getElementById('task').value,
                             complexity: parseFloat(document.getElementById('complexity').value) }; }
function curlFor(p){ return `curl -X POST ${base}/route -H "Content-Type: application/json" -d "{\\"task\\":\\"${p.task}\\",\\"complexity\\":${p.complexity}}"`; }
async function call(){
  const btn=document.getElementById('send'), out=document.getElementById('out');
  btn.disabled=true; out.textContent="Calling /route …";
  try{
    const res=await fetch(base+"/route",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload())});
    out.textContent=await res.text();
  }catch(e){ out.textContent="Error: "+e; } finally { btn.disabled=false; }
}
document.getElementById('send').onclick=call;
document.getElementById('copycurl').onclick=async()=>{ await navigator.clipboard.writeText(curlFor(payload())); const b=document.getElementById('copycurl'); const t=b.textContent; b.textContent="Copied"; setTimeout(()=>b.textContent=t,900); };
</script>
</body>
</html>
"""

# ------------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
