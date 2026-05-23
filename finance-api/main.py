"""finance-api — microservice financier coopératif KDMARCHE × O'SCOP.

Usage (dev):
    cd /app/finance-api
    uvicorn main:app --host 0.0.0.0 --port 8010 --reload

Docs interactives:
    http://localhost:8010/docs
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal, init_db
from app.models.user import User
from app.routes.auth import router as auth_router
from app.routes.parties import router as parties_router
from app.routes.receivables import router as receivables_router
from app.routes.payments import router as payments_router
from app.routes.sepa import router as sepa_router
from app.routes.installment_plans import router as installment_router
from app.routes.webhooks import router as webhooks_router
from app.routes.reporting import router as reporting_router

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("finance-api")


app = FastAPI(
    title="Finance API — KDMARCHE × O'SCOP",
    description=(
        "Microservice financier coopératif : tiers, créances, paiements, échéanciers, "
        "mandats SEPA, journal probant, webhooks PSP. Indépendant du backend KDM."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    with SessionLocal() as db:  # type: Session
        users_count = db.execute(select(User)).first()
        if users_count:
            logger.info("finance-api ready — bootstrap done")
        else:
            logger.warning("finance-api ready — bootstrap requis : POST /setup/bootstrap")


# ---------------- Public health (no auth) ----------------

@app.get("/health", tags=["meta"])
def health() -> dict:
    """Liveness + readiness check.

    Renvoie le statut du service et un mini-récap de configuration (booléens
    seulement — pas de secret). Toujours HTTP 200 si le process tourne.
    """
    with SessionLocal() as db:
        bootstrap_done = db.execute(select(User).limit(1)).first() is not None
    return {
        "status": "OK",
        "service": "finance-api",
        "version": app.version,
        "database": "ready",
        "bootstrap_done": bootstrap_done,
        "config": {
            "default_currency": settings.DEFAULT_CURRENCY,
            "stripe_configured": bool(settings.STRIPE_SECRET_KEY),
            "gocardless_configured": bool(settings.GOCARDLESS_ACCESS_TOKEN),
            "ged_connector_configured": bool(settings.GED_ESS_API_URL),
            "crm_connector_configured": bool(settings.CRM_API_URL),
        },
    }


# Routers
app.include_router(auth_router)
app.include_router(parties_router)
app.include_router(receivables_router)
app.include_router(payments_router)
app.include_router(sepa_router)
app.include_router(installment_router)
app.include_router(webhooks_router)
app.include_router(reporting_router)
