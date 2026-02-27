# PramanaGST 🛡️

**Intelligent Multi-Entity GST Reconciliation and Risk Assessment Engine**

PramanaGST is a comprehensive end-to-end FinTech pipeline built to synthesize, graph, reconcile, and assess risk for massive sequences of Indian GST Taxation data.

By utilizing **Neo4j** as a powerful Knowledge Graph substrate alongside a distributed **FastAPI** backend and **React + Vite** analytical frontend, PramanaGST efficiently monitors GSTIN behaviors, traces elusive circular trading loopholes (e.g. `A ➔ B ➔ C ➔ A`), and assigns deterministic scoring algorithms + SHAP-driven ML inferences to predict vendor risk.

---

## 🏗️ Architecture Stack

1. **Synthetic Data Generator** (`scripts/`): Procedurally engineers identical JSON and Golden CSV batches populated with predefined edge cases and anomalies (tax evasion, missing invoices, duplicate numbering).
2. **Pydantic Validation Layer** (`backend/schemas/`): Strictly enforces typings across Invoices, Reconciliations, Returns, Golden Source Observations, and Vendor Models.
3. **Neo4j Graph Database** (`backend/graph/`): Ingests the normalized models to compute multidimensional vendor histories and relationships, linking Taxpayers to Returns, Payments, and IRNs.
4. **AI Risk & Reconciliation Engine** (`backend/reconciliation/` & `backend/risk/`): Parses the Neo4j Graph to triangulate invoice legitimacy between **GSTR-1, GSTR-2B, and Purchase Registers**. ML models combine with deterministic graphs to classify vendors into `LOW`, `MEDIUM`, `HIGH`, or `CRITICAL` risk tiers, explaining *why* a score is high using NLG (Natural Language Generation).
5. **Dashboard Command Center** (`frontend/`): An interactive, Cytoscape.js powered React UI that gives auditors a high-altitude view of macro tax risks, circular trade mappings, and individual invoice-level discrepancy reviews.

## 🚀 Quick Start (Local Setup)

### 1. Boot up Neo4j
Ensure Docker is installed and running, then spin up the Neo4j Knowledge Graph:
```bash
docker-compose up -d
```
*Wait for the `bolt://localhost:7687` server to accept connections.*

### 2. Generate Data & Seed Graph
Execute the orchestration script to synthesize the Golden Mock data, ingest it to Neo4j, and calculate the Final Audit Metrics (Total Tax at Risk and CRITICAL loops):
```bash
$env:PYTHONPATH="." 
python scripts/seed_graph.py
```

### 3. Launch FastAPI Backend
Launch the internal API endpoints:
```bash
$env:PYTHONPATH="." 
python -m uvicorn backend.main:app --reload
```
API Documentation will be available at: http://localhost:8000/docs

### 4. Launch React Frontend
Navigate to the frontend layer to boot up the Command Center:
```bash
cd frontend
npm run dev
```
Explore the dashboard visually at: http://localhost:5173

---

*PramanaGST - Developed for Contract 1 MVP Verification.*
