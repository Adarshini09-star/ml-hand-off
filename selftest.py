import sys, glob, numpy as np, pandas as pd
sys.path.insert(0, "."); from predict_lstm import *
folder = sys.argv[1]
pkg = load_package(folder)
t = pd.read_csv(sys.argv[2]) if len(sys.argv) > 2 else None
base = pd.DataFrame({"Timestamp": pd.date_range("2018-02-15 09:00", periods=5, freq="min"),
    "Bot_Pct": [30, 32, 35, 33, 31.0], "Total_Flows": [5000]*5, "Fwd_Pkts_Bot": [2e4]*5, "Bwd_Pkts_Bot": [1e4]*5,
    "Fwd_Bytes_Bot": [1e6]*5, "Bwd_Bytes_Bot": [5e5]*5, "Avg_Duration_Bot": [1e6]*5})
print(predict_next_minute(pkg, base))
def expect(code, w):
    try: predict_next_minute(pkg, w); print("FAIL: no error for", code)
    except InputValidationError as e: assert e.code == code, e.code; print("PASS error:", e)
g = base.copy(); g.loc[3:, "Timestamp"] += pd.Timedelta(minutes=207); expect("NOT_CONSECUTIVE", g)
expect("MISSING_FEATURES", base.drop(columns=["Total_Flows"]))
expect("BAD_SHAPE", base.iloc[:4]); n = base.copy(); n.loc[2, "Bot_Pct"] = np.nan; expect("NAN_OR_INF", n)
n = base.copy(); n.loc[0, "Bot_Pct"] = 120; expect("BOT_PCT_RANGE", n)
shuffled = base[["Timestamp"] + FEATURES[::-1]]   # columns reordered: must still give the same answer (selected by name)
assert predict_next_minute(pkg, shuffled)["predicted_bot_pct_next_minute"] == predict_next_minute(pkg, base)["predicted_bot_pct_next_minute"]; print("PASS column-order independence")
for v in [9.9, 24.9, 25.0, 49.9, 50.0]: print(v, state_from_pct(v))
