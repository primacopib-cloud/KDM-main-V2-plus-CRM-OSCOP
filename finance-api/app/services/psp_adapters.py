"""PSP adapters — abstract a unified interface over Stripe / GoCardless / manual.

This module is intentionally *thin*. Each provider returns a dict shaped like:
  {
    "psp_payment_id": "...",
    "psp_session_id": "...",
    "hosted_url": "https://...",
    "status": "PENDING" | "SUCCEEDED" | "FAILED",
    "raw": {...},
  }

For now, only the `manual` adapter is implemented end-to-end; Stripe / GoCardless
return a placeholder until you wire real SDK calls — they will not raise though,
so the rest of the system stays fully testable.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings


def create_checkout(
    *,
    provider: str,
    amount_cents: int,
    currency: str,
    party_email: str,
    description: str,
    success_url: Optional[str] = None,
    cancel_url: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a hosted checkout session at the given PSP."""
    provider = (provider or "manual").lower()
    metadata = metadata or {}

    if provider == "stripe":
        return _stripe_checkout(amount_cents, currency, party_email, description, success_url, cancel_url, metadata)
    if provider == "gocardless":
        return _gocardless_billing_request(amount_cents, currency, party_email, description, metadata)
    return _manual_session(amount_cents, currency, description, metadata)


def refund_payment(
    *,
    provider: str,
    psp_payment_id: str,
    amount_cents: Optional[int] = None,
    reason: str = "",
) -> Dict[str, Any]:
    provider = (provider or "manual").lower()
    if provider == "stripe":
        return _stripe_refund(psp_payment_id, amount_cents, reason)
    if provider == "gocardless":
        return _gocardless_refund(psp_payment_id, amount_cents, reason)
    return {
        "ok": True,
        "psp_refund_id": f"manual_refund_{psp_payment_id}",
        "status": "REFUNDED",
        "amount_cents": amount_cents,
        "raw": {"reason": reason, "manual": True},
    }


# ---------------- Manual (always works, used for tests) ----------------

def _manual_session(amount_cents: int, currency: str, description: str, metadata: Dict[str, Any]) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    session_id = f"manual_session_{now}"
    return {
        "psp_payment_id": "",
        "psp_session_id": session_id,
        "hosted_url": f"https://finance.local/manual-checkout/{session_id}",
        "status": "PENDING",
        "raw": {"amount_cents": amount_cents, "currency": currency, "description": description, "metadata": metadata},
    }


# ---------------- Stripe (real SDK call would go here) ----------------

def _stripe_checkout(amount_cents, currency, email, description, success_url, cancel_url, metadata):
    if not settings.STRIPE_SECRET_KEY:
        return {
            "psp_payment_id": "",
            "psp_session_id": "",
            "hosted_url": "",
            "status": "FAILED",
            "raw": {"error": "STRIPE_SECRET_KEY non configurée — adaptateur Stripe non opérationnel."},
        }
    # Real implementation (to enable when STRIPE_SECRET_KEY is set) :
    #     import stripe
    #     stripe.api_key = settings.STRIPE_SECRET_KEY
    #     session = stripe.checkout.Session.create(...)
    #     return {...}
    return {
        "psp_payment_id": "",
        "psp_session_id": "stripe_session_placeholder",
        "hosted_url": "https://checkout.stripe.com/placeholder",
        "status": "PENDING",
        "raw": {"placeholder": True, "amount_cents": amount_cents, "currency": currency, "email": email,
                "description": description, "success_url": success_url, "cancel_url": cancel_url,
                "metadata": metadata},
    }


def _stripe_refund(psp_payment_id, amount_cents, reason):
    if not settings.STRIPE_SECRET_KEY:
        return {"ok": False, "status": "FAILED", "raw": {"error": "STRIPE_SECRET_KEY non configurée"}}
    return {
        "ok": True,
        "psp_refund_id": f"stripe_refund_placeholder_{psp_payment_id}",
        "status": "REFUND_PENDING",
        "amount_cents": amount_cents,
        "raw": {"placeholder": True, "reason": reason},
    }


# ---------------- GoCardless (real SDK call would go here) ----------------

def _gocardless_billing_request(amount_cents, currency, email, description, metadata):
    if not settings.GOCARDLESS_ACCESS_TOKEN:
        return {
            "psp_payment_id": "",
            "psp_session_id": "",
            "hosted_url": "",
            "status": "FAILED",
            "raw": {"error": "GOCARDLESS_ACCESS_TOKEN non configuré."},
        }
    return {
        "psp_payment_id": "",
        "psp_session_id": "gc_brfl_placeholder",
        "hosted_url": "https://pay.gocardless.com/placeholder",
        "status": "PENDING",
        "raw": {"placeholder": True, "amount_cents": amount_cents, "currency": currency,
                "email": email, "description": description, "metadata": metadata,
                "env": settings.GOCARDLESS_ENV},
    }


def _gocardless_refund(psp_payment_id, amount_cents, reason):
    return {
        "ok": True,
        "psp_refund_id": f"gc_refund_placeholder_{psp_payment_id}",
        "status": "REFUND_PENDING",
        "amount_cents": amount_cents,
        "raw": {"placeholder": True, "reason": reason},
    }
