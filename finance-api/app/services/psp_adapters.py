"""PSP adapters — Stripe + GoCardless real SDK integrations.

Design contract:
  • Every function returns a dict — never raises on missing config.
  • Missing API key → `status: "FAILED"` with a clear `raw.error` message,
    so the rest of the system stays observable and testable.
  • Real API errors → caught, logged, returned with `status: "FAILED"` + raw.

Supported:
  • Stripe : Checkout Session (card payments) + Refunds + webhook signature verify
  • GoCardless : Billing Request Flow (SEPA mandate + first collection) + Refunds
                 + webhook signature verify
  • manual : always returns a valid placeholder (for tests)

Unified envelope:
  {
    "psp_payment_id":   str,
    "psp_session_id":   str,
    "hosted_url":       str,
    "status":           "PENDING" | "SUCCEEDED" | "FAILED",
    "raw":              dict (sdk response or error),
  }
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


# ============================================================
# Public API
# ============================================================

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
        return _gocardless_billing_request(amount_cents, currency, party_email, description, success_url, cancel_url, metadata)
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


def verify_stripe_signature(*, payload: bytes, signature_header: str) -> Optional[Dict[str, Any]]:
    """Validate a Stripe webhook signature. Returns the parsed event or None."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        logger.warning("Stripe webhook received but STRIPE_WEBHOOK_SECRET unset — signature NOT verified")
        return None
    try:
        import stripe
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature_header,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as exc:
        logger.warning("Stripe webhook signature invalid: %s", exc)
        return None


def verify_gocardless_signature(*, payload: bytes, signature_header: str) -> Optional[Dict[str, Any]]:
    """Validate a GoCardless webhook signature. Returns the parsed event payload or None."""
    secret = (settings.GOCARDLESS_ACCESS_TOKEN or "").strip()
    # GoCardless uses a separate webhook secret in real life — convention here:
    # use env GOCARDLESS_WEBHOOK_SECRET; fall back to access token only for tests.
    import os as _os
    webhook_secret = _os.environ.get("GOCARDLESS_WEBHOOK_SECRET", "").strip() or secret
    if not webhook_secret:
        logger.warning("GoCardless webhook received but webhook secret unset — signature NOT verified")
        return None
    try:
        from gocardless_pro import webhooks
        events = webhooks.parse(payload.decode("utf-8"), webhook_secret, signature_header)
        return {"events": [e.attributes for e in events]}
    except Exception as exc:
        logger.warning("GoCardless webhook signature invalid: %s", exc)
        return None


# ============================================================
# Manual (always works, used for tests)
# ============================================================

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


# ============================================================
# Stripe — REAL SDK
# ============================================================

def _stripe_client():
    """Returns the configured stripe module or None if not configured."""
    if not settings.STRIPE_SECRET_KEY:
        return None
    import stripe
    stripe.api_key = settings.STRIPE_SECRET_KEY
    return stripe


def _stripe_checkout(amount_cents, currency, email, description, success_url, cancel_url, metadata):
    stripe = _stripe_client()
    if stripe is None:
        return {
            "psp_payment_id": "",
            "psp_session_id": "",
            "hosted_url": "",
            "status": "FAILED",
            "raw": {"error": "STRIPE_SECRET_KEY non configurée — adaptateur Stripe non opérationnel."},
        }
    try:
        # Stripe wants metadata values as strings; flatten anything else.
        flat_metadata = {k: str(v) for k, v in (metadata or {}).items() if v is not None}
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=[{
                "price_data": {
                    "currency": (currency or "eur").lower(),
                    "product_data": {"name": description[:200] or "Paiement"},
                    "unit_amount": int(amount_cents),
                },
                "quantity": 1,
            }],
            customer_email=email or None,
            success_url=success_url or "https://finance.local/return/success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=cancel_url or "https://finance.local/return/cancel",
            metadata=flat_metadata or None,
        )
        return {
            "psp_payment_id": session.payment_intent or "",
            "psp_session_id": session.id,
            "hosted_url": session.url or "",
            "status": "PENDING",
            "raw": {"id": session.id, "payment_intent": session.payment_intent, "amount_total": session.amount_total},
        }
    except Exception as exc:
        logger.exception("Stripe checkout creation failed: %s", exc)
        return {
            "psp_payment_id": "",
            "psp_session_id": "",
            "hosted_url": "",
            "status": "FAILED",
            "raw": {"error": f"Stripe error: {exc}"},
        }


def _stripe_refund(psp_payment_id, amount_cents, reason):
    stripe = _stripe_client()
    if stripe is None:
        return {"ok": False, "status": "FAILED", "raw": {"error": "STRIPE_SECRET_KEY non configurée"}}
    if not psp_payment_id:
        return {"ok": False, "status": "FAILED", "raw": {"error": "psp_payment_id manquant"}}
    try:
        kwargs: Dict[str, Any] = {"payment_intent": psp_payment_id}
        if amount_cents is not None:
            kwargs["amount"] = int(amount_cents)
        if reason:
            # Stripe restricts to a fixed set; fall back to passing as metadata
            allowed = {"duplicate", "fraudulent", "requested_by_customer"}
            if reason in allowed:
                kwargs["reason"] = reason
            else:
                kwargs["metadata"] = {"reason": reason[:200]}
        refund = stripe.Refund.create(**kwargs)
        return {
            "ok": True,
            "psp_refund_id": refund.id,
            "status": "REFUND_PENDING" if refund.status == "pending" else "REFUNDED",
            "amount_cents": refund.amount,
            "raw": {"id": refund.id, "status": refund.status, "charge": refund.charge},
        }
    except Exception as exc:
        logger.exception("Stripe refund failed: %s", exc)
        return {"ok": False, "status": "FAILED", "raw": {"error": f"Stripe error: {exc}"}}


# ============================================================
# GoCardless — REAL SDK (Billing Request Flow for SEPA + first payment)
# ============================================================

def _gocardless_client():
    if not settings.GOCARDLESS_ACCESS_TOKEN:
        return None
    import gocardless_pro
    env = settings.GOCARDLESS_ENV or "sandbox"
    return gocardless_pro.Client(access_token=settings.GOCARDLESS_ACCESS_TOKEN, environment=env)


def _gocardless_billing_request(amount_cents, currency, email, description, success_url, cancel_url, metadata):
    client = _gocardless_client()
    if client is None:
        return {
            "psp_payment_id": "",
            "psp_session_id": "",
            "hosted_url": "",
            "status": "FAILED",
            "raw": {"error": "GOCARDLESS_ACCESS_TOKEN non configuré."},
        }
    try:
        # 1) Create a Billing Request (mandate + initial payment)
        billing_request = client.billing_requests.create(params={
            "mandate_request": {
                "scheme": (metadata or {}).get("scheme", "sepa_core"),
                "description": description[:200] or "SEPA mandate",
            },
            "payment_request": {
                "description": description[:200] or "Paiement",
                "amount": int(amount_cents),
                "currency": (currency or "EUR").upper(),
            },
            "metadata": {k: str(v)[:500] for k, v in (metadata or {}).items() if v is not None} or None,
        })

        # 2) Create the Flow (hosted page) so the customer can sign
        flow = client.billing_request_flows.create(params={
            "redirect_uri": success_url or "https://finance.local/return/success",
            "exit_uri": cancel_url or "https://finance.local/return/cancel",
            "links": {"billing_request": billing_request.id},
            "prefilled_customer": {"email": email} if email else None,
        })

        return {
            "psp_payment_id": "",
            "psp_session_id": billing_request.id,
            "hosted_url": flow.authorisation_url,
            "status": "PENDING",
            "raw": {
                "billing_request_id": billing_request.id,
                "flow_id": flow.id,
                "scheme": (metadata or {}).get("scheme", "sepa_core"),
                "env": settings.GOCARDLESS_ENV,
            },
        }
    except Exception as exc:
        logger.exception("GoCardless billing request failed: %s", exc)
        return {
            "psp_payment_id": "",
            "psp_session_id": "",
            "hosted_url": "",
            "status": "FAILED",
            "raw": {"error": f"GoCardless error: {exc}"},
        }


def _gocardless_refund(psp_payment_id, amount_cents, reason):
    client = _gocardless_client()
    if client is None:
        return {"ok": False, "status": "FAILED", "raw": {"error": "GOCARDLESS_ACCESS_TOKEN non configuré"}}
    if not psp_payment_id:
        return {"ok": False, "status": "FAILED", "raw": {"error": "psp_payment_id (GoCardless payment id) manquant"}}
    if amount_cents is None:
        return {"ok": False, "status": "FAILED", "raw": {"error": "GoCardless impose un montant précis pour un refund"}}
    try:
        refund = client.refunds.create(params={
            "amount": int(amount_cents),
            "links": {"payment": psp_payment_id},
            "metadata": {"reason": reason[:500]} if reason else None,
        })
        return {
            "ok": True,
            "psp_refund_id": refund.id,
            "status": "REFUND_PENDING",
            "amount_cents": refund.amount,
            "raw": {"id": refund.id, "payment": psp_payment_id, "currency": refund.currency},
        }
    except Exception as exc:
        logger.exception("GoCardless refund failed: %s", exc)
        return {"ok": False, "status": "FAILED", "raw": {"error": f"GoCardless error: {exc}"}}
