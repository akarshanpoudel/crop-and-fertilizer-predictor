
# AgroSense – Intelligent Crop & Fertilizer Recommendation System

AgroSense is an end-to-end IoT and Machine Learning ecosystem designed to enhance agricultural efficiency. The platform collects real-time microclimate and soil telemetry via an ESP32 edge node, streams it persistently to a cloud-hosted MySQL database on Railway, processes the data through trained Scikit-Learn pipelines to recommend crops and fertilizer configurations, and manages local physical actuators (LCD screens) to provide instantaneous on-field feedback loops.

---

##  System Architecture & Data Flow

The project is engineered with a modular, decoupled architecture split across three distinctive layers:

1. **Hardware Ingress & Actuation (ESP32):** Runs an asynchronous, non-blocking control loop. It operates simultaneously as an outbound HTTP Client (polling sensor arrays every 30 seconds and sending data up to the Flask API) and an inbound HTTP Web Server (listening on Port 80 for rendering arrays dispatched by the user frontend).
2. **Backend API Core & ML Pipeline (Flask):** The central computational proxy. Configured with SQLAlchemy, it manages continuous connection pooling to the Railway MySQL instance. It intercept data packets, records them to database rows, and delivers microsecond-level local inferencing by keeping the `.pkl` serialization pipelines resident in memory.
3. **Frontend Analytics Panel (Streamlit):** The interactive control console. It tracks user input constraints, queries real-time regional precipitation data using external geospatial APIs (Open-Meteo), pulls the latest physical edge metrics from the MySQL server database, and routes programmatic triggers across the network layer.

---

##  Complete Tech Stack

### Edge Hardware Node
* **Microcontroller:** ESP32 (NodeMCU Development Board)
* **Microclimate Array:** DHT22 (Digital Air Temperature & Relative Humidity)
* **Soil Analysis:** Capacitive Soil Moisture Sensor v1.2 (Corrosion-resistant analog probe)
* **Visual Display Output:** 16x2 Character LCD Module equipped with an I2C Backpack interface

### Software & Cloud Infrastructure
* **Web Interfaces:** Streamlit Framework, Requests Networking Suite
* **API Service Cluster:** Python, Flask, Flask-SQLAlchemy, Joblib, NumPy, Scikit-Learn
* **Cloud Persistence Layer:** Managed MySQL Database Instance containerized on Railway
* **Firmware Runtime:** C++, Embedded Arduino Core Engine (PlatformIO / Arduino IDE compliant)

---

##  Hardware Configuration & Pin Map

Before powering on or flashing the microcontroller node, ensure your physical connections align with the defined pin structures:

| Sensor/Module | Module VCC | Module Pin | ESP32 GPIO | Communication Protocol |
| :--- | :--- | :--- | :--- | :--- |
| **DHT22 Sensor** | 3.3V / 5V | DATA | **GPIO 4** | Single-Wire Digital Bus |
| **Soil Moisture Probe** | 3.3V | AOUT (Analog) | **GPIO 32** | ADC Analog Channel 1 |
| **16x2 I2C LCD Display** | 5V | SDA | **GPIO 21** | I2C Data Line (Address `0x27`) |
| **16x2 I2C LCD Display** | 5V | SCL | **GPIO 22** | I2C Clock Line (Address `0x27`) |

### Calibration Constants
The analog soil moisture tracking algorithm operates via physical boundary mapping. Because capacitive sensors register *inversed values* (higher ADC numbers reflect dry air, lower numbers represent liquid submersion), the edge firmware enforces the following calibrated metrics to scale constraints cleanly between `0%` and `100%`:
* **`DRY_VALUE = 4095`** (Raw ADC ceiling captured in open environment air)
* **`WET_VALUE = 2050`** (Raw ADC floor captured when completely submerged in water)

---

## Repository Structural Blueprint

```text
AgroSense/
├── backend/
│   ├── app.py                      # Flask Server, Database Model, & Core Inference Routes
│   ├── crop_model.pkl              # Trained Multi-Class Crop Classification Model
│   ├── crop_label_encoder.pkl      # Encoder mapping numerical predictions to Crop Names
│   ├── fertilizer_model.pkl        # Trained Fertilizer Recommendation Model
│   ├── soil_type_encoder.pkl       # Label Encoder handling categorical Soil Inputs
│   ├── crop_type_encoder.pkl       # Label Encoder handling categorical Crop Inputs
│   └── fertilizer_label_encoder.pkl# Encoder mapping indices to Fertilizer Compound Names
├── frontend/
│   └── ui.py                       # Streamlit Multi-Step Processing Application
└── firmware/
    └── main.cpp                    # Asynchronous C++ Firmware for the ESP32 Controller

```

---

##  Setup & Deployment Protocol

### 1. Database Provisioning (Railway)

1. Initialize a **MySQL** database resource inside your **Railway Cloud Dashboard**.
2. Under the Query terminal panel (or through a secure remote client like TablePlus/Beekeeper), confirm or generate the relational persistence table structure:
```sql
CREATE TABLE IF NOT EXISTS sensor_readings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    temperature FLOAT NOT NULL,
    humidity FLOAT NOT NULL,
    soil_moisture FLOAT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);

```



### 2. API Server Execution

1. Navigate to your `/backend` repository folder and install the Python runtime libraries:
```bash
pip install flask flask-sqlalchemy mysql-connector-python joblib scikit-learn numpy

```


2. Create an environment configuration file named `.env` in the same directory to feed Railway variables safely into the container context without hardcoding strings:
```env
MYSQLHOST=your-railway-mysql-host.railway.internal
MYSQLPORT=3306
MYSQLUSER=root
MYSQLPASSWORD=your_railway_database_password
MYSQLDATABASE=railway

```


3. Boot the API backend engine:
```bash
python app.py

```


*Note: Upon connection, Flask-SQLAlchemy automatically verifies database connectivity and builds missing table assets on Railway seamlessly.*

### 3. Frontend Panel Initiation

1. Enter your `/frontend` directory and add the user interface requirements:
```bash
pip install streamlit requests

```


2. Initialize the dashboard:
```bash
streamlit run ui.py

```


3. Use the runtime sidebar configuration element to match your local or remote Flask URL gateway (e.g., `http://localhost:5000` or its public IP address).

### 4. Edge Hardware Flashing

1. Launch `/firmware/main.cpp` using your IDE.
2. Ensure you have downloaded the core libraries via your package manager:
* `ArduinoJson` (Minimum version 7.x required)
* `LiquidCrystal_I2C`
* `DHT sensor library` (Adafruit)


3. Modify network connectivity records to align with your active mobile hotspot setup:
```cpp
#define WIFI_SSID     "Your_Hotspot_SSID"
#define WIFI_PASSWORD "Your_Hotspot_Password"

```


4. Adjust the target server address `#define FLASK_URL "http://YOUR_LAPTOP_IP:5000"` to route packets out of your local network space. Upload the binary code to the ESP32.

---

##  Core API Integration Specifications

### `GET /health`

Verifies core runtime conditions and exposes dynamic operational metadata matrices to the caller.

* **Response Status Code:** `200 OK`
* **JSON Output Model:**
```json
{
  "status": "ok",
  "database": "connected",
  "soil_types": ["Black", "Clay", "Loamy", "Red", "Sandy"],
  "crop_types": ["Barley", "Cotton", "Groundnuts", "Maize", "Millets", "Oil seeds", "Paddy", "Pulses", "Sugarcane", "Tobacco", "Wheat"]
}

```



### `POST /sensor_data`

Receives transactional telemetry packages fired from edge microcontrollers and persists them inside cloud MySQL table configurations.

* **Payload Format:** `{"temperature": 27.5, "humidity": 62.3, "soil_moisture": 45.8}`
* **Response Status Code:** `200 OK`

### `GET /sensor_data`

Queries the MySQL tracking array, applies descending chronological ordering loops, and isolates the latest structural snapshot entry to serve UI views.

* **Response Status Code:** `200 OK` (or `404 Not Found` if database tracking records are blank)
* **JSON Output Model:**
```json
{
  "temperature": 27.5,
  "humidity": 62.3,
  "soil_moisture": 45.8,
  "timestamp": "2026-07-09 15:30:22"
}

```



### `POST /predict/crop`

Passes an array vector through the classification algorithm to generate an optimal crop prediction list.

* **Payload Format:** `{"N": 85, "P": 40, "K": 45, "temperature": 26.4, "humidity": 60.1, "ph": 6.8, "rainfall": 180.5}`
* **Response Model:** Returns the top recommended label string alongside confidence values and a breakdown of alternative probabilities.

### `POST /predict/fertilizer`

Computes fertilizer requirements using chemical arrays and targeted botanical parameters. If the incoming payload omits explicit moisture information, the route intercepts the request, runs a sub-query against the MySQL cloud records, extracts the latest hardware entry, and logs the data dependency source.

* **Payload Format:** `{"N": 40, "P": 20, "K": 10, "ph": 6.2, "temperature": 25.4, "humidity": 58.9, "rainfall": 120.3, "soil_type": "Loamy", "crop_type": "Wheat"}`
* **Response Status Code:** `200 OK`

```
***

```
