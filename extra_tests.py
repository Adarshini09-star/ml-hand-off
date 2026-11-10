r"""Extra validation tests for predict_lstm.py (covers the 2 error codes selftest.py skips).
Run from ml_module:  ..\.venv\Scripts\python.exe .\extra_tests.py
Does NOT load TensorFlow or the models: it tests validate_window() only, so it is fast."""
import sys
import numpy as np, pandas as pd
sys.path.insert(0, ".")
from predict_lstm import validate_window, state_from_pct, FEATURES, InputValidationError

base = pd.DataFrame({"Timestamp": pd.date_range("2018-02-15 09:00", periods=5, freq="min"),
    "Bot_Pct": [30, 32, 35, 33, 31.0], "Total_Flows": [5000]*5, "Fwd_Pkts_Bot": [2e4]*5, "Bwd_Pkts_Bot": [1e4]*5,
    "Fwd_Bytes_Bot": [1e6]*5, "Bwd_Bytes_Bot": [5e5]*5, "Avg_Duration_Bot": [1e6]*5})

results = []
def check(name, ok):
    results.append(ok); print(("PASS " if ok else "FAIL ") + name)

def expect(name, code, w):
    try:
        validate_window(w); check(f"{name}: expected {code}, got no error", False)
    except InputValidationError as e:
        check(f"{name} -> {code}" + ("" if e.code == code else f" (got {e.code})"), e.code == code)

# --- the two codes selftest.py never exercises ---
n = base.copy(); n.loc[1, "Total_Flows"] = -1;            expect("negative Total_Flows", "NEGATIVE_VALUE", n)
n = base.copy(); n.loc[0, "Bot_Pct"] = -5;                expect("negative Bot_Pct", "NEGATIVE_VALUE", n)
n = base.copy(); n["Timestamp"] = ["bad", "x", "y", "z", "w"]; expect("unparseable Timestamp", "BAD_TIMESTAMP", n)
n = base.copy(); n["Timestamp"] = n["Timestamp"].astype(object); n.loc[2, "Timestamp"] = None
expect("missing (None) Timestamp", "BAD_TIMESTAMP", n)

# --- extra edge cases ---
n = base.copy(); n.loc[4, "Fwd_Bytes_Bot"] = np.inf;      expect("infinite value", "NAN_OR_INF", n)
n = base.copy(); n.loc[0, "Bot_Pct"] = 100.01;            expect("Bot_Pct just over 100", "BOT_PCT_RANGE", n)
n = base.copy(); n["Timestamp"] = n["Timestamp"].iloc[::-1].values; expect("reversed timestamps", "NOT_CONSECUTIVE", n)
n = base.copy(); n.loc[4, "Timestamp"] = n.loc[3, "Timestamp"]; expect("duplicate timestamp", "NOT_CONSECUTIVE", n)
expect("6 rows", "BAD_SHAPE", pd.concat([base, base.iloc[[4]]]).assign(
    Timestamp=pd.date_range("2018-02-15 09:00", periods=6, freq="min")))
expect("raw array wrong shape", "BAD_SHAPE", np.ones((5, 6)))
expect("NaN in Bot_Pct", "NAN_OR_INF", base.assign(Bot_Pct=[30, 32, np.nan, 33, 31.0]))

# --- inputs that must be ACCEPTED ---
for name, w in [("valid window", base),
                ("Bot_Pct exactly 0 and 100", base.assign(Bot_Pct=[0, 100, 0, 100, 50.0])),
                ("all zeros (valid, non-negative)", base.assign(**{c: 0.0 for c in FEATURES}))]:
    try:
        arr, warns = validate_window(w); check(f"accepts {name}; shape {arr.shape}", arr.shape == (5, 7))
    except InputValidationError as e:
        check(f"accepts {name} (rejected with {e.code})", False)

# no Timestamp column -> allowed, but must warn
arr, warns = validate_window(base.drop(columns=["Timestamp"]))
check("no Timestamp column -> accepted with warning", any("No Timestamp" in x for x in warns))
# raw numpy array -> allowed, but must warn
arr, warns = validate_window(base[FEATURES].to_numpy())
check("raw array -> accepted with warning", any("Raw array" in x for x in warns))

# state thresholds at the edges
check("thresholds 0/24.999/25/49.999/50/100",
      [state_from_pct(v) for v in [0, 24.999, 25, 49.999, 50, 100]] == ["Low","Low","Medium","Medium","High","High"])

print(f"\n{sum(results)}/{len(results)} passed")
print("ALL PASS" if all(results) else "SOME FAILED - see FAIL lines above")
sys.exit(0 if all(results) else 1)
