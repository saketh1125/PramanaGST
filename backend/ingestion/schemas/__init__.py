"""
Ingestion Schemas — INGESTION ↔ KNOWLEDGE GRAPH Interface Contract v1.0.0.

Canonical Pydantic models for the five GST entities:
  - Taxpayer
  - Invoice
  - ReturnFiling  (RETURN entity)
  - Payment
  - IRN

All enums are re-exported for convenience.
"""

from .enums import (
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
from .invoice import Invoice
from .irn import IRN
from .payment import Payment
from .return_filing import ReturnFiling
from .taxpayer import Taxpayer

__all__ = [
    # Entities
    "Taxpayer",
    "Invoice",
    "ReturnFiling",
    "Payment",
    "IRN",
    # Enums
    "GSTRegistrationType",
    "GSTRegistrationStatus",
    "InvoiceType",
    "InvoiceStatus",
    "SupplyType",
    "DocumentType",
    "GSTReturnType",
    "ReturnFilingStatus",
    "PaymentMode",
    "PaymentStatus",
    "IRNStatus",
]
