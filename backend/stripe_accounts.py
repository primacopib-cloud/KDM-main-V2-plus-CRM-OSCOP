"""
Multi-account Stripe configuration for the KDMARCHE × O'SCOP platform.

Two Stripe accounts coexist in this platform:

- **O'SCOP OUTREMER** (account="oscop", default): handles PASS Vie Chère
  subscriptions, UC wallet recharges, auto-renew batches, delivery surcharges.
  Reads from STRIPE_API_KEY / STRIPE_LIVE_KEY.

- **KDMARCHE** (account="kdmarche"): handles product orders + LOLODRIVE
  drive payments (kind="ORDER" in lolodrive checkout).
  Reads from STRIPE_KDMARCHE_API_KEY / STRIPE_KDMARCHE_LIVE_KEY.

Both accounts honor the same STRIPE_MODE switch:
  - STRIPE_MODE=live → use *_LIVE_KEY (real charges)
  - anything else (test, unset, ...) → use *_API_KEY (test/sandbox)

This module is the single source of truth: never read STRIPE_* env vars
directly elsewhere — always call `get_stripe_key(account)` or
`get_stripe_checkout(account, webhook_url)`.
"""
from __future__ import annotations

import logging
import os
from typing import Literal, Optional

logger = logging.getLogger(__name__)
AccountName = Literal["oscop", "kdmarche"]

# Env var keys per account
_KEYS = {
    "oscop": {
        "test": "STRIPE_API_KEY",
        "live": "STRIPE_LIVE_KEY",
    },
    "kdmarche": {
        "test": "STRIPE_KDMARCHE_API_KEY",
        "live": "STRIPE_KDMARCHE_LIVE_KEY",
    },
}


def _current_mode() -> str:
    return (os.environ.get("STRIPE_MODE") or "test").strip().lower()


def get_stripe_key(account: AccountName = "oscop") -> Optional[str]:
    """Return the active Stripe secret key for the given account.

    Falls back to the O'SCOP key if a per-account key is missing — that way
    existing single-account integrations keep working even before the KDMARCHE
    keys are provisioned in every environment. A WARNING is logged when the
    fallback fires so misconfiguration is visible in prod.
    """
    if account not in _KEYS:
        raise ValueError(f"Unknown Stripe account: {account!r}")

    mode = _current_mode()
    env_key = _KEYS[account]["live" if mode == "live" else "test"]
    key = os.environ.get(env_key)

    if key:
        return key

    # Backwards-compatible fallback to O'SCOP keys for the kdmarche account
    if account == "kdmarche":
        fallback_env = _KEYS["oscop"]["live" if mode == "live" else "test"]
        fallback = os.environ.get(fallback_env) or os.environ.get("STRIPE_SECRET_KEY")
        if fallback:
            logger.warning(
                "Stripe: %s key missing in %s mode — falling back to O'SCOP %s. "
                "Configure %s to charge on the KDMARCHE account.",
                env_key, mode, fallback_env, env_key,
            )
        return fallback

    return os.environ.get("STRIPE_SECRET_KEY")


def get_stripe_checkout(account: AccountName, webhook_url: str):
    """Return an emergentintegrations StripeCheckout client for the given account."""
    from emergentintegrations.payments.stripe.checkout import StripeCheckout

    api_key = get_stripe_key(account)
    if not api_key:
        raise RuntimeError(
            f"Stripe API key missing for account={account!r} (mode={_current_mode()})"
        )
    return StripeCheckout(api_key=api_key, webhook_url=webhook_url)


def get_account_for_checkout_kind(kind: str) -> AccountName:
    """Route a LOLODRIVE checkout `kind` to the right Stripe account.

    - ORDER  → KDMARCHE (commande produits, paiement DRIVE)
    - PASS / RECHARGE / SUBSCRIPTION / autres → O'SCOP OUTREMER
    """
    if (kind or "").upper() == "ORDER":
        return "kdmarche"
    return "oscop"
