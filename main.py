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
<html>
<head><meta charset="utf-8"><title>QuantumPod Router Test</title></head>
<body>
  <h3>QuantumPod /route tester</h3>
  <label>Task: <input id="task" value="portfolio_optimisation"></label>
  <label>Complexity (0–1): <input id="complexity" type="number" step="0.01" value="0.75"></label>
  <button id="go">Send</button>
  <pre id="out"></pre>
  <script>
    document.getElementById('go').onclick = async () => {
      const body = {
        task: document.getElementById('task').value,
        complexity: parseFloat(document.getElementById('complexity').value)
      };
      const res = await fetch('/route', {
        method: 'POST',
        headers: {'Content-Type':'application/json'},
        body: JSON.stringify(body)
      });
      document.getElementById('out').textContent = await res.text();
    };
  </script>
</body>
</html>
"""
