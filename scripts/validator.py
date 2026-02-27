"""
PramanaGST Contract-1 Dataset Validator
=======================================
Validates whether generated CSV datasets can produce Contract-1 compliant
ingestion output for the Knowledge Graph layer.

Usage:
    python scripts/validator.py
"""

import os
import re
import sys
from datetime import datetime

import pandas as pd

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
DATA_DIR = os.path.join("backend", "ingestion", "dataset", "generated_data")

REQUIRED_FILES = {
    "taxpayers": "taxpayers.csv",
    "gstr1": "gstr1.csv",
    "gstr2b": "gstr2b.csv",
    "payments": "payments.csv",
    "einvoice": "einvoice.csv",
}

GSTIN_PATTERN = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[0-9A-Z]{1}Z[0-9A-Z]{1}$")
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}$")
MMYYYY_PATTERN = re.compile(r"^(0[1-9]|1[0-2])\d{4}$")

VALID_SUPPLY_TYPES = {"INTRA_STATE", "INTER_STATE"}
VALID_REG_TYPES = {"REGULAR", "COMPOSITION", "ISD", "TDS", "TCS", "CASUAL", "SEZ", "NRTP"}
VALID_IRN_STATUSES = {"ACTIVE", "CANCELLED"}


# ---------------------------------------------------------------------------
# Result Tracking
# ---------------------------------------------------------------------------
class ValidationReport:
    def __init__(self):
        self.passes = []
        self.fails = []
        self.warnings = []

    def add_pass(self, check_name, detail=""):
        self.passes.append((check_name, detail))

    def add_fail(self, check_name, detail=""):
        self.fails.append((check_name, detail))

    def add_warning(self, check_name, detail=""):
        self.warnings.append((check_name, detail))

    @property
    def total(self):
        return len(self.passes) + len(self.fails) + len(self.warnings)

    @property
    def score(self):
        if self.total == 0:
            return 0.0
        return round((len(self.passes) / self.total) * 100, 1)

    def print_report(self):
        sep = "=" * 70
        print(f"\n{sep}")
        print("  PramanaGST Contract-1 Dataset Validation Report")
        print(sep)

        # PASS
        print(f"\n[PASS] ({len(self.passes)} checks)")
        print("-" * 40)
        for name, detail in self.passes:
            msg = f"  [+] {name}"
            if detail:
                msg += f"  --  {detail}"
            print(msg)

        # FAIL
        print(f"\n[FAIL] ({len(self.fails)} checks)")
        print("-" * 40)
        if not self.fails:
            print("  None")
        for name, detail in self.fails:
            msg = f"  [X] {name}"
            if detail:
                msg += f"  --  {detail}"
            print(msg)

        # WARNING
        print(f"\n[WARNING] ({len(self.warnings)} checks)")
        print("-" * 40)
        if not self.warnings:
            print("  None")
        for name, detail in self.warnings:
            msg = f"  [!] {name}"
            if detail:
                msg += f"  --  {detail}"
            print(msg)

        # Score
        print(f"\n{sep}")
        print(f"  CONTRACT READINESS SCORE: {self.score}%")
        print(f"  ({len(self.passes)} passed / {self.total} total checks)")
        if self.score == 100.0:
            print("  STATUS: READY FOR INGESTION")
        elif self.score >= 80.0:
            print("  STATUS: MINOR ISSUES - Review warnings")
        elif self.score >= 50.0:
            print("  STATUS: SIGNIFICANT ISSUES - Fix failures before proceeding")
        else:
            print("  STATUS: NOT READY - Critical failures detected")
        print(sep)


# ---------------------------------------------------------------------------
# Loader
# ---------------------------------------------------------------------------
def load_datasets():
    dfs = {}
    missing = []
    # Columns that contain leading-zero formatted strings (e.g., MMYYYY periods)
    str_dtype_overrides = {
        "gstr2b": {"claim_period": str},
        "payments": {"return_period": str},
    }
    for key, filename in REQUIRED_FILES.items():
        path = os.path.join(DATA_DIR, filename)
        if os.path.exists(path):
            dtype = str_dtype_overrides.get(key, None)
            dfs[key] = pd.read_csv(path, dtype=dtype)
        else:
            missing.append(filename)
    return dfs, missing


# ---------------------------------------------------------------------------
# Individual Validation Checks
# ---------------------------------------------------------------------------

def check_file_presence(report, dfs, missing):
    """Check all 5 required files exist."""
    if not missing:
        report.add_pass("File Presence", f"All {len(REQUIRED_FILES)} required files found")
    else:
        report.add_fail("File Presence", f"Missing: {', '.join(missing)}")


def check_gstin_format(report, dfs):
    """Validate GSTIN regex across all datasets that contain GSTIN columns."""
    gstin_columns = {
        "taxpayers": ["gstin"],
        "gstr1": ["supplier_gstin", "recipient_gstin"],
        "gstr2b": ["recipient_gstin"],
        "payments": ["supplier_gstin"],
    }
    total_invalid = 0
    details = []

    for dataset, columns in gstin_columns.items():
        if dataset not in dfs:
            continue
        df = dfs[dataset]
        for col in columns:
            if col not in df.columns:
                continue
            series = df[col].dropna().astype(str)
            invalid = series[~series.str.match(GSTIN_PATTERN)]
            if len(invalid) > 0:
                total_invalid += len(invalid)
                details.append(f"{dataset}.{col}: {len(invalid)} invalid")

    if total_invalid == 0:
        report.add_pass("GSTIN Regex Validation", "All GSTINs match 15-char format")
    else:
        report.add_fail("GSTIN Regex Validation", "; ".join(details))


def check_iso_dates(report, dfs):
    """Validate all date columns use ISO 8601 (YYYY-MM-DD) format."""
    date_columns = {
        "gstr1": ["invoice_date"],
    }
    total_invalid = 0
    details = []

    for dataset, columns in date_columns.items():
        if dataset not in dfs:
            continue
        df = dfs[dataset]
        for col in columns:
            if col not in df.columns:
                continue
            series = df[col].dropna().astype(str)
            invalid = series[~series.str.match(ISO_DATE_PATTERN)]
            if len(invalid) > 0:
                total_invalid += len(invalid)
                details.append(f"{dataset}.{col}: {len(invalid)} non-ISO dates")

    # Also check timestamps in einvoice
    if "einvoice" in dfs and "generation_timestamp" in dfs["einvoice"].columns:
        ts = dfs["einvoice"]["generation_timestamp"].dropna().astype(str)
        bad_ts = []
        for val in ts:
            try:
                datetime.fromisoformat(val)
            except ValueError:
                bad_ts.append(val)
        if bad_ts:
            total_invalid += len(bad_ts)
            details.append(f"einvoice.generation_timestamp: {len(bad_ts)} non-ISO timestamps")

    if total_invalid == 0:
        report.add_pass("ISO Date Validation", "All dates/timestamps are ISO 8601 compliant")
    else:
        report.add_fail("ISO Date Validation", "; ".join(details))


def check_monetary_decimals(report, dfs):
    """Validate all monetary columns are non-negative numeric values."""
    money_columns = {
        "gstr1": ["invoice_value", "cgst_amount", "sgst_amount", "igst_amount"],
        "gstr2b": ["itc_claimed"],
        "payments": ["tax_paid"],
    }
    total_invalid = 0
    details = []

    for dataset, columns in money_columns.items():
        if dataset not in dfs:
            continue
        df = dfs[dataset]
        for col in columns:
            if col not in df.columns:
                continue
            series = pd.to_numeric(df[col], errors="coerce")
            neg_count = (series < 0).sum()
            nan_count = series.isna().sum()
            if neg_count > 0:
                total_invalid += neg_count
                details.append(f"{dataset}.{col}: {neg_count} negative values")
            if nan_count > 0:
                total_invalid += nan_count
                details.append(f"{dataset}.{col}: {nan_count} non-numeric values")

    if total_invalid == 0:
        report.add_pass("Monetary Decimal Validation", "All monetary values are non-negative numerics")
    else:
        report.add_fail("Monetary Decimal Validation", "; ".join(details))


def check_invoice_tax_sum(report, dfs):
    """Validate: cgst + sgst + igst should be a component of invoice_value."""
    if "gstr1" not in dfs:
        report.add_warning("Invoice Tax Sum", "gstr1.csv not loaded")
        return
    df = dfs["gstr1"]
    required = ["cgst_amount", "sgst_amount", "igst_amount"]
    if not all(c in df.columns for c in required):
        report.add_fail("Invoice Tax Sum", "Missing tax component columns")
        return

    tax_sum = df["cgst_amount"] + df["sgst_amount"] + df["igst_amount"]
    # Tax sum must be >= 0
    invalid = (tax_sum < 0).sum()
    if invalid == 0:
        report.add_pass("Invoice Tax Sum", f"All {len(df)} invoices have valid tax component sums")
    else:
        report.add_fail("Invoice Tax Sum", f"{invalid} invoices have negative aggregate tax")


def check_invoice_total_value(report, dfs):
    """Validate: invoice_value should be > sum of tax components (since it includes taxable value)."""
    if "gstr1" not in dfs:
        report.add_warning("Invoice Total Value", "gstr1.csv not loaded")
        return
    df = dfs["gstr1"]
    required = ["invoice_value", "cgst_amount", "sgst_amount", "igst_amount"]
    if not all(c in df.columns for c in required):
        report.add_fail("Invoice Total Value", "Missing required columns")
        return

    tax_sum = df["cgst_amount"] + df["sgst_amount"] + df["igst_amount"]
    invalid = (df["invoice_value"] < tax_sum).sum()
    if invalid == 0:
        report.add_pass("Invoice Total Value", "All invoice_values >= tax component sums")
    else:
        report.add_fail("Invoice Total Value", f"{invalid} invoices have total < tax sum")


def check_financial_year_derivation(report, dfs):
    """Validate invoice dates can derive a valid financial year."""
    if "gstr1" not in dfs:
        report.add_warning("Financial Year Derivation", "gstr1.csv not loaded")
        return
    df = dfs["gstr1"]
    if "invoice_date" not in df.columns:
        report.add_fail("Financial Year Derivation", "Missing invoice_date column")
        return

    try:
        dates = pd.to_datetime(df["invoice_date"], format="%Y-%m-%d", errors="coerce")
        invalid_count = dates.isna().sum()
        if invalid_count > 0:
            report.add_fail("Financial Year Derivation", f"{invalid_count} dates cannot be parsed")
        else:
            years = dates.dt.year.unique()
            report.add_pass("Financial Year Derivation", f"Dates span year(s): {sorted(years)}")
    except Exception as e:
        report.add_fail("Financial Year Derivation", str(e))


def check_foreign_key_resolution(report, dfs):
    """Cross-dataset FK checks: invoices reference existing taxpayers, etc."""
    details_pass = []
    details_fail = []

    # 1. gstr1.supplier_gstin -> taxpayers.gstin
    if "gstr1" in dfs and "taxpayers" in dfs:
        tp_set = set(dfs["taxpayers"]["gstin"].dropna().astype(str))
        supplier_set = set(dfs["gstr1"]["supplier_gstin"].dropna().astype(str))
        orphan_suppliers = supplier_set - tp_set
        if not orphan_suppliers:
            details_pass.append(f"gstr1.supplier_gstin -> taxpayers.gstin ({len(supplier_set)} resolved)")
        else:
            details_fail.append(f"gstr1.supplier_gstin: {len(orphan_suppliers)} orphaned GSTINs not in taxpayers")

    # 2. gstr1.recipient_gstin -> taxpayers.gstin
    if "gstr1" in dfs and "taxpayers" in dfs:
        recipient_set = set(dfs["gstr1"]["recipient_gstin"].dropna().astype(str))
        orphan_recipients = recipient_set - tp_set
        if not orphan_recipients:
            details_pass.append(f"gstr1.recipient_gstin -> taxpayers.gstin ({len(recipient_set)} resolved)")
        else:
            details_fail.append(f"gstr1.recipient_gstin: {len(orphan_recipients)} orphaned GSTINs not in taxpayers")

    # 3. gstr2b.recipient_gstin -> taxpayers.gstin
    if "gstr2b" in dfs and "taxpayers" in dfs:
        r2b_recipients = set(dfs["gstr2b"]["recipient_gstin"].dropna().astype(str))
        orphan_r2b = r2b_recipients - tp_set
        if not orphan_r2b:
            details_pass.append(f"gstr2b.recipient_gstin -> taxpayers.gstin ({len(r2b_recipients)} resolved)")
        else:
            details_fail.append(f"gstr2b.recipient_gstin: {len(orphan_r2b)} orphaned GSTINs not in taxpayers")

    # 4. payments.supplier_gstin -> taxpayers.gstin
    if "payments" in dfs and "taxpayers" in dfs:
        pay_suppliers = set(dfs["payments"]["supplier_gstin"].dropna().astype(str))
        orphan_pay = pay_suppliers - tp_set
        if not orphan_pay:
            details_pass.append(f"payments.supplier_gstin -> taxpayers.gstin ({len(pay_suppliers)} resolved)")
        else:
            details_fail.append(f"payments.supplier_gstin: {len(orphan_pay)} orphaned GSTINs not in taxpayers")

    # 5. gstr2b.invoice_number -> gstr1.invoice_number (subset expected due to mismatch injection)
    if "gstr2b" in dfs and "gstr1" in dfs:
        gstr1_invs = set(dfs["gstr1"]["invoice_number"].dropna().astype(str))
        gstr2b_invs = set(dfs["gstr2b"]["invoice_number"].dropna().astype(str))
        orphan_invs = gstr2b_invs - gstr1_invs
        if not orphan_invs:
            details_pass.append(f"gstr2b.invoice_number -> gstr1.invoice_number ({len(gstr2b_invs)} resolved)")
        else:
            details_fail.append(f"gstr2b.invoice_number: {len(orphan_invs)} invoices not found in gstr1")

    if details_fail:
        report.add_fail("Cross-Dataset FK Resolution", "; ".join(details_fail))
    if details_pass:
        report.add_pass("Cross-Dataset FK Resolution", "; ".join(details_pass))


def check_duplicate_invoices(report, dfs):
    """Check for duplicate invoice numbers within gstr1 (expected unique)."""
    if "gstr1" not in dfs:
        report.add_warning("Duplicate Invoice Check", "gstr1.csv not loaded")
        return
    df = dfs["gstr1"]
    if "invoice_number" not in df.columns:
        report.add_fail("Duplicate Invoice Check", "Missing invoice_number column")
        return

    dupes = df["invoice_number"].duplicated().sum()
    if dupes == 0:
        report.add_pass("Duplicate Invoice Check", f"All {len(df)} invoice numbers are unique in gstr1")
    else:
        report.add_warning("Duplicate Invoice Check", f"{dupes} duplicate invoice numbers found in gstr1")


def check_irn_linkage(report, dfs):
    """Validate IRN records link back to existing invoices in gstr1."""
    if "einvoice" not in dfs or "gstr1" not in dfs:
        report.add_warning("IRN Linkage Feasibility", "einvoice.csv or gstr1.csv not loaded")
        return

    einv_inv_nums = set(dfs["einvoice"]["invoice_number"].dropna().astype(str))
    gstr1_inv_nums = set(dfs["gstr1"]["invoice_number"].dropna().astype(str))

    orphan_irns = einv_inv_nums - gstr1_inv_nums
    if not orphan_irns:
        report.add_pass("IRN Linkage Feasibility", f"All {len(einv_inv_nums)} IRNs link to valid gstr1 invoices")
    else:
        report.add_fail("IRN Linkage Feasibility", f"{len(orphan_irns)} IRNs reference non-existent invoices")

    # Also check: IRN hash from gstr1.irn column matches einvoice.irn
    if "irn" in dfs["gstr1"].columns and "irn" in dfs["einvoice"].columns:
        gstr1_irns = set(dfs["gstr1"]["irn"].dropna().astype(str)) - {""}
        einv_irns = set(dfs["einvoice"]["irn"].dropna().astype(str))
        missing_from_einv = gstr1_irns - einv_irns
        if not missing_from_einv:
            report.add_pass("IRN Hash Cross-Reference", f"All {len(gstr1_irns)} gstr1 IRN hashes exist in einvoice")
        else:
            report.add_fail("IRN Hash Cross-Reference", f"{len(missing_from_einv)} gstr1 IRN hashes missing from einvoice")

    # Check IRN status values
    if "status" in dfs["einvoice"].columns:
        statuses = set(dfs["einvoice"]["status"].dropna().astype(str))
        invalid_statuses = statuses - VALID_IRN_STATUSES
        if not invalid_statuses:
            report.add_pass("IRN Status Values", f"All statuses valid: {statuses}")
        else:
            report.add_fail("IRN Status Values", f"Invalid statuses found: {invalid_statuses}")


def check_return_payment_completeness(report, dfs):
    """Validate that payment records cover the supplier GSTINs from gstr1."""
    if "payments" not in dfs or "gstr1" not in dfs:
        report.add_warning("Return/Payment Completeness", "payments.csv or gstr1.csv not loaded")
        return

    gstr1_suppliers = set(dfs["gstr1"]["supplier_gstin"].dropna().astype(str))
    payment_suppliers = set(dfs["payments"]["supplier_gstin"].dropna().astype(str))

    missing_payments = gstr1_suppliers - payment_suppliers
    if not missing_payments:
        report.add_pass("Return/Payment Completeness", f"All {len(gstr1_suppliers)} suppliers have payment records")
    else:
        report.add_warning("Return/Payment Completeness", f"{len(missing_payments)} suppliers in gstr1 have no payment record")

    # Check claim period format in gstr2b
    if "gstr2b" in dfs and "claim_period" in dfs["gstr2b"].columns:
        periods = dfs["gstr2b"]["claim_period"].dropna().astype(str)
        invalid_periods = periods[~periods.str.match(MMYYYY_PATTERN)]
        if len(invalid_periods) == 0:
            report.add_pass("Claim Period Format", "All gstr2b claim_period values match MMYYYY")
        else:
            report.add_fail("Claim Period Format", f"{len(invalid_periods)} invalid claim_period values")

    # Check return_period in payments
    if "return_period" in dfs["payments"].columns:
        periods = dfs["payments"]["return_period"].dropna().astype(str)
        invalid_periods = periods[~periods.str.match(MMYYYY_PATTERN)]
        if len(invalid_periods) == 0:
            report.add_pass("Payment Period Format", "All payment return_period values match MMYYYY")
        else:
            report.add_fail("Payment Period Format", f"{len(invalid_periods)} invalid return_period values")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    report = ValidationReport()

    print("Loading datasets...")
    dfs, missing = load_datasets()

    check_file_presence(report, dfs, missing)

    if missing:
        print(f"Cannot proceed: missing files {missing}")
        report.print_report()
        sys.exit(1)

    print(f"Loaded: {', '.join(f'{k}({len(v)} rows)' for k, v in dfs.items())}")
    print("Running validation checks...\n")

    check_gstin_format(report, dfs)
    check_iso_dates(report, dfs)
    check_monetary_decimals(report, dfs)
    check_invoice_tax_sum(report, dfs)
    check_invoice_total_value(report, dfs)
    check_financial_year_derivation(report, dfs)
    check_foreign_key_resolution(report, dfs)
    check_duplicate_invoices(report, dfs)
    check_irn_linkage(report, dfs)
    check_return_payment_completeness(report, dfs)

    report.print_report()

    # Exit with non-zero if any failures
    sys.exit(1 if report.fails else 0)


if __name__ == "__main__":
    main()
