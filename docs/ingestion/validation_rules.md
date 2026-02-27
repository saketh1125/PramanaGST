# Validation Rules (Contract 1)

All output from the Ingestion layer is aggressively validated via `pydantic`. The rules are hardcoded into the data models in `backend/ingestion/schemas/`.

## Key Enforcements
1. **GSTIN Format:** Guaranteed to be 15 chars, matching the regex `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`.
2. **PAN Format:** Extracted from GSTIN or provided explicitly, matching `^[A-Z]{5}[0-9]{4}[A-Z]{1}$`.
3. **Monetary Constraints:** All `Decimal` values (`taxable_value`, `igst_amount`, `total_liability`, etc.) must be `>= 0` (`ge=0`), with `max_digits=15` and `decimal_places=2`. Negative invoices must be handled via Credit Notes (`document_type="CRN"`).
4. **Filing Periods:** Enforced as `MMYYYY` (`^(0[1-9]|1[0-2])\d{4}$`).
5. **IRN Hashes:** Enforced as exact 64-character lengths.

## Error Handling
If a row fails Pydantic validation:
1. It is **DROPPED** from the output batch.
2. The `ValidationError` details (column name, input value, constraint failed) are written to the `logs/ingestion_errors.json` file.
3. The Ingestion step continues processing the remainder of the batch.
