"""InstallmentPlan + Installment (échéancier de paiement)."""
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


PLAN_STATUSES = ("DRAFT", "ACTIVE", "COMPLETED", "DEFAULTED", "CANCELLED")
INSTALLMENT_STATUSES = ("SCHEDULED", "PENDING", "PAID", "FAILED", "LATE", "CANCELLED")


class InstallmentPlan(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "installment_plans"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)
    receivable_id: Mapped[str] = mapped_column(ForeignKey("receivables.id"), nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(ForeignKey("sepa_mandates.id"), nullable=True)

    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)
    total_amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    number_of_installments: Mapped[int] = mapped_column(Integer, nullable=False)

    started_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)


class Installment(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "installments"

    plan_id: Mapped[str] = mapped_column(ForeignKey("installment_plans.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..N

    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    due_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="SCHEDULED", nullable=False)

    payment_id: Mapped[str] = mapped_column(ForeignKey("payments.id"), nullable=True, index=True)
    paid_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
