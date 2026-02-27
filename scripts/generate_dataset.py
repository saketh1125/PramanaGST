import os
import csv
import random
import hashlib
from datetime import datetime, timedelta

# Configurations
NUM_TAXPAYERS = 20
NUM_INVOICES = 200
START_DATE = datetime(2023, 4, 1)
END_DATE = datetime(2024, 3, 31)
TAX_RATES = [0.05, 0.12, 0.18, 0.28]
STATES = {"29": "KA", "27": "MH", "33": "TN", "07": "DL", "24": "GJ"}
OUTPUT_DIR = "data/raw"

os.makedirs(OUTPUT_DIR, exist_ok=True)
random.seed(42)  # Deterministic generation

def calculate_checksum(gstin_base):
    # Simplified mock checksum logic for GSTIN (last char)
    # A true implementation uses Modulo 36 algorithm
    hash_val = int(hashlib.md5(gstin_base.encode()).hexdigest(), 16)
    chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return chars[hash_val % 36]

def generate_gstin(index, state_code):
    business_char = chr(65 + (index % 26)) * 5  # AAAAA, BBBBB, etc.
    pan_nums = f"{(index % 1000):04d}"
    gstin_base = f"{state_code}{business_char}{pan_nums}A1Z"
    return gstin_base + calculate_checksum(gstin_base)

def random_date(start, end):
    return start + timedelta(days=random.randint(0, int((end - start).days)))

def get_return_period(dt):
    # Format: MMYYYY
    return dt.strftime("%m%Y")

taxpayers = []
state_codes = list(STATES.keys())

for i in range(1, NUM_TAXPAYERS + 1):
    sc = state_codes[i % len(state_codes)]
    tp = {
        "index": i,
        "gstin": generate_gstin(i, sc),
        "state_code": sc,
        "name": f"Company {chr(65 + i)} Pvt Ltd",
        "status": "ACTIVE"
    }
    taxpayers.append(tp)

# ANO-09: Cancelled Supplier
taxpayers[15]["status"] = "CANCELLED"

# ANO-10: Circular Trading Setup (A -> B -> C -> A)
circular_tps = [taxpayers[0], taxpayers[1], taxpayers[2]] 

invoices = []
invoice_counter = 1

# Base generation
for _ in range(NUM_INVOICES):
    supp = random.choice(taxpayers)
    buyer = random.choice(taxpayers)
    while supp == buyer:
        buyer = random.choice(taxpayers)
    
    inv_date = random_date(START_DATE, END_DATE)
    tax_rate = random.choice(TAX_RATES)
    taxable_val = round(random.uniform(10000, 500000), 2)
    
    # ANO-11: High value outlier (>1Cr)
    if _ == 50:
        taxable_val = 15000000.00 # 1.5 Cr
        
    inv = {
        "id": invoice_counter,
        "supplier_gstin": supp["gstin"],
        "buyer_gstin": buyer["gstin"],
        "invoice_number": f"INV/2023-24/{invoice_counter:04d}",
        "invoice_date": inv_date,
        "taxable_value": taxable_val,
        "tax_rate": tax_rate,
        "supply_type": "INTRA_STATE" if supp["state_code"] == buyer["state_code"] else "INTER_STATE",
        "return_period": get_return_period(inv_date),
        "supplier_state": supp["state_code"],
        "buyer_state": buyer["state_code"],
        "place_of_supply": buyer["state_code"]
    }
    
    if inv["supply_type"] == "INTRA_STATE":
        inv["cgst"] = round((taxable_val * tax_rate) / 2, 2)
        inv["sgst"] = round((taxable_val * tax_rate) / 2, 2)
        inv["igst"] = 0.0
    else:
        inv["cgst"] = 0.0
        inv["sgst"] = 0.0
        inv["igst"] = round((taxable_val * tax_rate), 2)
        
    inv["total"] = round(taxable_val + inv["cgst"] + inv["sgst"] + inv["igst"], 2)
    invoices.append(inv)
    invoice_counter += 1

# Inject Circular Trading (ANO-10)
circular_date = START_DATE + timedelta(days=100)
circ_val = 500000.00
for i in range(3):
    s_tp = circular_tps[i]
    b_tp = circular_tps[(i+1)%3]
    tax_rate = 0.18
    inv = {
        "id": invoice_counter,
        "supplier_gstin": s_tp["gstin"],
        "buyer_gstin": b_tp["gstin"],
        "invoice_number": f"INV/CIRC/{invoice_counter:04d}",
        "invoice_date": circular_date + timedelta(days=i*5), # Sequence of days
        "taxable_value": circ_val,
        "tax_rate": tax_rate,
        "supply_type": "INTRA_STATE" if s_tp["state_code"] == b_tp["state_code"] else "INTER_STATE",
        "return_period": get_return_period(circular_date + timedelta(days=i*5)),
        "supplier_state": s_tp["state_code"],
        "buyer_state": b_tp["state_code"],
        "place_of_supply": b_tp["state_code"]
    }
    if inv["supply_type"] == "INTRA_STATE":
        inv["cgst"] = round((circ_val * tax_rate) / 2, 2)
        inv["sgst"] = round((circ_val * tax_rate) / 2, 2)
        inv["igst"] = 0.0
    else:
        inv["cgst"] = 0.0
        inv["sgst"] = 0.0
        inv["igst"] = round((circ_val * tax_rate), 2)
        
    inv["total"] = round(circ_val + inv["cgst"] + inv["sgst"] + inv["igst"], 2)
    invoices.append(inv)
    invoice_counter += 1

# ANO-12: Duplicate Invoice Number
dup_inv = invoices[10].copy()
dup_inv["id"] = invoice_counter
dup_inv["buyer_gstin"] = taxpayers[5]["gstin"]
invoices.append(dup_inv)
invoice_counter += 1

# GSTR1 Selection
gstr1_invoices = invoices.copy()

# ANO-07: Supplier Not Filed
# Supplier 8 doesn't file GSTR1 for one specific period (e.g. 052023)
ano7_supplier = taxpayers[7]["gstin"]
ano7_period = "052023"
gstr1_invoices = [inv for inv in gstr1_invoices if not (inv["supplier_gstin"] == ano7_supplier and inv["return_period"] == ano7_period)]

# ANO-02: Missing in GSTR1
# Remove 5-8 invoices from GSTR1, but keep in Purchase Register
ano02_invoices = random.sample(invoices, 7)
gstr1_invoices = [inv for inv in gstr1_invoices if inv not in ano02_invoices]

# GSTR2B Selection & Anomalies
gstr2b_invoices = []
ano01_candidates = random.sample(gstr1_invoices, 18) # ANO-01: Missing in 2B
ano03_candidates = random.sample(gstr1_invoices, 10) # ANO-03: Value Mismatch
ano04_candidates = random.sample(gstr1_invoices, 5)  # ANO-04: Tax Mismatch

for inv in gstr1_invoices:
    if inv in ano01_candidates:
        continue # skip for 2B
        
    inv_2b = inv.copy()
    
    if inv in ano03_candidates:
        inv_2b["taxable_value"] += round(random.uniform(500, 5000), 2)
        
    if inv in ano04_candidates:
        if inv_2b["igst"] > 0:
            inv_2b["igst"] += round(random.uniform(100, 1000), 2)
        else:
            inv_2b["cgst"] += round(random.uniform(100, 1000), 2)
            
    gstr2b_invoices.append(inv_2b)

# Add ANO-07 invoices to 2B to simulate buyers claiming ITC despite supplier non-filing
for inv in invoices:
    if inv["supplier_gstin"] == ano7_supplier and inv["return_period"] == ano7_period:
        gstr2b_invoices.append(inv)

# Purchase Register Selection & Anomalies
pr_invoices = []
ano05_candidates = random.sample(invoices, 3) # ANO-05: Date Mismatch

for inv in invoices:
    # Some invoices might not be in purchase register but are in GSTR1, but we assume 95% mapping
    if random.random() < 0.05 and inv not in ano02_invoices:
        continue
    
    inv_pr = inv.copy()
    if inv in ano05_candidates:
        inv_pr["invoice_date"] = inv["invoice_date"] + timedelta(days=random.choice([-2, -1, 1, 2]))
    
    pr_invoices.append(inv_pr)

# Write gstr1_sales.csv
with open(os.path.join(OUTPUT_DIR, "gstr1_sales.csv"), "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["supplier_gstin", "receiver_gstin", "invoice_number", "invoice_date", "invoice_value", 
                     "place_of_supply", "reverse_charge", "invoice_type", "taxable_value", "igst", "cgst", "sgst", 
                     "cess", "return_period"])
    for inv in gstr1_invoices:
        writer.writerow([
            inv["supplier_gstin"], inv["buyer_gstin"], inv["invoice_number"], inv["invoice_date"].strftime("%d/%m/%Y"),
            inv["total"], inv["place_of_supply"], "N", "B2B", inv["taxable_value"], inv["igst"], inv["cgst"], inv["sgst"],
            0.00, inv["return_period"]
        ])

# Write gstr2b_itc.csv
with open(os.path.join(OUTPUT_DIR, "gstr2b_itc.csv"), "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["supplier_gstin", "buyer_gstin", "invoice_number", "invoice_date", "invoice_type", 
                     "taxable_value", "igst", "cgst", "sgst", "cess", "itc_available", "reason", "return_period"])
    for inv in gstr2b_invoices:
        writer.writerow([
            inv["supplier_gstin"], inv["buyer_gstin"], inv["invoice_number"], inv["invoice_date"].strftime("%d-%m-%Y"),
            "Invoices", inv["taxable_value"], inv["igst"], inv["cgst"], inv["sgst"], 0.00, "Yes", "", 
            inv["return_period"]
        ])

# Write purchase_register.csv
with open(os.path.join(OUTPUT_DIR, "purchase_register.csv"), "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["buyer_gstin", "vendor_gstin", "bill_number", "bill_date", "taxable_amount", 
                     "igst", "cgst", "sgst", "total_amount", "payment_status"])
    for inv in pr_invoices:
        # Normalization anomalies: lowercase GSTINs, backslashes, spaces
        bill_num = inv["invoice_number"].replace("/", "\\") + "  " if random.random() < 0.3 else inv["invoice_number"]
        ven_gstin = inv["supplier_gstin"].lower() if random.random() < 0.3 else inv["supplier_gstin"]
        
        writer.writerow([
            inv["buyer_gstin"], ven_gstin, bill_num, inv["invoice_date"].strftime("%Y-%m-%d"),
            inv["taxable_value"], inv["igst"], inv["cgst"], inv["sgst"], inv["total"], "PAID"
        ])

# E-invoice data
einvoice_candidates = random.sample(invoices, int(len(invoices) * 0.6))
ano06_candidates = random.sample(einvoice_candidates, 2) # ANO-06: Cancelled IRN
with open(os.path.join(OUTPUT_DIR, "einvoice_irn.csv"), "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["irn", "ack_number", "ack_date", "supplier_gstin", "buyer_gstin", "invoice_number", 
                     "invoice_date", "doc_type", "taxable_value", "igst", "cgst", "sgst", "cess", 
                     "total_value", "irn_status"])
    for idx, inv in enumerate(einvoice_candidates):
        irn_val = hashlib.sha256(f"{inv['invoice_number']}{inv['supplier_gstin']}".encode()).hexdigest()
        status = "CANCELLED" if inv in ano06_candidates else "ACTIVE"
        writer.writerow([
            irn_val, f"1324{(idx+1):011d}", inv["invoice_date"].strftime("%d/%m/%Y"), inv["supplier_gstin"],
            inv["buyer_gstin"], inv["invoice_number"], inv["invoice_date"].strftime("%d/%m/%Y"), "INV",
            inv["taxable_value"], inv["igst"], inv["cgst"], inv["sgst"], 0.00, inv["total"], status
        ])

# Tax Payments
tax_liabilities = {}
for inv in gstr1_invoices:
    tp = inv["supplier_gstin"]
    prd = inv["return_period"]
    key = (tp, prd)
    if key not in tax_liabilities:
        tax_liabilities[key] = {"igst": 0.0, "cgst": 0.0, "sgst": 0.0}
    tax_liabilities[key]["igst"] += inv["igst"]
    tax_liabilities[key]["cgst"] += inv["cgst"]
    tax_liabilities[key]["sgst"] += inv["sgst"]

# ANO-08: Tax Underpayment (3 pay less, 1 pays 0)
ano08_underpayers = list(tax_liabilities.keys())[:3]
ano08_nonpayer = list(tax_liabilities.keys())[4]

with open(os.path.join(OUTPUT_DIR, "tax_payments.csv"), "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(["gstin", "challan_number", "payment_date", "tax_period", "payment_mode", 
                     "igst_paid", "cgst_paid", "sgst_paid", "cess_paid", "interest", "penalty", "total_paid"])
    
    chal_idx = 1
    for (gstin, prd), liability in tax_liabilities.items():
        igst, cgst, sgst = liability["igst"], liability["cgst"], liability["sgst"]
        
        if (gstin, prd) in ano08_underpayers:
            igst = round(igst * 0.5, 2)
            cgst = round(cgst * 0.5, 2)
            sgst = round(sgst * 0.5, 2)
        elif (gstin, prd) == ano08_nonpayer:
            igst = cgst = sgst = 0.0
            
        total = round(igst + cgst + sgst, 2)
        pay_month = min(int(prd[:2]) + 1, 12)
        pay_year = int(prd[2:]) if pay_month > int(prd[:2]) else int(prd[2:]) + 1
        pay_date = datetime(pay_year, pay_month, 20)
        
        writer.writerow([
            gstin, f"CHL{chal_idx:010d}", pay_date.strftime("%d/%m/%Y"), prd, "NEFT",
            igst, cgst, sgst, 0.00, 0.00, 0.00, total
        ])
        chal_idx += 1

print("Dataset generated successfully in data/raw/")
