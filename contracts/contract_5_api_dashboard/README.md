# Contract-5: API -> Dashboard View Models

## Purpose

Contract-5 defines the view models served by the API layer to the React dashboard: the fleet-level risk summary, the flattened vendor-risk list, the force-graph view for a taxpayer ego network, and the uniform error envelope. These are projections of the Contract 4 domain models optimized for rendering.

> Contract 4 (`VendorRisk`) is the authoritative risk intelligence. Contract 5 models are presentation projections of the same vendor population; they must not carry independent risk semantics.

## Files

- `../../contracts/contract_5.json` — generated JSON Schema (draft-07), definitions for `RiskSummary`, `VendorRiskView`, `GraphNode`, `GraphLink`, `GraphView`, `ErrorResponse`
- `../../backend/api/models/contract5.py` — canonical view models (do not duplicate; Risk AI does not own Contract 5)
- `../../backend/api/main.py` — endpoints serving these models
- `examples/risk_summary.json` — `GET /api/v1/risk-summary` payload
- `examples/vendor_risk_view.json` — one `GET /api/v1/risks` item
- `examples/graph_view.json` — `GET /api/v1/graph/ego/{gstin}` payload
- `examples/error.json` — error envelope

## Metadata policy

`contract_version` and `entity` are real serialized fields on: `RiskSummary`, `VendorRiskView`, `GraphView`, `ErrorResponse`. `GraphNode`/`GraphLink` deliberately carry no per-item metadata — the enclosing `GraphView` envelope carries it. `json_schema_extra` is used only for schema-level entity labelling, never as a substitute for a wire field.

## Models

- **RiskSummary**: `contract_version`, `entity` (`"RISK_SUMMARY"`), `totalVendors`, `highRisk`, `mediumRisk`, `lowRisk`, `averageScore` (0–100). Derived from the same `_ctx.vendors` snapshot as `/api/v1/risks`. **Not affected by `/risks` filters** — `GET /risks?band=HIGH` filters the list but does not change `RiskSummary` totals. The dashboard renders it as summary cards.
- **VendorRiskView**: `contract_version`, `entity` (`"VENDOR_RISK_VIEW"`), `gstin`, `legalName`, `score`, `band`, `reasons`, `invoicesIssued`. This is a **presentation projection of Contract 4 `VendorRisk`**. The detailed signals (`mismatchedClaims`, `unreportedInvoices`, `taxLiability`, `taxPaid`, `shortfall`, `inCycle`) are intentionally omitted here; fetch them from `GET /api/v1/risks/{gstin}`. The frontend list view uses only `gstin`, `legalName`, `score`, `band`, `invoicesIssued`.
- **GraphNode**: `id`, `label`, optional `legalName`, `invoiceNumber`, `returnId`. `extra="forbid"` — internal graph attributes (supplierGstin, totalValue, Neo4j internals, …) cannot leak into the contract.
- **GraphLink**: `source`, `target`, optional `type`. `extra="forbid"` — same leakage protection.
- **GraphView**: `contract_version`, `entity` (`"GRAPH_VIEW"`), `nodes`, `links`. `nodes`/`links` remain top-level so `react-force-graph-2d` can consume the response directly.
- **ErrorResponse**: `contract_version`, `entity` (`"ERROR"`), `{"error": {"code", "message"}}`. Codes: `VENDOR_NOT_FOUND` (404), `TAXPAYER_NOT_FOUND` (404), `NOT_FOUND` (404, unknown route), `VALIDATION_ERROR` (422, including bad `band`/`minScore`/`depth` parameters), `SERVICE_UNAVAILABLE` (503 Neo4j), `INTERNAL_ERROR` (500). All HTTP and validation error paths, including routing-level 404s, return this shape.

## Endpoints

- `GET /api/v1/risk-summary` — fleet totals computed from the vendor risk set (full population, unfiltered).
- `GET /api/v1/risks?band=HIGH&minScore=30` — flattened `VendorRiskView` list, still sorted by score desc. **No pagination**: the synthetic dataset is ~20 vendors, so the full list is cheap; revisit with a real dataset.
- `GET /api/v1/graph/ego/{gstin}?depth=1..3` — `GraphView`; depth is clamped to 1–3.
- Contract 4 endpoints `GET /api/v1/risks/{gstin}` and `GET /api/v1/risks/{gstin}/explain` keep serving `VendorRisk` / `AuditNarrativeResponse`.

## Regeneration

```bash
python scripts/generate_contract5.py
```

Output is deterministic; running it twice produces byte-identical `contracts/contract_5.json`.

Auth is out of scope for Contract 5; it belongs to the API/deployment/security layer.
