# Crop and Fertilizer Predictor — Backend

Backend service for the Crop and Fertilizer Predictor project. It trains and serves machine learning models that recommend the most suitable **crop** and **fertilizer** based on soil and environmental input parameters.

## 📁 Project Structure

```
backend/
├── data/
│   ├── Crop_recommendation.csv        # Dataset used for crop recommendation model
│   └── fertilizer_recommendation.csv  # Dataset used for fertilizer recommendation model
│
├── models/
│   ├── crop_model.pkl                 # Trained crop recommendation model
│   ├── crop_label_encoder.pkl         # Label encoder for crop output classes
│   ├── fertilizer_model.pkl           # Trained fertilizer recommendation model
│   ├── fertilizer_label_encoder.pkl   # Label encoder for fertilizer output classes
│   └── soil_type_encoder.pkl          # Encoder for soil type input feature
│
├── notebooks/
│   ├── crop_recommendation.ipynb       # EDA + training pipeline for crop model
│   └── fertilizer_recommendation.ipynb # EDA + training pipeline for fertilizer model
│
├── app.py              # Flask app serving prediction endpoints
├── requirements.txt     # Python dependencies
└── README.md
```

## ⚙️ Setup

1. **Clone the repo and navigate to the backend folder:**
   ```bash
   git clone https://github.com/akarshanpoudel/crop-and-fertilizer-predictor.git
   cd crop-and-fertilizer-predictor/backend
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python -m venv venv
   source venv/bin/activate   # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run the Flask app:**
   ```bash
   python app.py
   ```
   By default, the server runs at `http://127.0.0.1:5000/`.

## 🧠 Model Training

The `.pkl` model files in `models/` are pre-trained and ready to use. If you want to retrain them:

1. Open the relevant notebook in `notebooks/` (`crop_recommendation.ipynb` or `fertilizer_recommendation.ipynb`).
2. Run all cells — this loads the dataset from `data/`, performs preprocessing/EDA, trains the model, and re-exports the updated `.pkl` files into `models/`.

## 🔌 API Endpoints

### `POST /predict/crop`

Recommends the most suitable crop based on soil nutrients and environmental conditions.

**Request body:**

| Field | Type | Source |
|---|---|---|
| `N` | float | Manually entered in UI |
| `P` | float | Manually entered in UI |
| `K` | float | Manually entered in UI |
| `temperature` | float | DHT22 sensor |
| `humidity` | float | DHT22 sensor |
| `ph` | float | pH sensor |
| `rainfall` | float | Manually entered in UI |

**Example request:**
```json
{
  "N": 90,
  "P": 42,
  "K": 43,
  "temperature": 20.8,
  "humidity": 82,
  "ph": 6.5,
  "rainfall": 202.9
}
```

**Example response:**
```json
{
  "recommended_crop": "rice",
  "confidence_pct": 94.32
}
```

---

### `POST /predict/fertilizer`

Recommends the most suitable fertilizer based on soil nutrients, soil/crop type, and environmental conditions.

**Request body:**

| Field | Type | Source |
|---|---|---|
| `Nitrogen_Level` | float | Manually entered in UI |
| `Phosphorus_Level` | float | Manually entered in UI |
| `Potassium_Level` | float | Manually entered in UI |
| `Soil_pH` | float | Sensor |
| `Soil_Moisture` | float | Sensor |
| `Temperature` | float | Sensor |
| `Humidity` | float | Sensor |
| `Rainfall` | float | Manually entered in UI |
| `Soil_Type` | string | Dropdown: `Clay` / `Loamy` / `Sandy` / `Silt` |
| `Crop_Type` | string | Dropdown: `Cotton` / `Maize` / `Potato` / `Rice` / `Sugarcane` / `Tomato` / `Wheat` |

**Example request:**
```json
{
  "Nitrogen_Level": 40,
  "Phosphorus_Level": 30,
  "Potassium_Level": 20,
  "Soil_pH": 6.8,
  "Soil_Moisture": 45,
  "Temperature": 26.5,
  "Humidity": 60,
  "Rainfall": 150,
  "Soil_Type": "Loamy",
  "Crop_Type": "Wheat"
}
```

**Example response:**
```json
{
  "recommended_fertilizer": "Urea",
  "confidence_pct": 88.71
}
```

**Error responses:** Both endpoints return `400` with an `error` message if a required field is missing or a value is invalid (e.g. `Soil_Type` not in the trained categories).

## 📦 Requirements

See `requirements.txt` for the full list of dependencies (typically includes `flask`, `pandas`, `scikit-learn`, `numpy`, `joblib`/`pickle`).

## 🤝 Contributing

This backend was added via a pull request to integrate the ML pipeline with the existing frontend structure. For changes, please open a PR with a clear description of what was modified.
