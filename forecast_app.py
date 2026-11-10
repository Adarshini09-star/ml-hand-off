r"""Bot-traffic forecast demo (Streamlit). Uses the verified predict_lstm.py module.
Run from ml_module:  ..\.venv\Scripts\python.exe -m streamlit run forecast_app.py"""
import os, sys, warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pandas as pd
import streamlit as st
from predict_lstm import load_package, predict_next_minute, InputValidationError, FEATURES

MODEL_DIR = os.path.join(HERE, "phase4_lstm_REGEN_v1_20261101_0503")

st.set_page_config(page_title="Bot Traffic Forecast", page_icon="📈", layout="centered")
st.title("📈 Bot Traffic Forecast")
st.caption("LSTM ensemble (5 models) · predicts the bot-traffic share for the NEXT minute from the last 5 minutes")
st.warning("Model status: PROVISIONAL. Treat the Low/Medium/High label as an estimate, not a guarantee.")

@st.cache_resource(show_spinner="Loading models...")
def get_pkg():
    return load_package(MODEL_DIR)

def make(bot, flows, fp, bp, fb, bb, dur):
    return pd.DataFrame({"Bot_Pct": bot, "Total_Flows": [float(flows)]*5, "Fwd_Pkts_Bot": [float(fp)]*5,
        "Bwd_Pkts_Bot": [float(bp)]*5, "Fwd_Bytes_Bot": [float(fb)]*5, "Bwd_Bytes_Bot": [float(bb)]*5,
        "Avg_Duration_Bot": [float(dur)]*5})[FEATURES]

PRESETS = {
    "Quiet traffic": make([3, 4, 2, 3, 4.0], 400, 200, 150, 10000, 5000, 5000),
    "Typical traffic (training average)": make([18, 19, 17, 18, 18.0], 1825, 1100, 850, 65000, 30000, 23000),
    "Busy traffic": make([45, 50, 55, 52, 56.0], 3000, 2500, 2000, 150000, 80000, 60000),
    "Out-of-range test (far above training data)": make([30, 32, 35, 33, 31.0], 5000, 2e4, 1e4, 1e6, 5e5, 1e6),
}

@st.cache_resource
def get_scaler():
    import joblib
    return joblib.load(os.path.join(MODEL_DIR, "scaler_features.joblib"))

mode = st.radio("Input", ["Type the 5 minutes in a table", "Upload a CSV file"], horizontal=True)
window = None

if mode.startswith("Type"):
    preset = st.selectbox("Start from an example (you can edit the numbers afterwards)", list(PRESETS))
    st.write("Edit the 5 rows (oldest at top, newest at bottom). One row = one minute.")
    edited = st.data_editor(PRESETS[preset], num_rows="fixed", width="stretch", key="editor_" + preset)
    ts = pd.date_range(end=pd.Timestamp.now().floor("min"), periods=5, freq="min")
    window = edited.copy()
    window.insert(0, "Timestamp", ts)
else:
    st.write("CSV columns needed: Timestamp, " + ", ".join(FEATURES) + ". The LAST 5 rows are used.")
    up = st.file_uploader("CSV file", type="csv")
    if up is not None:
        try:
            window = pd.read_csv(up).tail(5).reset_index(drop=True)
            st.dataframe(window, width="stretch")
        except Exception as e:
            st.error(f"Could not read the CSV: {e}")

if st.button("Predict next minute", type="primary", disabled=window is None):
    try:
        sc = get_scaler()
        z = ((window[FEATURES].astype(float).values - sc.mean_) / sc.scale_)
        far = [f for f, m in zip(FEATURES, abs(z).max(axis=0)) if m > 5]
        if far:
            st.warning("These inputs are far outside the data the model was trained on, so the forecast is "
                       "unreliable: " + ", ".join(far))
    except Exception:
        pass
    try:
        res = predict_next_minute(get_pkg(), window)
    except InputValidationError as e:
        st.error(f"Input problem: {e}")
    else:
        pct, state = res["predicted_bot_pct_next_minute"], res["predicted_state"]
        c1, c2 = st.columns(2)
        c1.metric("Predicted bot traffic (next minute)", f"{pct:.1f} %")
        c2.metric("State", state)
        {"Low": st.success, "Medium": st.warning, "High": st.error}[state](
            f"Predicted state: {state}  (Low <25%, Medium 25-<50%, High >=50%)")
        st.subheader("What each of the 5 models predicted")
        st.bar_chart(pd.Series(res["seed_predictions"], name="Predicted %"))
        st.write(f"The models disagree by {res['seed_spread_pct_points']:.1f} percentage points "
                 "(a large gap means low confidence).")
        for w in res["warnings"]:
            st.warning(w)
        with st.expander("Full raw output"):
            st.json(res)
