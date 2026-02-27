# Relationship Definitions

Relationships are the core of PramanaGST's intelligence. All relationships are directed graphs (`-->`).

## Core Edges

| Edge type | Source Node | Target Node | Properties / Context |
|:----------|:------------|:------------|:----------------------|
| `SUPPLIED` | `Taxpayer` | `Invoice` | Indicates the seller. Created matching `Taxpayer.gstin` to `Invoice.supplierGstin`. |
| `RECEIVED` | `Taxpayer` | `Invoice` | Indicates the buyer. Created matching `Taxpayer.gstin` to `Invoice.recipientGstin`. |
| `FILED` | `Taxpayer` | `ReturnFiling` | Links GSTIN to their GSTR filing. |
| `REPORTED_IN`| `Invoice` | `ReturnFiling` | Links a specific document to the specific GSTR-1/GSTR-2B where it appeared. |
| `PAID_VIA` | `ReturnFiling` | `Payment` | Links tax liability of a return to the cash/ITC settlement event. |
| `REGISTERED` | `Invoice` | `IRN` | Links the raw invoice to the IRP portal acknowledgement. |

## Temporal Relationships
- `NEXT_RETURN` (`ReturnFiling` -> `ReturnFiling`): Links sequential months for state tracking.
