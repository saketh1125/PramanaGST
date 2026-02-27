"""
Shared enum definitions for INGESTION ↔ KNOWLEDGE GRAPH Interface Contract v1.0.0.

All enums inherit from (str, Enum) for clean JSON serialization.
"""

from enum import Enum


class GSTRegistrationType(str, Enum):
    """Type of GST registration held by a taxpayer."""

    REGULAR = "REGULAR"
    COMPOSITION = "COMPOSITION"
    ISD = "ISD"
    TDS = "TDS"
    TCS = "TCS"
    CASUAL = "CASUAL"
    SEZ = "SEZ"
    NRTP = "NRTP"


class GSTRegistrationStatus(str, Enum):
    """Current status of a GST registration."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    SUSPENDED = "SUSPENDED"
    INACTIVE = "INACTIVE"


class InvoiceType(str, Enum):
    """Classification of invoice by supply category."""

    B2B = "B2B"
    B2C = "B2C"
    CDNR = "CDNR"
    CDNUR = "CDNUR"
    EXPORT = "EXPORT"
    SEZ = "SEZ"
    NIL_RATED = "NIL_RATED"
    ADVANCE = "ADVANCE"


class InvoiceStatus(str, Enum):
    """Current status of an invoice."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
    AMENDED = "AMENDED"


class SupplyType(str, Enum):
    """Whether the supply is intra-state or inter-state."""

    INTRA_STATE = "INTRA_STATE"
    INTER_STATE = "INTER_STATE"


class DocumentType(str, Enum):
    """Type of e-invoice document."""

    INV = "INV"
    CRN = "CRN"
    DBN = "DBN"


class GSTReturnType(str, Enum):
    """Type of GST return filed."""

    GSTR1 = "GSTR1"
    GSTR2A = "GSTR2A"
    GSTR2B = "GSTR2B"
    GSTR3B = "GSTR3B"
    GSTR9 = "GSTR9"
    GSTR9C = "GSTR9C"


class ReturnFilingStatus(str, Enum):
    """Filing status of a GST return."""

    FILED = "FILED"
    NOT_FILED = "NOT_FILED"
    LATE_FILED = "LATE_FILED"
    REVISED = "REVISED"


class PaymentMode(str, Enum):
    """Mode through which GST was paid."""

    CASH = "CASH"
    ITC_IGST = "ITC_IGST"
    ITC_CGST = "ITC_CGST"
    ITC_SGST = "ITC_SGST"
    ITC_CESS = "ITC_CESS"


class PaymentStatus(str, Enum):
    """Current status of a GST payment."""

    PAID = "PAID"
    PENDING = "PENDING"
    PARTIAL = "PARTIAL"
    FAILED = "FAILED"


class IRNStatus(str, Enum):
    """Current status of an Invoice Reference Number."""

    ACTIVE = "ACTIVE"
    CANCELLED = "CANCELLED"
