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
