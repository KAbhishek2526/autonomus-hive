# 🌱 Autonomous Hive
### Edge-AI Precision Farming System — ESP32 + Flask

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.9%2B-blue.svg)](https://www.python.org/)
[![Arduino](https://img.shields.io/badge/Arduino-ESP32-teal.svg)](https://www.arduino.cc/)

---

## 📡 Architecture: Sense → Think → Act

```
┌──────────────┐     WiFi/HTTP     ┌────────────────┐     GPIO      ┌──────────────┐
│  SENSE       │ ──────────────▶  │  THINK         │ ──────────▶  │  ACT         │
│  ESP32-CAM   │                  │  Flask Server  │              │  Relay Board │
│              │ ◀──────────────  │  Rule Engine   │              │              │
│ • DHT22      │   JSON Response  │  Python 3      │              │ • Pump (IN1) │
│ • BH1750     │                  │  Port 5000     │              │ • Light(IN2) │
│ • Soil ADC   │                  │  Dashboard     │              │ • Fan  (IN3) │
└──────────────┘                  └────────────────┘              └──────────────┘
```

---

## 🔧 Components

| Component | Role | Pin |
|---|---|---|
| ESP32-CAM (AI-Thinker) | Edge node, WiFi, relay control | — |
| DHT22 | Temperature & Humidity | GPIO13 |
| Capacitive Soil Sensor | Soil moisture (ADC) | GPIO33 |
| BH1750 | Light intensity (I2C) | SDA=GPIO14, SCL=GPIO15 |
| 4-Channel Relay Module | Actuator control (LOW=ON) | GPIO2, 4, 12 |
| Peristaltic Pump | Irrigation | IN1 |
| LED Grow Light | Supplemental lighting | IN2 |
| Cooling Fan | Temperature control | IN3 |

---

## 🧠 Rule Engine Logic (Flask `/process`)

```python
pump  = 1 if moist < 400 else 0   # Dry soil → irrigate
light = 1 if lux   < 200 else 0   # Low light → grow lamp ON
fan   = 1 if temp  > 32  else 0   # Hot → cooling fan
```

---

## 🚀 Setup & Run

### 1. Clone the repo
```bash
git clone https://github.com/KAbhishek2526/autonomus-hive.git
cd autonomus-hive
```

### 2. Start the Flask server (on your PC)
```bash
cd server
pip install -r requirements.txt
python app.py
```
Server runs at `http://0.0.0.0:5000`.  
Dashboard: open `http://localhost:5000` in your browser.

### 3. Flash ESP32 firmware
1. Open `firmware/main.ino` in **Arduino IDE**.
2. Install required libraries via Library Manager:
   - `DHT sensor library` (Adafruit)
   - `ArduinoJson` (bblanchon)
   - `BH1750` (claws)
3. Set your PC's local IP in `main.ino`:
   ```cpp
   const char* SERVER_URL = "http://<YOUR_PC_IP>:5000/process";
   ```
4. Select **ESP32-CAM** board, flash.

### 4. Watch the magic 🎉
- Open the dashboard at `http://localhost:5000`
- Sensor readings update every **5 seconds**
- Relays fire automatically based on the rule engine

---

## 📊 API Reference

### `POST /process`
**Request Body:**
```json
{ "temp": 28.5, "hum": 65.2, "moist": 312, "lux": 185 }
```
**Response:**
```json
{ "pump": 1, "light": 1, "fan": 0 }
```

### `GET /status`
Returns the latest sensor snapshot (used by the dashboard AJAX poll).

---

## 📁 Project Structure

```
autonomus-hive/
├── firmware/
│   └── main.ino          # ESP32 Arduino firmware
├── server/
│   ├── app.py            # Flask backend + rule engine
│   ├── requirements.txt  # Python dependencies
│   └── templates/
│       └── index.html    # Live dashboard UI
├── arcitecture.svg        # System architecture diagram
├── .gitignore
└── README.md
```

---

## 🏆 Hackathon Demo Script

1. Power on ESP32 → it connects to WiFi and starts sending data
2. Open browser → `http://localhost:5000`
3. Cover soil sensor → watch pump relay trigger (moist < 400)
4. Block BH1750 → grow light activates (lux < 200)
5. Warm DHT22 with hand → fan relay activates (temp > 32°C)
6. All relay states reflect live on the dashboard

---

## 👤 Author

**Abhishek K** — Computer Science  
[GitHub: @KAbhishek2526](https://github.com/KAbhishek2526)

---

*Built with ❤️ for precision farming — Autonomous Hive*
