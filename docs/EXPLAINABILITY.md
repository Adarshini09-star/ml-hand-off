# SIH26153 — Explainability and Uncertainty Documentation
**AI-Based Network Attack Forecasting from Network Traffic Data**
*Author: Team Member 3 (Architecture & Backend Integration)*
*Date: 2026-11-14 | Branch: member3-architecture*

---

> [!IMPORTANT]
> **Mandatory Limitations & Constraints**:
> - This system is **PROVISIONAL, offline/batch-only**. It forecasts next-minute Bot traffic percentage from a 5-minute window.
> - **Evaluated on 102 test targets from a single day** of the CSE-CIC-IDS2018 dataset.
> - **Low-state recall is ~0%** (all 23 Low targets in the test day were predicted Medium). A "Medium" prediction does **not** prove traffic is safe.
> - **Ensemble disagreement is NOT SHAP** and is **NOT a statistically calibrated confidence interval**. It measures variance across seeds resulting from random weight initialization and stochastic optimization.
> - The model forecasts macro traffic states, **not** individual attack flows or attacker identities.

---

## Table of Contents

1. [Executive Summary & Objectives](#1-executive-summary--objectives)
2. [Current Uncertainty Signals (What is Implemented)](#2-current-uncertainty-signals-what-is-implemented)
   - [2.1 Seed Disagreement (`seed_spread_pct_points`)](#21-seed-disagreement-seed_spread_pct_points)
   - [2.2 Built-in Model Warnings](#22-built-in-model-warnings)
   - [2.3 Out-of-Range Heuristic (`|z-score| > 5`)](#23-out-of-range-heuristic-z-score--5)
   - [2.4 Critical Distinctions: What Current Signals Do and Do Not Mean](#24-critical-distinctions-what-current-signals-do-and-do-not-mean)
3. [Technical Feasibility & Defensibility Assessment of SHAP](#3-technical-feasibility--defensibility-assessment-of-shap)
   - [3.1 DeepSHAP Evaluation](#31-deepshap-evaluation)
   - [3.2 KernelSHAP Evaluation](#32-kernelshap-evaluation)
   - [3.3 Defensibility & Scientific Rigor](#33-defensibility--scientific-rigor)
   - [3.4 Assessment Verdict](#34-assessment-verdict)
4. [Recommended Feasible Explainability Approaches](#4-recommended-feasible-explainability-approaches)
   - [4.1 Local Feature Perturbation (Sensitivity Analysis)](#41-local-feature-perturbation-sensitivity-analysis)
   - [4.2 Temporal Step Attribution (Time-Saliency)](#42-temporal-step-attribution-time-saliency)
   - [4.3 Validated Input Distribution Health Metric](#43-validated-input-distribution-health-metric)
5. [Classification: Implemented vs. Next Steps vs. Future Enhancements](#5-classification-implemented-vs-next-steps-vs-future-enhancements)
6. [Guidelines for Frontend Display (Member 4 Alignment)](#6-guidelines-for-frontend-display-member-4-alignment)
7. [System Limitations Summary](#7-system-limitations-summary)

---

## 1. Executive Summary & Objectives

In safety-critical cybersecurity deployments, an ML forecasting model cannot be treated as a black box. Team Member 3 is tasked with outlining how explainability and uncertainty work together within the backend architecture.

This document:
1. Clarifies what the existing uncertainty mechanisms (`seed_spread_pct_points` and warnings) mathematically represent.
2. Formally evaluates whether SHAP (SHapley Additive exPlanations) is technically feasible, stable, and scientifically defensible for this 5-seed LSTM ensemble.
3. Proposes feasible, lightweight feature attribution methods that can realistically be integrated into the backend without destabilizing the Python 3.13 / Keras 3 environment.
4. Categorizes every technique into **Already Implemented**, **Can Be Implemented Next**, or **Proposed Future Enhancement**.

---

## 2. Current Uncertainty Signals (What is Implemented)

### 2.1 Seed Disagreement (`seed_spread_pct_points`)

The LSTM ensemble contains 5 identical architectures trained from different initial random seeds (42, 43, 44, 45, 46). At inference, each model $m_s$ receives the scaled $5 \times 7$ window $X_s$ and produces an inverse-scaled prediction $\hat{y}_s$:

$$\hat{y}_s = \text{Scaler}_y^{-1}\left(m_s(X_s)\right), \quad s \in \{42, 43, 44, 45, 46\}$$

The ensemble point forecast is:
$$\hat{y}_{\text{ensemble}} = \text{clip}\left(\frac{1}{5} \sum_{s=42}^{46} \hat{y}_s, \, 0.0, \, 100.0\right)$$

The seed disagreement metric is computed as:
$$\text{seed\_spread\_pct\_points} = \max_{s}(\hat{y}_s) - \min_{s}(\hat{y}_s)$$

#### What it shows:
- **Model sensitivity to initialization**: It shows how much the model's hypothesis varies across local minima found during training.
- **Empirical volatility**: On realistic in-distribution inputs (e.g., training average traffic), the 5 seeds exhibit tight consensus (spread typically $1.4$ to $4.0$ percentage points). On out-of-distribution inputs (e.g., packets $\approx 20,000$ vs. training mean $\approx 1,101$), the spread widens to over $25$ percentage points.

#### What it DOES NOT show:
- It is **not** a calibrated epistemic uncertainty interval (e.g., it is not a 95% Bayesian credible interval).
- It is **not** aleatoric uncertainty (intrinsic noise in network traffic).
- It does **not** explain *why* the model predicted a specific traffic percentage.

---

### 2.2 Built-in Model Warnings

The `predict_next_minute()` function in `predict_lstm.py` returns an array of string warnings alongside numerical outputs:
1. **Low-State Recall Warning**:
   `"Low-state recall was ~0% on the test day; a 'Medium' output does not rule out Low."`
   *Always present*. Warns security analysts that the model fails to detect transitions into low-bot activity.
2. **Clipping Notice**:
   `"Raw ensemble output <raw> was clipped to the valid 0-100 range."`
   Triggered if unconstrained regression outputs fall outside $[0, 100]$.
3. **Timestamp Spacing Advisory**:
   `"No Timestamp column: consecutive 1-minute spacing could not be checked."`
   Triggered when raw array input is supplied without ISO timestamps.

---

### 2.3 Out-of-Range Heuristic (`|z-score| > 5`)

Implemented in the demo (`forecast_app.py`), this checks if any incoming feature in the 5-minute window deviates by more than 5 standard deviations from the training distribution:

$$z_{i, t} = \frac{x_{i, t} - \mu_i}{\sigma_i}, \quad \text{Flagged if } \max_{t} |z_{i, t}| > 5$$

where $\mu_i$ and $\sigma_i$ are extracted from `scaler_features.joblib`.

> [!WARNING]
> This out-of-range check is an **integration heuristic**, not an ML contract guarantee. It has not been formally calibrated against false-positive rates on normal peak-hour traffic.

---

### 2.4 Critical Distinctions: What Current Signals Do and Do Not Mean

| Signal | Mathematical Source | Proper Interpretation | Prohibited Misrepresentation |
|---|---|---|---|
| `seed_predictions` | Outputs of 5 seeds | Variation across optimization trajectories | "Confidence distribution" |
| `seed_spread_pct_points` | Range of 5 seeds ($\max - \min$) | Model disagreement / instability on input | "Error bounds", "Confidence interval", or "SHAP" |
| `warnings` | Rule-based flags | Known empirical failure modes | "Bug in execution" |
| `predicted_state` | Threshold slicing ($<25, 25-50, \ge 50$) | Coarse classification of next-minute bot ratio | "Definitive attack detection" |

---

## 3. Technical Feasibility & Defensibility Assessment of SHAP

Team Member 3 evaluated whether SHAP (SHapley Additive exPlanations) should be added to the inference pipeline for this project.

### 3.1 DeepSHAP Evaluation
- **Methodology**: Uses DeepLIFT approximations designed for neural network gradient graphs.
- **Technical Incompatibilities**:
  - `shap.DeepExplainer` relies on TensorFlow v1/v2 graph execution hooks that frequently fail or crash when inspecting modern Keras 3 recurrent layers (`tf.keras.layers.LSTM`) in Python 3.13.
  - The runtime environment uses **TensorFlow 2.21.0** with **Keras 3.15.1**. Keras 3 executes operations via a backend abstraction layer which causes `DeepExplainer` to fail with `AttributeError` or invalid tensor graph errors.
- **Ensemble Multiplier**: Computing DeepSHAP over 5 separate models requires 5 separate backpropagation passes through time per explanation, increasing latency by $5\times$ to $10\times$.

### 3.2 KernelSHAP Evaluation
- **Methodology**: Model-agnostic perturbation using weighted linear regression over subset masks.
- **Dimensionality Challenge**: The input sequence is $5 \text{ steps} \times 7 \text{ features} = 35 \text{ variables}$.
  - To compute shapley values across 35 variables with adequate convergence requires $2 \times 35 + 2048 \approx 2,100+$ model forward evaluations.
  - For a 5-model ensemble, this requires $2,100 \times 5 = 10,500$ model evaluations per minute. On a standard CPU (native Windows without CUDA), this takes **12 to 25 seconds per request**, rendering an interactive API or dashboard unresponsive.
- **Independence Assumption Violation**: KernelSHAP assumes features can be perturbed independently. In network traffic time-series:
  - Packets and bytes are physically correlated ($r > 0.85$).
  - Minute $t$ is strongly autocorrelated with minute $t-1$ (lag-1 autocorrelation is $0.9022$).
  - Perturbing temporal cells independently creates synthetic inputs that violate physics (e.g., 0 bytes with 10,000 packets, or erratic sudden drops across 60 seconds), forcing the LSTM to extrapolate on out-of-distribution artifacts.

### 3.3 Defensibility & Scientific Rigor
1. **Explaining Unreliable Predictions**: The LSTM model has **~0% recall on Low-state targets** (all 23 Low targets predicted Medium). Explaining *why* an inaccurate model predicted a wrong state with high-precision Shapley values gives stakeholders a false sense of trust.
2. **Attribution Drift Across Seeds**: Due to seed disagreement (up to 25.2 points), Seed 42 might attribute prediction to `Total_Flows`, while Seed 45 attributes it to `Fwd_Bytes_Bot`. Averaging conflicting attribution profiles across disagreeing models produces uninterpretable explanations.

### 3.4 Assessment Verdict

> [!CAUTION]
> **Verdict**: Full SHAP integration is **NOT technically defensible or computationally viable** for this provisional LSTM ensemble at inference time.
>
> It must **NOT** be claimed as implemented. Attempting to force SHAP into `predict_lstm.py` introduces external library fragility, heavy latency, and misleading explanations.

---

## 4. Recommended Feasible Explainability Approaches

Instead of SHAP, the following three lightweight, defensible methods are recommended for subsequent implementation:

### 4.1 Local Feature Perturbation (Sensitivity Analysis)

#### Concept:
Measure how much the ensemble forecast changes when each feature $j \in \{1..7\}$ in the 5-minute window is perturbed by a standard perturbation $\delta$:

$$\text{Sensitivity}(j) = \frac{|\hat{y}(X + \Delta_j) - \hat{y}(X)|}{\hat{y}(X) + \epsilon}$$

where $\Delta_j$ shifts feature $j$ across all 5 timesteps by $+1$ standard deviation ($\sigma_j$ from `scaler_features`).

#### Advantages:
- Requires only $7$ forward passes of the ensemble (35 model calls total $\approx 40\text{ ms}$ on CPU).
- Preserves the temporal sequence structure.
- Directly informs the operator: *"Which traffic attribute is driving the next minute's bot percentage estimate upward?"*

---

### 4.2 Temporal Step Attribution (Time-Saliency)

#### Concept:
Evaluate the relative importance of recent vs. older minutes ($t-4, t-3, t-2, t-1, t$).

By masking or holding each minute constant (replacing with previous step) and observing output drift, the backend can compute a 5-element temporal weight vector:

$$W_{\text{time}} = [w_{t-4}, w_{t-3}, w_{t-2}, w_{t-1}, w_t], \quad \sum w = 1.0$$

#### Operational Value:
Informs the analyst whether the forecast is driven by an ongoing 5-minute trend or a sudden spike in the most recent 60 seconds.

---

### 4.3 Validated Input Distribution Health Metric

#### Concept:
Formalize the demo's heuristic into an explicit **Data Quality & In-Distribution Score**:

$$\text{HealthScore}(X) = 100 - \min\left(100, \, 10 \times \sum_{i=1}^7 \max(0, |z_i| - 3)\right)$$

- **Score 100**: All features within $3\sigma$ of training data mean. High model reliability.
- **Score < 50**: Multiple features exceed $4\sigma$ to $5\sigma$. Model is extrapolating; forecast should be flagged with high uncertainty.

---

## 5. Classification: Implemented vs. Next Steps vs. Future Enhancements

The table below provides a strict, honest audit of all explainability and uncertainty components.

| Component / Capability | Category | Implementation Location | Computational Cost | Scientific Defensibility |
|---|---|---|---|---|
| **5-Seed Output Disagreement** | ✅ **Already Implemented** | `predict_lstm.py` (`seed_spread_pct_points`) | Zero additional cost (uses ensemble predictions) | **High** (accurately measures ensemble variance) |
| **Low-Recall Warning** | ✅ **Already Implemented** | `predict_lstm.py` (`warnings` list) | Zero | **High** (transparently reports test limitation) |
| **Prediction Clipping Warning** | ✅ **Already Implemented** | `predict_lstm.py` (`warnings` list) | Zero | **High** (reports boundary violations) |
| **Missing Timestamp Advisory** | ✅ **Already Implemented** | `predict_lstm.py` (`validate_window`) | Zero | **High** (reports unverified sample spacing) |
| **Out-of-Range Heuristic (`\|z\| > 5`)** | ⚠️ **Demo Prototype Only** | `forecast_app.py` | Low ($< 1\text{ ms}$) | **Medium** (useful heuristic; unvalidated thresholds) |
| **Feature Sensitivity Analysis** | 🔲 **Can Be Implemented Next** | Proposed for `api.py` / backend | Low ($35\text{ model calls} \approx 40\text{ ms}$) | **High** (transparent perturbation without graph hooks) |
| **Temporal Step Attribution** | 🔲 **Can Be Implemented Next** | Proposed for `api.py` / backend | Low ($25\text{ model calls} \approx 30\text{ ms}$) | **High** (detects trend vs sudden surge) |
| **Distribution Health Score** | 🔲 **Can Be Implemented Next** | Proposed for `api.py` / backend | Negligible (vector math) | **High** (identifies out-of-distribution inputs) |
| **KernelSHAP Attribution** | 💡 **Proposed Future Enhancement** | External evaluation module | Very High ($>10,000\text{ calls} \approx 20\text{ s}$) | **Low** (violates time-series feature independence) |
| **DeepSHAP Attributions** | 💡 **Proposed Future Enhancement** | Offline research only | Moderate | **Unusable** (breaks on Keras 3 recurrent graphs) |
| **Conformal Prediction Intervals** | 💡 **Proposed Future Enhancement** | Requires validation calibration split | Low | **High** (provides true statistical coverage guarantees) |

---

## 6. Guidelines for Frontend Display (Member 4 Alignment)

To prevent misinterpretation by end-users or evaluation judges, Team Member 4 must adhere to these UX rules:

1. **Naming Rules**:
   - Label `seed_spread_pct_points` as **"Model Disagreement (Ensemble Spread)"**.
   - **NEVER** label ensemble spread as *"Confidence Score"*, *"Accuracy"*, or *"Certainty"*.
   - A spread of $2.0\%$ means the models agree; it does **not** guarantee the forecast is accurate.
2. **Visual Warning Badges**:
   - If `seed_spread_pct_points > 10.0`, display a visual caution indicator: *"High Model Disagreement"*.
   - If any warning is returned in the `warnings` array, render it in an amber/yellow advisory callout.
3. **No Phantom SHAP Visualizations**:
   - Do not display feature importance bar charts claiming to be "SHAP values".
   - If sensitivity analysis is integrated, clearly label it as *"Local Perturbation Sensitivity (Percentage Point Impact)"*.

---

## 7. System Limitations Summary

These limitations must be presented alongside all explainability analyses:
1. **Provisional Model**: The LSTM ensemble is a regenerated prototype, not production-certified.
2. **Single-Day Evaluation**: Validated on only 102 test windows from CSE-CIC-IDS2018; performance on other days or topologies is unverified.
3. **Low-State Blindspot**: ~0% recall on Low-state traffic (all 23 Low targets predicted Medium). Explanations for Low/Medium boundaries cannot be considered authoritative.
4. **Offline Scope**: The system evaluates static 5-minute historical slices; it is not connected to a live network packet stream.
5. **No Individual Flow Identification**: The model forecasts aggregate bot percentage; it does not indicate which specific IP, port, or packet was malicious.

---

*End of EXPLAINABILITY.md*
*Next: PHASE 7 — `docs/FRONTEND_HANDOFF.md` (awaiting confirmation)*
