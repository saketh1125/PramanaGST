"""
Contract v1.0.0 — Schema generation & serialization verification.

Generates contracts/contract_1.json from Pydantic model JSON schemas,
then instantiates each model with sample data and validates round-trip
JSON serialization produces contract-compliant output.
"""

import json
import sys
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.ingestion.schemas import (
    Invoice,
    IRN,
    Payment,
    ReturnFiling,
    Taxpayer,
)
from backend.ingestion.schemas.enums import (
    DocumentType,
    GSTRegistrationStatus,
    GSTRegistrationType,
    GSTReturnType,
    InvoiceStatus,
    InvoiceType,
    IRNStatus,
    PaymentMode,
    PaymentStatus,
    ReturnFilingStatus,
    SupplyType,
)


def generate_contract() -> dict:
    """Generate the canonical contract JSON schema from all entity models."""
    contract = {
        "contract": "INGESTION <-> KNOWLEDGE GRAPH INTERFACE",
        "version": "1.0.0",
        "entities": {
            "TAXPAYER": Taxpayer.model_json_schema(),
            "INVOICE": Invoice.model_json_schema(),
            "RETURN": ReturnFiling.model_json_schema(),
            "PAYMENT": Payment.model_json_schema(),
            "IRN": IRN.model_json_schema(),
        },
    }
    return contract


def test_taxpayer_serialization():
    """Verify TAXPAYER model serializes to contract-compliant JSON."""
    tp = Taxpayer(
        gstin="27AAPFU0939F1ZV",
        legal_name="Test Corp Pvt Ltd",
        trade_name="TestCorp",
        registration_type=GSTRegistrationType.REGULAR,
        registration_status=GSTRegistrationStatus.ACTIVE,
        registration_date=date(2017, 7, 1),
        cancellation_date=None,
        state_code="27",
        pan="AAPFU0939F",
    )
    data = tp.model_dump(mode="json", by_alias=True)
    assert data["gstin"] == "27AAPFU0939F1ZV"
    assert data["legalName"] == "Test Corp Pvt Ltd"
    assert data["tradeName"] == "TestCorp"
    assert data["registrationType"] == "REGULAR"
    assert data["registrationStatus"] == "ACTIVE"
    assert data["registrationDate"] == "2017-07-01"
    assert data["cancellationDate"] is None
    assert data["stateCode"] == "27"
    assert data["pan"] == "AAPFU0939F"
    print("  [OK] TAXPAYER serialization OK")
    return data


def test_invoice_serialization():
    """Verify INVOICE model serializes to contract-compliant JSON."""
    inv = Invoice(
        invoice_number="INV-2026-001",
        invoice_date=date(2026, 1, 15),
        invoice_type=InvoiceType.B2B,
        invoice_status=InvoiceStatus.ACTIVE,
        supply_type=SupplyType.INTER_STATE,
        document_type=DocumentType.INV,
        supplier_gstin="27AAPFU0939F1ZV",
        recipient_gstin="29AABCU9603R1ZM",
        taxable_value=Decimal("100000.00"),
        igst_amount=Decimal("18000.00"),
        cgst_amount=Decimal("0.00"),
        sgst_amount=Decimal("0.00"),
        cess_amount=Decimal("0.00"),
        total_value=Decimal("118000.00"),
        place_of_supply="29",
        reverse_charge=False,
        irn=None,
        filing_period="012026",
    )
    data = inv.model_dump(mode="json", by_alias=True)
    assert data["invoiceNumber"] == "INV-2026-001"
    assert data["invoiceType"] == "B2B"
    assert data["supplierGstin"] == "27AAPFU0939F1ZV"
    assert data["recipientGstin"] == "29AABCU9603R1ZM"
    assert data["taxableValue"] == "100000.00"
    assert data["totalValue"] == "118000.00"
    assert data["placeOfSupply"] == "29"
    assert data["reverseCharge"] is False
    assert data["filingPeriod"] == "012026"
    print("  [OK] INVOICE serialization OK")
    return data


def test_return_filing_serialization():
    """Verify RETURN model serializes to contract-compliant JSON."""
    ret = ReturnFiling(
        return_id="RET-27AAPFU0939F1ZV-GSTR3B-012026",
        gstin="27AAPFU0939F1ZV",
        return_type=GSTReturnType.GSTR3B,
        return_period="012026",
        filing_date=date(2026, 2, 20),
        filing_status=ReturnFilingStatus.FILED,
        total_taxable_value=Decimal("500000.00"),
        total_igst=Decimal("90000.00"),
        total_cgst=Decimal("0.00"),
        total_sgst=Decimal("0.00"),
        total_cess=Decimal("0.00"),
        total_tax_liability=Decimal("90000.00"),
        itc_claimed_igst=Decimal("18000.00"),
        itc_claimed_cgst=Decimal("0.00"),
        itc_claimed_sgst=Decimal("0.00"),
        itc_claimed_cess=Decimal("0.00"),
    )
    data = ret.model_dump(mode="json", by_alias=True)
    assert data["returnId"] == "RET-27AAPFU0939F1ZV-GSTR3B-012026"
    assert data["returnType"] == "GSTR3B"
    assert data["filingStatus"] == "FILED"
    assert data["totalTaxLiability"] == "90000.00"
    assert data["itcClaimedIgst"] == "18000.00"
    print("  [OK] RETURN serialization OK")
    return data


def test_payment_serialization():
    """Verify PAYMENT model serializes to contract-compliant JSON."""
    pmt = Payment(
        payment_id="PMT-27AAPFU0939F1ZV-012026-001",
        gstin="27AAPFU0939F1ZV",
        return_period="012026",
        payment_date=date(2026, 2, 20),
        payment_mode=PaymentMode.CASH,
        payment_status=PaymentStatus.PAID,
        igst_paid=Decimal("72000.00"),
        cgst_paid=Decimal("0.00"),
        sgst_paid=Decimal("0.00"),
        cess_paid=Decimal("0.00"),
        total_paid=Decimal("72000.00"),
        challan_number="CIN202602200001",
        bank_reference="BRN202602200001",
    )
    data = pmt.model_dump(mode="json", by_alias=True)
    assert data["paymentId"] == "PMT-27AAPFU0939F1ZV-012026-001"
    assert data["paymentMode"] == "CASH"
    assert data["paymentStatus"] == "PAID"
    assert data["totalPaid"] == "72000.00"
    assert data["challanNumber"] == "CIN202602200001"
    print("  [OK] PAYMENT serialization OK")
    return data


def test_irn_serialization():
    """Verify IRN model serializes to contract-compliant JSON."""
    irn_hash = "a" * 64  # 64-char hash placeholder
    irn = IRN(
        irn=irn_hash,
        irn_date=datetime(2026, 1, 15, 10, 30, 0),
        irn_status=IRNStatus.ACTIVE,
        invoice_number="INV-2026-001",
        supplier_gstin="27AAPFU0939F1ZV",
        document_type=DocumentType.INV,
        signed_invoice=None,
        signed_qr_code=None,
        ack_number="ACK123456789",
        ack_date=datetime(2026, 1, 15, 10, 30, 5),
        cancellation_date=None,
        cancellation_reason=None,
    )
    data = irn.model_dump(mode="json", by_alias=True)
    assert data["irn"] == irn_hash
    assert data["irnStatus"] == "ACTIVE"
    assert data["invoiceNumber"] == "INV-2026-001"
    assert data["ackNumber"] == "ACK123456789"
    assert data["cancellationDate"] is None
    print("  [OK] IRN serialization OK")
    return data


def test_validation_errors():
    """Verify invalid data raises ValidationError."""
    from pydantic import ValidationError

    errors_caught = 0

    # Invalid GSTIN format
    try:
        Taxpayer(
            gstin="INVALID",
            legal_name="Test",
            registration_type=GSTRegistrationType.REGULAR,
            registration_status=GSTRegistrationStatus.ACTIVE,
            registration_date=date(2017, 7, 1),
            state_code="27",
            pan="AAPFU0939F",
        )
    except ValidationError:
        errors_caught += 1

    # Negative monetary value
    try:
        Payment(
            payment_id="PMT-001",
            gstin="27AAPFU0939F1ZV",
            return_period="012026",
            payment_date=date(2026, 2, 20),
            payment_mode=PaymentMode.CASH,
            payment_status=PaymentStatus.PAID,
            igst_paid=Decimal("-100.00"),  # negative — should fail
            cgst_paid=Decimal("0.00"),
            sgst_paid=Decimal("0.00"),
            cess_paid=Decimal("0.00"),
            total_paid=Decimal("-100.00"),
        )
    except ValidationError:
        errors_caught += 1

    # Invalid filing period format
    try:
        Invoice(
            invoice_number="INV-001",
            invoice_date=date(2026, 1, 15),
            invoice_type=InvoiceType.B2B,
            invoice_status=InvoiceStatus.ACTIVE,
            supply_type=SupplyType.INTER_STATE,
            document_type=DocumentType.INV,
            supplier_gstin="27AAPFU0939F1ZV",
            taxable_value=Decimal("1000.00"),
            igst_amount=Decimal("180.00"),
            cgst_amount=Decimal("0.00"),
            sgst_amount=Decimal("0.00"),
            cess_amount=Decimal("0.00"),
            total_value=Decimal("1180.00"),
            place_of_supply="27",
            reverse_charge=False,
            filing_period="13-2026",  # invalid format
        )
    except ValidationError:
        errors_caught += 1

    assert errors_caught == 3, f"Expected 3 validation errors, got {errors_caught}"
    print("  ✅ Validation error handling OK (3/3 caught)")


if __name__ == "__main__":
    print("=" * 60)
    print("CONTRACT v1.0.0 -- Schema Verification")
    print("=" * 60)

    # 1. Serialize each entity
    print("\n[SERIALIZATION TESTS]")
    sample_taxpayer = test_taxpayer_serialization()
    sample_invoice = test_invoice_serialization()
    sample_return = test_return_filing_serialization()
    sample_payment = test_payment_serialization()
    sample_irn = test_irn_serialization()

    # 2. Validation tests
    print("\n[VALIDATION TESTS]")
    test_validation_errors()

    # 3. Generate contract JSON
    print("\n[GENERATING contract_1.json]")
    contract = generate_contract()
    contract_path = Path(__file__).resolve().parent.parent / "contracts" / "contract_1.json"
    contract_path.parent.mkdir(parents=True, exist_ok=True)
    contract_path.write_text(json.dumps(contract, indent=2, default=str))
    print(f"  [OK] Contract written to {contract_path}")

    # 4. Summary
    print("\n" + "=" * 60)
    print("[OK] ALL CHECKS PASSED -- Models are contract-compliant.")
    print("=" * 60)

    # Print sample JSON for review
    print("\n[SAMPLE TAXPAYER JSON]")
    print(json.dumps(sample_taxpayer, indent=2, default=str))
