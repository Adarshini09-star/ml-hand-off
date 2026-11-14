# SIH26153 — Frontend Integration & Handoff Guide
**AI-Based Network Attack Forecasting from Network Traffic Data**
*Target Audience: Team Member 4 (Frontend & Dashboard Integration)*
*Author: Team Member 3 (Architecture & Backend Integration)*
*Date: 2026-11-14 | Branch: member3-architecture*

---

> [!IMPORTANT]
> **Cardinal Rules for the Frontend**:
> 1. **The frontend must NEVER load the model or scalers.** Do not import `predict_lstm.py`, TensorFlow, Keras, or joblib in UI code. All predictions come via HTTP from the Backend API.
> 2. **Never present forecasts as real-time detections.** The model estimates macro traffic state 1 minute ahead in batch mode; it does not detect live individual packets.
> 3. **Never label seed disagreement as "Confidence" or "SHAP".** Always label `seed_spread_pct_points` as **"Model Disagreement"** or **"Ensemble Spread"**.
> 4. **Low-State recall is ~0%.** A "Medium" or "Low" state does not prove the network is safe. The UI must always display this caveat.
> 5. **Mock Mode Banner:** When `model_status == "MOCK"`, a visible, prominent banner must inform the user that forecasts are synthetic placeholders.

---

## Table of Contents

1. [Role & Objectives of Team Member 4](#1-role--objectives-of-team-member-4)
2. [API Connection Details](#2-api-connection-details)
   - [2.1 Health Check (`GET /health`)](#21-health-check-get-health)
   - [2.2 Prediction Endpoint (`POST /predict`)](#22-prediction-endpoint-post-predict)
3. [Request Construction Guide](#3-request-construction-guide)
4. [Visual Display & Presentation Guidelines](#4-visual-display--presentation-guidelines)
   - [4.1 Distinguishing Observations from Forecasts](#41-distinguishing-observations-from-forecasts)
   - [4.2 Presenting Predicted State & Color Coding](#42-presenting-predicted-state--color-coding)
   - [4.3 Presenting Uncertainty & Model Disagreement](#43-presenting-uncertainty--model-disagreement)
   - [4.4 Rendering Warnings](#44-rendering-warnings)
5. [Mock Mode Requirements](#5-mock-mode-requirements)
6. [Error Handling & User Feedback](#6-error-handling--user-feedback)
7. [Recommended Dashboard Layout / Wireframe](#7-recommended-dashboard-layout--wireframe)
8. [Mandatory Limitations to Include in UI](#8-mandatory-limitations-to-include-in-ui)

---

## 1. Role & Objectives of Team Member 4

Team Member 4 owns the **Dashboard, User Interface, and Client-Side Testing**:
- Provide an intuitive interface for network operators to input/upload traffic data.
- Display the historical 5-minute traffic trends alongside the next-minute forecast.
- Render model predictions, traffic states, disagreement indicators, and system warnings clearly without misleading the user.
- Gracefully handle API errors and mock states.

---

## 2. API Connection Details

Base URL (default local development): `http://localhost:8000` (or `http://localhost:5000` depending on backend framework).

### 2.1 Health Check (`GET /health`)

Call this when the dashboard loads to verify backend availability and determine if the model is live or in mock mode.

- **Request**: `GET /health`
- **Response (`200 OK`)**:
```json
{
  "status": "ok",
  "model_version": "phase4_lstm_REGEN_v1",
  "model_status": "PROVISIONAL",
  "package_folder": "phase4_lstm_REGEN_v1_20261101_0503",
  "limitations": [
    "Offline/batch only. Not a live or real-time system.",
    "Low-state recall ~0% on the test day.",
    "Provisional model; not production-validated."
  ]
}
```

---

### 2.2 Prediction Endpoint (`POST /predict`)

- **Method**: `POST`
- **Path**: `/predict`
- **Headers**: `Content-Type: application/json`
- **Request Body**: JSON object containing a `window` array of exactly 5 consecutive minute records.

#### Success Response (`200 OK`)
```json
{
  "forecast_horizon_minutes": 1,
  "predicted_bot_pct_next_minute": 34.85,
  "predicted_state": "Medium",
  "state_thresholds": {
    "Low": "<25",
    "Medium": "25-<50",
    "High": ">=50"
  },
  "seed_predictions": {
    "42": 33.10,
    "43": 34.50,
    "44": 37.20,
    "45": 35.00,
    "46": 34.45
  },
  "seed_spread_pct_points": 4.10,
  "model_version": "phase4_lstm_REGEN_v1",
  "model_status": "PROVISIONAL",
  "warnings": [
    "Low-state recall was ~0% on the test day; a 'Medium' output does not rule out Low."
  ]
}
```

---

## 3. Request Construction Guide

The dashboard must format the payload into an array of **5 objects**, ordered chronologically from **oldest (index 0) to newest (index 4)**.

### Required Fields per Row
1. `Bot_Pct` (float, $0 \le x \le 100$)
2. `Total_Flows` (float or int, $\ge 0$)
3. `Fwd_Pkts_Bot` (float or int, $\ge 0$)
4. `Bwd_Pkts_Bot` (float or int, $\ge 0$)
5. `Fwd_Bytes_Bot` (float or int, $\ge 0$)
6. `Bwd_Bytes_Bot` (float or int, $\ge 0$)
7. `Avg_Duration_Bot` (float or int, $\ge 0$)
8. `Timestamp` (*Recommended*, ISO 8601 string, e.g. `"2018-02-03T09:04:00"`)

> [!TIP]
> Ensure consecutive timestamps are exactly **60 seconds apart**. If the gap between row $i$ and $i+1$ is not 60 seconds, the backend validator will reject the request with `NOT_CONSECUTIVE`.

---

## 4. Visual Display & Presentation Guidelines

### 4.1 Distinguishing Observations from Forecasts

A common UX pitfall in monitoring dashboards is confusing measured historical data with model predictions.

| Category | Temporal Context | Visual Treatment |
|---|---|---|
| **Input Window (Rows 0 to 4)** | Past 5 minutes ($t-4$ to $t$) | Solid line or distinct grey/blue bars. Label clearly: **"Historical Observed Traffic"**. |
| **Prediction Output** | Next minute ($t+1$) | Dashed line, highlighted forecast card, or distinct colored accent. Label clearly: **"Forecast (t+1 min)"**. |

---

### 4.2 Presenting Predicted State & Color Coding

Map `predicted_state` to standard status badges:

| State | Condition | Suggested Badge Color | UI Label |
|---|---|---|---|
| **Low** | $< 25\%$ | 🟢 Green | Low Risk (<25% Bot) |
| **Medium** | $25\% \le x < 50\%$ | 🟡 Amber / Orange | Elevated Caution (25–49% Bot) |
| **High** | $\ge 50\%$ | 🔴 Red | High Attack Threat (≥50% Bot) |

> [!CAUTION]
> Even if the state is **Low**, always include an asterisk or tooltip:
> *"Notice: Low-state recall is ~0% on test benchmarks; Low predictions are subject to high false-negative risk."*

---

### 4.3 Presenting Uncertainty & Model Disagreement

The payload includes `seed_spread_pct_points` and individual `seed_predictions`.

1. **Approved Terminology**:
   - ✅ Label: **"Model Disagreement"** or **"Ensemble Spread"**
   - ❌ FORBIDDEN: **"Confidence Score"**, **"Accuracy"**, **"Certainty"**, **"SHAP"**
2. **Visual Gauge**:
   - Spread $\le 5.0$ pts: Low Disagreement (models agree closely).
   - Spread $5.1 - 10.0$ pts: Moderate Disagreement.
   - Spread $> 10.0$ pts: ⚠️ High Disagreement (model optimization instability; treat forecast as highly uncertain).
3. **Optional Seed Breakdown**:
   - A small 5-bar chart showing predictions from Seeds 42, 43, 44, 45, and 46 can be shown under an expandable "Model Diagnostics" accordion.

---

### 4.4 Rendering Warnings

The `warnings` array in the response contains crucial operational advisories.
- Render each item inside an alert box with a warning icon (`⚠️`).
- **Never hide or suppress warnings.**

Example rendering:
```
┌────────────────────────────────────────────────────────────────────────┐
│ ⚠️ Model Advisory:                                                     │
│ • Low-state recall was ~0% on the test day; a 'Medium' output does not │
│   rule out Low.                                                        │
│ • Raw ensemble output 104.2 was clipped to the valid 0-100 range.     │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 5. Mock Mode Requirements

If the backend cannot load the model weights, it operates in **Mock Mode** (`"model_status": "MOCK"`).

### Mandatory UI Behavior in Mock Mode:
1. **Persistent Banner**: Render an unmissable top banner across the dashboard:
   ```
   ┌───────────────────────────────────────────────────────────────────────┐
   │ 🚩 SIMULATION MODE ACTIVE: Model is running in MOCK mode.            │
   │ Forecast values are placeholder stubs for testing UI layouts only.   │
   └───────────────────────────────────────────────────────────────────────┘
   ```
2. **Watermark / Tag**: Attach a `[MOCK]` tag directly adjacent to the percentage number and state badge (e.g., `0.0% [MOCK]`).

---

## 6. Error Handling & User Feedback

When input is invalid, the backend returns **HTTP 422 Unprocessable Entity**:
```json
{
  "error": true,
  "error_code": "NOT_CONSECUTIVE",
  "error_message": "[NOT_CONSECUTIVE] rows must be exactly 60 s apart; got gaps [120.0]",
  "model_status": "PROVISIONAL"
}
```

The frontend should catch 422 errors and display targeted user guidance based on `error_code`:

| `error_code` | User-Friendly Toast / Form Feedback |
|---|---|
| `MISSING_FEATURES` | "Missing required traffic columns. Ensure all 7 features are included." |
| `BAD_SHAPE` | "Window must contain exactly 5 rows of traffic data." |
| `NAN_OR_INF` | "Data contains invalid empty (NaN) or infinite values. Please check table cells." |
| `NEGATIVE_VALUE` | "Negative values are invalid for traffic counts, bytes, or durations." |
| `BOT_PCT_RANGE` | "Bot percentage must be between 0.0% and 100.0%." |
| `BAD_TIMESTAMP` | "Invalid timestamp format. Use standard YYYY-MM-DD HH:MM:SS." |
| `NOT_CONSECUTIVE` | "Time gap detected! Sequence rows must be exactly 60 seconds apart." |
| `SERVER_ERROR` (500) | "Backend service encountered an error. Please verify backend logs." |

---

## 7. Recommended Dashboard Layout / Wireframe

```
+-----------------------------------------------------------------------------------+
|  [LOGO]  SIH26153 - AI Network Attack Forecaster        Status: [ PROVISIONAL ● ]  |
+-----------------------------------------------------------------------------------+
| ⚠️ Model status: PROVISIONAL. Batch/offline forecast. Not a real-time detector.    |
+---------------------------------------------------+-------------------------------+
|  INPUT WINDOW (Last 5 Minutes)                    |  NEXT-MINUTE FORECAST (t+1)   |
|                                                   |                               |
|  [ Preset Dropdown: Typical Traffic ▼ ]           |    Predicted Bot Share:       |
|  [ Upload CSV ]   [ Edit Table ]                  |          34.85 %                  |
|                                                   |                               |
|  ┌─────┬─────────┬─────────────┬──────────────┐   |    Traffic Threat State:      |
|  | Min | Bot_Pct | Total_Flows | Fwd_Pkts_Bot |   |    [  🟡 MEDIUM (25-49%)  ]   |
|  ├─────┼─────────┼─────────────┼──────────────┤   |                               |
|  | t-4 |   18.0  |    1800     |     1050     |   |    Model Disagreement:        |
|  | t-3 |   19.5  |    1850     |     1100     |   |    4.10 percentage points     |
|  | t-2 |   17.2  |    1790     |     1020     |   |    [Agreement: Close]         |
|  | t-1 |   20.1  |    1900     |     1150     |   |                               |
|  |  t  |   18.8  |    1830     |     1080     |   |                               |
|  └─────┴─────────┴─────────────┴──────────────┘   |                               |
|                                                   |                               |
|  [ PREDICT NEXT MINUTE (POST /predict) ]          |                               |
+---------------------------------------------------+-------------------------------+
|  UNCERTAINTY & EXPLANATIONS                       |  SYSTEM ADVISORIES            |
|                                                   |                               |
|  Ensemble Seed Predictions:                       |  ⚠️ Low-state recall was ~0%  |
|  Seed 42: 33.1%  |  Seed 43: 34.5%                |     on benchmark tests.       |
|  Seed 44: 37.2%  |  Seed 45: 35.0%                |  ℹ️ 5-minute sequence cleanly |
|  Seed 46: 34.5%                                   |     validated (60s spacing).  |
+---------------------------------------------------+-------------------------------+
| Footer: SIH26153 Research Prototype | Evaluated on CSE-CIC-IDS2018 benchmark      |
+-----------------------------------------------------------------------------------+
```

---

## 8. Mandatory Limitations to Include in UI

Ensure the dashboard footer or "About" modal includes these statements:
1. **Offline & Batch Only:** Operates on pre-aggregated 1-minute tabular records. It is not an inline packet inspection engine.
2. **Benchmark Scope:** Evaluated on 102 target windows from a single day of CSE-CIC-IDS2018.
3. **Macro State Forecasting:** Predicts the aggregate percentage of bot flows; it does not isolate individual attacker IPs or packets.
4. **Low-State Blindspot:** Low-state recall on holdout tests was ~0%. A Low or Medium forecast is an estimate and must not be taken as proof that traffic is safe.

---

*End of FRONTEND_HANDOFF.md*
*Next: PHASE 8 — `docs/TESTING_SUMMARY.md` (awaiting confirmation)*
