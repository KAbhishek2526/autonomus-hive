/*
 * ┌─────────────────────────────────────────────────────────────┐
 * │  Autonomous Hive — ESP32 Firmware                           │
 * │  Sense → Think → Act                                        │
 * │                                                             │
 * │  Libraries required (install via Arduino Library Manager):  │
 * │    DHT sensor library  (Adafruit)                           │
 * │    ArduinoJson          (bblanchon)                         │
 * │    BH1750               (claws)                             │
 * └─────────────────────────────────────────────────────────────┘
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Wire.h>
#include <BH1750.h>

// ── WiFi credentials ────────────────────────────────────────────────────────
const char* SSID      = "TP-Link_251C_5G";
const char* PASSWORD  = "84674012";

// ── Server endpoint ─────────────────────────────────────────────────────────
const char* SERVER_URL = "http://192.168.0.103:5001/process";

// ── Test Mode ───────────────────────────────────────────────────────────────
// Set to true to mock sensor values for guaranteed relay activation
#define TEST_MODE true

// ── Pin definitions ─────────────────────────────────────────────────────────
#define DHT_PIN        13       // DHT22 data
#define DHT_TYPE       DHT22
#define SOIL_PIN       33       // Capacitive soil moisture (analog)
#define SDA_PIN        14       // BH1750 I2C SDA
#define SCL_PIN        15       // BH1750 I2C SCL

#define RELAY_PUMP     2        // IN1
#define RELAY_LIGHT    4        // IN2  (changed from GPIO14 to avoid I2C conflict)
#define RELAY_FAN      12       // IN3  (changed from GPIO15 to avoid I2C conflict)

// Relay module: LOW = ON, HIGH = OFF
#define RELAY_ON   LOW
#define RELAY_OFF  HIGH

// ── Loop interval ────────────────────────────────────────────────────────────
const unsigned long INTERVAL_MS = 8000;   // 8 seconds

// ── Global sensor objects ────────────────────────────────────────────────────
DHT    dht(DHT_PIN, DHT_TYPE);
BH1750 lightMeter;

// ── Forward declarations ─────────────────────────────────────────────────────
void connectWiFi();
void setRelays(int pump, int light, int fan);
void sendSensorData();

// ─────────────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println("\n🌱 Autonomous Hive — Booting...");

  // Relay pins
  pinMode(RELAY_PUMP,  OUTPUT);
  pinMode(RELAY_LIGHT, OUTPUT);
  pinMode(RELAY_FAN,   OUTPUT);
  // Default: all relays OFF
  setRelays(0, 0, 0);

  // DHT22
  dht.begin();

  // BH1750 via I2C
  Wire.begin(SDA_PIN, SCL_PIN);
  if (!lightMeter.begin(BH1750::CONTINUOUS_HIGH_RES_MODE)) {
    Serial.println("⚠️  BH1750 init failed — check wiring!");
  }

  // WiFi
  connectWiFi();
}

// ─────────────────────────────────────────────────────────────────────────────
void loop() {
  // Reconnect if WiFi dropped
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("⚠️  WiFi lost — reconnecting...");
    connectWiFi();
  }

  sendSensorData();
  delay(INTERVAL_MS);
}

// ─────────────────────────────────────────────────────────────────────────────
// Connect to WiFi with retry
// ─────────────────────────────────────────────────────────────────────────────
void connectWiFi() {
  Serial.printf("📡 Connecting to WiFi: %s\n", SSID);
  WiFi.begin(SSID, PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if (++attempts >= 40) {
      Serial.println("\n❌ WiFi connection failed — retrying in 5s");
      delay(5000);
      attempts = 0;
      WiFi.begin(SSID, PASSWORD);
    }
  }

  Serial.printf("\n✅ WiFi connected! IP: %s\n", WiFi.localIP().toString().c_str());
}

// ─────────────────────────────────────────────────────────────────────────────
// Read sensors, build JSON, POST to server, parse response, control relays
// ─────────────────────────────────────────────────────────────────────────────
void sendSensorData() {
  // 1. Read DHT22
  float temp = dht.readTemperature();
  float hum  = dht.readHumidity();
  if (isnan(temp) || isnan(hum)) {
    Serial.println("⚠️  DHT22 read failed — skipping cycle");
    return;
  }

  // 2. Read soil moisture (analog 0–4095)
  int moist = analogRead(SOIL_PIN);

  // 3. Read light intensity
  float lux = lightMeter.readLightLevel();
  if (lux < 0) lux = 0;   // sensor error guard

  // ── TEST MODE OVERRIDE ───────────────────────────────────────────────────
  if (TEST_MODE) {
    temp = 35.0;   // Trigger Fan   (> 32)
    moist = 300;   // Trigger Pump  (< 400)
    lux = 100.0;     // Trigger Light (< 200)
    Serial.println("🧪 TEST MODE ACTIVE: Overriding sensor values -> [Temp:35°C, Moist:300ADC, Lux:100]");
  }

  // 4. Debug output
  Serial.printf("\n📊 Temp=%.1f°C  Hum=%.1f%%  Moist=%d  Lux=%.0f\n",
                temp, hum, moist, lux);

  // 5. Build JSON payload
  StaticJsonDocument<128> doc;
  doc["temp"]  = temp;
  doc["hum"]   = hum;
  doc["moist"] = moist;
  doc["lux"]   = (int)lux;

  String payload;
  serializeJson(doc, payload);

  Serial.println("\n🌐 OUTGOING PAYLOAD:");
  Serial.println(payload);

  // 6. HTTP POST
  HTTPClient http;
  http.begin(SERVER_URL);
  http.addHeader("Content-Type", "application/json");

  int httpCode = http.POST(payload);

  if (httpCode == HTTP_CODE_OK) {
    String response = http.getString();
    Serial.println("✅ SERVER RESPONSE BODY:");
    Serial.println(response);

    // 7. Parse relay commands
    StaticJsonDocument<64> resp;
    DeserializationError err = deserializeJson(resp, response);
    if (!err) {
      int pump  = resp["pump"]  | 0;
      int light = resp["light"] | 0;
      int fan   = resp["fan"]   | 0;

      setRelays(pump, light, fan);
    } else {
      Serial.printf("⚠️  JSON parse error: %s\n", err.c_str());
    }
  } else {
    Serial.printf("❌ HTTP error: %d  — %s (Retrying next loop)\n", httpCode, http.errorToString(httpCode).c_str());
  }

  http.end();
}

// ─────────────────────────────────────────────────────────────────────────────
// Control relay channels  (1 = ON, 0 = OFF)
// ─────────────────────────────────────────────────────────────────────────────
void setRelays(int pump, int light, int fan) {
  digitalWrite(RELAY_PUMP,  pump  ? RELAY_ON : RELAY_OFF);
  digitalWrite(RELAY_LIGHT, light ? RELAY_ON : RELAY_OFF);
  digitalWrite(RELAY_FAN,   fan   ? RELAY_ON : RELAY_OFF);

  Serial.printf("🔌 Relays → Pump:%s  Light:%s  Fan:%s\n",
                pump  ? "ON" : "OFF",
                light ? "ON" : "OFF",
                fan   ? "ON" : "OFF");
}
