# PramanaGST

# Intelligent GST Reconciliation & Risk Intelligence Platform
### Solving Tax Compliance with Graph AI and Multi-Hop Traversal

## 📌 Project Overview
**Intelligent GST Reconciliation** is a relationship-validation engine built to solve the systemic failures of traditional tabular tax matching. This platform treats GST data as a complex web of multi-hop dependencies across taxpayers, invoices, returns, and payments.

By utilizing **Knowledge Graphs**, the system moves beyond simple 1-to-1 matching to detect complex fraud patterns like **Circular Trading** and **Ghost Billing**, providing explainable audit trails for tax authorities.

---

## 🏛 System Architecture
This platform follows a fixed seven-layer architecture to ensure semantic depth and logical rigor:

1.  **Data Ingestion Layer**: Validates and normalizes heterogeneous GST datasets (GSTR-1, GSTR-3B, E-Way Bills).
2.  **Knowledge Graph Construction**: Converts normalized records into a network of nodes and relationships using Neo4j.
3.  **Reconciliation Engine**: Performs multi-hop traversal to validate invoice-to-tax-payment chains.
4.  **Risk AI Layer**: Combines rule scoring with Graph Analytics (NetworkX) and ML (XGBoost) for compliance risk estimation.
5.  **Explainability Layer**: Uses LLM APIs to generate human-readable reasoning for every flagged mismatch.
6.  **API Layer**: Exposes structured intelligence outputs via RESTful FastAPI endpoints.
7.  **Dashboard**: Provides real-time risk visualization using React and `react-force-graph`.

---

## 💻 Tech Stack
| Component | Technology |
| :--- | :--- |
| **Backend** | Python, FastAPI, Pandas, NumPy, Pydantic |
| **Knowledge Graph** | Neo4j, neo4j-python-driver, NetworkX |
| **AI/ML** | scikit-learn, XGBoost, LLM API (Explainability) |
| **Frontend** | React + Vite, TailwindCSS, shadcn/ui |
| **Visualization** | react-force-graph, Recharts, Lucide-React |

---

## 🕸 Knowledge Graph Modeling
The system is built on the principle that **"Data must become relationships before intelligence can be applied"**.

- **Nodes**: `Taxpayer (GSTIN)`, `Invoice`, `Return (GSTR-1/3B)`, `Payment`, `IRN`, `EWayBill`.
- **Relationships**: 
    - `ISSUED_BY`: Links an Invoice to a Seller.
    - `CLAIMED_BY`: Links an Invoice to a Buyer.
    - `REPORTED_IN`: Links an Invoice to a GSTR-1 filing.
    - `PAID_TAX_IN`: Links a Return to a GSTR-3B payment node.



---

## 🚀 Key Features
- **Multi-Hop Reconciliation**: Validates the entire chain from Invoice issuance to actual tax payment.
- **Vendor Risk Scoring**: Dynamically calculates compliance scores based on a vendor's historical "broken paths" in the graph.
- **Circular Trade Detection**: Identifies shell company loops (A → B → C → A) designed to inflate Input Tax Credit (ITC).
- **Explainable Audit Trails**: Provides natural language justifications for why a specific ITC claim was denied.

---

## 🛠 Installation & Setup

### Prerequisites
- Python 3.9+
- Neo4j Desktop / Aura DB
- Node.js & npm

### Backend Setup
1. Clone the repository and navigate to the `backend` folder.
2. Install dependencies:
   ```bash
   pip install fastapi uvicorn neo4j pandas networkx xgboost pydantic

   Configure your .env with Neo4j credentials and LLM API keys.

Run the server:
uvicorn main:app --reload



It uses the FastAPI + Neo4j + React stack and aligns with the goals of ACM KLH HackWithAI.






👥 Team & Hackathon

Event: ACM KLH HackWithAI 

Domain: FinTech / GovTech / Graph AI


Duration: 24-Hour Sprint 

Developed by: Team Pramana 

Built with a graph-first philosophy for the next generation of tax intelligence.
