"""
IngestService — orchestrates the ingestion pipeline:

CSVs -> normalize -> Contract-1 validation -> batch JSON.

Output envelope per spec §9: {batch_metadata, entities, rejected_records}.
"""

import json
import os

from .batching.batch_builder import build_batch
from .normalization.loader import load_datasets
from .normalization.mappers import (
    map_gstr2b_return,
    map_invoice,
    map_irn,
    map_payment,
    map_taxpayer,
)
from .validation.record_validator import summarize_rejections, validate_entity


def _obs(row: dict) -> dict:
    """Per-invoice ITC claim observation from GSTR-2B."""
    required = ("invoice_number", "recipient_gstin", "itc_claimed", "claim_period")
    if any(not row.get(k) for k in required):
        raise ValueError(f"GSTR-2B claim missing required field(s): {row}")
    return {
        "entity_type": "SOURCE_OBSERVATION",
        "ref_id": f"OBS-{row['recipient_gstin']}|{row['invoice_number']}",
        "data": {
            "observation_type": "ITC_CLAIM",
            "invoiceNumber": str(row["invoice_number"]),
            "recipientGstin": str(row["recipient_gstin"]),
            "itcClaimed": float(row["itc_claimed"]),
            "claimPeriod": str(row["claim_period"]),
        },
    }


class IngestService:
    """Service to handle ingestion of GST data."""

    def __init__(self, dataset_dir: str):
        self.dataset_dir = dataset_dir

    def process(self) -> dict:
        dfs = load_datasets(self.dataset_dir)

        entities: list[dict] = []
        rejected: list[dict] = []

        def _accept_or_reject(result: dict, source: str, idx: int):
            if result.get("rejected"):
                rejected.append({**result, "source_file": result.get("source_file") or source, "row_index": idx})
            else:
                entities.append(result)

        # 1. Taxpayers — reference data first
        for idx, row in enumerate(dfs["taxpayers"].to_dict("records")):
            ref = str(row["gstin"])
            _accept_or_reject(
                validate_entity("TAXPAYER", ref, "taxpayers.csv", idx, map_taxpayer(row).model_dump(by_alias=True)),
                "taxpayers.csv",
                idx,
            )

        # 2. Invoices
        invoice_lookup: dict[str, dict] = {}
        for idx, row in enumerate(dfs["gstr1"].to_dict("records")):
            invoice_lookup[str(row["invoice_number"])] = row
            ref = f"{row['supplier_gstin']}|{row['invoice_number']}"
            _accept_or_reject(
                validate_entity("INVOICE", ref, "gstr1.csv", idx, map_invoice(row).model_dump(by_alias=True)),
                "gstr1.csv",
                idx,
            )

        # 3. GSTR-2B — one aggregated RETURN per recipient+period plus per-invoice observations
        g2b_rows = [r for r in dfs["gstr2b"].to_dict("records")]
        groups: dict[tuple[str, str], list[dict]] = {}
        for row in g2b_rows:
            try:
                entities.append(_obs(row))
            except ValueError as exc:
                rejected.append({"rejected": True, "entity_type": "SOURCE_OBSERVATION", "ref_id": None,
                                 "source_file": "gstr2b.csv", "row_index": g2b_rows.index(row), "errors": [str(exc)]})
            key = (str(row["recipient_gstin"]), str(row["claim_period"]))
            groups.setdefault(key, []).append(row)

        for (recipient, period), rows in sorted(groups.items()):
            ret = map_gstr2b_return(rows, recipient, period)
            _accept_or_reject(
                validate_entity("RETURN", ret.return_id, "gstr2b.csv", 0, ret.model_dump(by_alias=True)),
                "gstr2b.csv",
                0,
            )

        # 4. Payments
        for idx, row in enumerate(dfs["payments"].to_dict("records")):
            pay = map_payment(row)
            _accept_or_reject(
                validate_entity("PAYMENT", pay.payment_id, "payments.csv", idx, pay.model_dump(by_alias=True)),
                "payments.csv",
                idx,
            )

        # 5. IRNs — need supplier via invoice lookup
        for idx, row in enumerate(dfs["einvoice"].to_dict("records")):
            inv_num = str(row["invoice_number"])
            if inv_num not in invoice_lookup:
                rejected.append({"rejected": True, "entity_type": "IRN", "ref_id": row.get("irn"),
                                 "source_file": "einvoice.csv", "row_index": idx,
                                 "errors": [f"Invoice {inv_num} not found in gstr1"]})
                continue
            irn = map_irn(row, invoice_lookup)
            _accept_or_reject(
                validate_entity("IRN", irn.irn, "einvoice.csv", idx, irn.model_dump(by_alias=True)),
                "einvoice.csv",
                idx,
            )

        batch = build_batch(entities, rejected, self.dataset_dir)
        batch["batch_metadata"]["rejection_summary"] = summarize_rejections(rejected)
        return batch

    def process_to_file(self, output_path: str | None = None) -> dict:
        batch = self.process()
        out = output_path or os.path.join(
            os.path.dirname(self.dataset_dir), "batches", "latest_batch.json"
        )
        os.makedirs(os.path.dirname(out), exist_ok=True)
        with open(out, "w", encoding="utf-8") as f:
            json.dump(batch, f, indent=2)
        print(f"Batch written to {out}")
        return batch
