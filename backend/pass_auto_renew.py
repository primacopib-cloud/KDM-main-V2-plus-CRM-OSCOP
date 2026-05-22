"""
Auto-renewal soft for the PASS Vie Chère.

Why "soft" : Stripe Checkout (via emergentintegrations) is a one-shot redirect
flow ; we don't store cards on file. So our auto-renew implementation is :

  1. User opt-in via /api/lolodrive/pass/auto-renew
  2. Scheduler runs every 6h and finds PASSes with `is_auto_renew=true`,
     `status=ACTIVE`, `ends_at` in next 36h, where no recent PASS_RENEW tx exists.
  3. For each, we create a Stripe Checkout session AND email it via Brevo with
     a clear "Renew in 1 click" CTA. The user clicks → pays → PASS extended.

This is fully PSD2/SCA compliant (no card-on-file). It transforms expiry into
a frictionless touchpoint instead of a silent unsubscribe.
"""
from __future__ import annotations

import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

from emergentintegrations.payments.stripe.checkout import (
    StripeCheckout,
    CheckoutSessionRequest,
)

logger = logging.getLogger(__name__)

PASS_PRICE_EUR = 60.0
RENEW_LOOKAHEAD_HOURS = 36  # send renew emails for PASS expiring in <= 36h
RENEW_THROTTLE_DAYS = 7      # don't re-send a renew link within 7 days


def _public_origin() -> str:
    """Frontend origin used to build success/cancel URLs in the Checkout session."""
    return (
        os.environ.get("KDM_PUBLIC_ORIGIN")
        or os.environ.get("FRONTEND_URL")
        or "https://coop-dashboard-8.preview.emergentagent.com"
    ).rstrip("/")


def _stripe() -> StripeCheckout:
    # Honor STRIPE_MODE: 'live' uses STRIPE_LIVE_KEY, otherwise STRIPE_API_KEY (test).
    mode = (os.environ.get("STRIPE_MODE") or "test").strip().lower()
    if mode == "live":
        api_key = os.environ.get("STRIPE_LIVE_KEY") or os.environ.get("STRIPE_API_KEY")
    else:
        api_key = os.environ.get("STRIPE_API_KEY") or os.environ.get("STRIPE_SECRET_KEY")
    if not api_key:
        raise RuntimeError("STRIPE_API_KEY missing")
    backend_origin = os.environ.get("KDM_BACKEND_ORIGIN") or _public_origin()
    return StripeCheckout(
        api_key=api_key,
        webhook_url=f"{backend_origin}/api/webhook/stripe",
    )


async def create_pass_renewal_session(db, user_id: str) -> dict:
    """Create a Stripe Checkout session pre-tagged as PASS_RENEW for the given user.
    Returns {url, session_id}.
    """
    sc = _stripe()
    origin = _public_origin()
    metadata = {"kind": "PASS", "user_id": user_id, "auto_renew": "1"}
    req = CheckoutSessionRequest(
        amount=PASS_PRICE_EUR,
        currency="eur",
        success_url=f"{origin}/paiement/retour?session_id={{CHECKOUT_SESSION_ID}}&kind=PASS&ref={user_id}",
        cancel_url=f"{origin}/paiement/annule?kind=PASS&ref={user_id}",
        metadata=metadata,
    )
    session = await sc.create_checkout_session(req)
    now = datetime.now(timezone.utc)
    await db.payment_transactions.insert_one({
        "id": str(uuid.uuid4()),
        "session_id": session.session_id,
        "user_id": user_id,
        "kind": "PASS",
        "auto_renew": True,
        "amount_cents": int(PASS_PRICE_EUR * 100),
        "currency": "eur",
        "payment_status": "initiated",
        "metadata": metadata,
        "applied": False,
        "created_at": now,
        "updated_at": now,
    })
    return {"url": session.url, "session_id": session.session_id}


async def run_auto_renew_batch(db) -> dict:
    """One scheduler iteration: find PASSes about to expire with auto-renew=true,
    create a Stripe link, and email/SMS via Brevo. Idempotent via per-PASS throttle.
    """
    from brevo_service import send_email, send_sms, _wrap_html, is_brevo_configured

    if not is_brevo_configured():
        logger.info("AutoRenew: Brevo not configured — skipping batch")
        return {"sent": 0, "skipped": 0, "reason": "brevo_not_configured"}

    # Use naive UTC datetime to match MongoDB stored values (most legacy docs are naive).
    now = datetime.utcnow()
    horizon = now + timedelta(hours=RENEW_LOOKAHEAD_HOURS)
    throttle_after = now - timedelta(days=RENEW_THROTTLE_DAYS)

    cursor = db.lolodrive_passes.find({
        "is_auto_renew": True,
        "status": "ACTIVE",
        "ends_at": {"$gte": now, "$lte": horizon},
        "$or": [
            {"renew_email_sent_at": {"$exists": False}},
            {"renew_email_sent_at": None},
            {"renew_email_sent_at": {"$lt": throttle_after}},
        ],
    }, {"_id": 0})

    sent = 0
    skipped = 0
    async for p in cursor:
        user = await db.users.find_one(
            {"id": p["user_id"]},
            {"_id": 0, "email": 1, "contact_name": 1, "phone": 1},
        )
        if not user or not user.get("email"):
            skipped += 1
            continue
        try:
            session = await create_pass_renewal_session(db, p["user_id"])
        except Exception as exc:
            logger.warning("AutoRenew: Stripe session creation failed for %s: %s", user.get("email"), exc)
            skipped += 1
            continue

        # Build the email
        end_str = p["ends_at"].strftime("%d/%m/%Y") if isinstance(p["ends_at"], datetime) else str(p["ends_at"])
        first = (user.get("contact_name") or "").split()[0] if user.get("contact_name") else ""
        subject = "Votre PASS expire bientôt — Renouveler en 1 clic"
        body = f"""
          <p>Bonjour {first or 'cher coopérateur'},</p>
          <p>Votre <strong>PASS Vie Chère</strong> expire le <strong>{end_str}</strong>.
          Vous avez activé le renouvellement automatique : pour conserver vos avantages,
          finalisez le renouvellement en 1 clic ci-dessous.</p>
          <p style=\"margin:20px 0;text-align:center;\">
            <a href=\"{session['url']}\" style=\"display:inline-block;padding:14px 28px;background:linear-gradient(135deg,#D9B35A,#7c3aed);color:#000;text-decoration:none;border-radius:14px;font-weight:600;\">
              Renouveler mon PASS — 60 €
            </a>
          </p>
          <p style=\"font-size:11px;color:rgba(255,255,255,0.5);\">Lien personnel — sécurisé par Stripe. Aucune carte n'est conservée.</p>
        """
        try:
            await send_email(
                to_email=user["email"],
                to_name=user.get("contact_name"),
                subject=subject,
                html_content=_wrap_html(subject, body),
                text_content=f"Renouvelez votre PASS avant le {end_str} : {session['url']}",
                tags=["pass_auto_renew"],
            )
            if user.get("phone"):
                await send_sms(
                    user["phone"],
                    f"KDMARCHE x O'SCOP : votre PASS expire le {end_str}. Renouvelez en 1 clic : {session['url'][:90]}",
                    tag="pass_auto_renew",
                )
            await db.lolodrive_passes.update_one(
                {"id": p["id"]},
                {"$set": {
                    "renew_email_sent_at": now,
                    "renew_session_id": session["session_id"],
                    "updated_at": now,
                }},
            )
            sent += 1
        except Exception as exc:
            logger.warning("AutoRenew: notification failed for %s: %s", user.get("email"), exc)
            skipped += 1
    if sent:
        logger.info("AutoRenew batch: %d email(s) sent (skipped=%d)", sent, skipped)
    return {"sent": sent, "skipped": skipped}
