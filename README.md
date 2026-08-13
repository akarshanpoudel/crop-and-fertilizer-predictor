# 🌾 AgroSense — IoT-ML Crop & Fertilizer Recommendation System

![Python](https://img.shields.io/badge/Python-3.x-blue) ![Flask](https://img.shields.io/badge/Flask-REST%20API-lightgrey) ![Scikit-learn](https://img.shields.io/badge/Scikit--learn-1.8.0-orange) ![Streamlit](https://img.shields.io/badge/Streamlit-Dashboard-red) ![ESP32](https://img.shields.io/badge/ESP32-IoT-green)

AgroSense is a final year engineering project that combines IoT hardware and machine learning to help farmers in Nepal decide which crop to grow and which fertilizer to use based on real soil and environmental conditions. Instead of relying on guesswork or generic advice, AgroSense reads live data from sensors, runs it through trained machine learning models, and gives an instant recommendation.

---

## 🌱 What the System Does

The system takes soil nutrient levels (Nitrogen, Phosphorus, Potassium), temperature, humidity, soil moisture, soil pH, and rainfall as inputs. It first predicts the most suitable crop for those conditions, then uses that result to recommend the appropriate fertilizer. This two-step chained approach ensures the fertilizer recommendation is always linked to the predicted crop rather than being a separate and unrelated output.

---

## ⚙️ How It Works

Sensors connected to an ESP32 microcontroller read temperature, humidity, and soil moisture automatically. Soil pH and nutrient values (NPK) are entered manually through the dashboard. Rainfall data is fetched automatically from the Open-Meteo weather API for the Pokhara region. All this data is sent from the ESP32 to a Flask backend server over WiFi, where the machine learning models process it and return a recommendation. The result is shown on a Streamlit web dashboard and also displayed on a small LCD screen attached to the ESP32 device itself.

---

## 🤖 Machine Learning Models

Four classification algorithms were trained and compared: Random Forest, Decision Tree, Support Vector Machine, and Naive Bayes. Random Forest was selected as the final model for both crop and fertilizer recommendation.

| Model | Task | Accuracy | F1-Score |
|---|---|---|---|
| Random Forest | Crop Recommendation | 99.55% | 0.9955 |
| Random Forest | Fertilizer Recommendation | — | — |

- **Crop Dataset:** 2,200 records, 22 crop classes, 7 features
- **Fertilizer Dataset:** 99 records, 7 fertilizer classes, 9 features
- **Validation:** Stratified 5-Fold Cross Validation (Mean F1: 0.9926)

---

## 🔌 Hardware Components

| Component | Purpose | Quantity |
|---|---|---|
| ESP32 Dev Board | Microcontroller + WiFi | 1 |
| DHT22 Sensor | Temperature & Humidity | 2 |
| Capacitive Soil Moisture Sensor | Soil Moisture | 1 |
| Analog pH Probe | Soil pH | 1 |
| 16×2 I2C LCD | On-device display | 1 |
| 5V/2A Adapter + 18650 LiPo | Power supply | 1 |

---

## 🛠️ Software and Tools

| Tool | Purpose |
|---|---|
| Python 3.x | Core language |
| Scikit-learn 1.8.0 | ML model training |
| Flask | REST API backend |
| Streamlit | Web dashboard |
| Pandas & NumPy | Data processing |
| Matplotlib & Seaborn | Visualization |
| Joblib | Model saving and loading |
| Arduino (C++) | ESP32 firmware |

---

## 📁 Project Structure

```
AgroSense/
│
├── models/
│   ├── crop_model.pkl
│   ├── fertilizer_model.pkl
│   ├── crop_label_encoder.pkl
│   └── fertilizer_label_encoder.pkl
│
├── notebooks/
│   ├── CROP_REC.ipynb
│   └── FERTILIZER_REC.ipynb
│
├── esp32/
│   └── agrosense_firmware.ino
│
├── app.py                  
├── dashboard.py            
├── requirements.txt
└── README.md
```

---

## 🚀 Setup and Installation

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/agrosense.git
cd agrosense
```

### Step 2 — Create a Virtual Environment

```bash
python -m venv venv
```

Activate it:

- On Windows:
```bash
venv\Scripts\activate
```

- On Linux or Mac:
```bash
source venv/bin/activate
```

### Step 3 — Install Required Packages

```bash
pip install -r requirements.txt
```

If you do not have a requirements.txt file yet, install manually:

```bash
pip install flask streamlit scikit-learn==1.8.0 pandas numpy matplotlib seaborn joblib requests
```

### Step 4 — Run the Flask API

```bash
python app.py
```

The Flask server will start at:
```
http://127.0.0.1:5000
```

Keep this terminal running in the background.

### Step 5 — Run the Streamlit Dashboard

Open a new terminal, activate the virtual environment again, then run:

```bash
streamlit run dashboard.py
```

The dashboard will open automatically in your browser at:
```
http://localhost:8501
```

### Step 6 — Connect the ESP32 (Optional)

Upload the firmware from the `esp32/agrosense_firmware.ino` file to your ESP32 using the Arduino IDE. Make sure to set your WiFi SSID, password, and Flask server IP address inside the firmware before uploading. Once running, the ESP32 will automatically fetch sensor readings and send them to the Flask API over WiFi.

---

## 🌐 API Endpoints

### Crop Recommendation

- **URL:** `POST /predict_crop`
- **Input:** JSON with keys — `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`
- **Output:** JSON with predicted crop name

### Fertilizer Recommendation

- **URL:** `POST /predict_fertilizer`
- **Input:** JSON with keys — `N`, `P`, `K`, `temperature`, `humidity`, `ph`, `rainfall`, `soil_type`, `crop_type`
- **Output:** JSON with predicted fertilizer name

---

## 📊 Sample Prediction

For typical rice-growing conditions:
- N=90, P=42, K=43, Temperature=21°C, Humidity=82%, pH=6.5, Rainfall=203mm

The model correctly returns **RICE** as the recommended crop.

---

## ⚠️ Known Limitations

- The crop and fertilizer datasets are sourced from Indian agricultural data and may not fully represent Nepal's soil conditions, rainfall patterns, and temperature profiles
- The fertilizer dataset is small with only 99 records, so fertilizer model results should be interpreted with caution
- The pH sensor requires manual two-point calibration using pH 4.0 and pH 7.0 buffer solutions before field deployment

---

## 🔭 Future Plans

- Collect Nepal-specific field soil samples from multiple districts and retrain models on locally relevant data
- Deploy Flask API to a cloud server for remote access beyond local WiFi
- Add Nepali language support to the Streamlit dashboard
- Expand the fertilizer dataset with more Nepal-specific crop and soil combinations

---

## 👨‍💻 Team

| Name | Role |
|---|---|
| Sushovan | ML Models, Flask API, Documentation |
| Akarshan Poudel | Hardware Integration, ESP32 Firmware |
| Kushal Neupane | Streamlit Dashboard |
| Sachin Kandel | Dataset Preprocessing, Testing |

---

## 🏫 Institution

**Pokhara University — School of Engineering**
B.E. Computer Engineering — Final Year Project

---

## 📄 License

This project is developed for academic purposes under Pokhara University and is not intended for commercial use.
