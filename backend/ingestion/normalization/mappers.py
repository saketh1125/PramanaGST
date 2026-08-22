"""
Row mappers — transform raw CSV rows into canonical Contract-1 entities.

Every mapper is pure: raw dict in, Pydantic model out. Fields absent from
the source CSVs are derived deterministically (documented per field).
"""

import calendar
from datetime import date, datetime
from decimal import Decimal

from ..schemas import Invoice, IRN, Payment, ReturnFiling, Taxpayer
from ..schemas.enums import (
    DocumentType,
    GSTRegistrationStatus,
    GSTReturnType,
    InvoiceStatus,
    InvoiceType,
    IRNStatus,
    PaymentMode,
    PaymentStatus,
    ReturnFilingStatus,
)

# Registrations predating the dataset default to the GST launch date.
_DEFAULT_REGISTRATION_DATE = date(2017, 7, 1)


def _d(value) -> Decimal:
    return Decimal(str(value)).quantize(Decimal("0.01"))


def _clean(value) -> str | None:
    """CSV cells may hold NaN floats or blank strings — normalize to None."""
    if value is None or (isinstance(value, float) and value != value):
        return None
    s = str(value).strip()
    return s or None


def map_taxpayer(row: dict) -> Taxpayer:
    gstin = row["gstin"]
    return Taxpayer(
        gstin=gstin,
        legalName=row["legal_name"],
        registrationType=row["registration_type"],
        registrationStatus=GSTRegistrationStatus.ACTIVE,
        # ponytail: no registration_date column — default to GST launch; wire a real registry feed when one exists
        registrationDate=_DEFAULT_REGISTRATION_DATE,
        stateCode=row["state_code"],
        pan=gstin[2:12],
    )


def map_invoice(row: dict) -> Invoice:
    total = _d(row["invoice_value"])
    taxes = _d(row["cgst_amount"]) + _d(row["sgst_amount"]) + _d(row["igst_amount"])
    inv_date = datetime.strptime(row["invoice_date"], "%Y-%m-%d").date()
    recipient = _clean(row.get("recipient_gstin"))

    filing_period = f"{inv_date.month:02d}{inv_date.year}"

    return Invoice(
        invoiceNumber=row["invoice_number"],
        invoiceDate=inv_date,
        # All generated invoices carry a recipient GSTIN → B2B by definition
        invoiceType=InvoiceType.B2B if recipient else InvoiceType.B2C,
        invoiceStatus=InvoiceStatus.ACTIVE,
        supplyType=row["supply_type"],
        documentType=DocumentType.INV,
        supplierGstin=row["supplier_gstin"],
        recipientGstin=recipient,
        taxableValue=total - taxes,
        igstAmount=_d(row["igst_amount"]),
        cgstAmount=_d(row["cgst_amount"]),
        sgstAmount=_d(row["sgst_amount"]),
        cessAmount=Decimal("0.00"),
        totalValue=total,
        placeOfSupply=(recipient or "")[:2] or "00",
        reverseCharge=False,
        irn=_clean(row.get("irn")),
        filingPeriod=filing_period,
    )


def map_gstr2b_return(rows: list[dict], recipient_gstin: str, period: str) -> ReturnFiling:
    """Aggregate per-invoice GSTR-2B claim rows into one Return entity."""
    itc_total = sum((_d(r["itc_claimed"]) for r in rows), Decimal("0.00"))
    year = int(period[2:])
    month = int(period[:2])
    return ReturnFiling(
        returnId=f"GSTR2B-{recipient_gstin}-{period}",
        gstin=recipient_gstin,
        returnType=GSTReturnType.GSTR2B,
        returnPeriod=period,
        filingDate=date(year, month, calendar.monthrange(year, month)[1]),
        filingStatus=ReturnFilingStatus.FILED,
        totalTaxableValue=Decimal("0.00"),
        totalIgst=Decimal("0.00"),
        totalCgst=Decimal("0.00"),
        totalSgst=Decimal("0.00"),
        totalCess=Decimal("0.00"),
        totalTaxLiability=Decimal("0.00"),
        itcClaimedIgst=itc_total,
        itcClaimedCgst=Decimal("0.00"),
        itcClaimedSgst=Decimal("0.00"),
        itcClaimedCess=Decimal("0.00"),
    )


def map_gstr1_return(rows: list[dict], supplier_gstin: str, period: str) -> ReturnFiling:
    """Aggregate supplier invoices into one GSTR-1 Return entity."""
    taxable = sum(
        (_d(r["invoice_value"]) - _d(r["igst_amount"]) - _d(r["cgst_amount"]) - _d(r["sgst_amount"]) for r in rows),
        Decimal("0.00"),
    )
    igst = sum((_d(r["igst_amount"]) for r in rows), Decimal("0.00"))
    cgst = sum((_d(r["cgst_amount"]) for r in rows), Decimal("0.00"))
    sgst = sum((_d(r["sgst_amount"]) for r in rows), Decimal("0.00"))
    year = int(period[2:])
    month = int(period[:2])
    return ReturnFiling(
        returnId=f"GSTR1-{supplier_gstin}-{period}",
        gstin=supplier_gstin,
        returnType=GSTReturnType.GSTR1,
        returnPeriod=period,
        filingDate=date(year, month, calendar.monthrange(year, month)[1]),
        filingStatus=ReturnFilingStatus.FILED,
        totalTaxableValue=taxable,
        totalIgst=igst,
        totalCgst=cgst,
        totalSgst=sgst,
        totalCess=Decimal("0.00"),
        totalTaxLiability=igst + cgst + sgst,
        itcClaimedIgst=Decimal("0.00"),
        itcClaimedCgst=Decimal("0.00"),
        itcClaimedSgst=Decimal("0.00"),
        itcClaimedCess=Decimal("0.00"),
    )


def map_payment(row: dict) -> Payment:
    period = row["return_period"]
    year = int(period[2:])
    month = int(period[:2])
    paid = _d(row["tax_paid"])
    return Payment(
        paymentId=f"PMT-{row['supplier_gstin']}-{period}",
        gstin=row["supplier_gstin"],
        returnPeriod=period,
        paymentDate=date(year, month, calendar.monthrange(year, month)[1]),
        paymentMode=PaymentMode.CASH,
        paymentStatus=PaymentStatus.PAID,
        # ponytail: component split not present in payments.csv — total carried on totalPaid; split when ledger data arrives
        igstPaid=Decimal("0.00"),
        cgstPaid=Decimal("0.00"),
        sgstPaid=Decimal("0.00"),
        cessPaid=Decimal("0.00"),
        totalPaid=paid,
    )


def map_irn(row: dict, invoice_lookup: dict[str, dict]) -> IRN:
    inv = invoice_lookup[row["invoice_number"]]
    ts = datetime.fromisoformat(row["generation_timestamp"])
    return IRN(
        irn=row["irn"],
        irnDate=ts,
        irnStatus=IRNStatus(row["status"]),
        invoiceNumber=row["invoice_number"],
        supplierGstin=inv["supplier_gstin"],
        documentType=DocumentType.INV,
        ackNumber=row["irn"][:15],
        ackDate=ts,
    )
