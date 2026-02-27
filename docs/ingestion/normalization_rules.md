# Normalization Rules

Raw datasets from government portals or mock generators often contain inconsistencies. The Ingestion layer is responsible for normalizing these before applying Pydantic validation.

## Rule 1: Date Standardization
All dates must be parsed into the ISO 8601 YYYY-MM-DD format.
If a dataset uses DD-MM-YYYY or MM/DD/YYYY, Pandas `to_datetime` must be used during the DataFrame cleaning phase to ensure uniform mapping to the Pydantic `date` type.

## Rule 2: Currency and Floating Point Precision
GST amounts must never be processed as floating-point numbers due to precision loss.
- Parse string amounts directly into Python `Decimal`.
- Empty monetary values must be coalesced to `0.00`.
- Remove all thousand separators (commas).

## Rule 3: Enum Mapping
Raw string statuses must be mapped to the canonical `backend/ingestion/schemas/enums.py` equivalents.
- Example: "Active" -> `ACTIVE`
- Example: "Filed" / "Submitted" -> `FILED`
- Unrecognized enums must trigger a validation rejection for the row, preventing bad data from entering the graph.

## Rule 4: String Sanitization
- Trim leading/trailing whitespace (`str_strip_whitespace=True` is enabled in Pydantic, but Pandas `str.strip()` should be applied first for performance).
- Ensure GSTINs and PANs are strictly uppercase.
