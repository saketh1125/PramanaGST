"""
Generate Contract-5 JSON schema from dashboard view models.

Usage:
    python scripts/generate_contract5.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.api.models.contract5 import (
    ErrorResponse,
    GraphLink,
    GraphNode,
    GraphView,
    RiskSummary,
    VendorRiskView,
)


def main():
    contract = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "PramanaGST Contract-5: Dashboard View Models",
        "version": "1.0.0",
        "definitions": {
            "RiskSummary": RiskSummary.model_json_schema(),
            "VendorRiskView": VendorRiskView.model_json_schema(),
            "GraphNode": GraphNode.model_json_schema(),
            "GraphLink": GraphLink.model_json_schema(),
            "GraphView": GraphView.model_json_schema(),
            "ErrorResponse": ErrorResponse.model_json_schema(),
        },
    }
    out = os.path.join(os.path.dirname(__file__), "..", "contracts", "contract_5.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(contract, f, indent=2, default=str)
    print(f"Contract-5 written to {os.path.normpath(out)}")


if __name__ == "__main__":
    main()
