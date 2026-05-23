"""LedgerEntry — append-only chained journal (audit probant)."""
from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


# Standard double-entry-inspired vocabulary; we keep one row per movement.
ENTRY_KINDS = (
    "RECEIVABLE_CREATED",
    "RECEIVABLE_UPDATED",
    "PAYMENT_INITIATED",
    "PAYMENT_SUCCEEDED",
    "PAYMENT_FAILED",
    "PAYMENT_REFUNDED",
    "MANDATE_CREATED",
    "MANDATE_ACTIVATED",
    "MANDATE_REVOKED",
    "INSTALLMENT_SCHEDULED",
    "INSTALLMENT_PAID",
    "INSTALLMENT_FAILED",
    "RECONCILIATION_MATCHED",
    "OTHER",
)


class LedgerEntry(Base, UuidPkMixin, TimestampMixin):
    """Append-only chained journal — never UPDATE, only INSERT.

    Each entry stores:
      • `sequence` : monotonic position (set by ledger_service at insert time)
      • `previous_hash` : the hash of the previous entry (or 64 zeros for genesis)
      • `entry_hash` : SHA-256 of the canonical JSON payload of this entry
                      → any tampering of any row breaks the chain at insert.
    """
    __tablename__ = "ledger_entries"

    sequence: Mapped[int] = mapped_column(Integer, nullable=False, index=True, unique=True)
    occurred_at: Mapped[DateTime] = mapped_column(DateTime, nullable=False)

    kind: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    party_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    receivable_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    payment_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)
    mandate_id: Mapped[str] = mapped_column(String(36), default="", nullable=False, index=True)

    amount_cents: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="EUR", nullable=False)

    # The full canonical payload that has been hashed.
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    notes: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # Chain integrity
    previous_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
