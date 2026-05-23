"""Receivable — what a Party owes us (invoice, contribution call, PASS, etc.)."""
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


# Business taxonomy used by KDM / CRM
RECEIVABLE_TYPES = (
    "INVOICE",                 # Facture B2B classique
    "COTISATION",              # Cotisation coopérative
    "APPEL_CONTRIBUTION",      # Appel à contribution / sponsorship
    "PASS_CONSOMMATION",       # PASS Vie Chère KDMARCHE
    "RECHARGE_UC",             # Recharge crédits wallet
    "ORDER",                   # Commande LOLODRIVE
    "OTHER",
)

RECEIVABLE_STATUSES = (
    "DRAFT",
    "OPEN",        # Émise, non payée
    "PARTIAL",     # Partiellement payée
    "PAID",        # Soldée
    "OVERDUE",
    "CANCELLED",
    "REFUNDED",
)


class Receivable(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "receivables"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)

    receivable_type: Mapped[str] = mapped_column(String(40), nullable=False, default="INVOICE")
    reference: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(String(1024), default="", nullable=False)

    # Money is stored in MINOR units (cents) — never as float.
    amount_cents: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)
    amount_paid_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    amount_refunded_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    status: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    due_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # Anchor to KDM order / pass / etc.
    external_source: Mapped[str] = mapped_column(String(80), default="", nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), default="", nullable=False, index=True)

    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
