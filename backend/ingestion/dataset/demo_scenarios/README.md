# Demo scenarios — SYNTHETIC data, clearly labelled as such.

This directory is NOT real GST data. Every taxpayer, invoice, amount, and
finding below is fabricated to exercise the deterministic risk engine and
the dashboard investigation flow. Never represent these results as real
fraud findings.

Load it with: `PRAMANAGST_DATA_DIR=backend/ingestion/dataset/demo_scenarios`

## Scenarios

| Vendor | GSTIN | Scenario | Expected outcome |
|---|---|---|---|
| Normal Traders | 29AAAAA0001A1Z5 | NORMAL_VENDOR: 4 invoices, exact ITC claims, tax fully paid | score 0, LOW, no evidence |
| Mismatch Heavy Industries | 29AAAAA0002B1Z5 | MISMATCH_HEAVY: 5/5 ITC claims diverge (claimed 100 vs tax 1000) | score 35, MEDIUM, MISMATCH evidence |
| Shortfall Enterprises | 29AAAAA0003C1Z5 | TAX_SHORTFALL: liability 6000, paid 1000 | score 20.83, LOW, TAX_SHORTFALL evidence |
| Loop Alpha Traders | 29AAAAA0005E1Z5 | CIRCULAR_NETWORK: two-way trade with Loop Beta | score 15, LOW, CYCLE_MEMBERSHIP evidence |
| Loop Beta Traders | 29AAAAA0006F1Z5 | CIRCULAR_NETWORK: two-way trade with Loop Alpha | score 15, LOW, CYCLE_MEMBERSHIP evidence |
| Multi Signal High Risk | 29AAAAA0007G1Z5 | MULTI_SIGNAL_HIGH_RISK: 8/10 mismatches + 90% shortfall + cycle | score 65.5, HIGH, 3 evidence items |
| Loop Partner | 29AAAAA0008H1Z5 | CIRCULAR_NETWORK: closes the loop with Multi Signal | score 15, LOW, CYCLE_MEMBERSHIP evidence |

## Known gap: GHOST_INVOICE

There is intentionally no ghost scenario here. The batch builder always emits
a GSTR-1 return per (supplier, period), so every supplied invoice receives a
`REPORTED_IN` edge and the ghost rate can never exceed 0 through the CSV
pipeline (see `docs/architecture/risk_engine.md`). The ghost scoring path is
covered by synthetic unit tests (`test_ghost_only_scores_25_low`,
`test_ghost_evidence_names_invoice_nodes`) instead.
