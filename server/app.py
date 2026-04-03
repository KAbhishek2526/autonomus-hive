"""
Autonomous Hive — Flask Backend
Sense → Think → Act

Receives sensor data from ESP32, applies rule-based logic,
returns relay control commands.
"""

from flask import Flask, request, jsonify, render_template
from datetime import datetime
import csv
import os
import numpy as np
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib

app = Flask(__name__)

# ── Global Control State ─────────────────────────────────────────────────────
CONTROL = {
    "mode": "AUTO",   # AUTO or MANUAL
    "pump": 0,
    "light": 0,
    "fan": 0
}

# ── In-memory store for the latest sensor snapshot ──────────────────────────
latest_data = {
    "temp": 0.0,
    "hum": 0.0,
    "moist": 0,
    "lux": 0,
    "pump": 0,
    "light": 0,
    "fan": 0,
    "mode": "RULE",
    "timestamp": None,
}

# ── ML Model Initialization ──────────────────────────────────────────────────
pump_model = None
light_model = None
fan_model = None

def init_ml_models():
    global pump_model, light_model, fan_model
    
    if os.path.exists("pump_model.pkl") and os.path.exists("light_model.pkl") and os.path.exists("fan_model.pkl"):
        pump_model = joblib.load("pump_model.pkl")
        light_model = joblib.load("light_model.pkl")
        fan_model = joblib.load("fan_model.pkl")
        print("Models loaded successfully")
        return
    
    # Generate synthetic dataset (2500 samples) with added noise
    np.random.seed(42)
    N = 2500
    temp = np.random.uniform(10, 45, N) + np.random.normal(0, 2, N)
    hum = np.random.uniform(20, 90, N) + np.random.normal(0, 5, N)
    moist = np.random.uniform(100, 800, N) + np.random.normal(0, 30, N)
    lux = np.random.uniform(0, 1000, N) + np.random.normal(0, 20, N)

    X = np.column_stack((temp, hum, moist, lux))

    # Soften label boundaries (probabilistic near threshold)
    y_pump = np.zeros(N, dtype=int)
    y_pump[moist < 380] = 1
    mask_pump = (moist >= 380) & (moist <= 420)
    y_pump[mask_pump] = np.random.choice([0, 1], size=np.sum(mask_pump), p=[0.3, 0.7])

    y_light = np.zeros(N, dtype=int)
    y_light[lux < 180] = 1
    mask_light = (lux >= 180) & (lux <= 220)
    y_light[mask_light] = np.random.choice([0, 1], size=np.sum(mask_light), p=[0.3, 0.7])

    y_fan = np.zeros(N, dtype=int)
    y_fan[temp > 34] = 1
    mask_fan = (temp >= 30) & (temp <= 34)
    y_fan[mask_fan] = np.random.choice([0, 1], size=np.sum(mask_fan), p=[0.3, 0.7])

    # Split for accuracy comparison
    X_train, X_test, yp_train, yp_test = train_test_split(X, y_pump, test_size=0.2, random_state=42)
    _, _, yl_train, yl_test = train_test_split(X, y_light, test_size=0.2, random_state=42)
    _, _, yf_train, yf_test = train_test_split(X, y_fan, test_size=0.2, random_state=42)

    # Train Decision Tree (for comparison)
    dt_pump = DecisionTreeClassifier().fit(X_train, yp_train)
    dt_light = DecisionTreeClassifier().fit(X_train, yl_train)
    dt_fan = DecisionTreeClassifier().fit(X_train, yf_train)

    # Train Random Forest (Actual models)
    rf_pump = RandomForestClassifier(n_estimators=50, random_state=42).fit(X_train, yp_train)
    rf_light = RandomForestClassifier(n_estimators=50, random_state=42).fit(X_train, yl_train)
    rf_fan = RandomForestClassifier(n_estimators=50, random_state=42).fit(X_train, yf_train)

    # Compute Accuracies and Print Metrics
    print("\n" + "="*60)
    print("📊 --- ML MODEL EVALUATION METRICS ---")
    print("="*60)

    for name, yt, ml_dt, ml_rf, xt in [
        ("Pump", yp_test, dt_pump, rf_pump, X_test),
        ("Light", yl_test, dt_light, rf_light, X_test),
        ("Fan", yf_test, dt_fan, rf_fan, X_test)
    ]:
        print(f"\n[{name.upper()} MODEL]")
        for model_name, model in [("Decision Tree", ml_dt), ("Random Forest", ml_rf)]:
            preds = model.predict(xt)
            print(f"  --> {model_name} Accuracy: {accuracy_score(yt, preds):.4f}")
            print("  Confusion Matrix:")
            print(confusion_matrix(yt, preds))
            print("  Classification Report:")
            print(classification_report(yt, preds))
        print("-" * 60)
        
    print("\n" + "="*60)
    print("🔄 --- 5-FOLD CROSS-VALIDATION (RANDOM FOREST) ---")
    for name, yt_full, rf_blueprint in [
        ("Pump", y_pump, RandomForestClassifier(n_estimators=50, random_state=42)),
        ("Light", y_light, RandomForestClassifier(n_estimators=50, random_state=42)),
        ("Fan", y_fan, RandomForestClassifier(n_estimators=50, random_state=42))
    ]:
        cv_scores = cross_val_score(rf_blueprint, X, yt_full, cv=5)
        print(f"[{name.upper()} MODEL] CV Accuracies: {cv_scores}")
        print(f"[{name.upper()} MODEL] Mean CV Accuracy: {cv_scores.mean():.4f}")
    
    print("\n" + "="*60)
    print("🌟 --- FEATURE IMPORTANCE (RANDOM FOREST) ---")
    features = ["Temperature", "Humidity", "Moisture", "Lux"]
    for name, model_instance in [("Pump", rf_pump), ("Light", rf_light), ("Fan", rf_fan)]:
        print(f"[{name.upper()} MODEL] Feature Breakdown:")
        importances = model_instance.feature_importances_
        for f_name, imp in zip(features, importances):
            print(f"  --> {f_name:<12}: {imp:.4f} ({imp*100:4.1f}%)")
    print("="*60 + "\n")

    # Set globals to RandomForest
    pump_model = rf_pump
    light_model = rf_light
    fan_model = rf_fan

    # Save RandomForest models
    joblib.dump(pump_model, "pump_model.pkl")
    joblib.dump(light_model, "light_model.pkl")
    joblib.dump(fan_model, "fan_model.pkl")
    print("RandomForest Models trained and saved")

init_ml_models()


# ── Root: serve the live dashboard ──────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


# ── DEMO MODE FLAG ───────────────────────────────────────────────────────────
DEMO_MODE = True

@app.route("/process", methods=["POST"])
def process():
    try:
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

        # ── Data Sanity Check ────────────────────────────────────────────────
        if temp < -50 or temp > 150 or hum < 0 or hum > 100 or moist < 0 or lux < 0:
            print(f"⚠️ Rejecting impossible values: temp={temp}, hum={hum}, moist={moist}, lux={lux}")
            return jsonify({"error": "Data sanity check failed: impossible values"}), 400

        print(f"\n📡 Incoming Data: {data}")

        # ── DEMO MODE Override ───────────────────────────────────────────────
        if DEMO_MODE:
            temp = 35.0
            moist = 300
            lux = 100
            print("🧪 DEMO_MODE active: Overriding inputs -> temp=35.0, moist=300, lux=100")

        # ── Decision Logic (ML with Rule Fallback) ───────────────────────────
        if CONTROL["mode"] == "MANUAL":
            pump  = CONTROL["pump"]
            light = CONTROL["light"]
            fan   = CONTROL["fan"]
            mode  = "MANUAL"
            print(f"🕹️ Mode Used: MANUAL -> pump={pump}, light={light}, fan={fan}")
        else:
            try:
                pump  = int(pump_model.predict([[temp, hum, moist, lux]])[0])
                light = int(light_model.predict([[temp, hum, moist, lux]])[0])
                fan   = int(fan_model.predict([[temp, hum, moist, lux]])[0])
                mode  = "ML"
                print("🧠 Mode Used: ML (AUTO)")
            except Exception as e:
                pump  = 1 if moist < 400 else 0   # Dry soil  → irrigate
                light = 1 if lux < 200  else 0    # Low light → supplemental lighting
                fan   = 1 if temp > 32  else 0    # Hot       → cooling fan
                mode  = "RULE"
                print(f"⚠️ ML Prediction failed: {e}. Mode Used: RULE (AUTO)")

        # Update shared state for the dashboard
        latest_data.update({
            "temp": temp,
            "hum": hum,
            "moist": moist,
            "lux": lux,
            "pump": pump,
            "light": light,
            "fan": fan,
            "mode": mode,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        })

        print("="*50)
        print(f"✅ Final Decision: pump={pump}, light={light}, fan={fan}")
        print("="*50 + "\n")

        # ── Log data to CSV ──────────────────────────────────────────────────
        try:
            csv_file = "data_log.csv"
            file_exists = os.path.isfile(csv_file)
            with open(csv_file, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                if not file_exists:
                    writer.writerow(["timestamp", "temp", "hum", "moist", "lux"])
                writer.writerow([latest_data["timestamp"], temp, hum, moist, lux])
        except Exception as csv_err:
            print(f"Failed to write to CSV logs: {csv_err}")

        return jsonify({"pump": pump, "light": light, "fan": fan, "mode": mode})

    except Exception as general_error:
        print(f"🚨 CRITICAL ERROR in /process: {general_error}")
        print("🛡️ Returning SAFE DEFAULT fallback (all OFF).")
        return jsonify({"pump": 0, "light": 0, "fan": 0, "mode": "FAILSAFE"})


# ── /status: JSON snapshot for the dashboard AJAX poll ──────────────────────
@app.route("/status")
def status():
    try:
        with open("data_log.csv", "r") as f:
            data_count = max(0, len(f.readlines()) - 1)
    except FileNotFoundError:
        data_count = 0
    
    response_data = latest_data.copy()
    response_data["data_count"] = data_count
    # Also pass the latest CONTROL state
    response_data["control"] = CONTROL
    return jsonify(response_data)


# ── /set_control: Endpoint for Dashboard UI to trigger Manual overrides ──────
@app.route("/set_control", methods=["POST"])
def set_control():
    data = request.json
    if not data:
        return jsonify({"error": "No JSON payload received"}), 400
        
    if "mode" in data:
        CONTROL["mode"] = data["mode"]
    if "pump" in data:
        CONTROL["pump"] = int(data["pump"])
    if "light" in data:
        CONTROL["light"] = int(data["light"])
    if "fan" in data:
        CONTROL["fan"] = int(data["fan"])
        
    print(f"🎛️ Dashboard override synced: {CONTROL}")
    return jsonify({"status": "success", "control": CONTROL})


# ── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🌱 Autonomous Hive server starting on http://0.0.0.0:5001")
    app.run(host="0.0.0.0", port=5001, debug=True)
