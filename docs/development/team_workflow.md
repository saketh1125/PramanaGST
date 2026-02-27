# Team Workflow

PramanaGST embraces a highly parallel, autonomous team structure enabled by our strict contract-driven architecture.

## Team Isolation
Teams are organized around the five core architectural layers:
1. **Ingestion & Dataset**
2. **Knowledge Graph**
3. **Reconciliation Engine**
4. **Risk & AI**
5. **API & Dashboard**

## Working Against Contracts
Because Contract 1 (Ingestion ↔ Graph) is defined, the Graph team does not need to wait for the Ingestion team to finish building Python parsers. 
- The Graph team generates mock JSON data that complies with Contract 1's Pydantic schema and uses it to build Cypher ingestion scripts.
- Simultaneously, the Ingestion team builds Pandas scripts to generate that exact same JSON schema.

This pattern repeats across every layer.

## Integration Points
Integration testing occurs ONLY at the contract boundaries. If Layer A outputs valid Contract JSON, and Layer B correctly consumes valid Contract JSON, the integration is considered successful.
