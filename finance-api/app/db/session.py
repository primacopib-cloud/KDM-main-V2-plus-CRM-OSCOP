"""SQLAlchemy 2.x session + engine."""
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from typing import Iterator

from app.core.config import settings


class Base(DeclarativeBase):
    """Common base for all ORM models."""
    pass


# `check_same_thread=False` is required for SQLite + multiple workers.
connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    connect_args=connect_args,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, expire_on_commit=False)


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables (called once at startup)."""
    # Import all models so they register with Base.metadata
    from app.models import (  # noqa: F401
        user, party, receivable, payment, sepa_mandate, installment, ledger, webhook_event,
    )
    Base.metadata.create_all(bind=engine)
