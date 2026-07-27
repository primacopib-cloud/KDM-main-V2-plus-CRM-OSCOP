"""Reçu email automatique envoyé au client après chaque mouvement UC sur son CREDI'SCOP (best-effort)."""
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def send_uc_receipt(db, user_id: str, amount_uc, new_balance, kind: str = "DEBIT",
                          order_number: str = None, point_name: str = None, context: str = None):
    """kind = DEBIT (achat) ou CREDIT (recharge). Ne lève jamais d'exception."""
    try:
        user = await db.users.find_one({"id": user_id}, {"_id": 0, "email": 1, "contact_name": 1})
        if not user or not user.get("email"):
            return False
        from brevo_service import send_email, _wrap_html
        debit = kind == "DEBIT"
        color = "#dc2626" if debit else "#059669"
        sign = "−" if debit else "+"
        title = "Débit sur votre CREDI'SCOP" if debit else "Recharge de votre CREDI'SCOP"
        subject = f"🪙 {title} : {sign}{amount_uc} UC"
        ctx = context or ("Achat au comptoir" if debit else "Recharge au comptoir")
        body = f"""
          <p>Bonjour {(user.get('contact_name') or '').split(' ')[0]},</p>
          <p>Un mouvement vient d'être enregistré sur votre CREDI'SCOP :</p>
          <div style='background:rgba(217,179,90,0.08);border:1px solid rgba(217,179,90,0.3);border-radius:12px;padding:14px;margin:12px 0'>
            <p style='margin:0;font-size:15px'>{ctx}{f" — {point_name}" if point_name else ''}
            {f"<br/><span style='font-size:12px;color:#777'>Référence : {order_number}</span>" if order_number else ''}</p>
            <p style='margin:8px 0 0;font-size:17px'><strong style='color:{color}'>{sign}{amount_uc} UC</strong></p>
            <p style='margin:6px 0 0;font-size:14px'>Nouveau solde : <strong>{new_balance} UC</strong>
            <span style='color:#999;font-size:12px'>(≈ {float(new_balance) / 10:.2f} €)</span></p>
          </div>
          <p style='font-size:12px;color:#777'>Retrouvez l'historique complet de vos UC dans votre espace PASS.</p>
          <p style='color:#999;font-size:11px;margin-top:12px'>Reçu automatique — Réseau LOLODRIVE by O'SCOP, le {datetime.utcnow().strftime('%d/%m/%Y %H:%M')} UTC.</p>
        """
        await send_email(to_email=user["email"], to_name=user.get("contact_name"), subject=subject,
                         html_content=_wrap_html(subject, body),
                         text_content=f"{title} : {sign}{amount_uc} UC — nouveau solde {new_balance} UC.",
                         tags=["uc_receipt"])
        return True
    except Exception as exc:
        logger.warning("Reçu UC %s : %s", user_id, exc)
        return False
