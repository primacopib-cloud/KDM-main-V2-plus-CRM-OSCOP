"""Public schemas — keep them flat, no nested heavy hierarchies."""
from datetime import datetime
from typing import Optional, Dict, Any, List

from pydantic import BaseModel, EmailStr, Field


# ---------------- Auth ----------------

class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int


class BootstrapIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str = ""


# ---------------- Party ----------------

class PartyBase(BaseModel):
    party_type: str = "individual"
    display_name: str
    legal_name: str = ""
    siret: str = ""
    vat_number: str = ""
    email: str = ""
    phone: str = ""
    address_line1: str = ""
    address_line2: str = ""
    postal_code: str = ""
    city: str = ""
    country: str = "FR"
    external_customer_id: str = ""
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class PartyCreate(PartyBase):
    pass


class PartyOut(PartyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------- Receivable ----------------

class ReceivableBase(BaseModel):
    party_id: str
    receivable_type: str = "INVOICE"
    reference: str = ""
    title: str
    description: str = ""
    amount_cents: int = Field(ge=0)
    currency: str = "EUR"
    due_at: Optional[datetime] = None
    external_source: str = ""
    external_id: str = ""
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class ReceivableCreate(ReceivableBase):
    pass


class ReceivableOut(ReceivableBase):
    id: str
    amount_paid_cents: int
    amount_refunded_cents: int
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------- Payment ----------------

class PaymentCreate(BaseModel):
    party_id: str
    receivable_id: Optional[str] = None
    method: str = "CARD"
    amount_cents: int = Field(gt=0)
    currency: str = "EUR"
    psp_provider: str = "stripe"
    psp_account: str = ""
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class PaymentOut(BaseModel):
    id: str
    party_id: str
    receivable_id: Optional[str]
    method: str
    status: str
    amount_cents: int
    currency: str
    amount_refunded_cents: int
    psp_provider: str
    psp_payment_id: str
    psp_session_id: str
    hosted_url: str
    paid_at: Optional[datetime]
    refunded_at: Optional[datetime]
    failure_reason: str
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PaymentRefundIn(BaseModel):
    amount_cents: Optional[int] = Field(default=None, ge=1, description="Si null, full refund.")
    reason: str = ""


# ---------------- SEPA ----------------

class SepaMandateCreate(BaseModel):
    party_id: str
    scheme: str = "SEPA_CORE"
    debtor_name: str
    iban_masked: str = ""
    bic: str = ""
    psp_provider: str = ""
    psp_mandate_id: str = ""
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class SepaMandateOut(BaseModel):
    id: str
    party_id: str
    scheme: str
    status: str
    reference: str
    debtor_name: str
    iban_masked: str
    bic: str
    creditor_name: str
    creditor_ics: str
    signed_at: Optional[datetime]
    activated_at: Optional[datetime]
    revoked_at: Optional[datetime]
    psp_provider: str
    psp_mandate_id: str
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------- Installment ----------------

class InstallmentScheduleItem(BaseModel):
    sequence: int
    amount_cents: int
    due_at: datetime


class InstallmentPlanCreate(BaseModel):
    party_id: str
    receivable_id: str
    mandate_id: Optional[str] = None
    schedule: List[InstallmentScheduleItem] = Field(min_length=1)
    metadata_json: Dict[str, Any] = Field(default_factory=dict)


class InstallmentOut(BaseModel):
    id: str
    sequence: int
    amount_cents: int
    due_at: datetime
    status: str
    payment_id: Optional[str]
    paid_at: Optional[datetime]

    class Config:
        from_attributes = True


class InstallmentPlanOut(BaseModel):
    id: str
    party_id: str
    receivable_id: str
    mandate_id: Optional[str]
    status: str
    total_amount_cents: int
    currency: str
    number_of_installments: int
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    installments: List[InstallmentOut] = Field(default_factory=list)
    metadata_json: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# ---------------- Ledger / audit ----------------

class LedgerEntryOut(BaseModel):
    id: str
    sequence: int
    occurred_at: datetime
    kind: str
    party_id: str
    receivable_id: str
    payment_id: str
    mandate_id: str
    amount_cents: int
    currency: str
    payload_json: Dict[str, Any]
    notes: str
    previous_hash: str
    entry_hash: str

    class Config:
        from_attributes = True


class LedgerVerifyOut(BaseModel):
    ok: bool
    total_entries: int
    broken_at_sequence: Optional[int] = None
    error: Optional[str] = None
