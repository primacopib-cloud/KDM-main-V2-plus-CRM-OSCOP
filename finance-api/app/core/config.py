"""Application config loaded from env."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Always load the local .env first (idempotent if env vars are already set)
ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


class Settings:
    # Core
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./finance_api.db")
    SECRET_KEY: str = os.environ.get("SECRET_KEY", "change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
    DEFAULT_CURRENCY: str = os.environ.get("DEFAULT_CURRENCY", "EUR")

    # Bootstrap
    BOOTSTRAP_ADMIN_EMAIL: str = os.environ.get("BOOTSTRAP_ADMIN_EMAIL", "admin@finance.local")
    BOOTSTRAP_ADMIN_PASSWORD: str = os.environ.get("BOOTSTRAP_ADMIN_PASSWORD", "ChangeMe!")

    # PSP
    STRIPE_SECRET_KEY: str = os.environ.get("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.environ.get("STRIPE_WEBHOOK_SECRET", "")
    GOCARDLESS_ACCESS_TOKEN: str = os.environ.get("GOCARDLESS_ACCESS_TOKEN", "")
    GOCARDLESS_ENV: str = os.environ.get("GOCARDLESS_ENV", "sandbox")

    # Outbound connectors
    GED_ESS_API_URL: str = os.environ.get("GED_ESS_API_URL", "")
    GED_ESS_API_TOKEN: str = os.environ.get("GED_ESS_API_TOKEN", "")
    CRM_API_URL: str = os.environ.get("CRM_API_URL", "")
    CRM_API_TOKEN: str = os.environ.get("CRM_API_TOKEN", "")

    # Service
    PORT: int = int(os.environ.get("FINANCE_API_PORT", "8010"))


settings = Settings()
