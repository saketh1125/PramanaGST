# Batch Format

To prevent memory crashes during large file ingestion, data is emitted to Contract 1 in chunks.

## File Naming Convention
Normalized outputs are saved in `backend/ingestion/dataset/generated_data/` as NDJSON (Newline Delimited JSON).

`{entity_name}_batch_{timestamp}_{process_id}.ndjson`

## Example Chunk
`invoice_batch_1710000000_p1.ndjson`
```json
{"invoiceNumber": "INV-001", "invoiceDate": "2026-01-15", "supplierGstin": "...", ...}
{"invoiceNumber": "INV-002", "invoiceDate": "2026-01-16", "supplierGstin": "...", ...}
```

This format allows the Graph layer to stream the file line-by-line using Neo4j APOC procedures or the Python Neo4j driver without loading the entire array into RAM.
