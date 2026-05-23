"""SEPA Mandate (Core CORE for B2C, B2B for SEPA B2B)."""
from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


MANDATE_SCHEMES = ("SEPA_CORE", "SEPA_B2B")
MANDATE_STATUSES = (
    "DRAFT",        # Créé, pas encore signé
    "PENDING",      # Envoyé en signature
    "ACTIVE",       # Signé + premier prélèvement OK
    "SUSPENDED",
    "REVOKED",
    "EXPIRED",
    "FAILED",
)


class SepaMandate(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "sepa_mandates"

    party_id: Mapped[str] = mapped_column(ForeignKey("parties.id"), nullable=False, index=True)

    scheme: Mapped[str] = mapped_column(String(20), default="SEPA_CORE", nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT", nullable=False)

    reference: Mapped[str] = mapped_column(String(80), default="", nullable=False, index=True)  # UMR / Unique Mandate Reference
    debtor_name: Mapped[str] = mapped_column(String(255), nullable=False)
    iban_masked: Mapped[str] = mapped_column(String(40), default="", nullable=False)  # FR76****1234
    bic: Mapped[str] = mapped_column(String(20), default="", nullable=False)

    creditor_name: Mapped[str] = mapped_column(String(255), default="O'SCOP / KDMARCHE", nullable=False)
    creditor_ics: Mapped[str] = mapped_column(String(40), default="", nullable=False)  # Identifiant Créancier SEPA

    signed_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    activated_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    revoked_at: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    # PSP linkage (GoCardless / Stripe)
    psp_provider: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    psp_mandate_id: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)

    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
