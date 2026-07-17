"""
Brevo (Sendinblue) transactional Email + SMS service.

Async wrapper over Brevo REST API used for KDMARCHÉ / LOLODRIVE notifications:
- PASS Vie Chère activation (email + SMS)
- Commande prête au point de retrait (email + SMS)
- Rappel J-3 expiration PASS (email + SMS)

Configuration via /app/backend/.env :
    BREVO_API_KEY      = <REST API key>
    BREVO_SENDER_EMAIL = no_reply@kdmarche-oscop.fr
    BREVO_SENDER_NAME  = "KDMARCHE x O'SCOP"
    BREVO_SMS_SENDER   = "KDMARCHE" (optional, max 11 alphanumeric chars)

Sends are best-effort: failures are logged but do not raise to callers,
so business flows (Stripe, POS) are never broken by a notification outage.
"""
from __future__ import annotations

import os
import re
import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

BREVO_BASE_URL = "https://api.brevo.com/v3"


def _settings() -> Dict[str, str]:
    return {
        "api_key": os.environ.get("BREVO_API_KEY", "").strip(),
        "sender_email": os.environ.get("BREVO_SENDER_EMAIL", "no_reply@kdmarche-oscop.fr"),
        "sender_name": os.environ.get("BREVO_SENDER_NAME", "KDMARCHE x O'SCOP"),
        "sms_sender": os.environ.get("BREVO_SMS_SENDER", "KDMARCHE")[:11],
    }


def is_brevo_configured() -> bool:
    return bool(os.environ.get("BREVO_API_KEY", "").strip())


def _normalize_phone(raw: Optional[str]) -> Optional[str]:
    """Return phone in E.164-like format (+CCNNNNNN) or None if invalid."""
    if not raw:
        return None
    cleaned = re.sub(r"[^\d+]", "", raw)
    if not cleaned:
        return None
    if cleaned.startswith("00"):
        cleaned = "+" + cleaned[2:]
    if not cleaned.startswith("+"):
        # default to French country code if a 10-digit number starting with 0
        if re.fullmatch(r"0\d{9}", cleaned):
            cleaned = "+33" + cleaned[1:]
        else:
            cleaned = "+" + cleaned
    if len(cleaned) < 8 or len(cleaned) > 16:
        return None
    return cleaned


async def _post(path: str, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    cfg = _settings()
    if not cfg["api_key"]:
        logger.warning("Brevo not configured (BREVO_API_KEY missing) — skip notification")
        return None
    headers = {
        "api-key": cfg["api_key"],
        "accept": "application/json",
        "content-type": "application/json",
    }
    try:
        async with httpx.AsyncClient(base_url=BREVO_BASE_URL, timeout=10.0, headers=headers) as client:
            resp = await client.post(path, json=payload)
        if resp.status_code >= 400:
            logger.error("Brevo %s failed (%s): %s", path, resp.status_code, resp.text[:300])
            return None
        return resp.json() if resp.content else {"ok": True}
    except Exception as exc:  # network, timeout, etc.
        logger.error("Brevo %s exception: %s", path, exc)
        return None


async def send_email(
    to_email: str,
    to_name: Optional[str],
    subject: str,
    html_content: str,
    text_content: Optional[str] = None,
    tags: Optional[list] = None,
) -> Optional[Dict[str, Any]]:
    cfg = _settings()
    payload: Dict[str, Any] = {
        "sender": {"email": cfg["sender_email"], "name": cfg["sender_name"]},
        "to": [{"email": to_email, **({"name": to_name} if to_name else {})}],
        "subject": subject,
        "htmlContent": html_content,
    }
    if text_content:
        payload["textContent"] = text_content
    if tags:
        payload["tags"] = tags
    return await _post("/smtp/email", payload)


async def send_sms(
    recipient: str,
    content: str,
    tag: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    cfg = _settings()
    phone = _normalize_phone(recipient)
    if not phone:
        logger.info("Brevo SMS skipped — invalid recipient phone: %r", recipient)
        return None
    # Brevo expects phone as digits only with country code, no '+'
    # https://developers.brevo.com/reference/sendtransacsms
    payload: Dict[str, Any] = {
        "sender": cfg["sms_sender"],
        "recipient": phone,
        "content": content[:160],
        "type": "transactional",
    }
    if tag:
        payload["tag"] = tag
    return await _post("/transactionalSMS/sms", payload)


# ============================================================
#  Branded HTML wrapper (minimal, dark theme aligned with app)
# ============================================================

def _wrap_html(title: str, body_html: str) -> str:
    return f"""<!DOCTYPE html>
<html><head><meta charset=\"utf-8\"><title>{title}</title></head>
<body style=\"margin:0;padding:0;background:#070A10;font-family:Helvetica,Arial,sans-serif;color:#fff;\">
  <div style=\"max-width:600px;margin:0 auto;padding:32px 24px;\">
    <div style=\"text-align:center;margin-bottom:24px;\">
      <h1 style=\"color:#D9B35A;font-size:22px;margin:0;letter-spacing:1px;\">KDMARCHÉ × O'SCOP</h1>
      <p style=\"color:rgba(255,255,255,0.55);margin:6px 0 0;font-size:12px;\">LOLODRIVE — Plateforme coopérative ESS</p>
    </div>
    <div style=\"background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.08);border-radius:18px;padding:28px;\">
      {body_html}
    </div>
    <p style=\"color:rgba(255,255,255,0.4);font-size:11px;text-align:center;margin-top:24px;\">
      Email transactionnel automatique — Ne pas répondre.<br/>
      © {datetime.utcnow().year} KDMARCHÉ × O'SCOP — Communityplace coopérative ESS
    </p>
  </div>
</body></html>"""


# ============================================================
#  Domain-specific notifications (LOLODRIVE)
# ============================================================

async def notify_pass_activated(
    *,
    to_email: str,
    to_name: Optional[str],
    to_phone: Optional[str],
    pass_id: str,
    uc_granted: int,
    ends_at: datetime,
) -> Dict[str, Any]:
    first = (to_name or "").split()[0] if to_name else ""
    end_str = ends_at.strftime("%d/%m/%Y") if isinstance(ends_at, datetime) else str(ends_at)
    subject = "Votre PASS Vie Chère est actif"
    body = f"""
      <p>Bonjour {first or 'cher coopérateur'},</p>
      <p>Votre <strong>PASS Vie Chère</strong> est désormais <span style=\"color:#57D19A;font-weight:600;\">ACTIF</span>. Bienvenue dans la communauté KDMARCHÉ × O'SCOP !</p>
      <div style=\"background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:16px;margin:16px 0;\">
        <p style=\"margin:0 0 6px;color:#D9B35A;font-size:12px;text-transform:uppercase;letter-spacing:1px;\">PASS</p>
        <p style=\"margin:0;font-family:monospace;\">#{pass_id}</p>
        <p style=\"margin:12px 0 0;\">Crédit accordé : <strong>{uc_granted} UC</strong></p>
        <p style=\"margin:6px 0 0;\">Valide jusqu'au : <strong>{end_str}</strong></p>
      </div>
      <p>Rendez-vous sur votre espace pour commander en LOLODRIVE et profiter de vos UC.</p>
    """
    email_res = await send_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Bonjour {first}, votre PASS Vie Chère #{pass_id} est actif jusqu'au {end_str}. {uc_granted} UC crédités.",
        tags=["pass_activation"],
    )
    sms_text = (
        f"KDMARCHE x O'SCOP : votre PASS Vie Chere est actif jusqu'au {end_str}. "
        f"{uc_granted} UC credites. Bonnes courses !"
    )
    sms_res = await send_sms(to_phone, sms_text, tag="pass_activation") if to_phone else None
    return {"email": email_res, "sms": sms_res}


async def notify_order_ready(
    *,
    to_email: str,
    to_name: Optional[str],
    to_phone: Optional[str],
    order_number: str,
    pickup_point: str,
) -> Dict[str, Any]:
    first = (to_name or "").split()[0] if to_name else ""
    subject = f"Commande {order_number} prête au retrait"
    body = f"""
      <p>Bonjour {first or 'cher coopérateur'},</p>
      <p>Bonne nouvelle ! Votre commande <strong>#{order_number}</strong> est <span style=\"color:#57D19A;font-weight:600;\">prête</span> au point de retrait :</p>
      <div style=\"background:rgba(87,209,154,0.08);border:1px solid rgba(87,209,154,0.2);border-radius:12px;padding:16px;margin:16px 0;\">
        <p style=\"margin:0;color:#57D19A;font-size:12px;text-transform:uppercase;letter-spacing:1px;\">Point de retrait</p>
        <p style=\"margin:6px 0 0;font-size:18px;font-weight:600;\">{pickup_point}</p>
      </div>
      <p>Présentez-vous avec votre QR-code de commande pour le retrait.</p>
    """
    email_res = await send_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Commande #{order_number} prête au retrait : {pickup_point}.",
        tags=["order_ready"],
    )
    sms_text = (
        f"KDMARCHE x O'SCOP : votre commande #{order_number} est prete au retrait "
        f"({pickup_point}). Munissez-vous de votre QR-code."
    )
    sms_res = await send_sms(to_phone, sms_text, tag="order_ready") if to_phone else None
    return {"email": email_res, "sms": sms_res}


async def notify_pass_expiry_j3(
    *,
    to_email: str,
    to_name: Optional[str],
    to_phone: Optional[str],
    pass_id: str,
    ends_at: datetime,
) -> Dict[str, Any]:
    first = (to_name or "").split()[0] if to_name else ""
    end_str = ends_at.strftime("%d/%m/%Y") if isinstance(ends_at, datetime) else str(ends_at)
    subject = "Votre PASS expire dans 3 jours"
    body = f"""
      <p>Bonjour {first or 'cher coopérateur'},</p>
      <p>Petit rappel : votre <strong>PASS Vie Chère</strong> expire le <strong>{end_str}</strong> (dans 3 jours).</p>
      <p>Pensez à le <strong>renouveler</strong> pour continuer à profiter de vos avantages KDMARCHÉ et de vos UC.</p>
      <div style=\"background:rgba(217,179,90,0.10);border:1px solid rgba(217,179,90,0.25);border-radius:12px;padding:16px;margin:16px 0;\">
        <p style=\"margin:0;color:#D9B35A;font-size:12px;text-transform:uppercase;letter-spacing:1px;\">Pass concerné</p>
        <p style=\"margin:6px 0 0;font-family:monospace;\">#{pass_id}</p>
      </div>
    """
    email_res = await send_email(
        to_email=to_email,
        to_name=to_name,
        subject=subject,
        html_content=_wrap_html(subject, body),
        text_content=f"Rappel : votre PASS #{pass_id} expire le {end_str}. Pensez a le renouveler.",
        tags=["pass_expiry_j3"],
    )
    sms_text = (
        f"KDMARCHE x O'SCOP : votre PASS Vie Chere expire le {end_str}. "
        f"Renouvelez-le pour conserver vos avantages."
    )
    sms_res = await send_sms(to_phone, sms_text, tag="pass_expiry_j3") if to_phone else None
    return {"email": email_res, "sms": sms_res}
