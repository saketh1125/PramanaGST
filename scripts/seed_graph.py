import os
import json
import csv
from datetime import datetime
import hashlib
from typing import Dict, Any, List

# Ensure graph schema is set up
try:
    from backend.graph.constraints import create_constraints
    create_constraints()
except Exception as e:
    print(f"Constraints setup note: {e}")

from backend.graph.graph_loader import GraphLoader
from backend.graph.connection import db

OUTPUT_DIR = "data/processed"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Helper function to wipe db
def clear_db():
    with db.get_session() as session:
        session.run("MATCH (n) DETACH DELETE n")
        print("Database cleared.")

def parse_gstr1(filepath: str) -> dict:
    env = empty_envelope("GSTR1")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            sup_gstin = row["supplier_gstin"]
            buy_gstin = row["receiver_gstin"]
            inv_num = row["invoice_number"]
            fy = "2023-24" # hardcoded from script
            
            # Taxpayer refs
            sup_ref = f"TP::{sup_gstin}"
            buy_ref = f"TP::{buy_gstin}"
            
            # Invoice
            inv_ref = f"INV::{sup_gstin}::{inv_num}::{fy}"
            
            # Return
            ret_period = row["return_period"]
            ret_ref = f"RET::{sup_gstin}::GSTR1::{ret_period}"
            
            src_rec_id = f"SRC::GSTR1::{inv_ref}"
            
            # Add Invoice with Observation
            env["entities"]["invoices"].append({
                "entity_type": "INVOICE",
                "entity_ref_id": inv_ref,
                "source_record_id": src_rec_id,
                "data": {
                    "invoice_number": inv_num,
                    "invoice_date": row["invoice_date"],
                    "financial_year": fy,
                    "invoice_type": row.get("invoice_type", "B2B"),
                    "document_type": "INVOICE",
                    "supplier_gstin": sup_gstin,
                    "recipient_gstin": buy_gstin,
                    "place_of_supply": row["place_of_supply"],
                    "supply_type": "INTRA_STATE" if sup_gstin[:2] == buy_gstin[:2] else "INTER_STATE",
                    "reverse_charge": "N"
                },
                "source_context": {
                    "source_system": "GSTR1",
                    "reporter_gstin": sup_gstin,
                    "reporter_role": "SUPPLIER",
                    "reporting_period": ret_period,
                    "original_record_index": idx,
                    "source_file": "gstr1_sales.csv",
                    "taxable_value": float(row["taxable_value"]),
                    "igst_amount": float(row["igst"]),
                    "cgst_amount": float(row["cgst"]),
                    "sgst_amount": float(row["sgst"]),
                    "total_tax_amount": float(row["igst"]) + float(row["cgst"]) + float(row["sgst"]),
                    "total_invoice_value": float(row["invoice_value"])
                },
                "lineage": {
                    "batch_id": "BATCH-1",
                    "ingestion_timestamp": datetime.now().isoformat(),
                    "record_hash": "dummyhash",
                    "schema_version": "1.0.0"
                },
                "graph_hints": {
                    "foreign_keys": {
                        "supplier_ref_id": sup_ref,
                        "recipient_ref_id": buy_ref,
                        "return_ref_id": ret_ref
                    }
                }
            })
            
            # Add Return
            if not any(r["entity_ref_id"] == ret_ref for r in env["entities"]["returns"]):
                env["entities"]["returns"].append({
                    "entity_type": "RETURN",
                    "entity_ref_id": ret_ref,
                    "source_record_id": f"SRC::GSTR1::{ret_ref}",
                    "data": {
                        "gstin": sup_gstin,
                        "return_type": "GSTR1",
                        "return_period": ret_period,
                        "filing_status": "FILED"
                    },
                    "graph_hints": {
                        "foreign_keys": {
                            "taxpayer_ref_id": sup_ref
                        }
                    }
                })

    return env


def parse_gstr2b(filepath: str) -> dict:
    env = empty_envelope("GSTR2B")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            sup_gstin = row["supplier_gstin"]
            buy_gstin = row["buyer_gstin"]
            inv_num = row["invoice_number"]
            fy = "2023-24"
            buy_ref = f"TP::{buy_gstin}"
            inv_ref = f"INV::{sup_gstin}::{inv_num}::{fy}"
            ret_period = row["return_period"]
            # 2B is buyer's return
            ret_ref = f"RET::{buy_gstin}::GSTR2B::{ret_period}"
            src_rec_id = f"SRC::GSTR2B::{inv_ref}"
            
            env["entities"]["invoices"].append({
                "entity_type": "INVOICE",
                "entity_ref_id": inv_ref,
                "source_record_id": src_rec_id,
                "data": {
                    "invoice_number": inv_num,
                    "invoice_date": row["invoice_date"].replace("-", "/"),
                    "financial_year": fy,
                    "invoice_type": "B2B",
                    "document_type": "INVOICE",
                    "supplier_gstin": sup_gstin,
                    "recipient_gstin": buy_gstin,
                    "place_of_supply": buy_gstin[:2],
                    "supply_type": "INTRA_STATE" if sup_gstin[:2] == buy_gstin[:2] else "INTER_STATE",
                    "reverse_charge": "N"
                },
                "source_context": {
                    "source_system": "GSTR2B",
                    "reporter_gstin": buy_gstin,
                    "reporter_role": "BUYER",
                    "reporting_period": ret_period,
                    "original_record_index": idx,
                    "source_file": "gstr2b_itc.csv",
                    "taxable_value": float(row["taxable_value"]),
                    "igst_amount": float(row["igst"]),
                    "cgst_amount": float(row["cgst"]),
                    "sgst_amount": float(row["sgst"]),
                    "total_tax_amount": float(row["igst"]) + float(row["cgst"]) + float(row["sgst"]),
                    "total_invoice_value": float(row["taxable_value"]) + float(row["igst"]) + float(row["cgst"]) + float(row["sgst"])
                },
                "lineage": {
                    "batch_id": "BATCH-2",
                    "ingestion_timestamp": datetime.now().isoformat(),
                    "record_hash": "dummyhash",
                    "schema_version": "1.0.0"
                },
                "graph_hints": {
                    "foreign_keys": {
                        "return_ref_id": ret_ref
                    }
                }
            })
    return env

def parse_pr(filepath: str) -> dict:
    env = empty_envelope("PURCHASE_REGISTER")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            sup_gstin = row["vendor_gstin"].upper()
            buy_gstin = row["buyer_gstin"].upper()
            inv_num = row["bill_number"].strip().replace("\\", "/").upper()
            fy = "2023-24"
            buy_ref = f"TP::{buy_gstin}"
            inv_ref = f"INV::{sup_gstin}::{inv_num}::{fy}"
            src_rec_id = f"SRC::PR::{inv_ref}"
            
            env["entities"]["invoices"].append({
                "entity_type": "INVOICE",
                "entity_ref_id": inv_ref,
                "source_record_id": src_rec_id,
                "data": {
                    "invoice_number": inv_num,
                    "invoice_date": row["bill_date"],
                    "financial_year": fy,
                    "document_type": "INVOICE",
                    "supplier_gstin": sup_gstin,
                    "recipient_gstin": buy_gstin,
                },
                "source_context": {
                    "source_system": "PURCHASE_REGISTER",
                    "reporter_gstin": buy_gstin,
                    "reporter_role": "BUYER",
                    "reporting_period": "2023-24",
                    "original_record_index": idx,
                    "source_file": "purchase_register.csv",
                    "taxable_value": float(row["taxable_amount"]),
                    "igst_amount": float(row["igst"]),
                    "cgst_amount": float(row["cgst"]),
                    "sgst_amount": float(row["sgst"]),
                    "total_tax_amount": float(row["igst"]) + float(row["cgst"]) + float(row["sgst"]),
                    "total_invoice_value": float(row["total_amount"])
                },
                "lineage": {
                    "batch_id": "BATCH-3",
                    "ingestion_timestamp": datetime.now().isoformat(),
                    "record_hash": "dummyhash",
                    "schema_version": "1.0.0"
                },
                "graph_hints": {
                    "foreign_keys": {
                        "buyer_ref_id": buy_ref
                    }
                }
            })
    return env

def parse_einvoice(filepath: str) -> dict:
    env = empty_envelope("E_INVOICE")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            sup_gstin = row["supplier_gstin"]
            inv_num = row["invoice_number"]
            fy = "2023-24"
            irn_val = row["irn"]
            irn_ref = f"IRN::{irn_val}"
            inv_ref = f"INV::{sup_gstin}::{inv_num}::{fy}"
            
            env["entities"]["irns"].append({
                "entity_type": "IRN",
                "entity_ref_id": irn_ref,
                "source_record_id": irn_ref,
                "data": {
                    "irn": irn_val,
                    "ack_number": row["ack_number"],
                    "ack_date": row["ack_date"],
                    "irn_status": row["irn_status"],
                    "total_invoice_value": float(row["total_value"])
                },
                "graph_hints": {
                    "foreign_keys": {
                        "invoice_ref_id": inv_ref
                    }
                }
            })
    return env

def parse_payments(filepath: str) -> dict:
    env = empty_envelope("TAX_PAYMENT")
    with open(filepath, "r") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            gstin = row["gstin"]
            chal = row["challan_number"]
            pay_ref = f"PAY::{gstin}::{chal}"
            tp_ref = f"TP::{gstin}"
            
            env["entities"]["payments"].append({
                "entity_type": "PAYMENT",
                "entity_ref_id": pay_ref,
                "source_record_id": pay_ref,
                "data": {
                    "gstin": gstin,
                    "challan_number": chal,
                    "tax_period": row["tax_period"],
                    "payment_date": row["payment_date"],
                    "payment_mode": row["payment_mode"],
                    "total_paid": float(row["total_paid"]),
                    "igst_paid": float(row["igst_paid"]),
                    "cgst_paid": float(row["cgst_paid"]),
                    "sgst_paid": float(row["sgst_paid"])
                },
                "graph_hints": {
                    "foreign_keys": {
                        "taxpayer_ref_id": tp_ref
                    }
                }
            })
    return env


def empty_envelope(source_sys: str) -> dict:
    return {
        "contract_version": "1.0.0",
        "batch_metadata": {
            "batch_id": f"BATCH-{source_sys}",
            "source_system": source_sys,
            "timestamp": datetime.now().isoformat(),
            "record_count": 0
        },
        "entities": {
            "taxpayers": [],
            "invoices": [],
            "returns": [],
            "payments": [],
            "irns": []
        }
    }


def push_taxpayers():
    # We will import the dataset script statically to pull the taxpayers list 
    # to populate full Taxpayer objects (with STATUS to trigger ANO-09)
    try:
        import scripts.generate_dataset as gd
        env = empty_envelope("MASTER")
        for tp in gd.taxpayers:
            tp_ref = f"TP::{tp['gstin']}"
            env["entities"]["taxpayers"].append({
                "entity_type": "TAXPAYER",
                "entity_ref_id": tp_ref,
                "source_record_id": tp_ref,
                "data": {
                    "gstin": tp["gstin"],
                    "legal_name": tp["name"],
                    "state_code": tp["state_code"],
                    "status": tp["status"]
                }
            })
        
        filepath = os.path.join(OUTPUT_DIR, "BATCH-TAXPAYERS.json")
        with open(filepath, "w") as f:
            json.dump(env, f)
        
        return filepath
            
    except Exception as e:
        print(f"Error extracting taxpayers: {e}")
        return None

def main():
    print("Clearing Neo4j DB...")
    clear_db()
    
    loader = GraphLoader()
    
    # 1. Taxpayers (from memory structure)
    tp_file = push_taxpayers()
    if tp_file:
        loader.load_batch_to_graph(tp_file)

    # 2. Parse and Load Data
    files = [
        ("GSTR1", "data/raw/gstr1_sales.csv", parse_gstr1),
        ("GSTR2B", "data/raw/gstr2b_itc.csv", parse_gstr2b),
        ("PR", "data/raw/purchase_register.csv", parse_pr),
        ("E-IN", "data/raw/einvoice_irn.csv", parse_einvoice),
        ("PAY", "data/raw/tax_payments.csv", parse_payments)
    ]
    
    for name, fpath, parser_fn in files:
        if os.path.exists(fpath):
            print(f"Parsing {name}...")
            env = parser_fn(fpath)
            json_path = os.path.join(OUTPUT_DIR, f"BATCH-{name}.json")
            with open(json_path, "w") as f:
                json.dump(env, f)
            print(f"Loading {name} into Graph...")
            stats = loader.load_batch_to_graph(json_path)
            print(f"Stats after {name}: {stats}")
        else:
            print(f"Missing {fpath}")

    print("✅ Graph Ingestion Complete.")
    
    # 3. Trigger Reconciliation
    from backend.reconciliation import matcher
    summary, results = matcher.reconcile_all()
    print("✅ Reconciliation Complete.")
    print(f"   Match Rate: {summary.match_rate_percent}%")
    print(f"   Total Tax at Risk: ₹{summary.total_tax_at_risk}")
    
    # 4. Trigger Risk Calculation
    from backend.risk.composite_scorer import compute_all_vendor_scores
    gstins = []
    with db.get_session() as session:
        gstins = [r["g"] for r in session.run("MATCH (t:Taxpayer) RETURN t.gstin AS g")]
    
    circ = matcher._get_circular_trading_gstins()
    scores = compute_all_vendor_scores(gstins, results, circ)
    
    print("✅ Risk Compute Complete.")
    print("   Critical vendors:", len([s for s in scores if s.risk_level == "CRITICAL"]))
    if scores:
        print(f"   Highest Risk Vendor GSTIN: {scores[0].gstin} (Score: {scores[0].composite_score})")
        print(f"   Triggered Rules: {scores[0].triggered_rules}")

if __name__ == "__main__":
    main()
