# Ingestion Dataset Specification

The Ingestion layer expects raw datasets (CSV/JSON/Excel) containing fragments of GST information representing real-world filing scenarios.

## Supported Input Formats
- Form GSTR-1 (Outward Supplies)
- Form GSTR-2B (Auto-drafted ITC Statement)
- Form GSTR-3B (Summary Return)
- e-Invoice (JSON Payloads)
- Cash Ledger / ITC Utilization Logs

## Goal of Ingestion
The singular goal of the Ingestion layer is to read these raw formats and transform them into the **Contract 1 Canonical JSON Specification** (defined by strict Pydantic models).

## Mandatory Outputs
Regardless of the input source, the Ingestion layer must produce an array of the following canonical entities:
1. `TAXPAYER`
2. `INVOICE`
3. `RETURN` (Mapped to `ReturnFiling`)
4. `PAYMENT`
5. `IRN`

For detailed schema constraints on these outputs, refer to `backend/ingestion/schemas/`.
