import os
import random
from datetime import datetime, timedelta
import pandas as pd

# Determinism Setup
SEED = 42
random.seed(SEED)

output_dir = "backend/ingestion/dataset/generated_data/"
gstr1_path = os.path.join(output_dir, "gstr1.csv")
ewaybill_path = os.path.join(output_dir, "ewaybill.csv")

# Constants
TRANSPORT_MODES = ["ROAD", "RAIL", "AIR", "SHIP"]
STATUSES = ["ACTIVE", "COMPLETED"]

def generate_vehicle_number():
    # Mock Indian vehicle format e.g., KA01AB1234
    states = ["MH", "KA", "DL", "TN", "UP", "GJ", "TS", "WB", "RJ", "MP"]
    state = random.choice(states)
    rto = f"{random.randint(1, 99):02d}"
    chars = f"{chr(random.randint(65, 90))}{chr(random.randint(65, 90))}"
    num = f"{random.randint(1000, 9999)}"
    return f"{state}{rto}{chars}{num}"

def run_generator():
    print(f"Loading invoices from {gstr1_path}...")
    if not os.path.exists(gstr1_path):
        print(f"Error: {gstr1_path} not found. Ensure Contract 1 dataset generation is run first.")
        return

    df_gstr1 = pd.read_csv(gstr1_path)
    all_invoices = df_gstr1.to_dict('records')
    
    # Guarantee 60-70% coverage precisely
    target_volume = int(len(all_invoices) * random.uniform(0.6, 0.7))
    selected_invoices = random.sample(all_invoices, target_volume)
    
    ewaybills = []
    
    for inv in selected_invoices:
        # 12-digit numeric eway_bill_number
        eway_bill_number = "".join([str(random.randint(0, 9)) for _ in range(12)])
        
        # Dispatch date matches invoice date (for simplicity, or +1 day)
        inv_date = datetime.strptime(inv["invoice_date"], "%Y-%m-%d")
        dispatch_date = inv_date + timedelta(days=random.randint(0, 1))
        
        # Delivery date 1-5 days after dispatch
        delivery_date = dispatch_date + timedelta(days=random.randint(1, 5))
        
        ewaybills.append({
            "eway_bill_number": eway_bill_number,
            "invoice_number": inv["invoice_number"],
            "supplier_gstin": inv["supplier_gstin"],
            "recipient_gstin": inv["recipient_gstin"],
            "transport_mode": random.choice(TRANSPORT_MODES),
            "vehicle_number": generate_vehicle_number(),
            "dispatch_date": dispatch_date.strftime("%Y-%m-%d"),
            "delivery_date": delivery_date.strftime("%Y-%m-%d"),
            "distance_km": random.randint(20, 1200),
            "eway_status": "COMPLETED" if random.random() > 0.1 else "ACTIVE"
        })

    df_ewaybill = pd.DataFrame(ewaybills)
    df_ewaybill.to_csv(ewaybill_path, index=False)
    
    print(f"Successfully generated {len(ewaybills)} e-Way Bills matching invoices.")
    print(f"Saved to {ewaybill_path}")

if __name__ == "__main__":
    run_generator()
