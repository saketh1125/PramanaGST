"""
TAXPAYER entity model — Contract v1.0.0.

Represents a GST-registered entity identified by a unique GSTIN.
"""

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from .enums import GSTRegistrationStatus, GSTRegistrationType


class Taxpayer(BaseModel):
    """
    Canonical schema for the TAXPAYER entity.

    The GSTIN (Goods and Services Tax Identification Number) is the primary
    identifier — a 15-character alphanumeric code whose first two digits
    encode the state code and whose characters 3–12 mirror the PAN.
    """

    model_config = ConfigDict(
        populate_by_name=True,
        str_strip_whitespace=True,
        json_schema_extra={
            "entity": "TAXPAYER",
            "contract_version": "1.0.0",
        },
    )

    gstin: str = Field(
        ...,
        alias="gstin",
        min_length=15,
        max_length=15,
        pattern=r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$",
        description="15-character GSTIN identifier",
        examples=["27AAPFU0939F1ZV"],
    )

    legal_name: str = Field(
        ...,
        alias="legalName",
        min_length=1,
        max_length=300,
        description="Legal name of the registered entity",
    )

    trade_name: Optional[str] = Field(
        None,
        alias="tradeName",
        max_length=300,
        description="Trading name, if different from legal name",
    )

    registration_type: GSTRegistrationType = Field(
        ...,
        alias="registrationType",
        description="Type of GST registration",
    )

    registration_status: GSTRegistrationStatus = Field(
        ...,
        alias="registrationStatus",
        description="Current registration status",
    )

    registration_date: date = Field(
        ...,
        alias="registrationDate",
        description="Date of GST registration",
    )

    cancellation_date: Optional[date] = Field(
        None,
        alias="cancellationDate",
        description="Date of registration cancellation, if applicable",
    )

    state_code: str = Field(
        ...,
        alias="stateCode",
        min_length=2,
        max_length=2,
        pattern=r"^[0-9]{2}$",
        description="Two-digit state jurisdiction code",
        examples=["27"],
    )

    pan: str = Field(
        ...,
        alias="pan",
        min_length=10,
        max_length=10,
        pattern=r"^[A-Z]{5}[0-9]{4}[A-Z]{1}$",
        description="10-character PAN of the taxpayer",
        examples=["AAPFU0939F"],
    )
