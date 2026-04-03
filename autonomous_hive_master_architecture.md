---
title: Autonomous Hive — System Architecture & Technical Master Document
description: Complete specification of the Autonomous Hive IoT/ML platform, perfectly formatted to be ingestible by Antigravity instances on new devices.
version: 1.0.0
---

# 🐝 Autonomous Hive - Master Reference

This document serves as the absolute "Ground Truth" for the Autonomous Hive codebase. It contains the exact logic flow, routing topology, and architecture design so that any Antigravity AI instance can seamlessly pick up development on a new context/device.

## 1. System Topology (Polling Architecture)

The system is decoupled using a strict polling architecture. There are **no active push mechanisms** initiated by the Flask server. All interactions are driven by client polls.

### The Network Flow
```mermaid
graph LR
    UI[Dashboard UI] -- "GET /status (Every 5s)" --> FS[Flask Backend]
    UI -- "POST /set_control" --> FS
    ESP[ESP32 IoT] -- "POST /process (Every 5s)" --> FS
    FS -- "Returns: {pump, light, fan}" --> ESP
    ESP -- "GPIO Out" --> Relays[4-Channel Relay]
```

## 2. Server Backend (`server/app.py`)

The Flask backend is the central source of truth. It manages two main states in memory:
1. `latest_data`: A snapshot of the last known sensor telemetry and the ML prediction.
2. `CONTROL`: A global dictionary tracking user override limits.

### Global State Control Dictionary
```python
CONTROL = {
    "mode": "AUTO",   # Toggles between AUTO (AI inference) and MANUAL (User inputs)
    "pump": 0,
    "light": 0,
    "fan": 0
}
```

### Core API Endpoints

| Route | Method | Purpose |
|-----------------|----------|---------------------------------------------------------|
| `/` | `GET` | Serves the `index.html` SaaS Dashboard UI. |
| `/status` | `GET` | Returns `latest_data` and the current `CONTROL` state to the UI loop. |
| `/set_control` | `POST` | Called by the UI when the user clicks 'MANUAL' or toggles a relay switch. Overwrites the `CONTROL` dictionary in memory. |
| `/process` | `POST` | The heart of the IoT link. ESP32 sends telemetry `{temp, hum, moist, lux}` here. Flask evaluates the numbers and returns `{pump, light, fan, mode}` to the ESP32. |

### Decision Logic (`POST /process`)
When the ESP32 hits `/process`, the Flask Server executes an ordered logical tree:
1. **Manual Override Bypass**: `if CONTROL["mode"] == "MANUAL"` -> Bypass all AI, just return `CONTROL` variables.
2. **Machine Learning Pipeline (`rf_model.predict`)**: If `AUTO`, the pre-trained `RandomForestClassifier` dynamically evaluates the payload.
3. **Safety Fallback (`try/except`)**: If the ML pipeline crashes, hardcoded rule thresholds instantly execute so the plants don't die.

## 3. Machine Learning Core

The system uses `scikit-learn` to run 3 independent `RandomForestClassifier` (n_estimators=50) models, one for each actuator.

*   **Initialization**: When `app.py` boots, it checks for `pump_model.pkl`, `light_model.pkl`, `fan_model.pkl`.
*   **Synthetic Engine (Training)**: If `.pkl` files are missing, it dynamically generates 2,500 samples of synthetic agricultural data with simulated sensor noise (`np.random.normal`) and probabilistic boundaries (e.g. moisture sitting exactly at threshold has a 70% chance of irrigating).
*   **Accuracy Check**: The engine inherently runs a 5-fold cross-validation during training and prints the Confusion Matrices directly to the terminal stdout.

## 4. Dashboard UI (`index.html`)

The UI is built with vanilla HTML, **Tailwind CSS**, and Google Material Icons. It requires no build step (`npm`/`vite`). It uses a premium "SaaS-Dashboard" visual aesthetic.

### Two-Way Asynchronous Polling
The UI runs a highly robust JavaScript `setInterval(poll, 5000)` loop.

*   **UI Conflict Resolution**: 
    When the system is in `MANUAL` mode, the asynchronous Javascript ignores incoming relay states from `GET /status`. It prevents the physical toggle handles on the screen from bouncing/glitching if the polling packet misaligns with the user's immediate click.
*   **Mode Swapping**: 
    When `AUTO` is selected, the UI actively sends this exact payload to Flask:
    ```javascript
    {
      "mode": "AUTO"
    }
    ```
    When `MANUAL` is toggled, it sends explicit configurations:
    ```javascript
    {
      "mode": "MANUAL",
      "pump": 1,
      "light": 0,
      "fan": 1
    }
    ```

## 5. IoT ESP32 Firmware Expectation

Since the system handles all logic in Flask, the ESP32 Firmware (`main.ino`) must be completely "dumb".
It should only:
1. `analogRead()` and `pulseIn()` its connected sensors.
2. Format a flat JSON: `{"temp": 28.5, "hum": 65.0, "moist": 320, "lux": 850}`.
3. `POST` it to `http://<FLASK_IP>:5001/process`.
4. Parse the returned JSON response and securely `digitalWrite()` the GPIO pins assigned to the relay board based on that response.

## Notes for AI Context Restoration
1. **Start Here**: If you are loaded into a new session, verify `app.py` has no missing `sklearn` dependencies and that Tailwind is successfully loading in `index.html`. 
2. **Current Port**: The server runs exclusively on Port `5001` to avoid arbitrary macOS port-5000 conflicts.
3. **Styling**: Do not modify overarching Tailwind styles unless specifically requested. The color palette follows strict brand guidelines: Success/Green (`#22C55E`), Accent Soft (`#DCFCE7`), Warning/Manual (`#f97316`).
