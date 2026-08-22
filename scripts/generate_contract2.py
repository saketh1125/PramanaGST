"""
Generate Contract-2 JSON schema from reconciliation evidence models.

Usage:
    python scripts/generate_contract2.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.reconciliation.engine.models import ReconItem, ReconReport, ReconSummary


def main():
    contract = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "PramanaGST Contract-2: Reconciliation Evidence",
        "version": "1.0.0",
        "definitions": {
            "ReconItem": ReconItem.model_json_schema(),
            "ReconSummary": ReconSummary.model_json_schema(),
            "ReconReport": ReconReport.model_json_schema(),
        },
    }
    out = os.path.join(os.path.dirname(__file__), "..", "contracts", "contract_2.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, default=str)
    print(f"Contract-2 written to {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
