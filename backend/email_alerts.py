"""KDMARCHE × O'SCOP - Alertes critiques admin par email (split from email_service.py)."""
import os
import logging

from email_service import send_email, is_email_configured, FRONTEND_URL

logger = logging.getLogger(__name__)

# ============== ALERTES CRITIQUES ADMIN ==============

# Configuration des seuils d'alerte
ALERT_THRESHOLDS = {
    "large_order_amount": 5000,  # Commande > 5000€
    "critical_stock_level": 5,   # Stock < 5 unités
    "payment_failed_threshold": 1000,  # Paiement échoué > 1000€
}

# Email admin par défaut
ADMIN_ALERT_EMAIL = os.environ.get("ADMIN_ALERT_EMAIL", "admin@kdmarche-oscop.fr")


def send_critical_alert_email(
    alert_type: str,
    title: str,
    message: str,
    details: dict = None,
    priority: str = "high",
    admin_emails: list = None
):
    """
    Envoie une alerte email critique aux administrateurs
    
    Args:
        alert_type: Type d'alerte (large_order, stock_rupture, payment_failed, etc.)
        title: Titre de l'alerte
        message: Message principal
        details: Dictionnaire avec les détails supplémentaires
        priority: Priorité (critical, high, medium)
        admin_emails: Liste des emails admin (utilise ADMIN_ALERT_EMAIL par défaut)
    """
    recipients = admin_emails or [ADMIN_ALERT_EMAIL]
    
    # Couleurs selon priorité
    priority_colors = {
        "critical": {"bg": "rgba(239,68,68,0.15)", "border": "rgba(239,68,68,0.3)", "text": "#EF4444", "icon": "🚨"},
        "high": {"bg": "rgba(245,158,11,0.15)", "border": "rgba(245,158,11,0.3)", "text": "#F59E0B", "icon": "⚠️"},
        "medium": {"bg": "rgba(59,130,246,0.15)", "border": "rgba(59,130,246,0.3)", "text": "#3B82F6", "icon": "ℹ️"},
    }
    colors = priority_colors.get(priority, priority_colors["high"])
    
    # Construction des détails HTML
    details_html = ""
    if details:
        details_rows = "".join([
            f'<div class="detail-row"><span class="detail-label">{k}</span><span class="detail-value">{v}</span></div>'
            for k, v in details.items()
        ])
        details_html = f'<div class="details-box">{details_rows}</div>'
    
    subject = f"{colors['icon']} [{priority.upper()}] {title}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #070A10; color: #ffffff; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: {colors['bg']}; border-radius: 22px; padding: 40px; border: 2px solid {colors['border']}; }}
            .header {{ text-align: center; margin-bottom: 25px; }}
            .alert-icon {{ font-size: 48px; margin-bottom: 15px; }}
            .header h1 {{ color: {colors['text']}; font-size: 22px; margin: 0; }}
            .priority-badge {{ display: inline-block; background: {colors['text']}; color: #000; padding: 4px 12px; border-radius: 20px; font-size: 11px; font-weight: bold; text-transform: uppercase; margin-top: 10px; }}
            .content {{ color: rgba(255,255,255,0.9); line-height: 1.6; }}
            .message {{ background: rgba(255,255,255,0.06); padding: 20px; border-radius: 12px; margin: 20px 0; font-size: 15px; }}
            .details-box {{ background: rgba(0,0,0,0.2); padding: 20px; border-radius: 12px; margin: 20px 0; }}
            .detail-row {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid rgba(255,255,255,0.08); }}
            .detail-row:last-child {{ border-bottom: none; }}
            .detail-label {{ color: rgba(255,255,255,0.5); font-size: 13px; }}
            .detail-value {{ color: #ffffff; font-size: 13px; font-weight: 600; }}
            .action-btn {{ display: inline-block; background: {colors['text']}; color: #000; padding: 12px 24px; text-decoration: none; border-radius: 10px; font-weight: 600; margin-top: 15px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.4); font-size: 11px; text-align: center; }}
            .alert-type {{ color: rgba(255,255,255,0.4); font-size: 11px; text-transform: uppercase; letter-spacing: 1px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="alert-icon">{colors['icon']}</div>
                <h1>{title}</h1>
                <span class="priority-badge">{priority}</span>
            </div>
            <div class="content">
                <div class="message">{message}</div>
                {details_html}
                <center>
                    <a href="{FRONTEND_URL}/superadmin" class="action-btn">Voir le Dashboard Admin</a>
                </center>
            </div>
            <div class="footer">
                <p class="alert-type">Type: {alert_type}</p>
                <p>KDMARCHE × O'SCOP - Système d'alertes automatiques</p>
                <p>Cet email a été envoyé automatiquement suite à un événement critique.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    [{priority.upper()}] {title}
    
    {message}
    
    Détails:
    {chr(10).join([f'- {k}: {v}' for k, v in (details or {}).items()])}
    
    Accéder au Dashboard: {FRONTEND_URL}/superadmin
    
    Type d'alerte: {alert_type}
    KDMARCHE × O'SCOP - Système d'alertes automatiques
    """
    
    success = True
    for email in recipients:
        try:
            result = send_email(email, subject, html_content, plain_content)
            if not result:
                success = False
                logger.error(f"Failed to send alert to {email}")
            else:
                logger.info(f"Critical alert sent to {email}: {title}")
        except Exception as e:
            logger.error(f"Error sending alert to {email}: {e}")
            success = False
    
    return success


def send_large_order_alert(order_data: dict, admin_emails: list = None):
    """
    Alerte pour commande importante (> 5000€)
    """
    amount = order_data.get("total_ttc", 0)
    threshold = ALERT_THRESHOLDS["large_order_amount"]
    
    if amount < threshold:
        return False
    
    return send_critical_alert_email(
        alert_type="large_order",
        title=f"Commande importante: {amount:.2f}€",
        message=f"Une nouvelle commande de <strong>{amount:.2f}€</strong> vient d'être passée. Cette commande dépasse le seuil de {threshold}€ et nécessite une attention particulière.",
        details={
            "N° Commande": order_data.get("order_number", "N/A"),
            "Montant TTC": f"{amount:.2f}€",
            "Organisation": order_data.get("org_name", "N/A"),
            "Zone": order_data.get("zone_code", "N/A"),
            "Articles": str(order_data.get("items_count", 0)),
        },
        priority="high",
        admin_emails=admin_emails
    )


def send_stock_rupture_alert(product_data: dict, admin_emails: list = None):
    """
    Alerte pour rupture de stock
    """
    return send_critical_alert_email(
        alert_type="stock_rupture",
        title=f"Rupture de stock: {product_data.get('name', 'Produit')}",
        message=f"Le produit <strong>{product_data.get('name', 'Produit')}</strong> est en rupture de stock (0 unités). Les commandes contenant ce produit ne pourront pas être honorées.",
        details={
            "Produit": product_data.get("name", "N/A"),
            "SKU": product_data.get("sku", "N/A"),
            "Catégorie": product_data.get("category", "N/A"),
            "Zone": product_data.get("zone_code", "Toutes zones"),
            "Dernier stock": "0 unités",
        },
        priority="critical",
        admin_emails=admin_emails
    )


def send_low_stock_alert(product_data: dict, admin_emails: list = None):
    """
    Alerte pour stock faible (< 5 unités)
    """
    stock = product_data.get("stock", 0)
    threshold = ALERT_THRESHOLDS["critical_stock_level"]
    
    if stock >= threshold or stock == 0:
        return False
    
    return send_critical_alert_email(
        alert_type="low_stock",
        title=f"Stock faible: {product_data.get('name', 'Produit')}",
        message=f"Le stock du produit <strong>{product_data.get('name', 'Produit')}</strong> est critique ({stock} unités). Pensez à réapprovisionner pour éviter une rupture.",
        details={
            "Produit": product_data.get("name", "N/A"),
            "SKU": product_data.get("sku", "N/A"),
            "Stock actuel": f"{stock} unités",
            "Seuil critique": f"< {threshold} unités",
            "Zone": product_data.get("zone_code", "Toutes zones"),
        },
        priority="high",
        admin_emails=admin_emails
    )


def send_payment_failed_alert(payment_data: dict, admin_emails: list = None):
    """
    Alerte pour paiement échoué
    """
    amount = payment_data.get("amount", 0)
    
    return send_critical_alert_email(
        alert_type="payment_failed",
        title=f"Paiement échoué: {amount:.2f}€",
        message=f"Un paiement de <strong>{amount:.2f}€</strong> a échoué. L'intervention de l'équipe peut être nécessaire pour contacter le client.",
        details={
            "Montant": f"{amount:.2f}€",
            "N° Commande": payment_data.get("order_number", "N/A"),
            "Organisation": payment_data.get("org_name", "N/A"),
            "Méthode": payment_data.get("payment_method", "N/A"),
            "Erreur": payment_data.get("error_message", "Erreur inconnue"),
        },
        priority="critical" if amount > ALERT_THRESHOLDS["payment_failed_threshold"] else "high",
        admin_emails=admin_emails
    )


def send_new_org_application_alert(org_data: dict, admin_emails: list = None):
    """
    Alerte pour nouvelle demande d'adhésion B2B
    """
    return send_critical_alert_email(
        alert_type="new_org_application",
        title=f"Nouvelle demande B2B: {org_data.get('legal_name', 'Organisation')}",
        message=f"Une nouvelle organisation <strong>{org_data.get('legal_name', 'N/A')}</strong> demande à rejoindre la plateforme. Une validation est requise.",
        details={
            "Raison sociale": org_data.get("legal_name", "N/A"),
            "SIRET": org_data.get("siret", "N/A"),
            "Territoire": org_data.get("territory", "N/A"),
            "Contact": org_data.get("contact_name", "N/A"),
            "Email": org_data.get("contact_email", "N/A"),
        },
        priority="medium",
        admin_emails=admin_emails
    )


def send_signature_declined_alert(signature_data: dict, admin_emails: list = None):
    """
    Alerte pour signature refusée
    """
    return send_critical_alert_email(
        alert_type="signature_declined",
        title="Signature refusée par le client",
        message=f"Le client <strong>{signature_data.get('signer_name', 'N/A')}</strong> a refusé de signer le document. Un suivi commercial peut être nécessaire.",
        details={
            "Signataire": signature_data.get("signer_name", "N/A"),
            "Email": signature_data.get("signer_email", "N/A"),
            "Document": signature_data.get("document_type", "N/A"),
            "Organisation": signature_data.get("org_name", "N/A"),
            "Motif": signature_data.get("decline_reason", "Non spécifié"),
        },
        priority="high",
        admin_emails=admin_emails
    )
