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
- **Purpose:** Augments the Reconciliation data with calculated Risk Scores (0-100) and generated English-language Audit Narratives.

### Contract 5: API Layer ↔ Frontend Dashboard
- **Owner:** API Team
- **Consumer:** Frontend Team
- **Purpose:** Defines the precise view models required by the React dashboard, heavily optimized for rendering force-directed graphs and statistical widgets.

## Modifying Contracts
Contracts represent a hard boundary. Any change to a contract requires explicit cross-team agreement. Breaking changes require v-bumping the contract version.
