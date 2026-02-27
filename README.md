# PramanaGST
### Intelligent GST Reconciliation Using Knowledge Graphs

PramanaGST is a Knowledge Graph–driven GST reconciliation and compliance intelligence platform built for **PS-76 (FinTech / GovTech / Graph AI)**.

The system models GST filings as interconnected entities and performs **multi-hop graph traversal** to validate Input Tax Credit (ITC) chains, detect mismatches, and generate explainable audit intelligence.

---

## 🚀 Problem Statement

India’s GST reconciliation is fundamentally a **relationship validation problem**, not a flat table matching task.

PramanaGST transforms GST datasets into a **financial knowledge graph** enabling:

- Invoice-to-tax-payment validation
- ITC eligibility verification
- Vendor compliance risk scoring
- Explainable audit trails

---

## 🧠 System Philosophy

1. Data → Relationships → Intelligence
2. Logical reconciliation before AI prediction
3. Explainability as a primary output
4. Graph reasoning over tabular matching

---

## 🏗️ System Architecture
Data Ingestion
↓
Knowledge Graph (Neo4j)
↓
Reconciliation Engine
↓
Risk Intelligence + Explainability
↓
REST API Layer
↓
Interactive Dashboard

---

## 📦 Technology Stack

### Backend
- Python 3.11+
- FastAPI
- Pandas + NumPy
- Pydantic

### Knowledge Graph
- Neo4j
- neo4j-python-driver
- NetworkX (analytics)

### AI & Risk Intelligence
- Scikit-learn
- XGBoost
- LLM API (Explainable Audit Reports)

### Frontend
- React + Vite
- TailwindCSS
- shadcn/ui
- Recharts
- react-force-graph

---

## 🔄 Data Flow
Raw GST Data
→ Normalization
→ Graph Construction
→ Multi-hop Traversal
→ Risk Scoring
→ Explainable Audit Output
→ Dashboard Visualization


---

## 🤝 Parallel Development Contracts

The project uses strict **layer contracts** enabling parallel development.

| Contract | Flow |
|---|---|
| ✅ Contract 1 | Ingestion → Knowledge Graph |
| ✅ Contract 2 | Knowledge Graph → Reconciliation |
| ✅ Contract 3 | Reconciliation → Risk AI |
| ✅ Contract 4 | Risk AI → API Layer |
| ✅ Contract 5 | API Layer → Dashboard |

Each layer communicates only through structured JSON schemas.

---

## 📁 Project Structure

PramanaGST/
│
├── backend/
│ ├── ingestion/
│ ├── graph/
│ ├── reconciliation/
│ ├── risk_ai/
│ └── api/
│
├── frontend/
│
├── contracts/
│ ├── contract_1.json
│ ├── contract_2.json
│ ├── contract_3.json
│ ├── contract_4.json
│ └── contract_5.json
│
├── docs/
└── README.md

---

## ⚙️ Setup Instructions

### 1️⃣ Clone Repository
git clone https://github.com/saketh1125/PramanaGST.git

cd PramanaGST

---

### 2️⃣ Backend Setup
python -m venv venv
source venv/bin/activate # Mac/Linux
venv\Scripts\activate # Windows

pip install -r requirements.txt

Run backend:
uvicorn backend.api.main:app --reload


---

### 3️⃣ Neo4j Setup
- Install Neo4j Desktop OR use Neo4j Aura Free
- Create database
- Update `.env`:

NEO4J_URI=
NEO4J_USER=
NEO4J_PASSWORD=

---

### 4️⃣ Frontend Setup
cd frontend
npm install
npm run dev

---

## 📊 Core Features

- Knowledge Graph GST Modeling
- Multi-hop ITC Validation
- Mismatch Classification Engine
- Vendor Compliance Risk Scoring
- Explainable Audit Narratives
- Interactive Graph Visualization

---

## 🧩 Key Innovation

PramanaGST treats GST reconciliation as a **graph traversal problem**, enabling detection of:

- Broken ITC chains
- Circular trading patterns
- Missing tax payments
- High-risk vendor clusters

---

## 👥 Team Workflow

- Contracts define layer boundaries
- Each team works independently
- Integration happens via stable schemas

---

## 🎯 Hackathon Focus

- High-impact visualization
- Explainable AI decisions
- Enterprise-grade architecture
- Deployable prototype

---

## 📄 License
MIT License

---

## ✨ Project Name Meaning

**Pramana** (प्रमाण) — Sanskrit for *proof, validation, or evidence*.

PramanaGST represents **verified financial truth through intelligent reasoning**.

