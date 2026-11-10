r"""Demo: read a CSV of per-minute traffic, take the LAST 5 rows, print the forecast.
Run from ml_module:  ..\.venv\Scripts\python.exe .\run_demo.py
Optional:            ..\.venv\Scripts\python.exe .\run_demo.py my_data.csv
CSV needs columns: Timestamp, Bot_Pct, Total_Flows, Fwd_Pkts_Bot, Bwd_Pkts_Bot,
                   Fwd_Bytes_Bot, Bwd_Bytes_Bot, Avg_Duration_Bot  (1 row per minute)"""
import os, sys, warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
warnings.filterwarnings("ignore")
import pandas as pd
sys.path.insert(0, ".")
from predict_lstm import load_package, predict_next_minute, InputValidationError

MODEL_DIR = "phase4_lstm_REGEN_v1_20261101_0503"
csv_path = sys.argv[1] if len(sys.argv) > 1 else "sample_window.csv"

if not os.path.exists(csv_path):
    if len(sys.argv) > 1:
        sys.exit(f"File not found: {csv_path}")
    pd.DataFrame({
        "Timestamp": pd.date_range("2018-02-15 09:00", periods=5, freq="min"),
        "Bot_Pct": [30, 32, 35, 33, 31.0], "Total_Flows": [5000]*5,
        "Fwd_Pkts_Bot": [2e4]*5, "Bwd_Pkts_Bot": [1e4]*5,
        "Fwd_Bytes_Bot": [1e6]*5, "Bwd_Bytes_Bot": [5e5]*5, "Avg_Duration_Bot": [1e6]*5,
    }).to_csv(csv_path, index=False)
    print(f"Created sample file: {csv_path}")

df = pd.read_csv(csv_path)
window = df.tail(5).reset_index(drop=True)
print(f"Using the last 5 rows of {csv_path}:")
print(window.to_string(index=False))

try:
    result = predict_next_minute(load_package(MODEL_DIR), window)
except InputValidationError as e:
    sys.exit(f"\nINPUT PROBLEM: {e}")

print("\n=== FORECAST FOR NEXT MINUTE ===")
print(f"Predicted bot traffic : {result['predicted_bot_pct_next_minute']} %")
print(f"State                 : {result['predicted_state']}   (Low <25, Medium 25-<50, High >=50)")
print(f"Seed disagreement     : {result['seed_spread_pct_points']} percentage points")
print(f"Model status          : {result['model_status']}")
for w in result["warnings"]:
    print("WARNING:", w)
