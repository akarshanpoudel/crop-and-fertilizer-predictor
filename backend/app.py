"""
AgroSense Flask API v2 — Soil Moisture & Recommendation Logging Integration
───────────────────────────────────────────────────────────────────────────
Endpoints:
    GET  /health            → status check + valid soil/crop type lists
    POST /sensor_data       → ESP32 pushes temperature, humidity, soil_moisture
    GET  /sensor_data       → Streamlit fetches latest sensor readings
    POST /predict/crop      → predicts crop & creates ONE recommendation_logs row
    POST /predict/fertilizer → predicts fertilizer & COMPLETES that same row
                                — one INSERT per completed cycle, nothing written on Step 1

Run:
    pip install flask joblib scikit-learn numpy flask-sqlalchemy mysql-connector-python python-dotenv
    python app.py
Starts on http://0.0.0.0:5000
"""

import os
from datetime import datetime
from zoneinfo import ZoneInfo

import joblib
import numpy as np
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
load_dotenv()

# MySQL Configuration
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

# Nepal Standard Time (UTC+5:45)
NEPAL_TZ = ZoneInfo("Asia/Kathmandu")


def nepal_now():

    return datetime.now(NEPAL_TZ).replace(tzinfo=None)


# Database Models
# Table 1: Live ESP32 Sensor Readings
class SensorReading(db.Model):
    __tablename__ = "sensor_readings"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    soil_moisture = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=nepal_now)


# Table 2: Complete Pipeline Recommendation History
# One row == one complete prediction cycle.
class RecommendationLog(db.Model):
    __tablename__ = "recommendation_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    nitrogen = db.Column(db.Float, nullable=False)
    phosphorus = db.Column(db.Float, nullable=False)
    potassium = db.Column(db.Float, nullable=False)
    ph = db.Column(db.Float, nullable=False)
    rainfall = db.Column(db.Float, nullable=False)
    rainfall_growing_season = db.Column(db.Float, nullable=True)
    temperature = db.Column(db.Float, nullable=False)
    humidity = db.Column(db.Float, nullable=False)
    soil_moisture = db.Column(db.Float, nullable=False)
    soil_type = db.Column(db.String(50), nullable=True)
    predicted_crop = db.Column(db.String(100), nullable=True)
    recommended_fertilizer = db.Column(db.String(100), nullable=True)
    timestamp = db.Column(db.DateTime, default=nepal_now)


# ML Model Loading

BASE = os.path.dirname(os.path.abspath(__file__))


def safe_load(filename):
    filepath = os.path.join(BASE, filename)
    if os.path.exists(filepath):
        try:
            return joblib.load(filepath)
        except (OSError, ValueError, EOFError) as e:
            print(f"[Warning] Could not load {filename}: {e}")
    else:
        print(f"[Warning] File not found: {filename}")
    return None


print("Loading models...")
crop_model = safe_load("models/crop_model.pkl")
crop_le = safe_load("models/crop_label_encoder.pkl")

fert_model = safe_load("models/fertilizer_model.pkl")
soil_le = safe_load("models/soil_type_encoder.pkl")
crop_type_le = safe_load("models/crop_type_encoder.pkl")
fert_le = safe_load("models/fertilizer_label_encoder.pkl")
print("Models loaded (or safely bypassed).")

SOIL_TYPES = list(soil_le.classes_) if soil_le else []
CROP_TYPES = list(crop_type_le.classes_) if crop_type_le else []


# Chain-inference crop mapping (Step 1 -> Step 2)

CROP_TO_FERTILIZER_TYPE = {

    "rice": "Rice",
    "maize": "Maize",
    "cotton": "Cotton",

    "blackgram": "Wheat",
    "chickpea": "Wheat",
    "kidneybeans": "Wheat",
    "lentil": "Wheat",
    "mothbeans": "Wheat",
    "mungbean": "Wheat",
    "pigeonpeas": "Wheat",

    "banana": "Sugarcane",
    "coconut": "Sugarcane",
    "papaya": "Sugarcane",

    "apple": "Potato",
    "grapes": "Potato",

    "coffee": "Cotton",
    "jute": "Cotton",

    "mango": "Tomato",
    "muskmelon": "Tomato",
    "orange": "Tomato",
    "pomegranate": "Tomato",
    "watermelon": "Tomato",
}


def resolve_fertilizer_crop_type(predicted_crop):
    """
    Chain-inference step: maps Step 1's predicted crop (any of the 22
    crop_model classes) onto one of the 7 crop types the fertilizer model
    actually supports. Fully automatic — no manual override.

    Returns (fertilizer_crop_type, was_mapped) or (None, None) if the
    predicted crop isn't recognized at all (defensive — shouldn't happen
    for any output of crop_model, but the model/CSV could change).
    """
    key = str(predicted_crop).strip().lower()

    for ct in CROP_TYPES:
        if ct.lower() == key:
            return ct, False

    mapped = CROP_TO_FERTILIZER_TYPE.get(key)
    if mapped is None:
        return None, None
    return mapped, True


# Routes

@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "status": "ok",
        "soil_types": SOIL_TYPES,
        "crop_types": CROP_TYPES,
    })


@app.route("/sensor_data", methods=["POST"])
def receive_sensor_data():
    """ESP32 posts telemetry every 30s"""
    data = request.get_json(force=True, silent=True) or {}
    try:
        temp = round(float(data["temperature"]), 2)
        humidity = round(float(data["humidity"]), 2)
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
    """Streamlit fetches latest sensor readings"""
    latest = SensorReading.query.order_by(SensorReading.id.desc()).first()

    if latest is None:
        return jsonify({"error": "No sensor data received yet from ESP32"}), 404

    return jsonify({
        "temperature": latest.temperature,
        "humidity": latest.humidity,
        "soil_moisture": latest.soil_moisture,
        "timestamp": latest.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
    })


# Step 1: Crop Prediction — PREDICTION ONLY
@app.route("/predict/crop", methods=["POST"])
def predict_crop():
    if crop_model is None or crop_le is None:
        return jsonify({"error": "Crop models failed to load on server boot."}), 500

    data = request.get_json(force=True, silent=True) or {}
    try:
        n = float(data["N"])
        p = float(data["P"])
        k = float(data["K"])
        temp = float(data["temperature"])
        hum = float(data["humidity"])
        ph = float(data["ph"])
        rainfall = float(data["rainfall"])
        features = [[n, p, k, temp, hum, ph, rainfall]]
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid or missing input: {e}"}), 400

    pred_enc = crop_model.predict(features)[0]
    proba = crop_model.predict_proba(features)[0]
    crop = crop_le.inverse_transform([pred_enc])[0]
    confidence = round(float(proba[pred_enc]) * 100, 2)

    top3_idx = np.argsort(proba)[::-1][:3]
    top3 = [
        {"crop": crop_le.inverse_transform([i])[0], "confidence": round(float(proba[i]) * 100, 1)}
        for i in top3_idx
    ]

    return jsonify({
        "crop": crop,
        "confidence": confidence,
        "top3": top3,
    })


# Step 2: Fertilizer Prediction — COMPLETES the row created in Step 1
@app.route("/predict/fertilizer", methods=["POST"])
def predict_fertilizer():
    if fert_model is None or soil_le is None or crop_type_le is None:
        return jsonify({"error": "Fertilizer models failed to load on server boot."}), 500

    data = request.get_json(force=True, silent=True) or {}
    try:
        N = float(data["N"])
        P = float(data["P"])
        K = float(data["K"])
        ph = float(data["ph"])
        temperature = float(data["temperature"])
        humidity = float(data["humidity"])
        rainfall = float(data["rainfall"])
        soil_type = str(data["soil_type"])
        predicted_crop = str(data["predicted_crop"])
    except (KeyError, TypeError, ValueError) as e:
        return jsonify({"error": f"Invalid or missing input: {e}"}), 400

    rainfall_growing_season = None
    if "rainfall_growing_season" in data:
        try:
            rainfall_growing_season = float(data["rainfall_growing_season"])
        except (TypeError, ValueError):
            return jsonify({"error": "'rainfall_growing_season' must be a number"}), 400

    # Chain inference: Step 1's predicted crop is the ONLY input here
    crop_type, crop_type_mapped = resolve_fertilizer_crop_type(predicted_crop)
    if crop_type is None:
        return jsonify({
            "error": (
                f"'{predicted_crop}' is not a crop this pipeline knows how to "
                f"handle (not in crop_model's classes or the fertilizer "
                f"crop-type mapping table)."
            )
        }), 400

    #  moisture
    if "moisture" in data:
        try:
            moisture = float(data["moisture"])
            moisture_source = "request_body"
        except (TypeError, ValueError):
            return jsonify({"error": "'moisture' must be a number (0–100)"}), 400
    elif SensorReading.query.order_by(SensorReading.id.desc()).first() is not None:
        latest = SensorReading.query.order_by(SensorReading.id.desc()).first()
        moisture = latest.soil_moisture
        moisture_source = "esp32_sensor"
    else:
        return jsonify({
            "error": "No moisture value available. Either include 'moisture' or POST sensor data first."
        }), 400

    if soil_type not in SOIL_TYPES:
        return jsonify({"error": f"soil_type must be one of {SOIL_TYPES}"}), 400

    soil_enc = int(soil_le.transform([soil_type])[0])

    crop_enc = int(crop_type_le.transform([crop_type])[0])

    features = [[N, P, K, ph, moisture, temperature, humidity, rainfall, soil_enc, crop_enc]]

    pred_enc = fert_model.predict(features)[0]
    proba = fert_model.predict_proba(features)[0]
    fertilizer = fert_le.inverse_transform([pred_enc])[0]
    confidence = round(float(proba[pred_enc]) * 100, 2)

    all_idx = np.argsort(proba)[::-1]
    all_fertilizers = [
        {"name": fert_le.inverse_transform([i])[0], "confidence": round(float(proba[i]) * 100, 1)}
        for i in all_idx
    ]

    # This is the ONE and only INSERT for the whole cycle.
    log_entry = RecommendationLog(
        nitrogen=N,
        phosphorus=P,
        potassium=K,
        ph=ph,
        rainfall=rainfall,
        rainfall_growing_season=rainfall_growing_season,
        temperature=temperature,
        humidity=humidity,
        soil_moisture=moisture,
        soil_type=soil_type,
        predicted_crop=predicted_crop,
        recommended_fertilizer=fertilizer
    )
    db.session.add(log_entry)
    db.session.commit()

    print(
        f"[Log Saved] Complete cycle logged as ID={log_entry.id} | "
        f"Predicted={predicted_crop} -> FertCropType={crop_type} "
        f"({'mapped' if crop_type_mapped else 'exact match'}) -> Fertilizer={fertilizer}"
    )

    return jsonify({
        "fertilizer": fertilizer,
        "confidence": confidence,
        "moisture_used": moisture,
        "moisture_source": moisture_source,
        "all_fertilizers": all_fertilizers,
        "predicted_crop": predicted_crop,
        "fertilizer_crop_type": crop_type,
        "crop_type_mapped": crop_type_mapped,
        "log_id": log_entry.id
    })


# App Entry Point

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Automatically creates tables in MySQL if they don't exist
    app.run(host="0.0.0.0", port=5000, debug=True)
