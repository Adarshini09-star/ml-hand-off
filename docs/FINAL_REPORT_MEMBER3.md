# SIH26153 — Final Architecture & Integration Report
**AI-Based Network Attack Forecasting from Network Traffic Data**
*Author: Team Member 3 (ML Systems Architecture & Backend Integration)*
*Project ID: SIH26153 | Branch: member3-architecture*
*Date: 2026-11-14*

---

> [!IMPORTANT]
> **Executive Summary & Operational Constraints**:
> - **Provisional Status**: The deployed model package (`phase4_lstm_REGEN_v1_20261101_0503`) is a regenerated ensemble of 5 LSTM models. It reproduces saved test metrics to within $10^{-3}$ percentage points, but is not byte-identical to the original lost archive.
> - **Evaluation Scope**: Validated on **102 test target windows from a single day** of the CSE-CIC-IDS2018 dataset.
> - **Critical Blindspot**: **Low-state recall is ~0%** (all 23 Low targets were predicted Medium). A "Medium" or "Low" forecast does **not** prove traffic is benign.
> - **Batch / Offline Only**: The system operates on pre-aggregated 1-minute historical windows; it is **not** an inline, real-time packet inspection tool.
> - **Macro Forecasting**: Forecasts future aggregate bot-traffic share; it does not isolate individual attack packets or malicious IP addresses.

---

## Table of Contents

1. [Project Overview & Member 3 Mandate](#1-project-overview--member-3-mandate)
2. [Inventory of Completed Deliverables](#2-inventory-of-completed-deliverables)
3. [Verified Model Specifications & Benchmark Metrics](#3-verified-model-specifications--benchmark-metrics)
4. [System Architecture & Pipeline Integration](#4-system-architecture--pipeline-integration)
5. [Dataset & Preprocessing Pipeline Audit](#5-dataset--preprocessing-pipeline-audit)
6. [Backend API Contract & Execution Model](#6-backend-api-contract--execution-model)
7. [Explainability, Uncertainty & SHAP Assessment](#7-explainability-uncertainty--shap-assessment)
8. [Frontend Handoff & Dashboard Guidance](#8-frontend-handoff--dashboard-guidance)
9. [Verification, Testing & Quality Assurance](#9-verification-testing--quality-assurance)
10. [Known System Limitations & Defensibility](#10-known-system-limitations--defensibility)
11. [Cross-Functional Action Items for Team Members](#11-cross-functional-action-items-for-team-members)

---

## 1. Project Overview & Member 3 Mandate

Project **SIH26153** aims to forecast future botnet traffic states from aggregated network flow metrics. The project team is organized into four complementary roles:
- **Member 1 (Dataset)**: Raw dataset exploration, feature selection, and traffic preprocessing.
- **Member 2 (ML & Forecasting)**: Baseline comparison, LSTM/GRU model training, and offline evaluation.
- **Member 3 (Architecture & Backend Integration — THIS REPORT)**: Outlining the end-to-end system architecture, structuring the input contract, designing the backend API, evaluating explainability/uncertainty, and formalizing handoffs.
- **Member 4 (Frontend & Dashboard)**: Operator interface, visualization of forecasts, uncertainty, and mock-mode handling.

---

## 2. Inventory of Completed Deliverables

All documentation artifacts have been systematically authored, reviewed against source code and frozen configuration, and committed to git branch `member3-architecture`:

| Deliverable Artifact | Path | Scope & Focus |
|---|---|---|
| **System Architecture** | [`docs/ARCHITECTURE.md`](file:///C:/Users/ullas/member3-backend/docs/ARCHITECTURE.md) | End-to-end Mermaid diagram (Nodes A–H), data flow, implemented vs. pending status. |
| **Preprocessing Audit** | [`docs/PREPROCESSING.md`](file:///C:/Users/ullas/member3-backend/docs/PREPROCESSING.md) | Training vs. inference pipelines, 207-min gap, Row 259/502 audits, missing raw steps. |
| **Backend API Contract** | [`docs/API_CONTRACT.md`](file:///C:/Users/ullas/member3-backend/docs/API_CONTRACT.md) | Framework-independent specification for `GET /health` and `POST /predict`, 7 error codes, mock mode. |
| **Explainability Analysis** | [`docs/EXPLAINABILITY.md`](file:///C:/Users/ullas/member3-backend/docs/EXPLAINABILITY.md) | Math of seed spread vs. SHAP, DeepSHAP/KernelSHAP feasibility assessment, feasible sensitivity. |
| **Frontend Handoff Guide** | [`docs/FRONTEND_HANDOFF.md`](file:///C:/Users/ullas/member3-backend/docs/FRONTEND_HANDOFF.md) | UI wireframes, observation vs. forecast visual distinction, mock mode banner, error mapping. |
| **Integration Test Suite** | [`docs/INTEGRATION_TESTS.md`](file:///C:/Users/ullas/member3-backend/docs/INTEGRATION_TESTS.md) | Executed vs. proposed tests, hash check (11/11), 17 validation checks, Streamlit presets. |
| **Validation Engine** | [`predict_lstm.py`](file:///C:/Users/ullas/member3-backend/predict_lstm.py) | Verified inference engine (lazy TF load, validation, ensemble prediction, clipping). |
| **Extended Test Harness** | [`extra_tests.py`](file:///C:/Users/ullas/member3-backend/extra_tests.py) | 17/17 automated unit tests exercising all 7 input error codes. |
| **Interactive Prototype** | [`forecast_app.py`](file:///C:/Users/ullas/member3-backend/forecast_app.py) | Streamlit verification app with 4 traffic presets and out-of-range z-score warning. |
| **CLI Demo Script** | [`run_demo.py`](file:///C:/Users/ullas/member3-backend/run_demo.py) | Command-line demo reading from CSV and outputting structured predictions. |

---

## 3. Verified Model Specifications & Benchmark Metrics

### 3.1 Model Architecture & Hyperparameters
Extracted directly from `config.json` inside `phase4_lstm_REGEN_v1_20261101_0503/`:
- **Architecture**: `Input(shape=(5, 7))` $\to$ `LSTM(16 units, recurrent_dropout=0.0)` $\to$ `Dropout(0.2)` $\to$ `Dense(16, relu)` $\to$ `Dense(1, linear)`
- **Ensemble**: 5 independent seeds (`42, 43, 44, 45, 46`).
- **Trainable Parameters**: 1,825 per model ($5 \times 1,825 = 9,125$ parameters total).
- **Training Protocol**: Adam optimizer ($\text{lr} = 0.001$), batch size 16, MSE loss, max 200 epochs with EarlyStopping ($\text{patience} = 20$, $\text{min\_delta} = 10^{-4}$).
- **Feature Order**: `Bot_Pct`, `Total_Flows`, `Fwd_Pkts_Bot`, `Bwd_Pkts_Bot`, `Fwd_Bytes_Bot`, `Bwd_Bytes_Bot`, `Avg_Duration_Bot`.
- **Scalers**: `StandardScaler` for features (fit on 322 training rows) and `StandardScaler` for target (fit on training targets excluding Row 259).

### 3.2 Evaluation Benchmark (102 Holdout Test Targets)

| Metric | LSTM Ensemble | Persistence Baseline ("Same as Last Minute") | Performance Context |
|---|---|---|---|
| **MAE** | **6.9211** | 9.3123 | LSTM achieves 25.7% error reduction over baseline |
| **RMSE** | **8.4283** | 11.6736 | LSTM achieves 27.8% lower variance |
| **$R^2$ Score** | **0.6216** | 0.2741 | Explains 62.2% of target variance |
| **Overall Accuracy** | **71.57%** (73/102) | 59.80% (61/102) | Evaluated across 3 discrete states |
| **High State Recall** | **92.31%** (12/13) | 61.54% (8/13) | Reliable detection of heavy attack phases |
| **Medium State Recall** | **92.42%** (61/66) | 74.24% (49/66) | High sensitivity to transitional attack traffic |
| **Low State Recall** | **0.00%** (0/23) | 17.39% (4/23) | **Critical Flaw**: All 23 Low targets predicted Medium |

---

## 4. System Architecture & Pipeline Integration

The architecture connects pre-aggregated network statistics to the operator dashboard via a clean separation of concerns:

```
[Historical Ingestion & Aggregation]  <-- Caller / Pipeline Responsibility
                  │
                  ▼
   5-Row × 7-Feature Window (Raw, Unscaled)
                  │
                  ▼
┌────────────────────────────────────────────────────────┐
│ Backend Service Layer                                  │
│   1. validate_window() (predict_lstm.py)               │
│      - 7 Contract Validation Checks                    │
│   2. scaler_features.transform() (StandardScaler)      │
│   3. 5-Seed LSTM Forward Pass (Keras 3)                │
│   4. scaler_target.inverse_transform()                 │
│   5. Ensemble Mean + Range Clipping [0, 100]           │
│   6. State Mapping (<25, 25-50, >=50)                  │
│   7. Uncertainty & Warnings Assembly                   │
└────────────────────────────────────────────────────────┘
                  │
                  ▼ HTTP / JSON
┌────────────────────────────────────────────────────────┐
│ Frontend Dashboard (Member 4)                          │
│   - Historical Trends vs. Next-Minute Forecast (t+1)   │
│   - Threat State Badges (Green / Amber / Red)          │
│   - Model Disagreement Gauge (seed_spread_pct_points)  │
│   - System Warnings & Mock Mode Banners                │
└────────────────────────────────────────────────────────┘
```

---

## 5. Dataset & Preprocessing Pipeline Audit

The pipeline audit conducted in [`docs/PREPROCESSING.md`](file:///C:/Users/ullas/member3-backend/docs/PREPROCESSING.md) revealed critical operational insights:
1. **Missing Raw Extraction Code**: The repository begins from pre-aggregated per-minute Parquet/CSV files (`ML_ready_traffic.csv`). The code executing CICFlowMeter extraction from raw PCAPs is **missing** and must be provided by Member 1.
2. **The 207-Minute Gap**: Between row 259 (05:29) and row 260 (08:56), a 207-minute data gap exists. Inference windows must **never** span this gap.
3. **Target Invalidation (Row 259)**: Row 259's target was created via a naive shift across the gap; it was properly identified and excluded from training.
4. **Unverified Target (Row 502)**: Row 502 (12:59) target provenance is unverified in on-disk files; retained per protocol to yield 102 test targets.

---

## 6. Backend API Contract & Execution Model

The framework-independent specification formalized in [`docs/API_CONTRACT.md`](file:///C:/Users/ullas/member3-backend/docs/API_CONTRACT.md) defines:
- **`GET /health`**: Returns model status (`PROVISIONAL` or `MOCK`) and version.
- **`POST /predict`**: Accepts a JSON payload containing the 5-row array and returns the full 9-field forecast dictionary.
- **Single Model Loading Rule**: `load_package()` runs **once at startup**. Models remain in memory; they are never re-instantiated per request.
- **Strict Error Mapping**: `InputValidationError` from `validate_window()` maps directly to **HTTP 422 Unprocessable Entity** with machine-readable error codes:
  `MISSING_FEATURES`, `BAD_SHAPE`, `NAN_OR_INF`, `NEGATIVE_VALUE`, `BOT_PCT_RANGE`, `BAD_TIMESTAMP`, `NOT_CONSECUTIVE`.
- **Mock Fallback**: If model weights cannot be loaded, the backend enters mock mode with a mandatory UI banner requirement.

---

## 7. Explainability, Uncertainty & SHAP Assessment

A technical assessment in [`docs/EXPLAINABILITY.md`](file:///C:/Users/ullas/member3-backend/docs/EXPLAINABILITY.md) resolved the explainability approach:
- **Ensemble Spread (`seed_spread_pct_points`)**: Accurately measures model disagreement across training initializations ($1.4-4.0$ pts on normal traffic, $>25$ pts on out-of-distribution traffic).
- **SHAP Assessment**:
  - **DeepSHAP**: Incompatible with Keras 3.15 recurrent layer graphs in TF 2.21; crashes at runtime.
  - **KernelSHAP**: Requires $>10,000$ forward passes ($12-25$ seconds CPU latency) and violates feature independence assumptions across correlated time-series data.
  - **Conclusion**: SHAP is **neither technically viable nor scientifically defensible** for real-time inference on this model.
- **Feasible Next Step**: Local feature perturbation sensitivity analysis (~40 ms CPU latency) and temporal step attribution.

---

## 8. Frontend Handoff & Dashboard Guidance

The guidelines in [`docs/FRONTEND_HANDOFF.md`](file:///C:/Users/ullas/member3-backend/docs/FRONTEND_HANDOFF.md) provide Team Member 4 with complete implementation blueprints:
- **Model Isolation**: Frontend code must never import Keras, TensorFlow, or `predict_lstm.py`.
- **Visual Separation**: Past 5 minutes ($t-4 \dots t$) are rendered as solid observations; next minute ($t+1$) is rendered as a distinct dashed forecast card.
- **Terminology Enforcement**: `seed_spread_pct_points` must be labelled **"Model Disagreement"**, never "Confidence" or "SHAP".
- **Warning Prominence**: All warnings from the response array must be prominently displayed in alert callouts.

---

## 9. Verification, Testing & Quality Assurance

As documented in [`docs/INTEGRATION_TESTS.md`](file:///C:/Users/ullas/member3-backend/docs/INTEGRATION_TESTS.md), all local tests pass on native Windows with Python 3.13.2:
- **T01 (Package Hashes)**: 11/11 SHA-256 hashes verified OK against `MANIFEST_sha256.txt`.
- **T02 (Core Self-Test)**: `selftest.py` passed all checks including column-order independence and state threshold sanity.
- **T03 (Extended Validation)**: `extra_tests.py` passed 17/17 tests covering all 7 contract error codes.
- **T04 (CLI Demo)**: `run_demo.py` successfully executed on `sample_window.csv`.
- **T05 (Streamlit Prototype)**: `forecast_app.py` verified across 4 realistic and out-of-range presets.

---

## 10. Known System Limitations & Defensibility

When presenting this project to evaluators or stakeholders, these 6 limitations must be stated transparently:
1. **Low-State Blindspot**: The model cannot reliably detect when traffic transitions to a clean, Low-attack state (0% recall on benchmark test day).
2. **Single-Day Evaluation**: The 102 test windows originate from a single day of recording; cross-day and cross-network generalizability remains unproven.
3. **Macro State vs. Packet Detection**: Forecasts the future aggregate bot percentage; it does not flag individual packets or provide firewall mitigation rules.
4. **Offline / Batch Scope**: Requires pre-aggregated 1-minute tabular buckets; real-time streaming ingestion is not yet implemented.
5. **Ensemble Spread is Not Calibrated Confidence**: Seed disagreement indicates optimization variance, not statistical error bounds.
6. **Regenerated Artifacts**: Model package was retrained from frozen configuration and reproduces metrics to $10^{-3}$, but is not byte-identical to original Phase 4 files.

---

## 11. Cross-Functional Action Items for Team Members

### For Team Member 1 (Dataset):
- [ ] Document the exact CICFlowMeter version, arguments, and scripts used to produce per-flow records.
- [ ] Provide the raw-to-per-minute aggregation code that computes `Bot_Pct`, `Total_Flows`, and packet/byte metrics.
- [ ] Clarify the exact calendar date of the benchmark traffic (notebook reads `2018-02-03`).
- [ ] Confirm units for `Avg_Duration_Bot` (microseconds vs. milliseconds vs. seconds).

### For Team Member 2 (ML & Modeling):
- [ ] Investigate retraining or loss-weighting strategies to address the ~0% Low-state recall failure.
- [ ] Provide input feature splits (`test.parquet`) to enable local execution of the 102-target replay test.
- [ ] Explore temporal calibration methods (such as conformal prediction) to provide statistical confidence bounds.

### For Team Member 4 (Frontend):
- [ ] Implement the dashboard layout following the wireframe in [`docs/FRONTEND_HANDOFF.md`](file:///C:/Users/ullas/member3-backend/docs/FRONTEND_HANDOFF.md).
- [ ] Connect the dashboard to `POST /predict` and `GET /health` via HTTP.
- [ ] Enforce visual distinction between historical observations ($t-4 \dots t$) and prediction ($t+1$).
- [ ] Implement user-friendly form feedback for all 7 HTTP 422 error codes.

---

*End of FINAL_REPORT_MEMBER3.md*
*Team Member 3 Mandate: COMPLETE*
