# Contract-4: Risk Intelligence Interface

## Purpose

Contract-4 defines the interface between the Risk AI engine and the API layer. It is the authoritative, deterministic risk-intelligence contract: the scoring engine is deterministic (no ML theater on synthetic data) and every score is explainable from signals. Absolute: vendor risk scores are computed with fixed weights; narration may use an LLM but the LLM can never change a score — narrative is explanation-only.

Score weights: mismatch 35%, ghost (unreported invoices) 25%, shortfall 25%, cycle 15%.
Bands: HIGH >= 60, MEDIUM >= 30, LOW < 30.

## Files

- `../../contracts/contract_4.json` — generated JSON Schema (draft-07), definitions for `RiskSignal`, `VendorRisk`, `AuditNarrativeResponse`
- `../../backend/risk_ai/models/vendor_risk.py` — canonical `RiskSignal` / `VendorRisk` models (do not duplicate)
- `../../backend/risk_ai/models/contract4.py` — `AuditNarrativeResponse` model
- `../../backend/risk_ai/explainability/narrator.py` — narrative generation (template fallback; LLM optional via `PRAMANAGST_LLM_URL` + `OPENAI_API_KEY`, never alters score)
- `examples/vendor_risk.json` — example `VendorRisk` payload
- `examples/audit_narrative.json` — example `AuditNarrativeResponse` payload

## Regeneration

```bash
python scripts/generate_contract4.py
```

Output is deterministic; running it twice produces byte-identical `contracts/contract_4.json`.
