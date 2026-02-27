# PramanaGST System Overview

## Architecture Vision
PramanaGST is a specialized intelligence platform designed to transition GST reconciliation from a flat-file matching process to a **multi-hop knowledge graph validation**. 

By modeling taxpayers, invoices, return filings, and tax payments as interconnected nodes, the system inherently captures the foundational structure of the Indian GST framework.

## Core Capabilities
1. **Intelligent Ingestion:** Normalizes heterogeneous dataset fragments (GSTR-1, GSTR-3B, e-Invoices) into a canonical format mapped to strictly typed Pydantic schemas.
2. **Graph Construction:** Translates tabular data into Neo4j graph structures, explicitly defining financial relationships.
3. **Reconciliation Engine:** Executes Cypher-based validation to verify entire Input Tax Credit (ITC) supply chains across multiple vendor hops.
4. **Risk Intelligence:** Generates risk scores using AI models based on graph traversal features (e.g., circular trading detection).
5. **Dashboard API:** Exposes GraphQL/REST endpoints for an interactive UI to visualize relationships and audit narratives.

## Technology Stack
- **Backend:** Python 3.11+, FastAPI, Pydantic, Pandas
- **Knowledge Graph:** Neo4j (Cypher)
- **AI/ML:** Scikit-learn, XGBoost (Risk scoring)
- **Frontend:** React, TailwindCSS, Force Graph

## The "Layered Contract" Philosophy
To enable high-velocity parallel development, PramanaGST employs a strict **Contract-driven Architecture**. The system is divided into five isolated layers. Communication between layers occurs *exclusively* via versioned JSON schemas (Contracts). As long as a layer fulfills its output contract, its internal implementation can be freely optimized or rewritten without breaking dependent teams.
