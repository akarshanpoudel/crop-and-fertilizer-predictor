"""
AgroSense Flask API  v2 — Soil Moisture Integration (no database)
─────────────────────────────────────────────────────────────────
Changes from v1:
  • ESP32 now sends soil_moisture alongside temperature & humidity
  • /sensor_data  stores + returns soil_moisture
  • /predict/fertilizer auto-fills moisture from the sensor snapshot
    when the Streamlit caller doesn't supply it explicitly

Endpoints:
    GET  /health             → status check + valid soil/crop type lists
    POST /sensor_data        → ESP32 pushes temperature, humidity, soil_moisture
    GET  /sensor_data        → Streamlit fetches latest sensor readings
    POST /predict/crop       → predicts crop from soil + climate inputs
    POST /predict/fertilizer → predicts fertilizer; moisture from body or sensor

Run:
    pip install flask joblib scikit-learn numpy
    python app.py
Starts on http://0.0.0.0:5000
"""

from flask import Flask, request, jsonify
import joblib
import numpy as np
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()

db_user = os.getenv("MYSQLUSER")
db_pass = os.getenv("MYSQLPASSWORD")
db_host = os.getenv("MYSQLHOST")
db_port = os.getenv("MYSQLPORT")
db_name = os.getenv("MYSQLDATABASE")

app.config["SQLALCHEMY_DATABASE_URI"] = (
    f"mysql+mysqlconnector://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

class SensorReading(db.Model):
    __tablename__ = "sensor_readings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    soil_moisture = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

BASE = os.path.dirname(os.path.abspath(__file__))


# This prevents the app from crashing if a .pkl file is missing or has a version mismatch
def safe_load(filename):
    filepath = os.path.join(BASE, filename)
    if os.path.exists(filepath):
        try:
            return joblib.load(filepath)
        except Exception as e:
            print(f"[Warning] Could not load {filename}: {e}")
    else:
        print(f"[Warning] File not found: {filename}")
    return None

print("Loading models...")
crop_model   = safe_load("models/crop_model.pkl")
crop_le      = safe_load("models/crop_label_encoder.pkl")

fert_model   = safe_load("models/fertilizer_model.pkl")
soil_le      = safe_load("models/soil_type_encoder.pkl")
crop_type_le = safe_load("models/crop_type_encoder.pkl")
fert_le      = safe_load("models/fertilizer_label_encoder.pkl")
print("Models loaded (or safely bypassed).")

# Safely extract classes if the encoders loaded successfully
SOIL_TYPES = list(soil_le.classes_) if soil_le else []
CROP_TYPES = list(crop_type_le.classes_) if crop_type_le else []

# In-memory latest sensor snapshot (written by ESP32, read by Streamlit) 
# _sensor_snapshot = {
#     "temperature":   None,
#     "humidity":      None,
#     "soil_moisture": None,   
#     "timestamp":     None,
# }


#  Health check 
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status":     "ok",
        "soil_types": SOIL_TYPES,
        "crop_types": CROP_TYPES,
    })


#  Sensor data — ESP32 POSTs here; Streamlit GETs here 
@app.route("/sensor_data", methods=["POST"])
def receive_sensor_data():
    """
    Called by ESP32 over WiFi every 30 s.
    Expects JSON: { "temperature": 28.4, "humidity": 65.2, "soil_moisture": 42.0 }
    soil_moisture is a % value (0–100) mapped from the ADC reading.
    """
    data = request.get_json(force=True, silent=True) or {}
    try:
        temp     = round(float(data["temperature"]),   2)
        humidity = round(float(data["humidity"]),      2)
        moisture = round(float(data["soil_moisture"]), 2)   
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({
            "error": f"Missing or invalid field: {e}",
            "required_fields": ["temperature", "humidity", "soil_moisture"],
        }), 400

    reading = SensorReading(
        temperature=temp,
        humidity=humidity,
        soil_moisture=moisture,
    )
    db.session.add(reading)
    db.session.commit()

    print(f"[Sensor] T={temp}°C  H={humidity}%  SM={moisture}%  (saved as id={reading.id})")
    return jsonify({"status": "ok"})



@app.route("/sensor_data", methods=["GET"])
def get_sensor_data():
    """
    Called by Streamlit to fetch the latest DHT22 + moisture readings.
    Returns: { temperature, humidity, soil_moisture, timestamp }
    """
    latest = SensorReading.query.order_by(SensorReading.id.desc()).first()

    if latest is None:
        return jsonify({"error": "No sensor data received yet from ESP32"}), 404

    return jsonify({
        "temperature":   latest.temperature,
        "humidity":      latest.humidity,
        "soil_moisture": latest.soil_moisture,
        "timestamp":     latest.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    })


#  Step 1: Crop prediction 
@app.route("/predict/crop", methods=["POST"])
def predict_crop():
    """
    Expects JSON: { N, P, K, temperature, humidity, ph, rainfall }
    Returns:      { crop, confidence, top3: [{crop, confidence}, ...] }
    """
    if crop_model is None or crop_le is None:
        return jsonify({"error": "Crop models failed to load on server boot."}), 500
        
    data = request.get_json(force=True, silent=True) or {}
    try:
        features = [[
            float(data["N"]),
            float(data["P"]),
            float(data["K"]),
            float(data["temperature"]),
            float(data["humidity"]),
            float(data["ph"]),
            float(data["rainfall"]),
        ]]
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid or missing input: {e}"}), 400

    pred_enc   = crop_model.predict(features)[0]
    proba      = crop_model.predict_proba(features)[0]
    crop       = crop_le.inverse_transform([pred_enc])[0]
    confidence = round(float(proba[pred_enc]) * 100, 2)

    top3_idx = np.argsort(proba)[::-1][:3]
    top3 = [
        {"crop": crop_le.inverse_transform([i])[0], "confidence": round(float(proba[i]) * 100, 1)}
        for i in top3_idx
    ]

    return jsonify({"crop": crop, "confidence": confidence, "top3": top3})


#  Step 2: Fertilizer prediction
@app.route("/predict/fertilizer", methods=["POST"])
def predict_fertilizer():
    """
    Expects JSON: { N, P, K, ph, temperature, humidity, rainfall,
                    soil_type, crop_type [, moisture] }
    """
    if fert_model is None or soil_le is None or crop_type_le is None:
        return jsonify({"error": "Fertilizer models failed to load on server boot."}), 500
        
    data = request.get_json(force=True, silent=True) or {}
    try:
        N           = float(data["N"])
        P           = float(data["P"])
        K           = float(data["K"])
        ph          = float(data["ph"])
        temperature = float(data["temperature"])
        humidity    = float(data["humidity"])
        rainfall    = float(data["rainfall"])
        soil_type   = str(data["soil_type"])
        crop_type   = str(data["crop_type"])
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid or missing input: {e}"}), 400

    # Resolve moisture 
    if "moisture" in data:
        try:
            moisture = float(data["moisture"])
            moisture_source = "request_body"
        except (TypeError, ValueError):
            return jsonify({"error": "'moisture' must be a number (0–100)"}), 400
    elif SensorReading.query.order_by(SensorReading.id.desc()).first() is not None:
        latest          = SensorReading.query.order_by(SensorReading.id.desc()).first()
        moisture        = latest.soil_moisture
        moisture_source = "esp32_sensor"
        print(f"[Fertilizer] Using ESP32 soil_moisture={moisture}% "
              f"(reading id={latest.id} @ {latest.timestamp})")
    else:
        return jsonify({
            "error": (
                "No moisture value available. Either include 'moisture' in this "
                "request body, or POST to /sensor_data from the ESP32 first."
            )
        }), 400

    if soil_type not in SOIL_TYPES:
        return jsonify({"error": f"soil_type must be one of {SOIL_TYPES}"}), 400
    if crop_type not in CROP_TYPES:
        return jsonify({"error": f"crop_type must be one of {CROP_TYPES}"}), 400

    soil_enc = int(soil_le.transform([soil_type])[0])
    crop_enc = int(crop_type_le.transform([crop_type])[0])

    features = [[N, P, K, ph, moisture, temperature, humidity, rainfall, soil_enc, crop_enc]]

    pred_enc   = fert_model.predict(features)[0]
    proba      = fert_model.predict_proba(features)[0]
    fertilizer = fert_le.inverse_transform([pred_enc])[0]
    confidence = round(float(proba[pred_enc]) * 100, 2)

    all_idx = np.argsort(proba)[::-1]
    all_fertilizers = [
        {"name": fert_le.inverse_transform([i])[0], "confidence": round(float(proba[i]) * 100, 1)}
        for i in all_idx
    ]

    return jsonify({
        "fertilizer":      fertilizer,
        "confidence":      confidence,
        "moisture_used":   moisture,
        "moisture_source": moisture_source, 
        "all_fertilizers": all_fertilizers,
    })

if __name__ == '__main__':
   
    app.run(host='0.0.0.0', port=5000, debug=True)