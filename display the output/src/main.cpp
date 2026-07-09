#include <Arduino.h>
#include <Wire.h>
#include <LiquidCrystal_I2C.h>
#include <DHT.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <ArduinoJson.h>

//LCD Configuration 
#define LCD_ADDR 0x27
#define LCD_COLS 16
#define LCD_ROWS 2

// DHT22 Configuration 
#define DHTPIN   4
#define DHTTYPE  DHT22

// Soil Moisture Sensor Configuration
#define MOISTURE_PIN 32
const int DRY_VALUE = 4095;  // Calibrated: sensor in open air
const int WET_VALUE = 2050;  // Calibrated: sensor fully submerged in water

// WiFi Settings (Update these to your Mobile Hotspot credentials!)
#define WIFI_SSID     "Your_Hotspot_SSID"
#define WIFI_PASSWORD "Your_Hotspot_Password"
// Flask Server Network Route - UPDATED TO NEW HOTSPOT IP
#define FLASK_URL "http://10.96.220.61:5000"

//Execution Interval 
#define PUSH_INTERVAL_MS 30000  // Push sensor data every 30 seconds

LiquidCrystal_I2C lcd(LCD_ADDR, LCD_COLS, LCD_ROWS);
DHT               dht(DHTPIN, DHTTYPE);
WebServer         server(80);

unsigned long lastPush = 0;

//LCD Helper 
void showLine(String l1, String l2) {
  lcd.clear();
  lcd.setCursor(0, 0); lcd.print(l1.substring(0, LCD_COLS));
  lcd.setCursor(0, 1); lcd.print(l2.substring(0, LCD_COLS));
}

//Push Data to Flask API 
void pushSensorData() {
  float temp = NAN, hum = NAN;

  for (int i = 0; i < 3 && (isnan(temp) || isnan(hum)); i++) {
    temp = dht.readTemperature();
    hum  = dht.readHumidity();
    if (isnan(temp) || isnan(hum)) delay(500);
  }

  if (isnan(temp) || isnan(hum)) {
    Serial.println("[DHT Error] Pin 4 read failed. Check your data wire!");
    showLine("Sensor Error", "Check DHT22 Wire");
    return;
  }

  // Read raw ADC and map to 0–100%
  // High ADC = dry (air), Low ADC = wet (water) — map inverts this correctly
  int rawMoisture = analogRead(MOISTURE_PIN);
  float moisturePercent = map(rawMoisture, DRY_VALUE, WET_VALUE, 0, 100);
  moisturePercent = constrain(moisturePercent, 0.0, 100.0);

  Serial.printf("[Moisture] Raw=%d  Mapped=%.1f%%\n", rawMoisture, moisturePercent);

  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[WiFi Error] Disconnected. Skipping push.");
    return;
  }

  WiFiClient client;
  HTTPClient http;
  http.begin(client, String(FLASK_URL) + "/sensor_data");
  http.addHeader("Content-Type", "application/json");

  JsonDocument doc;
  doc["temperature"]   = temp;
  doc["humidity"]      = hum;
  doc["soil_moisture"] = moisturePercent;

  String body;
  serializeJson(doc, body);

  int code = http.POST(body);
  Serial.printf("[Flask Sync] Temp=%.2fC  Hum=%.2f%%  Moist=%.1f%%  HTTP=%d\n",
                temp, hum, moisturePercent, code);

  // LCD intentionally not updated here — reserved for crop/fertilizer
  // results pushed from Streamlit via the /display endpoint
  if (code != 200) {
    Serial.printf("[Flask Error] HTTP %d — check FLASK_URL in code\n", code);
  }

  http.end();
}

//Streamlit Display Endpoint 
void handleDisplay() {
  if (!server.hasArg("plain")) {
    server.send(400, "application/json", "{\"error\":\"Missing payload\"}");
    return;
  }

  JsonDocument doc;
  DeserializationError err = deserializeJson(doc, server.arg("plain"));
  if (err) {
    server.send(400, "application/json", "{\"error\":\"Invalid JSON\"}");
    return;
  }

  String line1 = doc["line1"] | "---";
  String line2 = doc["line2"] | "---";

  showLine(line1, line2);
  server.send(200, "application/json", "{\"status\":\"ok\"}");
  Serial.printf("[LCD] '%s' / '%s'\n", line1.c_str(), line2.c_str());
}

// Health Check Endpoint
void handleHealth() {
  server.send(200, "application/json", "{\"status\":\"ok\",\"device\":\"AgroSense-ESP32\"}");
}

//Setup 
void setup() {
  Serial.begin(115200);
  delay(500);

  Wire.begin(21, 22);
  dht.begin();
  pinMode(MOISTURE_PIN, INPUT);

  lcd.init();
  lcd.backlight();
  showLine("AgroSense", "Booting...");
  delay(500);

  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print("[WiFi] Connecting");

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    Serial.print(".");
    attempts++;
    if (attempts % 2 == 0) showLine("Connecting WiFi", "Searching...");
  }

  delay(200);
  lcd.init();
  lcd.backlight();

  if (WiFi.status() == WL_CONNECTED) {
    String ip = WiFi.localIP().toString();
    Serial.println("\n[WiFi] Connected. IP: " + ip);
    showLine("WiFi Connected!", ip);
  } else {
    Serial.println("\n[WiFi] Timeout. Check credentials.");
    showLine("WiFi Failed", "Check Credentials");
  }

  server.on("/display", HTTP_POST, handleDisplay);
  server.on("/health",  HTTP_GET,  handleHealth);
  server.begin();
  Serial.println("[System HTTP] Core pipeline active on Port 80");

  if (WiFi.status() == WL_CONNECTED) {
    pushSensorData();
    showLine("AgroSense Ready", "Run from UI");
  }
  lastPush = millis();
}

//Loop 
void loop() {
  server.handleClient();

  if (millis() - lastPush >= PUSH_INTERVAL_MS) {
    lastPush = millis();
    pushSensorData();
  }
}