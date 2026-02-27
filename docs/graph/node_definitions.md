# Node Definitions

Neo4j Nodes mirror the core entities defined in **Contract 1**.

| Label | Primary Key | Description | Extracted From |
|-------|-------------|-------------|:---------------|
| `Taxpayer` | `gstin` | Registered entity | Canonical `TAXPAYER` JSON |
| `Invoice` | `(supplierGstin, invoiceNumber, filingPeriod)` | Financial document | Canonical `INVOICE` JSON |
| `ReturnFiling` | `returnId` | Filed GSTR form | Canonical `RETURN` JSON |
| `Payment` | `paymentId` | Cash or ITC payment | Canonical `PAYMENT` JSON |
| `IRN` | `irn` | e-Invoice Hash | Canonical `IRN` JSON |

## Metadata Node Properties
Every node contains standard audit properties:
- `ingestedAt`: ISO UTC timestamp of record creation
- `sourceFile`: Originating batch payload reference for traceability
- `contractVersion`: The version of the schema parsing this node
