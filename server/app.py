"""
Autonomous Hive — Flask Backend
Sense → Think → Act

Receives sensor data from ESP32, applies rule-based logic,
returns relay control commands.
"""

from flask import Flask, request, jsonify, render_template
from datetime import datetime

app = Flask(__name__)

# ── In-memory store for the latest sensor snapshot ──────────────────────────
latest_data = {
    "temp": 0.0,
    "hum": 0.0,
    "moist": 0,
    "lux": 0,
    "pump": 0,
    "light": 0,
    "fan": 0,
    "timestamp": None,
}


# ── Root: serve the live dashboard ──────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── /process: core rule engine endpoint ─────────────────────────────────────
@app.route("/process", methods=["POST"])
def process():
    data = request.get_json(force=True)

    if not data:
        return jsonify({"error": "No JSON payload received"}), 400

    # Validate required fields
    required = ["temp", "hum", "moist", "lux"]
    for field in required:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    temp  = float(data["temp"])
    hum   = float(data["hum"])
    moist = int(data["moist"])
    lux   = int(data["lux"])

    # ── Rule-based decision logic ────────────────────────────────────────────
    pump  = 1 if moist < 400 else 0   # Dry soil  → irrigate
    light = 1 if lux < 200  else 0    # Low light → supplemental lighting
    fan   = 1 if temp > 32  else 0    # Hot       → cooling fan

    # Update shared state for the dashboard
    latest_data.update({
        "temp": temp,
        "hum": hum,
        "moist": moist,
        "lux": lux,
        "pump": pump,
        "light": light,
        "fan": fan,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    print("\n" + "="*50)
    print(f"📡 [{latest_data['timestamp']}] Incoming Data: {data}")
    print(f"🧠 Rule Engine Decision: pump={pump}, light={light}, fan={fan}")
    print("="*50 + "\n")

    return jsonify({"pump": pump, "light": light, "fan": fan})


# ── /status: JSON snapshot for the dashboard AJAX poll ──────────────────────
@app.route("/status")
def status():
    return jsonify(latest_data)


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌱 Autonomous Hive server starting on http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
