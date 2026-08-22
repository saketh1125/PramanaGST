"""
Generate Contract-3 JSON schema from risk intelligence models.

Usage:
    python scripts/generate_contract3.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.risk_ai.models.vendor_risk import RiskSignal, VendorRisk


def main():
    contract = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "PramanaGST Contract-3: Risk Intelligence",
        "version": "1.0.0",
        "definitions": {
            "RiskSignal": RiskSignal.model_json_schema(),
            "VendorRisk": VendorRisk.model_json_schema(),
        },
    }
    out = os.path.join(os.path.dirname(__file__), "..", "contracts", "contract_3.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, default=str)
    print(f"Contract-3 written to {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
