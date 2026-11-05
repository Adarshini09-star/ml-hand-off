# SIH26153 - ML Integration Contract (Member 2 -> Member 3)

**Status: PROVISIONAL. Offline/batch forecasting only. Not a live, real-time or production-validated system.**
Package: `phase4_lstm_REGEN_v1_<date_time>.zip` (regenerated copy of the frozen Phase 4 LSTM; reproduces saved test metrics to 1e-3; not byte-identical to the lost original zip).
**Verified hand-off package: `phase4_lstm_REGEN_v1_20261101_0503.zip`** - `REAL1_cell.py` printed `OVERALL: ALL PASS (5/5 checks)` on this exact zip in Colab (manifest hashes, self-test, replay of all 102 real test windows within 5e-5 percentage points). Two earlier regenerations (`..._20261021_1523`, and the 2026-10-15 one) gave bit-identical predictions, so any of them behaves the same; use 0503.

## 1. What the model does
Given the **last 5 consecutive 1-minute rows** of traffic features, it forecasts the **bot-traffic percentage of the next minute**, `Bot_Pct(t+1)` (0-100), and maps it to a state:

| State  | Bot_Pct(t+1) |
|--------|--------------|
| Low    | < 25         |
| Medium | 25 to < 50   |
| High   | >= 50        |

It forecasts a **traffic state**. It does not detect or prove individual attacks, and was tested on a single day of CSE-CIC-IDS2018 (102 targets).

## 2. Files you receive
`lstm_primary_seed_42..46.keras` (5 models), `scaler_features.joblib`, `scaler_target.joblib`, `config.json`, `test_predictions_lstm_regen.csv`, `seed_metrics_lstm_regen.csv`, `MANIFEST_sha256.txt`, `README.md`, plus `predict_lstm.py` (reference loader/validator).
Check `MANIFEST_sha256.txt` after unzipping. Requires **Python 3.13, TensorFlow/Keras 2.21.0, scikit-learn 1.6.1, numpy 2.1.3, pandas 2.2.3** (also recorded in `config.json -> environment`). Use these versions: the scalers were pickled with scikit-learn 1.6.1 and other versions only warn, so check results if you must differ.

## 3. Input contract
- Exactly **5 rows x 7 features**, **consecutive minutes (exactly 60 s apart)**, in raw units (do NOT pre-scale).
- Columns (select by name; order is applied by the module): `Bot_Pct, Total_Flows, Fwd_Pkts_Bot, Bwd_Pkts_Bot, Fwd_Bytes_Bot, Bwd_Bytes_Bot, Avg_Duration_Bot`
- Optional `Timestamp` column: if present it is checked for 60 s spacing.
- Windows must never span a data gap (the training data has a 207-minute gap, 05:29 -> 08:56, never crossed).

## 4. Processing pipeline (what `predict_lstm.py` does)
1. Validate window. 2. `scaler_features.transform` (fitted on training rows only). 3. Each of 5 seed models predicts. 4. `scaler_target.inverse_transform` each output. 5. Final value = **mean of the 5 seeds**, clipped to 0-100. 6. State from thresholds above.

## 5. Output schema (JSON-serialisable dict)
```json
{
  "forecast_horizon_minutes": 1,
  "predicted_bot_pct_next_minute": 30.17,
  "predicted_state": "Medium",
  "state_thresholds": {"Low": "<25", "Medium": "25-<50", "High": ">=50"},
  "seed_predictions": {"42": 37.16, "43": 27.68, "44": 17.43, "45": 37.72, "46": 30.86},
  "seed_spread_pct_points": 20.29,
  "model_version": "phase4_lstm_REGEN_v1",
  "model_status": "PROVISIONAL",
  "warnings": ["..."]
}
```
(Values above are illustrative of the schema only; they come from a 2-epoch test model, NOT the real one.)

## 6. Error contract
`InputValidationError` with `.code`: `MISSING_FEATURES`, `BAD_SHAPE`, `NAN_OR_INF`, `NEGATIVE_VALUE`, `BOT_PCT_RANGE`, `BAD_TIMESTAMP`, `NOT_CONSECUTIVE`. Treat any of these as "no forecast available" - never fill gaps silently.

## 7. Evidence and limitations (report these; do not hide them)
- Test (L=5, 5 seeds, mean +/- sample std): MAE 6.9694, RMSE 8.5978, R2 0.6062; ensemble 6.9211 / 8.4283 / 0.6216. Persistence baseline: 9.3123 / 11.6736 / 0.2741.
- **Low-state recall is ~0% on the test day** (all 23 Low targets predicted Medium); persistence got 17.39%. Do not present "Medium" as safe.
- The state rule has a shift between validation and test days; one test day only.
- Target at 12:59 (row 502) is retained but its provenance is unverified.
- Model comparison (valid, same 102 test targets, same +1-minute horizon, same 7 features): the earlier GRU screening grid was excluded because of incorrect (2-minute-ahead) alignment; GRU-V2 replaced it. By the pre-declared rule GRU-V2 is **comparable to the LSTM, no demonstrated advantage** (ensemble RMSE 8.2242 vs 8.4283; paired bootstrap interval includes 0). A validation-selected Random Forest (window L=5) scores MAE 7.2718 / RMSE 8.7015 / R2 0.5967; persistence 9.3123 / 11.6736 / 0.2741. Differences among the learned models are small relative to seed and test-day noise. Details: `comparison_VALID_v1_20261101_0505.zip`.
- The LSTM remains the provisional integration model. This integration does not depend on any further GRU work.
- Any UI/doc wording must say "forecast / estimate", never "live", "real-time" or "production-ready".

## 8. Mock mode (if you cannot load the package yet)
Return the schema in section 5 with `"model_status": "MOCK"`, `"model_version": "mock"`, and a visible banner. Mock values must not be shown as real forecasts.

## 9. Minimal example
```python
from predict_lstm import load_package, predict_next_minute
pkg = load_package("phase4_lstm_REGEN_v1_<date_time>")
print(predict_next_minute(pkg, window_df))   # window_df = 5 consecutive 1-minute rows
```
Sanity test: run `python selftest.py <package_folder>` (included); all error cases and the column-order check must print PASS.
