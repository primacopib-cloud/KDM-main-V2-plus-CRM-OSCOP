"""WebhookEvent — raw PSP webhook intake with idempotency."""
from sqlalchemy import Boolean, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base
from app.models._common import TimestampMixin, UuidPkMixin


class WebhookEvent(Base, UuidPkMixin, TimestampMixin):
    __tablename__ = "webhook_events"

    provider: Mapped[str] = mapped_column(String(40), nullable=False, index=True)  # stripe | gocardless
    external_event_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    processing_error: Mapped[str] = mapped_column(Text, default="", nullable=False)
    raw_payload: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
