# Data Flow Architecture

The PramanaGST pipeline is unidirectional and strictly governed by contracts at each interface boundary.

## High-Level Pipeline

```mermaid
flowchart TD
    %% Define layers
    A((Datasets)) -->|Raw CSV/JSON| B[Ingestion Layer]
    B -->|Contract 1: Canonical JSON| C[(Neo4j Knowledge Graph)]
    C -->|Contract 2: Graph Subsets| D[Reconciliation Engine]
    D -->|Contract 3: Mismatch Vectors| E[Risk AI Layer]
    E -->|Contract 4: Scored Entities| F[API Layer]
    F -->|Contract 5: View Models| G[Frontend Dashboard]

    %% Styling
    classDef contract fill:#f9f,stroke:#333,stroke-width:2px;
    class B,C,D,E,F fill:#bbf,stroke:#333;
```

## Stage Descriptions

1. **Ingestion Layer:** Reads raw, mocked dataset files. Applies Pandas-driven normalization and sanitization. Validates the output strictly against the Pydantic models (e.g., `Taxpayer`, `Invoice`) defined in Contract 1.
2. **Knowledge Graph Layer:** Consumes Contract 1 payloads. Executes optimized Neo4j Cypher queries (e.g., `UNWIND`) to merge nodes and build relationships (e.g., `FILED_BY`, `BILLED_TO`, `PAID_TOWARDS`).
3. **Reconciliation Engine:** Queries the graph (Contract 2) to identify anomalies:
   - Invoice exists in GSTR-1 but not in GSTR-2B.
   - ITC claimed in GSTR-3B exceeds eligible ITC from supplier invoices.
4. **Risk AI Layer:** Ingests the output vectors of the Reconciliation Engine (Contract 3). Applies lightweight ML models to classify risk severity and generates an explainable audit narrative.
5. **API Layer:** Wraps the entire backend stack in a FastAPI application, serving endpoints formatted to Contract 5 for UI consumption.
