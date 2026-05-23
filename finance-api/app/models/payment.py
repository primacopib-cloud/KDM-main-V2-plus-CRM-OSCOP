"""Payment — collected money (PSP, cash, transfer) applied to a Receivable."""
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


PAYMENT_METHODS = (
    "CARD",           # Stripe / CB
    "SEPA_CORE",
    "SEPA_B2B",
    "BANK_TRANSFER",
    "CASH",
    "WALLET_UC",
    "OTHER",
)

PAYMENT_STATUSES = (
    "PENDING",
    "PROCESSING",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "REFUND_PENDING",
    "REFUNDED",
    "PARTIAL_REFUND",
)


class Payment(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "payments"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    receivable_id: Mapped[str] = mapped_column(ForeignKey("receivables.id"), nullable=True, index=True)

    method: Mapped[str] = mapped_column(String(30), nullable=False, default="CARD")
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    amount_refunded_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # PSP traceability
    psp_provider: Mapped[str] = mapped_column(String(40), default="", nullable=False)  # stripe | gocardless | manual
    psp_payment_id: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    psp_session_id: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    psp_account: Mapped[str] = mapped_column(String(40), default="", nullable=False)  # oscop | kdmarche

    # Hosted payment link (Stripe Checkout URL etc.)
    hosted_url: Mapped[str] = mapped_column(String(1024), default="", nullable=False)

    paid_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    refunded_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    failure_reason: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
