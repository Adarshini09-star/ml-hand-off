# SIH26153 — Integration Tests and Verification Suite
**AI-Based Network Attack Forecasting from Network Traffic Data**
*Author: Team Member 3 (Architecture & Backend Integration)*
*Date: 2026-11-14 | Branch: member3-architecture*

---

> [!IMPORTANT]
> **Audit Status & Scope**:
> - This document distinguishes **Executed & Verified Tests** (run directly on Windows 11 with Python 3.13.2) from **Proposed Tests** (planned for the backend API and end-to-end integration).
> - **Scope Caveats**:
>   - `extra_tests.py` verifies the input validation logic (`validate_window()`) only; it does not load TensorFlow models.
>   - Replay of the 102 real holdout test windows was performed in Google Colab; local reproduction is currently blocked because input feature windows for test parquet are not in this repository.
>   - All tests operate in **offline/batch mode**.

---

## Table of Contents

1. [Executive Summary: Test Matrix](#1-executive-summary-test-matrix)
2. [Executed Tests (Verified on Local Windows Machine)](#2-executed-tests-verified-on-local-windows-machine)
   - [2.1 Test Suite 1: Model Package Hash Verification](#21-test-suite-1-model-package-hash-verification)
   - [2.2 Test Suite 2: Core Self-Test (`selftest.py`)](#22-test-suite-2-core-self-test-selftestpy)
   - [2.3 Test Suite 3: Extended Input Validation (`extra_tests.py`)](#23-test-suite-3-extended-input-validation-extra_testspy)
   - [2.4 Test Suite 4: Command-Line Demo (`run_demo.py`)](#24-test-suite-4-command-line-demo-rundemopy)
   - [2.5 Test Suite 5: Interactive UI Prototype (`forecast_app.py`)](#25-test-suite-5-interactive-ui-prototype-forecast_apppy)
3. [Proposed Tests (For Backend API & End-to-End System)](#3-proposed-tests-for-backend-api--end-to-end-system)
   - [3.1 API Health & Mock Mode Test](#31-api-health--mock-mode-test)
   - [3.2 API Prediction Contract Test (Valid Payload)](#32-api-prediction-contract-test-valid-payload)
   - [3.3 API Error Handling Suite (7 Error Codes)](#33-api-error-handling-suite-7-error-codes)
   - [3.4 API Latency & Concurrency Benchmark](#34-api-latency--concurrency-benchmark)
   - [3.5 102 Holdout Test Target Local Replay (Blocked)](#35-102-holdout-test-target-local-replay-blocked)
4. [Reproduction Guide for Team Members](#4-reproduction-guide-for-team-members)

---

## 1. Executive Summary: Test Matrix

| ID | Test Target | Suite / File | Status | What is Verified |
|---|---|---|---|---|
| **T01** | Package Integrity | `MANIFEST_sha256.txt` | ✅ **EXECUTED** | 11/11 SHA-256 hashes match bit-for-bit |
| **T02** | Core ML Pipeline | `selftest.py` | ✅ **EXECUTED** | Model loading, inference, 5 error codes, column invariance, thresholds |
| **T03** | Validation Robustness | `extra_tests.py` | ✅ **EXECUTED** | 17/17 PASS: covers `NEGATIVE_VALUE`, `BAD_TIMESTAMP`, inf, edge bounds |
| **T04** | CLI Pipeline | `run_demo.py` | ✅ **EXECUTED** | End-to-end CSV ingestion -> inference -> terminal report |
| **T05** | UI & Range Warnings | `forecast_app.py` | ✅ **EXECUTED** | Streamlit UI, 4 traffic presets, out-of-range z-score warning |
| **T06** | Backend Health Endpoint | `GET /health` | 🔲 **PROPOSED** | Verify startup state (`PROVISIONAL` vs `MOCK`) |
| **T07** | Backend Predict Endpoint | `POST /predict` | 🔲 **PROPOSED** | HTTP 200 JSON contract with full 9-field schema |
| **T08** | Backend HTTP Error Codes | `POST /predict` (bad) | 🔲 **PROPOSED** | HTTP 422 returned with machine-readable `error_code` |
| **T09** | End-to-End Latency | Benchmark script | 🔲 **PROPOSED** | In-process inference latency < 100 ms on CPU |
| **T10** | 102 Test Window Replay | Replay script | ⚠️ **BLOCKED** | Needs test parquet input features from Member 1/2 |

---

## 2. Executed Tests (Verified on Local Windows Machine)

All tests in this section were executed on Windows 11 using Python 3.13.2 in the dedicated virtual environment (`C:\Users\ullas\sih26153-ml\.venv\Scripts\python.exe`).

### 2.1 Test Suite 1: Model Package Hash Verification

Verifies that model weights, scalers, and configuration files in `phase4_lstm_REGEN_v1_20261101_0503/` match the author's cryptographic checksums.

#### Command:
```powershell
cd "$HOME\member3-backend\phase4_lstm_REGEN_v1_20261101_0503"
Get-Content MANIFEST_sha256.txt | ForEach-Object {
    $h, $f = $_ -split '\s+', 2
    $actual = (Get-FileHash $f -Algorithm SHA256).Hash.ToLower()
    "{0,-9} {1}" -f $(if ($actual -eq $h) { "OK" } else { "MISMATCH" }), $f
}
```

#### Verified Result:
```
OK        README.md
OK        config.json
OK        lstm_primary_seed_42.keras
OK        lstm_primary_seed_43.keras
OK        lstm_primary_seed_44.keras
OK        lstm_primary_seed_45.keras
OK        lstm_primary_seed_46.keras
OK        scaler_features.joblib
OK        scaler_target.joblib
OK        seed_metrics_lstm_regen.csv
OK        test_predictions_lstm_regen.csv
```
**Verdict:** **11/11 OK (100% integrity verified)**.

---

### 2.2 Test Suite 2: Core Self-Test (`selftest.py`)

Verifies lazy model loading, seed ensemble forward pass, column ordering invariance, threshold mappings, and core validation error raising.

#### Command:
```powershell
cd "$HOME\member3-backend"
& "$HOME\sih26153-ml\.venv\Scripts\python.exe" .\selftest.py .\phase4_lstm_REGEN_v1_20261101_0503
```

#### Verified Output:
```
=== 1. PREDICTION ON SYNTHETIC WINDOW ===
{'forecast_horizon_minutes': 1,
 'model_status': 'PROVISIONAL',
 'model_version': 'phase4_lstm_REGEN_v1',
 'predicted_bot_pct_next_minute': 62.8012,
 'predicted_state': 'High',
 'seed_predictions': {'42': 57.5746, '43': 72.8194, '44': 67.2844, '45': 47.5746, '46': 68.753},
 'seed_spread_pct_points': 25.2448,
 'state_thresholds': {'High': '>=50', 'Low': '<25', 'Medium': '25-<50'},
 'warnings': ["Low-state recall was ~0% on the test day; a 'Medium' output does not rule out Low."]}

=== 2. ERROR CONTRACT CHECKS ===
PASS error: NOT_CONSECUTIVE
PASS error: MISSING_FEATURES
PASS error: BAD_SHAPE
PASS error: NAN_OR_INF
PASS error: BOT_PCT_RANGE

=== 3. COLUMN-ORDER INVARIANCE ===
PASS column-order independence

=== 4. STATE THRESHOLD SANITY ===
9.9 -> Low
24.9 -> Low
25.0 -> Medium
49.9 -> Medium
50.0 -> High
```
**Verdict:** **All Checks PASS**. Model predicts deterministically; column order can be shuffled without affecting predictions; edge thresholds accurately partition states.

---

### 2.3 Test Suite 3: Extended Input Validation (`extra_tests.py`)

Verifies the 2 error codes omitted by `selftest.py` (`NEGATIVE_VALUE`, `BAD_TIMESTAMP`), plus 15 additional edge cases.

#### Command:
```powershell
cd "$HOME\member3-backend"
& "$HOME\sih26153-ml\.venv\Scripts\python.exe" .\extra_tests.py
```

#### Verified Output:
```
PASS negative Total_Flows -> NEGATIVE_VALUE
PASS negative Bot_Pct -> NEGATIVE_VALUE
PASS unparseable Timestamp -> BAD_TIMESTAMP
PASS missing (None) Timestamp -> BAD_TIMESTAMP
PASS infinite value -> NAN_OR_INF
PASS Bot_Pct just over 100 -> BOT_PCT_RANGE
PASS reversed timestamps -> NOT_CONSECUTIVE
PASS duplicate timestamp -> NOT_CONSECUTIVE
PASS 6 rows -> BAD_SHAPE
PASS raw array wrong shape -> BAD_SHAPE
PASS NaN in Bot_Pct -> NAN_OR_INF
PASS accepts valid window; shape (5, 7)
PASS accepts Bot_Pct exactly 0 and 100; shape (5, 7)
PASS accepts all zeros (valid, non-negative); shape (5, 7)
PASS no Timestamp column -> accepted with warning
PASS raw array -> accepted with warning
PASS thresholds 0/24.999/25/49.999/50/100

17/17 passed
ALL PASS
```
**Verdict:** **17/17 PASS**. All 7 contract error codes (`MISSING_FEATURES`, `BAD_SHAPE`, `NAN_OR_INF`, `NEGATIVE_VALUE`, `BOT_PCT_RANGE`, `BAD_TIMESTAMP`, `NOT_CONSECUTIVE`) are explicitly tested and verified.

---

### 2.4 Test Suite 4: Command-Line Demo (`run_demo.py`)

Verifies standalone batch file processing: reading 5 rows from CSV and emitting formatted forecast metrics.

#### Command:
```powershell
cd "$HOME\member3-backend"
& "$HOME\sih26153-ml\.venv\Scripts\python.exe" .\run_demo.py
```

#### Verified Output:
```
=== FORECAST FOR NEXT MINUTE ===
Predicted bot traffic : 62.8012 %
State                 : High (Low <25, Medium 25-<50, High >=50)
Seed disagreement     : 25.2448 percentage points
Model status          : PROVISIONAL
WARNING: Low-state recall was ~0% on the test day; a 'Medium' output does not rule out Low.
```
**Verdict:** **PASS**. Confirms that `predict_lstm.py` can be seamlessly embedded into an external script.

---

### 2.5 Test Suite 5: Interactive UI Prototype (`forecast_app.py`)

Verifies realistic vs. unrealistic traffic scenarios and integration of the out-of-range z-score warning.

#### Command:
```powershell
cd "$HOME\member3-backend"
& "$HOME\sih26153-ml\.venv\Scripts\python.exe" -m streamlit run forecast_app.py
```

#### Verified Results Across Presets:
| Preset | Input Bot_Pct Profile | Forecast $\hat{y}$ | Predicted State | Seed Disagreement | Out-of-Range Warning Triggered? |
|---|---|---|---|---|---|
| **Quiet Traffic** | $2.0\% - 4.0\%$ | **3.40%** | **Low** | 1.40 pts | No |
| **Typical Traffic** | $17.0\% - 19.0\%$ | **19.10%** | **Low** | 4.00 pts | No |
| **Busy Traffic** | $45.0\% - 56.0\%$ | **44.40%** | **Medium** | 7.10 pts | No |
| **Out-of-Range Test** | $30.0\% - 35.0\%$ (pkts $20,000$) | **62.80%** | **High** | 25.20 pts | **Yes** (5 features flagged $|z| > 5$) |

**Verdict:** **PASS**. Confirms that under in-distribution inputs the ensemble behaves stably (spread $\le 4.0$ pts), and when exposed to out-of-distribution inputs, seed disagreement widens significantly and triggers the safety warning.

---

## 3. Proposed Tests (For Backend API & End-to-End System)

The following tests will be executed once the Backend API service (`api.py`) is deployed.

### 3.1 API Health & Mock Mode Test

Verifies that `GET /health` reports the operational status of the model.

#### Proposed Command:
```powershell
Invoke-RestMethod -Uri "http://localhost:8000/health" -Method GET
```

#### Expected Output (Normal Live Mode):
```json
{
  "status": "ok",
  "model_version": "phase4_lstm_REGEN_v1",
  "model_status": "PROVISIONAL",
  "package_folder": "phase4_lstm_REGEN_v1_20261101_0503"
}
```

#### Expected Output (Simulated Failure / Mock Mode):
```json
{
  "status": "ok",
  "model_version": "mock",
  "model_status": "MOCK",
  "package_folder": null
}
```

---

### 3.2 API Prediction Contract Test (Valid Payload)

Sends a standard 5-minute JSON window and verifies HTTP 200 response with all 9 contract fields.

#### Proposed Command:
```powershell
$body = @{
    window = @(
        @{ Timestamp="2018-02-03T09:00:00"; Bot_Pct=18.0; Total_Flows=1800; Fwd_Pkts_Bot=1050; Bwd_Pkts_Bot=820; Fwd_Bytes_Bot=63000; Bwd_Bytes_Bot=28000; Avg_Duration_Bot=22000 },
        @{ Timestamp="2018-02-03T09:01:00"; Bot_Pct=19.5; Total_Flows=1850; Fwd_Pkts_Bot=1100; Bwd_Pkts_Bot=860; Fwd_Bytes_Bot=66000; Bwd_Bytes_Bot=30000; Avg_Duration_Bot=23000 },
        @{ Timestamp="2018-02-03T09:02:00"; Bot_Pct=17.2; Total_Flows=1790; Fwd_Pkts_Bot=1020; Bwd_Pkts_Bot=800; Fwd_Bytes_Bot=61000; Bwd_Bytes_Bot=27500; Avg_Duration_Bot=21500 },
        @{ Timestamp="2018-02-03T09:03:00"; Bot_Pct=20.1; Total_Flows=1900; Fwd_Pkts_Bot=1150; Bwd_Pkts_Bot=890; Fwd_Bytes_Bot=68000; Bwd_Bytes_Bot=31000; Avg_Duration_Bot=24000 },
        @{ Timestamp="2018-02-03T09:04:00"; Bot_Pct=18.8; Total_Flows=1830; Fwd_Pkts_Bot=1080; Bwd_Pkts_Bot=840; Fwd_Bytes_Bot=65000; Bwd_Bytes_Bot=29500; Avg_Duration_Bot=22500 }
    )
} | ConvertTo-Json -Depth 4

Invoke-RestMethod -Uri "http://localhost:8000/predict" -Method POST -Body $body -ContentType "application/json"
```

#### Expected Status & Response:
- **HTTP Status**: `200 OK`
- Contains: `predicted_bot_pct_next_minute`, `predicted_state`, `seed_predictions`, `seed_spread_pct_points`, `warnings`.

---

### 3.3 API Error Handling Suite (7 Error Codes)

Verifies that sending malformed windows triggers HTTP 422 with the exact matching `error_code`.

| Test Scenario | Payload Fault | Expected HTTP Status | Expected `error_code` |
|---|---|---|---|
| **P-ERR-01** | Omit `"Fwd_Bytes_Bot"` column | `422 Unprocessable Entity` | `MISSING_FEATURES` |
| **P-ERR-02** | Send 4 rows instead of 5 | `422 Unprocessable Entity` | `BAD_SHAPE` |
| **P-ERR-03** | Send `null` inside `Total_Flows` | `422 Unprocessable Entity` | `NAN_OR_INF` |
| **P-ERR-04** | Set `Total_Flows` to `-10` | `422 Unprocessable Entity` | `NEGATIVE_VALUE` |
| **P-ERR-05** | Set `Bot_Pct` to `105.0` | `422 Unprocessable Entity` | `BOT_PCT_RANGE` |
| **P-ERR-06** | Pass string `"invalid-date"` in Timestamp | `422 Unprocessable Entity` | `BAD_TIMESTAMP` |
| **P-ERR-07** | Timestamps spaced 120 seconds apart | `422 Unprocessable Entity` | `NOT_CONSECUTIVE` |

---

### 3.4 API Latency & Concurrency Benchmark

Tests whether inference through the HTTP API on native Windows CPU satisfies interactive responsiveness constraints.

#### Proposed Target Metrics:
- **Single-request latency (p95)**: $< 80\text{ ms}$
- **Throughput**: $\ge 15\text{ requests/sec}$ on CPU
- **Memory footprint**: $< 600\text{ MB}$ RSS with all 5 Keras models resident in memory

---

### 3.5 102 Holdout Test Target Local Replay (Blocked)

- **Objective**: Replay all 102 test windows from CSE-CIC-IDS2018 locally and verify that predictions match `test_predictions_lstm_regen.csv` to within $10^{-3}$ percentage points.
- **Current Blocker**: The repository contains `test_predictions_lstm_regen.csv` (which records true labels and predictions), but does **NOT** contain the raw 5-minute input feature windows (`test.parquet` or `df_annotated`).
- **Remediation**: Once Member 1 or Member 2 provides the input feature splits, this test script will be executed.

---

## 4. Reproduction Guide for Team Members

Any team member can verify all executed tests on their local machine with this 3-step sequence:

```powershell
# 1. Ensure you are in the workspace
cd "$HOME\member3-backend"

# 2. Run the core self-test
& "$HOME\sih26153-ml\.venv\Scripts\python.exe" .\selftest.py .\phase4_lstm_REGEN_v1_20261101_0503

# 3. Run the extended 17-check validation suite
& "$HOME\sih26153-ml\.venv\Scripts\python.exe" .\extra_tests.py
```

Expected result: Both scripts must complete with zero errors and print `ALL PASS`.

---

*End of INTEGRATION_TESTS.md*
*Next: PHASE 9 — Updated Final Report (`docs/FINAL_REPORT_MEMBER3.md`) (awaiting confirmation)*
