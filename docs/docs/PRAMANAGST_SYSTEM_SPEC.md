# PRAMANAGST — SYSTEM SPECIFICATION DOCUMENT (SSD)

## Intelligent GST Reconciliation Using Knowledge Graphs

---

# 1. Project Overview

**Project Name:** PramanaGST
**Domain:** FinTech / GovTech / Graph AI
**Problem Statement:** PS-76 — Intelligent GST Reconciliation Using Knowledge Graphs

PramanaGST is a contract-driven, knowledge-graph based system that models India's GST ecosystem as interconnected financial entities and performs reconciliation using graph traversal rather than flat table matching.

The system detects:

* Broken ITC chains
* Missing tax payments
* Invoice mismatches
* Vendor compliance risks

The architecture prioritizes **deterministic data modeling, explainability, and auditability**.

---

# 2. Core Philosophy

## 2.1 Graph-First Thinking

GST reconciliation is fundamentally a **relationship validation problem**.

Instead of comparing tables:

```
Buyer → Invoice → Seller → Return → Payment
```

is validated as a graph traversal.

---

## 2.2 Contract-Driven Architecture

Each system layer communicates ONLY via formal contracts.

Layers are isolated and independently buildable.

```
Layer A → Contract → Layer B
```

No direct internal dependencies allowed.

---

# 3. System Architecture

```
Datasets
   ↓
Ingestion Layer
   ↓
Knowledge Graph (Neo4j)
   ↓
Reconciliation Engine
   ↓
Risk Intelligence + Explainability
   ↓
API Layer
   ↓
Dashboard
```

---

# 4. Technology Stack

## Backend

* Python 3.11+
* FastAPI
* Pandas / NumPy
* Pydantic

## Knowledge Graph

* Neo4j
* Cypher Queries
* NetworkX (analytics)

## AI Layer

* Scikit-learn
* XGBoost
* LLM API (explanations only)

## Frontend

* React + Vite
* TailwindCSS
* shadcn/ui
* react-force-graph
* Recharts

---

# 5. Contract System

## Contract 1 — Ingestion → Knowledge Graph ✅

Transforms source datasets into graph-ready entities.

## Contract 2 — Graph → Reconciliation

Provides graph evidence objects.

## Contract 3 — Reconciliation → Risk AI

Outputs structured mismatch intelligence.

## Contract 4 — Risk AI → API

Produces finalized risk decisions and explanations.

## Contract 5 — API → Dashboard

Provides UI-ready responses.

---

# 6. Contract 1 (CURRENT IMPLEMENTATION SCOPE)

## Objective

Generate deterministic source datasets that can be transformed into graph entities without ambiguity.

---

## 6.1 Entity Types

| Entity   | Description            |
| -------- | ---------------------- |
| TAXPAYER | GST registered entity  |
| INVOICE  | Financial transaction  |
| RETURN   | Filed GST return       |
| PAYMENT  | Tax payment            |
| IRN      | e-Invoice registration |

---

## 6.2 Required Relationships

```
Taxpayer ─ISSUED→ Invoice
Invoice ─RECEIVED_BY→ Taxpayer
Invoice ─REPORTED_IN→ Return
Taxpayer ─PAID_TAX→ Return
Invoice ─HAS_IRN→ IRN
```

Datasets MUST allow deterministic creation of these edges.

---

# 7. Dataset Design Rules

## Generation Order (MANDATORY)

1. Taxpayers
2. Invoices
3. Returns
4. Payments
5. ITC Claims
6. IRNs

Datasets are relationship-consistent, not random.

---

## Required Datasets

### taxpayers.csv

```
gstin
legal_name
state_code
registration_type
```

### gstr1.csv

```
invoice_number
supplier_gstin
recipient_gstin
invoice_date
invoice_value
cgst_amount
sgst_amount
igst_amount
supply_type
irn
```

### gstr2b.csv

```
invoice_number
recipient_gstin
itc_claimed
claim_period
```

### payments.csv

```
supplier_gstin
return_period
tax_paid
```

### einvoice.csv

```
irn
invoice_number
generation_timestamp
status
```

---

# 8. Dataset Constraints

* GSTIN references must resolve.
* Tax totals must match invoice value.
* Dates must be ISO-8601.
* Deterministic generation using fixed seed.
* Some mismatches intentionally included.

---

# 9. Ingestion Layer Responsibilities

The ingestion layer:

1. Normalizes records
2. Validates schema
3. Generates deterministic entity IDs
4. Produces Contract-1 Batch JSON

Output format:

```json
{
  "batch_metadata": {},
  "entities": [],
  "rejected_records": []
}
```

---

# 10. Knowledge Graph Model

## Node Labels

* Taxpayer
* Invoice
* Return
* Payment
* IRN
* SourceObservation

Each entity node is unique via `entity_ref_id`.

---

## Graph Principles

* Entities are immutable truths.
* Observations represent filings.
* Multiple filings attach to same entity.

---

# 11. Development Workflow

## Branch Strategy

```
main → demo stable
dev → integration
feature/* → development
```

---

## Push Rule

Push ONLY when a contract boundary stabilizes.

Never push partial schemas.

---

# 12. AI Worker Protocol

| Model           | Responsibility                  |
| --------------- | ------------------------------- |
| Opus Thinking   | Architecture & schema reasoning |
| Gemini Pro      | Implementation                  |
| Sonnet Thinking | Validation & logic refinement   |
| Gemini Flash    | Utility tasks                   |

AI agents must follow contracts strictly.

---

# 13. Folder Structure

```
backend/
  ingestion/
  graph/
  reconciliation/
  risk_ai/
  api/

contracts/
docs/
frontend/
scripts/
```

Layers must not cross boundaries.

---

# 14. Design Principles

1. Deterministic IDs
2. Idempotent ingestion
3. Graph as source of truth
4. Explainability first
5. Contract stability over speed

---

# 15. Success Definition (Hackathon Scope)

A successful system demonstrates:

* Graph-based reconciliation
* Vendor risk scoring
* Explainable audit trail
* Interactive visualization

---

# 16. Meaning of Pramana

**Pramāṇa (प्रमाण)** — Sanskrit for *proof, validation, or evidence*.

The system represents verified financial truth through structured reasoning.

---

END OF SYSTEM SPECIFICATION
