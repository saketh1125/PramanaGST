# Top-Level Design Principles

The PramanaGST build is guided by five non-negotiable architectural principles.

## 1. Contract-First Development
No code is written until the JSON schema interface between two interacting layers is agreed upon and finalized in the `contracts/` repository folder. Once a contract is sealed, teams work strictly against that schema.

## 2. Unidirectional Data Flow
Data flows strictly from Ingestion -> Graph -> Reconciliation -> Risk -> API. Backward dependencies are strictly prohibited to prevent distributed monolith anti-patterns.

## 3. Strict Schema Validation at Boundaries
Every layer must rigorously validate incoming data against the expected contract before processing. `Pydantic` and `FastAPI` are utilized heavily for this purpose. 

## 4. Graph-Native Thinking
We do not build a relational database in Neo4j. We do not use JOIN-like thinking. We model verbs as edges (e.g., `[:FILED]`, `[:PAID]`) and nouns as nodes. Queries must leverage path traversal (`MATCH (a)-[*]->(b)`).

## 5. Explainability over Black-box Accuracy
A risk score of `99` is useless to a GST auditor without knowing *why*. Every anomaly or AI-generated risk score MUST be accompanied by an explainable evidence vector containing the exact nodes and edges that triggered the flag.
