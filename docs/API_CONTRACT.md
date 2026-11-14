# SIH26153 — Backend API Contract
**AI-Based Network Attack Forecasting from Network Traffic Data**
*Author: Team Member 3 (Architecture & Backend Integration)*
*Date: 2026-11-14 | Branch: member3-architecture*

---

> [!IMPORTANT]
> This is a **framework-independent** contract.
> It defines what the backend API must accept and return regardless of the web framework chosen
> (Flask, FastAPI, Django REST, etc.).
> Any backend implementation must satisfy every rule in this document exactly.
>
> **The frontend must never load the model directly.**
> All calls to `predict_next_minute()` happen inside the backend process only.

---

## Table of Contents

1. [Design Principles](#1-design-principles)
2. [Endpoints](#2-endpoints)
   - [POST /predict](#21-post-predict)
   - [GET /health](#22-get-health)
3. [Request Schema — POST /predict](#3-request-schema--post-predict)
4. [Success Response Schema — POST /predict](#4-success-response-schema--post-predict)
5. [Error Response Schema](#5-error-response-schema)
6. [Validation Rules and Error Codes](#6-validation-rules-and-error-codes)
7. [Model-Loading Strategy](#7-model-loading-strategy)
8. [Mock Mode](#8-mock-mode)
9. [Backend-to-Frontend Flow](#9-backend-to-frontend-flow)
10. [Security and Deployment Notes](#10-security-and-deployment-notes)
11. [Conformance Checklist](#11-conformance-checklist)

---

## 1. Design Principles

| Principle | Rule |
|-----------|------|
| Single prediction module | `predict_lstm.py` is imported as-is; never copy or rewrite its logic |
| No duplicate model loading | The `pkg` object from `load_package()` is created **once at startup** and shared across all requests |
| Frontend isolation | The frontend receives JSON over HTTP only; it never touches `.keras` files or `.joblib` scalers |
| Fail loudly | Every validation error from `validate_window()` is surfaced as an HTTP 422 with a machine-readable `error_code`; errors are never silently swallowed |
| Honest labelling | Responses always include `model_status` and `warnings`; the frontend must display both |
| Mock safety | If the model cannot be loaded, the backend enters **mock mode** (`model_status: "MOCK"`); mock values are clearly labelled and must never appear as real forecasts |
| Offline / batch only | The API accepts pre-assembled windows; it does not connect to live traffic feeds |

---

## 2. Endpoints

### 2.1 `POST /predict`

| Property | Value |
|----------|-------|
| Method | `POST` |
| Path | `/predict` |
| Purpose | Accepts a 5-row window of per-minute traffic features; returns the next-minute bot-traffic forecast |
| Content-Type (request) | `application/json` |
| Content-Type (response) | `application/json` |
| Success status | `200 OK` |
| Validation error status | `422 Unprocessable Entity` |
| Server error status | `500 Internal Server Error` |

---

### 2.2 `GET /health`

| Property | Value |
|----------|-------|
| Method | `GET` |
| Path | `/health` |
| Purpose | Returns the model's load status and version; lets the frontend check connectivity |
| Content-Type (response) | `application/json` |
| Success status | `200 OK` |

#### Health response schema

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

If the model failed to load (mock mode):

```json
{
  "status": "ok",
  "model_version": "mock",
  "model_status": "MOCK",
  "package_folder": null,
  "limitations": ["Model could not be loaded. All predictions are mock values."]
}
```

---

## 3. Request Schema — POST /predict

The request body must be a JSON object with one required key: `window`.

### Top-level structure

```json
{
  "window": [ <row_0>, <row_1>, <row_2>, <row_3>, <row_4> ]
}
```

- `window` is a JSON **array of exactly 5 objects**.
- Each object represents one minute of aggregated traffic features.
- Rows must be ordered **oldest first, newest last** (index 0 = oldest, index 4 = newest).

### Row object schema

Each row object must contain the following keys. All values are numbers (JSON `number` type).

| Key | Type | Constraints | Description |
|-----|------|-------------|-------------|
| `Timestamp` | string (ISO 8601) | Optional; if present, must be parseable and rows must be exactly 60 s apart | Minute timestamp in UTC or local time |
| `Bot_Pct` | number | ≥ 0, ≤ 100 | Bot-traffic percentage for this minute |
| `Total_Flows` | number | ≥ 0 | Total flow count in this minute |
| `Fwd_Pkts_Bot` | number | ≥ 0 | Forward packets from bot flows |
| `Bwd_Pkts_Bot` | number | ≥ 0 | Backward packets from bot flows |
| `Fwd_Bytes_Bot` | number | ≥ 0 | Forward bytes from bot flows |
| `Bwd_Bytes_Bot` | number | ≥ 0 | Backward bytes from bot flows |
| `Avg_Duration_Bot` | number | ≥ 0 | Mean duration of bot flows |

### Complete example request

```json
{
  "window": [
    {
      "Timestamp": "2018-02-03T09:00:00",
      "Bot_Pct": 18.0,
      "Total_Flows": 1800,
      "Fwd_Pkts_Bot": 1050,
      "Bwd_Pkts_Bot": 820,
      "Fwd_Bytes_Bot": 63000,
      "Bwd_Bytes_Bot": 28000,
      "Avg_Duration_Bot": 22000
    },
    {
      "Timestamp": "2018-02-03T09:01:00",
      "Bot_Pct": 19.5,
      "Total_Flows": 1850,
      "Fwd_Pkts_Bot": 1100,
      "Bwd_Pkts_Bot": 860,
      "Fwd_Bytes_Bot": 66000,
      "Bwd_Bytes_Bot": 30000,
      "Avg_Duration_Bot": 23000
    },
    {
      "Timestamp": "2018-02-03T09:02:00",
      "Bot_Pct": 17.2,
      "Total_Flows": 1790,
      "Fwd_Pkts_Bot": 1020,
      "Bwd_Pkts_Bot": 800,
      "Fwd_Bytes_Bot": 61000,
      "Bwd_Bytes_Bot": 27500,
      "Avg_Duration_Bot": 21500
    },
    {
      "Timestamp": "2018-02-03T09:03:00",
      "Bot_Pct": 20.1,
      "Total_Flows": 1900,
      "Fwd_Pkts_Bot": 1150,
      "Bwd_Pkts_Bot": 890,
      "Fwd_Bytes_Bot": 68000,
      "Bwd_Bytes_Bot": 31000,
      "Avg_Duration_Bot": 24000
    },
    {
      "Timestamp": "2018-02-03T09:04:00",
      "Bot_Pct": 18.8,
      "Total_Flows": 1830,
      "Fwd_Pkts_Bot": 1080,
      "Bwd_Pkts_Bot": 840,
      "Fwd_Bytes_Bot": 65000,
      "Bwd_Bytes_Bot": 29500,
      "Avg_Duration_Bot": 22500
    }
  ]
}
```

> [!NOTE]
> The `Timestamp` field is optional in the JSON schema, but **strongly recommended**.
> When `Timestamp` is absent, `predict_lstm.py` cannot verify that rows are exactly
> 60 seconds apart, and a warning is added to the response.

---

## 4. Success Response Schema — POST /predict

HTTP 200 OK. The response body mirrors the output dict returned by `predict_next_minute()`,
with no fields added, removed, or renamed by the backend.

```json
{
  "forecast_horizon_minutes": 1,
  "predicted_bot_pct_next_minute": 19.1234,
  "predicted_state": "Low",
  "state_thresholds": {
    "Low": "<25",
    "Medium": "25-<50",
    "High": ">=50"
  },
  "seed_predictions": {
    "42": 18.9100,
    "43": 19.3200,
    "44": 18.7600,
    "45": 19.4100,
    "46": 19.2100
  },
  "seed_spread_pct_points": 0.6500,
  "model_version": "phase4_lstm_REGEN_v1",
  "model_status": "PROVISIONAL",
  "warnings": [
    "Low-state recall was ~0% on the test day; a 'Medium' output does not rule out Low."
  ]
}
```

> [!CAUTION]
> The values above are **illustrative only** (schema example, not from the real model).
> The frontend must display `model_status` and all `warnings` alongside the forecast.
> A `predicted_state` of "Low" or "Medium" does **not** mean traffic is safe.

### Field descriptions

| Field | Type | Always present | Description |
|-------|------|---------------|-------------|
| `forecast_horizon_minutes` | integer | Yes | Always `1` — forecast is always 1 minute ahead |
| `predicted_bot_pct_next_minute` | number | Yes | Ensemble mean, clipped to [0, 100], rounded to 4 d.p. |
| `predicted_state` | string | Yes | `"Low"`, `"Medium"`, or `"High"` |
| `state_thresholds` | object | Yes | The thresholds used to derive `predicted_state` |
| `seed_predictions` | object | Yes | Dict of `{"seed_id": value}` for all 5 seeds |
| `seed_spread_pct_points` | number | Yes | max(seeds) − min(seeds); **ensemble disagreement, not a confidence interval** |
| `model_version` | string | Yes | Artifact version string from `config.json` |
| `model_status` | string | Yes | `"PROVISIONAL"` (live model) or `"MOCK"` (mock mode) |
| `warnings` | array of strings | Yes | Always includes the low-recall advisory; may include clipping or spacing warnings |

---

## 5. Error Response Schema

All errors (validation errors and server errors) return a JSON object in this form:

```json
{
  "error": true,
  "error_code": "MISSING_FEATURES",
  "error_message": "[MISSING_FEATURES] missing columns: ['Fwd_Bytes_Bot']",
  "model_status": "PROVISIONAL"
}
```

| Field | Type | Always present | Description |
|-------|------|---------------|-------------|
| `error` | boolean | Yes | Always `true` for error responses |
| `error_code` | string | Yes | Machine-readable code (see §6) |
| `error_message` | string | Yes | Human-readable description from `InputValidationError` |
| `model_status` | string | Yes | `"PROVISIONAL"` or `"MOCK"` — always present so the frontend knows the model's state |

> [!NOTE]
> `error_code` is the `.code` attribute of `InputValidationError`, forwarded verbatim.
> The frontend must handle all 7 codes without crashing.

---

## 6. Validation Rules and Error Codes

The backend converts the JSON request to a `pandas.DataFrame`, then passes it to
`validate_window()` from `predict_lstm.py`. The following errors are raised by that function
and must be mapped to HTTP 422 by the backend.

| `error_code` | HTTP status | Trigger condition | Frontend action |
|-------------|-------------|-------------------|-----------------|
| `MISSING_FEATURES` | 422 | One or more of the 7 feature columns absent from the window | Show which features are missing |
| `BAD_SHAPE` | 422 | Window does not have exactly 5 rows and 7 feature columns | Show expected vs received shape |
| `NAN_OR_INF` | 422 | Any cell is `NaN` or infinite | Prompt user to check the data |
| `NEGATIVE_VALUE` | 422 | Any cell value is < 0 | Show which field has a negative value |
| `BOT_PCT_RANGE` | 422 | `Bot_Pct` > 100 in any row | Show which row has an out-of-range value |
| `BAD_TIMESTAMP` | 422 | `Timestamp` present but cannot be parsed to datetime | Show unparseable value |
| `NOT_CONSECUTIVE` | 422 | Rows are not exactly 60 seconds apart | Show actual gaps found |

**Additional backend-side validation** (before calling `validate_window()`):

| Check | HTTP status | Trigger |
|-------|-------------|---------|
| `window` key missing from request body | 422 | `{"error_code": "BAD_REQUEST", ...}` |
| `window` is not an array | 422 | `{"error_code": "BAD_REQUEST", ...}` |
| `window` has ≠ 5 elements | 422 | `{"error_code": "BAD_SHAPE", ...}` |
| Unexpected server exception | 500 | `{"error_code": "SERVER_ERROR", ...}` |

> [!CAUTION]
> **Never fill gaps, drop rows, or modify the window silently** to make validation pass.
> Every error must be returned to the caller. The caller is responsible for supplying valid data.

---

## 7. Model-Loading Strategy

```
Server starts
      │
      ▼
  load_package("phase4_lstm_REGEN_v1_20261101_0503")
  ┌── Success → pkg stored in a module-level or app-level variable
  │             model_status = "PROVISIONAL"
  │
  └── Failure (file missing, hash mismatch, TF error, etc.)
              → pkg = None
              → model_status = "MOCK"
              → log the error (stack trace)
              → server continues to run in mock mode
              → all /predict requests return mock values with
                model_status "MOCK" and a visible warning
              → /health returns model_status "MOCK"
```

### Rules

1. **Call `load_package()` exactly once**, at application startup (or at first request if lazy loading is used — but only once, not per request).
2. **Pass the `pkg` object** to every call of `predict_next_minute(pkg, window_df)`. Never call `load_package()` inside a request handler.
3. **Do not expose `pkg` to the frontend** via any endpoint.
4. **Thread safety**: if the framework is multi-threaded, `pkg` must be a read-only object (it is — `load_package()` returns a dict of already-loaded models; Keras inference is read-only).
5. **Model folder path** must be configurable (environment variable or config file), not hardcoded.

### Recommended startup pattern (framework-agnostic pseudocode)

```python
# At module level / app startup:
import predict_lstm

MODEL_FOLDER = os.environ.get("MODEL_FOLDER", "phase4_lstm_REGEN_v1_20261101_0503")

try:
    PKG = predict_lstm.load_package(MODEL_FOLDER)
    MODEL_STATUS_OVERRIDE = None          # let predict_next_minute set "PROVISIONAL"
except Exception as e:
    PKG = None
    MODEL_STATUS_OVERRIDE = "MOCK"
    print(f"WARNING: model load failed — running in mock mode. Error: {e}")

# In the POST /predict handler:
def handle_predict(request_body):
    if PKG is None:
        return mock_response()            # see §8
    window_df = build_dataframe(request_body["window"])
    try:
        result = predict_lstm.predict_next_minute(PKG, window_df)
        return result, 200
    except predict_lstm.InputValidationError as e:
        return {"error": True, "error_code": e.code,
                "error_message": str(e), "model_status": "PROVISIONAL"}, 422
    except Exception as e:
        return {"error": True, "error_code": "SERVER_ERROR",
                "error_message": str(e), "model_status": "PROVISIONAL"}, 500
```

---

## 8. Mock Mode

Mock mode is active when `load_package()` fails at startup.
In mock mode **every `/predict` call** returns a fixed response with `model_status: "MOCK"`.

### Mock response (illustrative values — not from the real model)

```json
{
  "forecast_horizon_minutes": 1,
  "predicted_bot_pct_next_minute": 0.0,
  "predicted_state": "Low",
  "state_thresholds": {
    "Low": "<25",
    "Medium": "25-<50",
    "High": ">=50"
  },
  "seed_predictions": {
    "42": 0.0,
    "43": 0.0,
    "44": 0.0,
    "45": 0.0,
    "46": 0.0
  },
  "seed_spread_pct_points": 0.0,
  "model_version": "mock",
  "model_status": "MOCK",
  "warnings": [
    "MODEL NOT LOADED — this is a mock response. All values are placeholder zeros.",
    "Do not interpret these numbers as forecasts."
  ]
}
```

### Mock mode rules

1. The frontend **must** check `model_status` on every response.
2. If `model_status == "MOCK"`, the frontend must display a **prominent banner** (e.g. red or orange) stating the model is not loaded and the values are not real.
3. Mock values must **never** be presented as forecasts in any chart or table without the banner.
4. The `/health` endpoint must return `model_status: "MOCK"` so the frontend can detect this state before making a `/predict` call.

---

## 9. Backend-to-Frontend Flow

```
Frontend                         Backend                           predict_lstm.py
   │                                │                                     │
   │  GET /health                   │                                     │
   │ ──────────────────────────────▶│                                     │
   │  ◀── 200 {model_status, ...} ──│                                     │
   │                                │                                     │
   │  [user assembles 5-min window] │                                     │
   │                                │                                     │
   │  POST /predict {window: [...]} │                                     │
   │ ──────────────────────────────▶│                                     │
   │                                │  build_dataframe(request["window"]) │
   │                                │ ───────────────────────────────────▶│
   │                                │                                     │  validate_window()
   │                                │  InputValidationError               │  (raises on bad input)
   │                                │ ◀─── e.code, str(e) ───────────────│
   │  ◀── 422 {error_code, ...} ────│                                     │
   │  [display error to user]       │                                     │
   │                                │                                     │  predict_next_minute()
   │                                │  result dict                        │  (on valid input)
   │                                │ ◀── {predicted_state, ...} ────────│
   │  ◀── 200 {result} ─────────────│                                     │
   │  [display forecast + warnings] │                                     │
```

### Frontend responsibilities (defined here; detailed in PHASE 7)

| Responsibility | Rule |
|----------------|------|
| Display `model_status` | Always visible — `PROVISIONAL` or `MOCK` |
| Display all `warnings` | Never suppress any element of the `warnings` array |
| Display `seed_spread_pct_points` | Label it "model disagreement" — never "confidence" or "certainty" |
| Distinguish observations from forecast | The 5 input rows are **observations**; `predicted_bot_pct_next_minute` is a **forecast** — label them differently |
| Mock banner | If `model_status == "MOCK"`, show a prominent banner before any values |
| Error display | Show `error_code` and `error_message` to the user; do not crash silently |

---

## 10. Security and Deployment Notes

> [!NOTE]
> This project is a college mini-project running locally. The notes below apply if the API
> is ever deployed beyond a local laptop.

| Topic | Recommendation |
|-------|---------------|
| CORS | If frontend and backend run on different ports, enable CORS for the frontend's origin only |
| Input size limit | Limit request body to ~10 KB (a valid 5-row window is < 2 KB) |
| Rate limiting | Not required for local demo; add for any public deployment |
| HTTPS | Not required for localhost; required for any network-accessible deployment |
| Model file access | The model folder must not be served as a static directory; only the backend process reads it |
| Error detail | Do not expose internal stack traces in production error responses |
| Environment variable | `MODEL_FOLDER` should be set in an `.env` file excluded from version control |

---

## 11. Conformance Checklist

An implementation satisfies this contract when all of the following are true:

- [ ] `predict_lstm.py` is imported unchanged; its logic is not duplicated
- [ ] `load_package()` is called exactly once at startup, not per request
- [ ] `POST /predict` returns HTTP 200 with the full output dict on a valid input
- [ ] `POST /predict` returns HTTP 422 with `error_code` for each of the 7 `InputValidationError` codes
- [ ] `POST /predict` returns HTTP 500 with `error_code: "SERVER_ERROR"` for unexpected exceptions
- [ ] `GET /health` returns `model_version` and `model_status`
- [ ] `model_status` is `"PROVISIONAL"` when the model is loaded, `"MOCK"` otherwise
- [ ] All `warnings` from `predict_next_minute()` are forwarded in the response without modification
- [ ] Mock responses have `model_status: "MOCK"` and plainly state values are not real forecasts
- [ ] The frontend never receives the `pkg` object or any reference to model files
- [ ] `seed_spread_pct_points` is never labelled "confidence" in any response or UI

---

*End of API_CONTRACT.md*
*Next: PHASE 6 — `docs/EXPLAINABILITY.md` (awaiting confirmation)*
