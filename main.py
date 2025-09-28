from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route("/")
def home():
    return "🚀 QuantumPod Alpha is online!"

@app.route("/route", methods=["POST"])
def route_task():
    """
    Example:
    Input: {"task": "portfolio_optimisation", "complexity": 0.7}
    Output: {"decision": "Quantum"}
    """
    data = request.get_json(force=True)
    task = data.get("task", "unspecified")
    complexity = float(data.get("complexity", 0.5))

    if complexity > 0.8:
        decision = "Quantum"
    elif 0.4 < complexity <= 0.8:
        decision = "Hybrid"
    else:
        decision = "Classical"

    return jsonify({
        "task": task,
        "complexity": complexity,
        "decision": decision
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
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
        </div>
      </div>

      <div class="out" id="out">{ "status": "ready" }</div>
      <div class="muted" style="margin-top:8px">Tip: use the slider to nudge complexity across the 0.4 and 0.8 thresholds to see decisions flip between <b>Classical</b>, <b>Hybrid</b>, and <b>Quantum</b>.</div>
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
  const body = JSON.stringify(p).replaceAll('"','\\"');
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

