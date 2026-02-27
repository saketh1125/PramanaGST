# Technology Stack

PramanaGST utilizes a modern, performance-oriented stack tuned for data processing and graph analytics.

## Backend 
- **Language:** Python 3.11+
- **Framework:** FastAPI (High performance, built-in async, native OpenAPI support)
- **Validation:** Pydantic V2 (Rust-backed core for extremely fast schema validation)
- **Data Engineering:** Pandas & NumPy (Vectorized normalization of large CSV/JSON sets)
- **Testing:** Pytest

## Knowledge Graph
- **Database:** Neo4j (Version 5+)
- **Query Language:** Cypher
- **Driver:** `neo4j-python-driver`
- **Analytics:** NetworkX (For in-memory graph algorithms prior to DB ingestion)

## AI & Machine Learning
- **Tabular ML:** Scikit-learn & XGBoost (Vendor risk scoring based on reconciliation metrics)
- **Explainability:** LLM Integration (OpenAI API / Local alternatives like LLaMA) for translating graph anomalies into auditor-friendly narratives.

## Frontend
- **Framework:** React + Vite
- **Styling:** TailwindCSS
- **Components:** shadcn/ui
- **Charting:** Recharts
- **Graph Visualization:** `react-force-graph` (WebGL acceleration for large entity networks)
