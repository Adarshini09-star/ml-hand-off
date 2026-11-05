"""
SIH26153 - ML inference module for the PROVISIONAL Phase 4 LSTM (package: phase4_lstm_REGEN_v1_*).
Offline / batch use only. This is NOT a live or production-validated system.

Usage:
    from predict_lstm import load_package, predict_next_minute
    pkg = load_package("phase4_lstm_REGEN_v1_20261015_1406")
    out = predict_next_minute(pkg, window_df)     # window_df: 5 CONSECUTIVE 1-minute rows
"""
import os, json
import numpy as np, pandas as pd, joblib

FEATURES = ["Bot_Pct", "Total_Flows", "Fwd_Pkts_Bot", "Bwd_Pkts_Bot", "Fwd_Bytes_Bot", "Bwd_Bytes_Bot", "Avg_Duration_Bot"]
L = 5
SEEDS = [42, 43, 44, 45, 46]

class InputValidationError(ValueError):
    """Raised with a machine-readable .code and a human-readable message."""
    def __init__(self, code, message):
        super().__init__(f"[{code}] {message}"); self.code = code

def state_from_pct(x):
    """Low < 25 <= Medium < 50 <= High (percent)."""
    return "Low" if x < 25 else ("Medium" if x < 50 else "High")

def load_package(folder):
    from tensorflow.keras.models import load_model   # imported lazily so the validator can be tested without TF
    cfg = json.load(open(os.path.join(folder, "config.json")))
    assert cfg["features_in_order"] == FEATURES, "package feature order differs from this module"
    assert cfg["model"]["sequence_length"] == L
    sx = joblib.load(os.path.join(folder, "scaler_features.joblib"))
    sy = joblib.load(os.path.join(folder, "scaler_target.joblib"))
    assert np.allclose(sx.mean_, cfg["scaler_features"]["mean"]) and np.allclose(sy.mean_, cfg["scaler_target"]["mean"]), "scaler/config mismatch"
    models = {s: load_model(os.path.join(folder, f"lstm_primary_seed_{s}.keras")) for s in SEEDS}
    return {"cfg": cfg, "sx": sx, "sy": sy, "models": models, "folder": folder}

def validate_window(window):
    """Returns (X_raw float array (5,7), warnings). Raises InputValidationError on anything unsafe."""
    warnings = []
    if isinstance(window, pd.DataFrame):
        missing = [c for c in FEATURES if c not in window.columns]
        if missing: raise InputValidationError("MISSING_FEATURES", f"missing columns: {missing}")
        if "Timestamp" in window.columns:
            ts = pd.to_datetime(window["Timestamp"], errors="coerce")
            if ts.isna().any(): raise InputValidationError("BAD_TIMESTAMP", "unparseable Timestamp")
            d = ts.diff().dropna().dt.total_seconds().values
            if not np.all(d == 60):
                raise InputValidationError("NOT_CONSECUTIVE", f"rows must be exactly 60 s apart; got gaps {sorted(set(d.tolist()))}")
        else:
            warnings.append("No Timestamp column: consecutive 1-minute spacing could not be checked.")
        arr = window[FEATURES].to_numpy(dtype=float)
    else:
        arr = np.asarray(window, dtype=float)
        warnings.append("Raw array given: assumed columns are in FEATURES order and rows are consecutive minutes.")
    if arr.shape != (L, len(FEATURES)):
        raise InputValidationError("BAD_SHAPE", f"expected {(L, len(FEATURES))}, got {arr.shape}")
    if not np.isfinite(arr).all(): raise InputValidationError("NAN_OR_INF", "window contains NaN/inf")
    if (arr < 0).any(): raise InputValidationError("NEGATIVE_VALUE", "negative values are not valid for these features")
    if (arr[:, 0] > 100).any(): raise InputValidationError("BOT_PCT_RANGE", "Bot_Pct must be within 0-100")
    return arr, warnings

def predict_next_minute(pkg, window):
    arr, warnings = validate_window(window)
    Xs = pkg["sx"].transform(arr).reshape(1, L, len(FEATURES))
    seed_preds = {s: float(pkg["sy"].inverse_transform(m.predict(Xs, verbose=0).reshape(-1, 1))[0, 0]) for s, m in pkg["models"].items()}
    raw = float(np.mean(list(seed_preds.values())))
    pct = float(np.clip(raw, 0.0, 100.0))
    if raw != pct: warnings.append(f"Raw ensemble output {raw:.3f} was clipped to the valid 0-100 range.")
    return {
        "forecast_horizon_minutes": 1,
        "predicted_bot_pct_next_minute": round(pct, 4),
        "predicted_state": state_from_pct(pct),
        "state_thresholds": {"Low": "<25", "Medium": "25-<50", "High": ">=50"},
        "seed_predictions": {str(k): round(v, 4) for k, v in seed_preds.items()},
        "seed_spread_pct_points": round(float(np.ptp(list(seed_preds.values()))), 4),
        "model_version": pkg["cfg"]["artifact_version"],
        "model_status": "PROVISIONAL",
        "warnings": warnings + ["Low-state recall was ~0% on the test day; a 'Medium' output does not rule out Low."],
    }
