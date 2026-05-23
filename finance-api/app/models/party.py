"""Party — physical or moral person (client, adhérent, fournisseur)."""
from sqlalchemy import String, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


PARTY_TYPES = ("individual", "company", "association", "cooperative", "public_body")


class Party(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "parties"

    party_type: Mapped[str] = mapped_column(String(40), default="individual", nullable=False)
    display_name: Mapped[str] = mapped_column(String(255), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    siret: Mapped[str] = mapped_column(String(20), default="", nullable=False, index=True)
    vat_number: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    email: Mapped[str] = mapped_column(String(255), default="", nullable=False, index=True)
    phone: Mapped[str] = mapped_column(String(40), default="", nullable=False)
    address_line1: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    address_line2: Mapped[str] = mapped_column(String(255), default="", nullable=False)
    postal_code: Mapped[str] = mapped_column(String(20), default="", nullable=False)
    city: Mapped[str] = mapped_column(String(120), default="", nullable=False)
    country: Mapped[str] = mapped_column(String(2), default="FR", nullable=False)

    # External anchors (CRM KDM, etc.)
    external_customer_id: Mapped[str] = mapped_column(String(120), default="", nullable=False, index=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
