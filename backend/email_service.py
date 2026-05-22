"""
SendGrid Email Service for KDMARCHE × O'SCOP B2B ESS Platform
Handles password reset emails and contact form notifications
"""

import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

logger = logging.getLogger(__name__)

# Get SendGrid API key from environment
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "noreply@kdmarche-oscop.fr")
FRONTEND_URL = os.environ.get("FRONTEND_URL", "https://plan-builder-75.preview.emergentagent.com")


class EmailServiceError(Exception):
    """Custom exception for email service errors"""
    pass


def is_email_configured():
    """Check if SendGrid is properly configured"""
    return bool(SENDGRID_API_KEY)


def send_email(to: str, subject: str, html_content: str, plain_content: str = None):
    """
    Send an email via SendGrid
    
    Args:
        to: Recipient email address
        subject: Email subject line
        html_content: HTML email content
        plain_content: Plain text fallback (optional)
    
    Returns:
        bool: True if email was sent successfully
    """
    if not is_email_configured():
        logger.warning(f"SendGrid not configured. Would send email to {to}: {subject}")
        # Return True in dev mode to not block the flow
        return True
    
    message = Mail(
        from_email=SENDER_EMAIL,
        to_emails=to,
        subject=subject,
        html_content=html_content,
        plain_text_content=plain_content
    )
    
    try:
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        logger.info(f"Email sent to {to}: {subject} (status: {response.status_code})")
        return response.status_code == 202
    except Exception as e:
        logger.error(f"Failed to send email to {to}: {str(e)}")
        raise EmailServiceError(f"Échec de l'envoi de l'email: {str(e)}")


def send_password_reset_email(to: str, reset_token: str, user_name: str):
    """
    Send password reset email
    """
    reset_link = f"{FRONTEND_URL}/reinitialiser-mot-de-passe?token={reset_token}"
    
    subject = "Réinitialisation de votre mot de passe - KDMARCHE × O'SCOP"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #070A10; color: #ffffff; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); border-radius: 22px; padding: 40px; border: 1px solid rgba(255,255,255,0.10); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: #D9B35A; font-size: 24px; margin: 0; }}
            .content {{ color: rgba(255,255,255,0.85); line-height: 1.6; }}
            .btn {{ display: inline-block; background: linear-gradient(135deg, #D9B35A, #F2D07A); color: #000; padding: 14px 28px; text-decoration: none; border-radius: 14px; font-weight: 600; margin: 20px 0; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); font-size: 12px; text-align: center; }}
            .warning {{ background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.2); padding: 15px; border-radius: 10px; margin: 20px 0; font-size: 13px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>KDMARCHE × O'SCOP</h1>
                <p style="color: rgba(255,255,255,0.6); margin-top: 8px;">Centrale d'achats B2B ESS</p>
            </div>
            <div class="content">
                <p>Bonjour {user_name},</p>
                <p>Vous avez demandé la réinitialisation de votre mot de passe.</p>
                <p>Cliquez sur le bouton ci-dessous pour créer un nouveau mot de passe :</p>
                <center>
                    <a href="{reset_link}" class="btn">Réinitialiser mon mot de passe</a>
                </center>
                <div class="warning">
                    ⚠️ Ce lien expire dans 1 heure. Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
                </div>
            </div>
            <div class="footer">
                <p>KDMARCHE × O'SCOP - Centrale d'achats B2B ESS</p>
                <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Bonjour {user_name},
    
    Vous avez demandé la réinitialisation de votre mot de passe.
    
    Cliquez sur le lien suivant pour créer un nouveau mot de passe :
    {reset_link}
    
    Ce lien expire dans 1 heure.
    
    Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.
    
    KDMARCHE × O'SCOP - Centrale d'achats B2B ESS
    """
    
    return send_email(to, subject, html_content, plain_content)


def send_contact_notification(admin_email: str, contact_data: dict):
    """
    Send notification email when new contact/quote request is submitted
    """
    subject = f"Nouvelle demande de devis - {contact_data.get('company', 'N/A')}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #070A10; color: #ffffff; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); border-radius: 22px; padding: 40px; border: 1px solid rgba(255,255,255,0.10); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: #57D19A; font-size: 24px; margin: 0; }}
            .field {{ background: rgba(255,255,255,0.04); padding: 15px; border-radius: 10px; margin: 10px 0; }}
            .field-label {{ color: rgba(255,255,255,0.5); font-size: 12px; text-transform: uppercase; letter-spacing: 1px; }}
            .field-value {{ color: #ffffff; font-size: 15px; margin-top: 5px; }}
            .footer {{ margin-top: 30px; color: rgba(255,255,255,0.5); font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Nouvelle demande de devis</h1>
            </div>
            <div class="field">
                <div class="field-label">Entreprise</div>
                <div class="field-value">{contact_data.get('company', 'N/A')}</div>
            </div>
            <div class="field">
                <div class="field-label">Contact</div>
                <div class="field-value">{contact_data.get('contact_name', 'N/A')}</div>
            </div>
            <div class="field">
                <div class="field-label">Email</div>
                <div class="field-value">{contact_data.get('email', 'N/A')}</div>
            </div>
            <div class="field">
                <div class="field-label">Téléphone</div>
                <div class="field-value">{contact_data.get('phone', 'N/A')}</div>
            </div>
            <div class="field">
                <div class="field-label">Formule souhaitée</div>
                <div class="field-value">{contact_data.get('plan', 'Non spécifié')}</div>
            </div>
            <div class="field">
                <div class="field-label">Message</div>
                <div class="field-value">{contact_data.get('message', 'Aucun message')}</div>
            </div>
            <div class="footer">
                <p>Reçu le {contact_data.get('created_at', 'N/A')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(admin_email, subject, html_content)


def send_welcome_email(to: str, user_name: str, company_name: str):
    """
    Send welcome email after registration
    """
    subject = "Bienvenue sur KDMARCHE × O'SCOP !"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #070A10; color: #ffffff; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, rgba(255,255,255,0.06), rgba(255,255,255,0.02)); border-radius: 22px; padding: 40px; border: 1px solid rgba(255,255,255,0.10); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: #D9B35A; font-size: 28px; margin: 0; }}
            .content {{ color: rgba(255,255,255,0.85); line-height: 1.6; }}
            .btn {{ display: inline-block; background: linear-gradient(135deg, #D9B35A, #F2D07A); color: #000; padding: 14px 28px; text-decoration: none; border-radius: 14px; font-weight: 600; margin: 20px 0; }}
            .feature {{ display: flex; align-items: center; gap: 15px; padding: 15px; background: rgba(87,209,154,0.08); border-radius: 10px; margin: 10px 0; }}
            .feature-icon {{ color: #57D19A; font-size: 20px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Bienvenue !</h1>
                <p style="color: rgba(255,255,255,0.6); margin-top: 8px;">KDMARCHE × O'SCOP</p>
            </div>
            <div class="content">
                <p>Bonjour {user_name},</p>
                <p>Votre compte pour <strong>{company_name}</strong> a été créé avec succès sur la centrale d'achats B2B ESS.</p>
                <p>Voici ce que vous pouvez faire :</p>
                <div class="feature">
                    <span class="feature-icon">✓</span>
                    <span>Accéder au catalogue KDMARCHE avec jusqu'à -50% sur les prix</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">✓</span>
                    <span>Utiliser vos crédits wallet pour vos achats</span>
                </div>
                <div class="feature">
                    <span class="feature-icon">✓</span>
                    <span>Suivre vos commandes et économies en temps réel</span>
                </div>
                <center>
                    <a href="{FRONTEND_URL}/connexion" class="btn">Accéder à mon espace</a>
                </center>
            </div>
            <div class="footer">
                <p>KDMARCHE × O'SCOP - Centrale d'achats B2B ESS</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(to, subject, html_content)


def send_otp_email(to: str, otp_code: str, signer_name: str, document_type: str, expires_minutes: int = 10):
    """
    Send OTP code via email for signature verification
    (Alternative to SMS for testing/backup)
    """
    subject = f"Code de signature KDMARCHE - {otp_code}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #070A10; color: #ffffff; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, rgba(74,23,118,0.15), rgba(26,11,46,0.25)); border-radius: 22px; padding: 40px; border: 1px solid rgba(106,43,182,0.25); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .header h1 {{ color: #D9B35A; font-size: 24px; margin: 0; }}
            .otp-box {{ background: linear-gradient(135deg, rgba(212,175,55,0.15), rgba(106,43,182,0.1)); border: 2px solid rgba(212,175,55,0.3); border-radius: 16px; padding: 30px; text-align: center; margin: 25px 0; }}
            .otp-code {{ font-family: 'Courier New', monospace; font-size: 42px; font-weight: bold; letter-spacing: 8px; color: #D9B35A; text-shadow: 0 0 20px rgba(212,175,55,0.3); }}
            .content {{ color: rgba(255,255,255,0.85); line-height: 1.6; }}
            .warning {{ background: rgba(255,107,107,0.1); border: 1px solid rgba(255,107,107,0.2); padding: 15px; border-radius: 10px; margin: 20px 0; font-size: 13px; color: rgba(255,255,255,0.8); }}
            .doc-info {{ background: rgba(255,255,255,0.04); padding: 15px; border-radius: 10px; margin: 15px 0; }}
            .doc-label {{ color: rgba(255,255,255,0.5); font-size: 12px; text-transform: uppercase; }}
            .doc-value {{ color: #ffffff; font-size: 14px; margin-top: 4px; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>🔐 Code de vérification</h1>
                <p style="color: rgba(255,255,255,0.6); margin-top: 8px;">Signature électronique KDMARCHE × O'SCOP</p>
            </div>
            <div class="content">
                <p>Bonjour {signer_name},</p>
                <p>Voici votre code de vérification pour signer le document :</p>
                
                <div class="otp-box">
                    <div class="otp-code">{otp_code}</div>
                    <p style="color: rgba(255,255,255,0.6); margin-top: 15px; font-size: 13px;">
                        Ce code expire dans <strong>{expires_minutes} minutes</strong>
                    </p>
                </div>
                
                <div class="doc-info">
                    <div class="doc-label">Document à signer</div>
                    <div class="doc-value">{document_type.replace('_', ' ')}</div>
                </div>
                
                <div class="warning">
                    ⚠️ <strong>Ne partagez jamais ce code.</strong> KDMARCHE ne vous demandera jamais ce code par téléphone ou email.
                </div>
            </div>
            <div class="footer">
                <p>KDMARCHE × O'SCOP - Signature électronique conforme eIDAS</p>
                <p>Cet email a été envoyé automatiquement suite à une demande de signature.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    plain_content = f"""
    Code de vérification KDMARCHE
    
    Bonjour {signer_name},
    
    Votre code de vérification pour signer le document est :
    
    {otp_code}
    
    Ce code expire dans {expires_minutes} minutes.
    
    Document : {document_type.replace('_', ' ')}
    
    Ne partagez jamais ce code.
    
    KDMARCHE × O'SCOP
    """
    
    return send_email(to, subject, html_content, plain_content)


def send_signature_confirmation_email(to: str, signer_name: str, document_type: str, signature_id: str, signed_at: str):
    """
    Send email confirming successful signature
    """
    subject = f"Document signé avec succès - {document_type.replace('_', ' ')}"
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #070A10; color: #ffffff; padding: 40px 20px; }}
            .container {{ max-width: 600px; margin: 0 auto; background: linear-gradient(180deg, rgba(16,185,129,0.1), rgba(26,11,46,0.15)); border-radius: 22px; padding: 40px; border: 1px solid rgba(16,185,129,0.2); }}
            .header {{ text-align: center; margin-bottom: 30px; }}
            .success-icon {{ font-size: 60px; margin-bottom: 15px; }}
            .header h1 {{ color: #10B981; font-size: 24px; margin: 0; }}
            .content {{ color: rgba(255,255,255,0.85); line-height: 1.6; }}
            .info-box {{ background: rgba(255,255,255,0.04); padding: 20px; border-radius: 12px; margin: 20px 0; }}
            .info-row {{ display: flex; justify-content: space-between; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.08); }}
            .info-row:last-child {{ border-bottom: none; }}
            .info-label {{ color: rgba(255,255,255,0.5); font-size: 13px; }}
            .info-value {{ color: #ffffff; font-size: 13px; font-family: monospace; }}
            .footer {{ margin-top: 30px; padding-top: 20px; border-top: 1px solid rgba(255,255,255,0.1); color: rgba(255,255,255,0.5); font-size: 12px; text-align: center; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <div class="success-icon">✅</div>
                <h1>Document signé avec succès</h1>
            </div>
            <div class="content">
                <p>Bonjour {signer_name},</p>
                <p>Votre signature électronique a été enregistrée avec succès.</p>
                
                <div class="info-box">
                    <div class="info-row">
                        <span class="info-label">Document</span>
                        <span class="info-value">{document_type.replace('_', ' ')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">ID Signature</span>
                        <span class="info-value">{signature_id}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Date de signature</span>
                        <span class="info-value">{signed_at}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Niveau</span>
                        <span class="info-value">eIDAS AES</span>
                    </div>
                </div>
                
                <p style="font-size: 13px; color: rgba(255,255,255,0.6);">
                    Ce document est conservé de manière sécurisée. Vous pouvez accéder au certificat de signature depuis votre espace client.
                </p>
            </div>
            <div class="footer">
                <p>KDMARCHE × O'SCOP - Signature électronique conforme eIDAS</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(to, subject, html_content)


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
