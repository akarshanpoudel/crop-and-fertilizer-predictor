import streamlit as st
import requests

# Page config
st.set_page_config(
    page_title="AgroSense – Crop & Fertilizer Intelligence",
    page_icon="🌾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Sidebar — Flask API + ESP32 controls
with st.sidebar:
    st.markdown("### Flask API")
    flask_api_url = st.text_input("Flask API URL", value="http://10.96.220.61:5000")
    flask_api_url = flask_api_url.rstrip("/")

    st.markdown("### ESP32 (WiFi)")
    st.caption("Enter the IP shown on the LCD after boot")
    # UPDATED: Adjusted the placeholder subnet to match your hotspot
    esp32_ip = st.text_input("ESP32 IP Address", value="10.96.220.x",
                              placeholder="e.g. 10.96.220.45")
    esp32_url = f"http://{esp32_ip}" if esp32_ip and "x" not in esp32_ip else None

    lcd_enabled = st.toggle("Send results to LCD", value=True)

    if esp32_url and st.button("Test ESP32 Connection"):
        try:
            r = requests.get(f"{esp32_url}/health", timeout=4)
            if r.status_code == 200:
                st.success("ESP32 reachable!")
            else:
                st.error(f"ESP32 replied with HTTP {r.status_code}")
        except Exception as e:
            st.error(f"Cannot reach ESP32: {e}")


# LCD — HTTP POST to ESP32 /display endpoint
def update_lcd(esp32_base_url, line1, line2):
    """Sends two display lines to the ESP32 over WiFi (HTTP POST)."""
    if not esp32_base_url:
        return False
    try:
        resp = requests.post(
            f"{esp32_base_url}/display",
            json={"line1": str(line1)[:16], "line2": str(line2)[:16]},
            timeout=5,
        )
        return resp.status_code == 200
    except Exception as e:
        st.error(f"LCD Update Error: {e}")
        return False


# Fetch live sensor data — reads Flask's /sensor_data
def fetch_sensor_data_from_flask(api_url):
    """Reads the latest DHT22 + moisture snapshot stored in Flask by the ESP32."""
    try:
        resp = requests.get(f"{api_url}/sensor_data", timeout=5)
        if resp.status_code == 404:
            st.error("No sensor data yet — make sure ESP32 is powered on and connected to WiFi.")
            return None
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Could not fetch sensor data: {e}")
        return None


# Live rainfall (Open-Meteo)
POKHARA_LAT = 28.2096
POKHARA_LON = 83.9856

def fetch_live_rainfall():
    """Fetches current real-time precipitation (mm) for Pokhara via Open-Meteo."""
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": POKHARA_LAT,
                "longitude": POKHARA_LON,
                "current": "precipitation",
                "timezone": "Asia/Kathmandu",
            },
            timeout=8,
        )
        resp.raise_for_status()
        data = resp.json()
        return float(data["current"]["precipitation"])
    except Exception as e:
        st.error(f"Could not fetch live rainfall: {e}")
        return None


@st.cache_data(ttl=60, show_spinner=False)
def get_metadata(api_url):
    resp = requests.get(f"{api_url}/health", timeout=5)
    resp.raise_for_status()
    data = resp.json()
    return data["soil_types"], data["crop_types"]


try:
    SOIL_TYPES, CROP_TYPES = get_metadata(flask_api_url)
    
   
    # If app.py safely bypassed loading models due to version errors, these lists might be empty.
    # This prevents the UI from crashing on the selectbox render.
    if not SOIL_TYPES:
        SOIL_TYPES = ["Sandy", "Loamy", "Clay", "Black", "Red"]
    if not CROP_TYPES:
        CROP_TYPES = ["Rice", "Wheat", "Maize", "Cotton"]
        
except requests.exceptions.RequestException as e:
    st.error(
        f"Cannot reach the Flask API at **{flask_api_url}**.\n\n"
        f"Make sure it's running: `python app.py` inside your `flask_api` folder.\n\n"
        f"Error: {e}"
    )
    st.stop()


# Session state — all sensor/input defaults set to 0.0
for key, default in {
    "crop_result":     None,
    "crop_confidence": None,
    "crop_top3":       None,
    "chain":           None,
    "live_temp":       0.0,
    "live_humidity":   0.0,
    "live_moisture":   0.0,
    "live_rainfall":   0.0,
}.items():
    if key not in st.session_state:
        st.session_state[key] = default


# CSS
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Inter:wght@300;400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    background-color: #0D1A0F;
    color: #E8F0E9;
}
.hero {
    text-align: center;
    padding: 1rem 1rem 1.5rem;
    border-bottom: 1px solid #1E3322;
    margin-bottom: 2.5rem;
}
.hero h1 {
    font-family: 'DM Serif Display', serif;
    font-size: 2.9rem;
    color: #7FD18E;
    letter-spacing: -0.5px;
    margin-bottom: 0.35rem;
}
.hero p { color: #8BA892; font-size: 1rem; font-weight: 300; margin: 0; }

/* Tab pills */
.stRadio > div { flex-direction: row; gap: 10px; }
.stRadio > div > label {
    background: #152318; border: 1px solid #2A4230;
    border-radius: 999px; padding: 0.4rem 1.3rem;
    color: #8BA892; font-size: 0.88rem; cursor: pointer; transition: all 0.2s;
}
.stRadio > div > label:has(input:checked) {
    background: #7FD18E; color: #0D1A0F;
    border-color: #7FD18E; font-weight: 600;
}

/* Section labels */
.sec-label {
    font-size: 0.68rem; font-weight: 600; letter-spacing: 1.4px;
    text-transform: uppercase; color: #4E7A57;
    margin-top: 1.5rem; margin-bottom: 0.6rem;
}

/* Badges */
.badge {
    display: inline-block; background: #0D2810;
    border: 1px solid #2A4230; border-radius: 5px;
    font-size: 0.67rem; color: #5A9466;
    padding: 2px 7px; margin-left: 6px;
    vertical-align: middle; letter-spacing: 0.4px;
}
.badge-lock {
    display: inline-block; background: #1A1A0D;
    border: 1px solid #3A3A20; border-radius: 5px;
    font-size: 0.67rem; color: #8A8A50;
    padding: 2px 7px; margin-left: 6px;
    vertical-align: middle; letter-spacing: 0.4px;
}

/* Locked display field */
.locked-field {
    background: #0A150B;
    border: 1px solid #1A2E1C;
    border-radius: 9px;
    padding: 0.55rem 0.9rem;
    margin-bottom: 0.3rem;
}
.locked-field .lf-label {
    font-size: 0.67rem; letter-spacing: 1px;
    text-transform: uppercase; color: #3D6646; margin-bottom: 2px;
}
.locked-field .lf-value {
    font-size: 1.1rem; color: #C8E8CC; font-weight: 500;
}
.locked-field .lf-unit {
    font-size: 0.75rem; color: #4E7A57; margin-left: 3px;
}

/* Locked crop field */
.locked-crop {
    background: #0F2011;
    border: 1px solid #2A4D30;
    border-radius: 10px;
    padding: 0.8rem 1.1rem;
    display: flex; align-items: center; gap: 12px;
}
.locked-crop .lc-label {
    font-size: 0.67rem; letter-spacing: 1px;
    text-transform: uppercase; color: #3D6646;
}
.locked-crop .lc-value {
    font-family: 'DM Serif Display', serif;
    font-size: 1.5rem; color: #7FD18E;
}

/* Button */
.stButton > button {
    background: #7FD18E !important; color: #0D1A0F !important;
    border: none !important; border-radius: 10px !important;
    font-weight: 600 !important; font-size: 0.95rem !important;
    padding: 0.65rem 2rem !important; width: 100%;
    transition: opacity 0.2s !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

/* Result box */
.result-box {
    background: linear-gradient(135deg, #152B18, #0F2213);
    border: 1px solid #2E5C38; border-radius: 14px;
    padding: 2rem; text-align: center; margin-top: 1.5rem;
}
.result-label {
    font-size: 0.68rem; letter-spacing: 1.5px;
    text-transform: uppercase; color: #4E7A57; margin-bottom: 0.35rem;
}
.result-value {
    font-family: 'DM Serif Display', serif;
    font-size: 2.5rem; color: #7FD18E; line-height: 1.1;
}
.conf-bar-bg {
    background: #1E3322; border-radius: 999px;
    height: 5px; margin: 1rem auto 0.35rem; max-width: 300px;
}
.conf-bar-fill { background: #7FD18E; border-radius: 999px; height: 5px; }
.conf-text { font-size: 0.82rem; color: #8BA892; }

.warn-box {
    background: #1A1500; border: 1px solid #3A3000;
    border-radius: 10px; padding: 1rem 1.2rem;
    color: #C8A840; font-size: 0.88rem; margin-bottom: 1rem;
}

hr { border-color: #1E3322; }

#MainMenu, footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent !important; }
.block-container { padding-top: 1rem; max-width: 880px; }
</style>
""", unsafe_allow_html=True)

# Hero
st.markdown("""
<div class="hero">
    <h1>AgroSense</h1>
    <p><h4>Crop Recommendation &rarr; Fertilizer Recommendation</h4></p>
</div>
""", unsafe_allow_html=True)

tab_options = ["Step 1 · Crop Recommendation", "Step 2 · Fertilizer Recommendation"]
mode = st.radio("Navigation", tab_options, label_visibility="collapsed")
st.markdown("<hr>", unsafe_allow_html=True)

is_step_1 = (mode == tab_options[0])

# ─────────────────────────────────────────────────────────────
# STEP 1 — CROP RECOMMENDATION
# ─────────────────────────────────────────────────────────────

if is_step_1:
    st.markdown('<div class="sec-label">Soil Nutrients <span class="badge">Manual entry</span></div>', unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
    with c1:
        N = st.number_input("Nitrogen (N) kg/ha", 0.0, 300.0, 0.0, 1.0, key="N")
    with c2:
        P = st.number_input("Phosphorus (P) kg/ha", 0.0, 300.0, 0.0, 1.0, key="P")
    with c3:
        K = st.number_input("Potassium (K) kg/ha", 0.0, 300.0, 0.0, 1.0, key="K")

    st.markdown('<div class="sec-label">Rainfall <span class="badge">Manual / Open-Meteo · Pokhara</span></div>', unsafe_allow_html=True)

    rf1, rf2 = st.columns([1, 3])
    with rf1:
        st.markdown("<div style='margin-top: 1.8rem;'></div>", unsafe_allow_html=True)
        if st.button("Fetch Live Rainfall", use_container_width=True):
            with st.spinner("Fetching current precipitation for Pokhara..."):
                value = fetch_live_rainfall()
                if value is not None:
                    st.session_state.live_rainfall = value
                    st.toast("Rainfall synchronized.")
                    st.rerun()
    with rf2:
        st.session_state.live_rainfall = st.number_input(
            "Current precipitation (mm)",
            min_value=0.0,
            max_value=1000.0,
            value=float(st.session_state.live_rainfall),
            step=1.0,
            help="Enter manually or use the Fetch button",
        )
        rainfall = st.session_state.live_rainfall

    st.markdown(
        '<div class="sec-label">'
        'Sensor Readings '
        '<span class="badge">DHT22 · Moisture</span> '
        '<span class="badge-lock">Sensor-read only</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    if st.button("Fetch Live Sensor Data", use_container_width=True):
        with st.spinner("Requesting real-time climate metrics from ESP32 via Flask..."):
            sensor_data = fetch_sensor_data_from_flask(flask_api_url)
            if sensor_data:
                st.session_state.live_temp     = sensor_data["temperature"]
                st.session_state.live_humidity = sensor_data["humidity"]
                st.session_state.live_moisture = sensor_data.get(
                    "soil_moisture",
                    st.session_state.live_moisture,
                )
                ts = sensor_data.get("timestamp", "")
                st.toast(f"Sensor data synced. Last push: {ts}")
                st.rerun()
            else:
                st.error("No data response received. Make sure the ESP32 is powered on and connected to WiFi.")

    temperature     = st.session_state.live_temp
    humidity        = st.session_state.live_humidity
    moisture_sensor = st.session_state.live_moisture

    cs1, cs2, cs3, cs4 = st.columns(4)
    with cs1:
        st.markdown(
            f'<div class="locked-field">'
            f'<div class="lf-label">Temperature</div>'
            f'<div class="lf-value">{temperature}<span class="lf-unit">°C</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cs2:
        st.markdown(
            f'<div class="locked-field">'
            f'<div class="lf-label">Humidity</div>'
            f'<div class="lf-value">{humidity}<span class="lf-unit">%</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cs3:
        st.markdown(
            f'<div class="locked-field">'
            f'<div class="lf-label">Soil Moisture</div>'
            f'<div class="lf-value">{moisture_sensor}<span class="lf-unit">%</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with cs4:
        ph = st.number_input(
            "Soil pH (manual entry)", 0.0, 14.0, 0.0, 0.01,
            help="No pH sensor connected yet — enter the reading manually",
        )

    st.markdown("<br>", unsafe_allow_html=True)
    do_crop = st.button("Run Crop Recommendation")

    if do_crop:
        try:
            resp = requests.post(f"{flask_api_url}/predict/crop", json={
                "N": N, "P": P, "K": K,
                "temperature": temperature, "humidity": humidity,
                "ph": ph, "rainfall": rainfall,
            }, timeout=8)
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach Flask API: {e}")
            st.stop()

        crop       = result["crop"]
        confidence = result["confidence"]
        top3       = result["top3"]

        st.session_state.crop_result     = crop
        st.session_state.crop_confidence = confidence
        st.session_state.crop_top3       = top3

        st.session_state.chain = {
            "N": N, "P": P, "K": K, "rainfall": rainfall,
            "temperature": temperature, "humidity": humidity,
            "ph": ph,
            "moisture": moisture_sensor,
        }

        st.markdown(f"""
        <div class="result-box">
            <div class="result-label">Recommended Crop</div>
            <div class="result-value">{crop.title()}</div>
        </div>
        """, unsafe_allow_html=True)

    elif st.session_state.crop_result:
        crop = st.session_state.crop_result
        st.markdown(f"""
        <div class="result-box">
            <div class="result-label">Last Recommended Crop</div>
            <div class="result-value">{crop.title()}</div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────
# STEP 2 — FERTILIZER RECOMMENDATION
# ─────────────────────────────────────────────────────────────

else:
    ch = st.session_state.chain

    # Guard: Step 1 must be completed first
    if ch is None:
        st.markdown(
            '<div class="warn-box">⚠️ Complete Step 1 first — run a Crop Recommendation before proceeding.</div>',
            unsafe_allow_html=True,
        )
        st.stop()

    crop_name  = st.session_state.crop_result
    crop_title = crop_name.title()
    matched_crop = crop_title if crop_title in CROP_TYPES else (
        next((ct for ct in CROP_TYPES if ct.lower() == crop_name.lower()), CROP_TYPES[0])
    )

    st.markdown('<div class="sec-label">Predicted Crop <span class="badge-lock">Locked</span></div>', unsafe_allow_html=True)
    st.markdown(
        f'<div class="locked-crop">'
        f'<div><div class="lc-label">Crop</div><div class="lc-value">{crop_title}</div></div>'
        f'</div>',
        unsafe_allow_html=True,
    )

    st.markdown('<div class="sec-label">Soil Nutrients & Rainfall <span class="badge-lock">Locked</span></div>', unsafe_allow_html=True)
    lc1, lc2, lc3, lc4 = st.columns(4)

    def locked(col, label, value, unit):
        with col:
            st.markdown(
                f'<div class="locked-field">'
                f'<div class="lf-label">{label}</div>'
                f'<div class="lf-value">{value}<span class="lf-unit">{unit}</span></div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    locked(lc1, "Nitrogen (N)",   ch["N"],        "kg/ha")
    locked(lc2, "Phosphorus (P)", ch["P"],        "kg/ha")
    locked(lc3, "Potassium (K)",  ch["K"],        "kg/ha")
    locked(lc4, "Rainfall",       ch["rainfall"], "mm")

    st.markdown(
        '<div class="sec-label">'
        'Soil Moisture '
        '<span class="badge">Sensor-read</span> '
        '<span class="badge-lock">From Step 1</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    sm1, sm2 = st.columns([2, 2])
    with sm1:
        st.markdown(
            f'<div class="locked-field">'
            f'<div class="lf-label">Soil Moisture (sensor)</div>'
            f'<div class="lf-value">{ch["moisture"]}<span class="lf-unit">%</span></div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    with sm2:
        moisture_override = st.number_input(
            "Override (if needed)",
            min_value=0.0, max_value=100.0,
            value=float(ch["moisture"]),
            step=0.1,
            help="Defaults to the live sensor reading. Change only if you want to override.",
            key="moisture_override",
        )

    final_moisture = moisture_override

    st.markdown('<div class="sec-label">Soil Type <span class="badge">Manual input</span></div>', unsafe_allow_html=True)
    soil_type = st.selectbox("Select Soil Type", SOIL_TYPES)

    st.markdown("<br>", unsafe_allow_html=True)
    do_fert = st.button("Run Fertilizer Recommendation")

    if do_fert:
        try:
            resp = requests.post(f"{flask_api_url}/predict/fertilizer", json={
                "N": ch["N"], "P": ch["P"], "K": ch["K"],
                "ph": ch["ph"], "moisture": final_moisture,
                "temperature": ch["temperature"], "humidity": ch["humidity"],
                "rainfall": ch["rainfall"],
                "soil_type": soil_type, "crop_type": matched_crop,
            }, timeout=8)
            resp.raise_for_status()
            result = resp.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Could not reach Flask API: {e}")
            st.stop()

        fertilizer = result["fertilizer"]

        if lcd_enabled and esp32_url:
            sent = update_lcd(esp32_url, f"Crop: {crop_title}", f"Fert: {fertilizer}")
            if sent:
                st.toast("Sent to LCD.")

        st.markdown(f"""
        <div class="result-box">
            <div class="result-label">Recommended Fertilizer</div>
            <div class="result-value">{fertilizer}</div>
        </div>
        """, unsafe_allow_html=True)

# Footer
st.markdown("<br><hr>", unsafe_allow_html=True)
st.markdown('<p style="text-align:center;color:#2A4230;font-size:0.76rem;padding-bottom:1rem;">AgroSense · Chain Inference Pipeline</p>', unsafe_allow_html=True)




