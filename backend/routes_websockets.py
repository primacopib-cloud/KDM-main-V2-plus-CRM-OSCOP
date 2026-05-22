"""
KDMARCHE × O'SCOP - WebSocket Notifications API
Real-time notifications for admin dashboard
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from typing import List, Dict, Set
import json
import asyncio
import logging
from datetime import datetime, timezone
import uuid

# Import email alerts
from email_service import (
    send_large_order_alert,
    send_stock_rupture_alert,
    send_low_stock_alert,
    send_payment_failed_alert,
    send_new_org_application_alert,
    send_signature_declined_alert,
    ALERT_THRESHOLDS
)

logger = logging.getLogger(__name__)

# Router
websocket_router = APIRouter()

# Database reference
db = None

def set_websocket_database(database):
    """Set database reference from main server"""
    global db
    db = database


# ============== CONNECTION MANAGER ==============

class ConnectionManager:
    """Manages WebSocket connections"""
    
    def __init__(self):
        # Active connections by user_id
        self.active_connections: Dict[str, List[WebSocket]] = {}
        # Admin connections (for broadcast)
        self.admin_connections: Set[WebSocket] = set()
        # All connections for global broadcast
        self.all_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, user_id: str = None, is_admin: bool = False):
        """Accept and store a new connection"""
        await websocket.accept()
        self.all_connections.add(websocket)
        
        if user_id:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = []
            self.active_connections[user_id].append(websocket)
        
        if is_admin:
            self.admin_connections.add(websocket)
        
        logger.info(f"WebSocket connected: user_id={user_id}, is_admin={is_admin}, total_connections={len(self.all_connections)}")
    
    def disconnect(self, websocket: WebSocket, user_id: str = None):
        """Remove a connection"""
        self.all_connections.discard(websocket)
        self.admin_connections.discard(websocket)
        
        if user_id and user_id in self.active_connections:
            self.active_connections[user_id] = [
                ws for ws in self.active_connections[user_id] if ws != websocket
            ]
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected: user_id={user_id}, total_connections={len(self.all_connections)}")
    
    async def send_personal(self, user_id: str, message: dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            disconnected = []
            for ws in self.active_connections[user_id]:
                try:
                    await ws.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending to {user_id}: {e}")
                    disconnected.append(ws)
            
            # Clean up disconnected
            for ws in disconnected:
                self.disconnect(ws, user_id)
    
    async def broadcast_to_admins(self, message: dict):
        """Broadcast message to all admin connections"""
        disconnected = []
        for ws in self.admin_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting to admin: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.admin_connections.discard(ws)
    
    async def broadcast_all(self, message: dict):
        """Broadcast message to all connections"""
        disconnected = []
        for ws in self.all_connections:
            try:
                await ws.send_json(message)
            except Exception as e:
                logger.error(f"Error broadcasting: {e}")
                disconnected.append(ws)
        
        for ws in disconnected:
            self.all_connections.discard(ws)
    
    def get_stats(self) -> dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.all_connections),
            "admin_connections": len(self.admin_connections),
            "user_connections": len(self.active_connections),
        }


# Global connection manager
manager = ConnectionManager()


# ============== NOTIFICATION HELPERS ==============

async def create_notification(
    notification_type: str,
    title: str,
    message: str,
    target_roles: List[str] = None,
    target_user_id: str = None,
    data: dict = None,
    priority: str = "normal"
) -> dict:
    """Create and store a notification"""
    notification = {
        "id": str(uuid.uuid4()),
        "type": notification_type,
        "title": title,
        "message": message,
        "data": data or {},
        "target_roles": target_roles or [],
        "target_user_id": target_user_id,
        "priority": priority,
        "is_read": False,
        "read_by": [],
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    if db is not None:
        await db.notifications.insert_one(notification)
    
    return notification


async def send_notification(notification: dict):
    """Send notification via WebSocket"""
    ws_message = {
        "type": "notification",
        "payload": notification
    }
    
    # If targeted to specific user
    if notification.get("target_user_id"):
        await manager.send_personal(notification["target_user_id"], ws_message)
    
    # If targeted to admin roles
    if notification.get("target_roles") and any(
        role in ["oscop_super_admin", "oscop_compliance_admin", "kdm_b2b_admin"]
        for role in notification.get("target_roles", [])
    ):
        await manager.broadcast_to_admins(ws_message)


# ============== PUBLIC API FUNCTIONS ==============

async def emit_new_order_notification(order: dict):
    """Emit notification for new order + email alert if large"""
    total = order.get('total_ttc', 0)
    
    notification = await create_notification(
        notification_type="new_order",
        title="Nouvelle commande",
        message=f"Commande #{order.get('order_number', 'N/A')} - {total:.2f}€",
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={
            "order_id": order.get("id"),
            "order_number": order.get("order_number"),
            "total": total,
            "org_id": order.get("org_id")
        },
        priority="high" if total >= ALERT_THRESHOLDS["large_order_amount"] else "normal"
    )
    await send_notification(notification)
    
    # Send email alert for large orders (> 5000€)
    if total >= ALERT_THRESHOLDS["large_order_amount"]:
        try:
            send_large_order_alert({
                "order_number": order.get("order_number"),
                "total_ttc": total,
                "org_name": order.get("org_name", "N/A"),
                "zone_code": order.get("zone_code", "N/A"),
                "items_count": len(order.get("items", []))
            })
            logger.info(f"Large order email alert sent for order {order.get('order_number')}")
        except Exception as e:
            logger.error(f"Failed to send large order email alert: {e}")


async def emit_new_user_notification(user: dict):
    """Emit notification for new user registration"""
    notification = await create_notification(
        notification_type="new_user",
        title="Nouvel utilisateur",
        message=f"{user.get('contact_name', 'N/A')} - {user.get('company_name', 'N/A')}",
        target_roles=["oscop_super_admin", "oscop_compliance_admin"],
        data={
            "user_id": user.get("id"),
            "email": user.get("email"),
            "company": user.get("company_name")
        },
        priority="low"
    )
    await send_notification(notification)


async def emit_large_order_notification(order: dict):
    """Emit notification for large orders (> 5000€) - Deprecated, use emit_new_order_notification"""
    # Now handled by emit_new_order_notification
    await emit_new_order_notification(order)


async def emit_org_application_notification(org: dict, application: dict):
    """Emit notification for new B2B application + email alert"""
    notification = await create_notification(
        notification_type="org_application",
        title="Nouvelle demande d'adhésion B2B",
        message=f"{org.get('legal_name', 'N/A')} demande à rejoindre la plateforme",
        target_roles=["oscop_super_admin", "oscop_compliance_admin"],
        data={
            "org_id": org.get("id"),
            "application_id": application.get("id"),
            "siret": org.get("registration_id")
        },
        priority="high"
    )
    await send_notification(notification)
    
    # Send email alert
    try:
        send_new_org_application_alert({
            "legal_name": org.get("legal_name"),
            "siret": org.get("registration_id"),
            "territory": org.get("territory", "N/A"),
            "contact_name": org.get("contact_name", "N/A"),
            "contact_email": org.get("contact_email", "N/A")
        })
        logger.info(f"New org application email alert sent for {org.get('legal_name')}")
    except Exception as e:
        logger.error(f"Failed to send org application email alert: {e}")


async def emit_low_stock_notification(product: dict):
    """Emit notification for low stock + email alert"""
    stock = product.get('stock', 0)
    is_rupture = stock == 0
    
    notification = await create_notification(
        notification_type="stock_rupture" if is_rupture else "low_stock",
        title="Rupture de stock" if is_rupture else "Stock faible",
        message=f"{product.get('name', 'N/A')} - Stock: {stock} unités",
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={
            "product_id": product.get("id"),
            "product_name": product.get("name"),
            "stock": stock
        },
        priority="critical" if is_rupture else "medium"
    )
    await send_notification(notification)
    
    # Send email alert for critical stock
    try:
        if is_rupture:
            send_stock_rupture_alert({
                "name": product.get("name"),
                "sku": product.get("sku", "N/A"),
                "category": product.get("category", "N/A"),
                "zone_code": product.get("zone_code", "Toutes zones")
            })
            logger.info(f"Stock rupture email alert sent for {product.get('name')}")
        elif stock < ALERT_THRESHOLDS["critical_stock_level"]:
            send_low_stock_alert({
                "name": product.get("name"),
                "sku": product.get("sku", "N/A"),
                "stock": stock,
                "zone_code": product.get("zone_code", "Toutes zones")
            })
            logger.info(f"Low stock email alert sent for {product.get('name')}")
    except Exception as e:
        logger.error(f"Failed to send stock email alert: {e}")


async def emit_signature_completed_notification(signature: dict):
    """Emit notification for completed signature"""
    notification = await create_notification(
        notification_type="signature_completed",
        title="Signature complétée",
        message=f"Document signé par {signature.get('signer', {}).get('email', 'N/A')}",
        target_roles=["oscop_super_admin"],
        data={
            "signature_id": signature.get("id"),
            "document_type": signature.get("document_type")
        },
        priority="normal"
    )
    await send_notification(notification)


async def emit_payment_failed_notification(payment: dict):
    """Emit notification for failed payment + email alert"""
    amount = payment.get('amount', 0)
    
    notification = await create_notification(
        notification_type="payment_failed",
        title="Paiement échoué",
        message=f"Échec du paiement pour la commande #{payment.get('order_number', 'N/A')}",
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={
            "order_id": payment.get("order_id"),
            "amount": amount,
            "error": payment.get("error_message")
        },
        priority="critical" if amount > ALERT_THRESHOLDS["payment_failed_threshold"] else "high"
    )
    await send_notification(notification)
    
    # Send email alert
    try:
        send_payment_failed_alert({
            "amount": amount,
            "order_number": payment.get("order_number", "N/A"),
            "org_name": payment.get("org_name", "N/A"),
            "payment_method": payment.get("payment_method", "Carte"),
            "error_message": payment.get("error_message", "Erreur inconnue")
        })
        logger.info(f"Payment failed email alert sent for order {payment.get('order_number')}")
    except Exception as e:
        logger.error(f"Failed to send payment failed email alert: {e}")


# ============== WEBSOCKET ENDPOINTS ==============

@websocket_router.websocket("/api/ws/notifications")
async def websocket_notifications(
    websocket: WebSocket,
    user_id: str = Query(None),
    is_admin: str = Query("false")
):
    """
    WebSocket endpoint for real-time notifications
    
    Query params:
    - user_id: User ID for personal notifications
    - is_admin: "true" to receive admin broadcasts
    """
    is_admin_bool = is_admin.lower() == "true"
    
    await manager.connect(websocket, user_id, is_admin_bool)
    
    # Send connection confirmation
    await websocket.send_json({
        "type": "connected",
        "payload": {
            "message": "Connexion WebSocket établie",
            "user_id": user_id,
            "is_admin": is_admin_bool,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    })
    
    try:
        while True:
            # Wait for messages from client (heartbeat/ping)
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                if message.get("type") == "ping":
                    # Respond to ping with pong
                    await websocket.send_json({
                        "type": "pong",
                        "payload": {"timestamp": datetime.now(timezone.utc).isoformat()}
                    })
                
                elif message.get("type") == "mark_read":
                    # Mark notification as read
                    notification_id = message.get("payload", {}).get("notification_id")
                    if notification_id and db and user_id:
                        await db.notifications.update_one(
                            {"id": notification_id},
                            {"$addToSet": {"read_by": user_id}}
                        )
                        await websocket.send_json({
                            "type": "notification_marked_read",
                            "payload": {"notification_id": notification_id}
                        })
                
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket, user_id)


@websocket_router.get("/api/ws/status")
async def websocket_status():
    """Get WebSocket connection statistics"""
    return {
        "status": "active",
        **manager.get_stats(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@websocket_router.post("/api/ws/test-notification")
async def test_notification():
    """Send a test notification (for debugging)"""
    notification = await create_notification(
        notification_type="test",
        title="Notification de test",
        message="Ceci est une notification de test pour vérifier le système",
        target_roles=["oscop_super_admin"],
        data={"test": True},
        priority="normal"
    )
    await send_notification(notification)
    
    return {
        "success": True,
        "notification_id": notification["id"],
        "message": "Notification de test envoyée"
    }


@websocket_router.get("/api/alerts/thresholds")
async def get_alert_thresholds():
    """Get current alert thresholds configuration"""
    return {
        "thresholds": ALERT_THRESHOLDS,
        "description": {
            "large_order_amount": "Seuil pour alertes commandes importantes (€)",
            "critical_stock_level": "Seuil stock critique (unités)",
            "payment_failed_threshold": "Seuil paiement échoué critique (€)"
        }
    }


@websocket_router.post("/api/alerts/test-email")
async def test_email_alert(alert_type: str = "large_order"):
    """
    Test email alert system
    alert_type: large_order, stock_rupture, low_stock, payment_failed, org_application
    """
    from email_service import (
        send_large_order_alert,
        send_stock_rupture_alert,
        send_low_stock_alert,
        send_payment_failed_alert,
        send_new_org_application_alert
    )
    
    test_data = {
        "large_order": {
            "func": send_large_order_alert,
            "data": {
                "order_number": "TEST-001",
                "total_ttc": 7500.00,
                "org_name": "Entreprise Test",
                "zone_code": "971",
                "items_count": 15
            }
        },
        "stock_rupture": {
            "func": send_stock_rupture_alert,
            "data": {
                "name": "Produit Test",
                "sku": "SKU-TEST-001",
                "category": "Fruits",
                "zone_code": "Guadeloupe"
            }
        },
        "low_stock": {
            "func": send_low_stock_alert,
            "data": {
                "name": "Produit Test",
                "sku": "SKU-TEST-002",
                "stock": 3,
                "zone_code": "Martinique"
            }
        },
        "payment_failed": {
            "func": send_payment_failed_alert,
            "data": {
                "amount": 2500.00,
                "order_number": "ORD-TEST-001",
                "org_name": "Entreprise Test",
                "payment_method": "Carte Visa",
                "error_message": "Fonds insuffisants"
            }
        },
        "org_application": {
            "func": send_new_org_application_alert,
            "data": {
                "legal_name": "Nouvelle Entreprise SARL",
                "siret": "12345678901234",
                "territory": "Guadeloupe",
                "contact_name": "Jean Test",
                "contact_email": "jean@test.fr"
            }
        }
    }
    
    if alert_type not in test_data:
        return {
            "success": False,
            "error": f"Type d'alerte inconnu. Types disponibles: {list(test_data.keys())}"
        }
    
    try:
        alert_info = test_data[alert_type]
        result = alert_info["func"](alert_info["data"])
        return {
            "success": result,
            "alert_type": alert_type,
            "message": f"Email d'alerte test '{alert_type}' envoyé" if result else "Échec de l'envoi"
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
