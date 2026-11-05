# SIH26153 – ML Model Handoff

## Project
AI-Based Network Attack Forecasting from Network Traffic Data.

## Overview
This repository contains the provisional LSTM forecasting model and the supporting files required for application integration.

## Folder Structure

- `model/` – Exported trained LSTM models, scalers and configuration.
- `integration/` – Prediction script, self-test script and integration contract.
- `evaluation/` – Model comparison and evaluation evidence.

## Model Input
The model requires:
- 5 consecutive one-minute traffic records.
- 7 features in raw units.
- A one-minute forecast horizon.

## Model Output
- Predicted Bot traffic percentage.
- Predicted traffic state: Low, Medium or High.
- Seed predictions and warnings.

## Important Limitations
- Provisional model.
- Offline/batch forecasting only.
- Not live, real-time or production-validated.
- Low-state recall was approximately 0% on the test day.

Refer to `integration/ML_INTEGRATION_CONTRACT.md` for the complete integration instructions.
