import hashlib
import os
import random
from datetime import datetime, timedelta

import pandas as pd
from faker import Faker

# Determinism Setup
SEED = 42
random.seed(SEED)
fake = Faker("en_IN")
Faker.seed(SEED)

output_dir = "backend/ingestion/dataset/generated_data/"
os.makedirs(output_dir, exist_ok=True)


# Utility logic for generating conformant identifiers
def generate_gstin(state_code: str, pan: str, entity_num: int = 1) -> str:
    # 2 chars state + 10 chars PAN + 1 char entity num + Z + 1 check character (mocked)
    return f"{state_code}{pan}{entity_num}Z5"


def generate_irn(invoice_num: str, supplier_gstin: str, doc_year: str) -> str:
    # 64-character hash mock based on composite key
    raw_str = f"{supplier_gstin}-{doc_year}-INV-{invoice_num}"
    return hashlib.sha256(raw_str.encode()).hexdigest()


# --- Domain Configurations ---
STATES = ["27", "29", "07", "09", "33"]
REG_TYPES = ["REGULAR", "COMPOSITION", "SEZ"]
PERIOD = "012026"
BASE_DATE = datetime(2026, 1, 1)

# Numbers configuration
NUM_TAXPAYERS = 20
NUM_INVOICES = 100


def generate_taxpayers():
    taxpayers = []
    for _ in range(NUM_TAXPAYERS):
        state = random.choice(STATES)
        # Random 10 character PAN (5 letters, 4 numbers, 1 letter)
        pan = f"{''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ', k=5))}{''.join(random.choices('0123456789', k=4))}{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
        gstin = generate_gstin(state, pan)

        taxpayers.append(
            {
                "gstin": gstin,
                "legal_name": fake.company(),
                "state_code": state,
                "registration_type": random.choice(REG_TYPES),
            }
        )

    df = pd.DataFrame(taxpayers)
    df.to_csv(os.path.join(output_dir, "taxpayers.csv"), index=False)
    return taxpayers


def generate_invoices_and_irns(taxpayers):
    gstr1 = []
    einvoices = []

    for i in range(NUM_INVOICES):
        supplier = random.choice(taxpayers)
        # Recipient must be different from supplier
        recipient = random.choice([t for t in taxpayers if t["gstin"] != supplier["gstin"]])

        inv_num = f"INV-2026-{i+1:04d}"
        inv_date = BASE_DATE + timedelta(days=random.randint(0, 30))
        date_str = inv_date.strftime("%Y-%m-%d")

        # Financial Math
        taxable_value = round(random.uniform(1000, 500000), 2)
        supply_type = "INTRA_STATE" if supplier["state_code"] == recipient["state_code"] else "INTER_STATE"

        if supply_type == "INTRA_STATE":
            cgst = round(taxable_value * 0.09, 2)
            sgst = cgst
            igst = 0.0
        else:
            cgst = 0.0
            sgst = 0.0
            igst = round(taxable_value * 0.18, 2)

        invoice_value = round(taxable_value + cgst + sgst + igst, 2)

        # IRN Generation (Not all invoices get an IRN, simulate B2C or non-applicable)
        has_irn = random.random() > 0.2
        irn_hash = generate_irn(inv_num, supplier["gstin"], "2026") if has_irn else ""

        gstr1.append(
            {
                "invoice_number": inv_num,
                "supplier_gstin": supplier["gstin"],
                "recipient_gstin": recipient["gstin"],
                "invoice_date": date_str,
                "invoice_value": invoice_value,
                "cgst_amount": cgst,
                "sgst_amount": sgst,
                "igst_amount": igst,
                "supply_type": supply_type,
                "irn": irn_hash,
            }
        )

        if has_irn:
            einv_status = "ACTIVE" if random.random() > 0.05 else "CANCELLED"
            einvoices.append(
                {
                    "irn": irn_hash,
                    "invoice_number": inv_num,
                    "generation_timestamp": (inv_date + timedelta(hours=random.randint(1, 48))).isoformat(),
                    "status": einv_status,
                }
            )

    df_gstr1 = pd.DataFrame(gstr1)
    df_gstr1.to_csv(os.path.join(output_dir, "gstr1.csv"), index=False)

    df_einv = pd.DataFrame(einvoices)
    df_einv.to_csv(os.path.join(output_dir, "einvoice.csv"), index=False)

    return gstr1


def generate_gstr2b(invoices):
    gstr2b = []

    for inv in invoices:
        # Simulate ITC claim scenarios
        # 1. Normal claim (80% chance)
        # 2. Mismatch claim (10% chance - short claim or typo)
        # 3. No claim (10% chance - missing invoice in 2B)

        scenario = random.random()
        total_tax = round(inv["cgst_amount"] + inv["sgst_amount"] + inv["igst_amount"], 2)

        if scenario < 0.8:
            itc_claimed = total_tax
        elif scenario < 0.9:
            # Under-claim by some random percentage
            itc_claimed = round(total_tax * random.uniform(0.5, 0.9), 2)
        else:
            # Skip claiming for this invoice (creates a broken path for recon engine)
            continue

        gstr2b.append(
            {
                "invoice_number": inv["invoice_number"],
                "recipient_gstin": inv["recipient_gstin"],
                "itc_claimed": itc_claimed,
                "claim_period": PERIOD,
            }
        )

    df_gstr2b = pd.DataFrame(gstr2b)
    df_gstr2b["claim_period"] = df_gstr2b["claim_period"].astype(str)
    df_gstr2b.to_csv(os.path.join(output_dir, "gstr2b.csv"), index=False)


def generate_payments(invoices):
    payments = []
    
    # Group tax liability by supplier
    liability_map = {}
    for inv in invoices:
        sup = inv["supplier_gstin"]
        tax = inv["cgst_amount"] + inv["sgst_amount"] + inv["igst_amount"]
        if sup not in liability_map:
            liability_map[sup] = 0.0
        liability_map[sup] += tax

    for gstin, total_liability in liability_map.items():
        total_liability = round(total_liability, 2)
        
        # Simulate payment completeness
        # 90% full payment, 10% short payment
        if random.random() > 0.1:
            tax_paid = total_liability
        else:
            tax_paid = round(total_liability * random.uniform(0.4, 0.8), 2)

        payments.append(
            {
                "supplier_gstin": gstin,
                "return_period": PERIOD,
                "tax_paid": tax_paid,
            }
        )

    df_payments = pd.DataFrame(payments)
    df_payments["return_period"] = df_payments["return_period"].astype(str)
    df_payments.to_csv(os.path.join(output_dir, "payments.csv"), index=False)


def run_generator():
    print(f"Generating deterministic datasets to {output_dir}...")
    
    taxpayers = generate_taxpayers()
    print(f"  - Generated {len(taxpayers)} taxpayers.")
    
    invoices = generate_invoices_and_irns(taxpayers)
    print(f"  - Generated {len(invoices)} GSTR-1 invoices and their IRNs.")
    
    generate_gstr2b(invoices)
    print("  - Generated GSTR-2B ITC claims (with intentional mismatches).")
    
    generate_payments(invoices)
    print("  - Generated periodic payment aggregations.")
    
    print("Generation complete.")


if __name__ == "__main__":
    run_generator()
