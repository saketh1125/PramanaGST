# Contracts Overview

Contracts are the foundational API boundaries of PramanaGST. They are defined as JSON Schemas generated from Python Pydantic models.

## The Five Contracts

### Contract 1: Ingestion ↔ Knowledge Graph
- **Owner:** Ingestion Team
- **Consumer:** Graph Team
- **Purpose:** Defines the canonical structure of the five core entities: `TAXPAYER`, `INVOICE`, `RETURN`, `PAYMENT`, `IRN`.
- **Status:** **FINALIZED (v1.0.0)**

### Contract 2: Graph ↔ Reconciliation Engine
- **Owner:** Graph Team
- **Consumer:** Reconciliation Team
- **Purpose:** Defines the structure of sub-graphs and query results extracted for validation (e.g., "All invoices for a given GSTIN in period MMYYYY and their matching status").

### Contract 3: Reconciliation Engine ↔ Risk AI
- **Owner:** Reconciliation Team
- **Consumer:** Risk AI Team
- **Purpose:** Defines the feature vectors and anomaly flags identified during graph traversal (e.g., `ITC_MISMATCH_AMOUNT`, `MISSING_INVOICE_COUNT`).

### Contract 4: Risk AI ↔ API Layer
- **Owner:** Risk AI Team
- **Consumer:** API Team
- **Status:** **IMPLEMENTED (v1.0.0)**
- **Models:** `VendorRisk`, `RiskSignal` (`backend/risk_ai/models/vendor_risk.py`), `AuditNarrativeResponse` (`backend/risk_ai/models/contract4.py`)
- **Served by:** `GET /api/v1/risks/{gstin}` (`VendorRisk`), `GET /api/v1/risks/{gstin}/explain` (`AuditNarrativeResponse`; keeps `gstin` + `narrative` top-level)
- **Generator:** `python scripts/generate_contract4.py` -> `contracts/contract_4.json`
- **Examples/docs:** `contracts/contract_4_risk_api/`

### Contract 5: API Layer ↔ Frontend Dashboard
- **Owner:** API Team
- **Consumer:** Frontend Team
- **Status:** **IMPLEMENTED (v1.0.0)**
- **Models:** `RiskSummary`, `VendorRiskView`, `GraphNode`, `GraphLink`, `GraphView`, `ErrorResponse` (`backend/api/models/contract5.py`)
  - `RiskSummary`: `contract_version`, `entity="RISK_SUMMARY"`, `totalVendors`, `highRisk`, `mediumRisk`, `lowRisk`, `averageScore`. Full vendor population; unaffected by `/risks` filters. Rendered by the dashboard summary cards.
  - `VendorRiskView`: presentation projection of Contract 4 `VendorRisk` — `contract_version`, `entity="VENDOR_RISK_VIEW"`, `gstin`, `legalName`, `score`, `band`, `reasons`, flat `invoicesIssued` (no nested `signals`; detail signals live on `GET /api/v1/risks/{gstin}`)
  - `GraphNode`: `id`, `label`, optional `legalName`, `invoiceNumber`, `returnId`, `extra="forbid"`. `GraphLink`: `source`, `target`, optional `type`, `extra="forbid"`. Envelope metadata (`contract_version`, `entity="GRAPH_VIEW"`) lives on `GraphView`; nodes/links carry no per-item metadata.
  - `ErrorResponse`: `contract_version`, `entity="ERROR"`, `{"error": {"code", "message"}}` — covers routing-level 404 (`NOT_FOUND`), `VENDOR_NOT_FOUND`, `TAXPAYER_NOT_FOUND`, `VALIDATION_ERROR` (422), `SERVICE_UNAVAILABLE` (503), `INTERNAL_ERROR` (500)
- **Served by:** `GET /api/v1/risk-summary`, `GET /api/v1/risks?band=&minScore=` (no pagination — ~20-vendor dataset), `GET /api/v1/graph/ego/{gstin}`
- **Generator:** `python scripts/generate_contract5.py` -> `contracts/contract_5.json`
- **Examples/docs:** `contracts/contract_5_api_dashboard/`

Auth is out of scope for Contracts 1–5. Contracts 1–3 are unchanged.

## Modifying Contracts
Contracts represent a hard boundary. Any change to a contract requires explicit cross-team agreement. Breaking changes require v-bumping the contract version.
