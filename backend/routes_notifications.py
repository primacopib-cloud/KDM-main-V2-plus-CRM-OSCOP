"""
KDMARCHE × O'SCOP - Real-time Notifications API
WebSocket-based notifications system for Super Admin
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException, Depends, Request, Query
from typing import List, Dict, Optional, Set
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel
import asyncio
import logging
import json
import uuid

logger = logging.getLogger(__name__)

# Router
notifications_router = APIRouter(prefix="/api/notifications")

# Database reference
db = None

def set_notifications_database(database):
    global db
    db = database


# ============== WEBSOCKET CONNECTION MANAGER ==============

class ConnectionManager:
    """Manage WebSocket connections for real-time notifications"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.admin_connections: Set[str] = set()
    
    async def connect(self, websocket: WebSocket, client_id: str, is_admin: bool = False):
        await websocket.accept()
        self.active_connections[client_id] = websocket
        if is_admin:
            self.admin_connections.add(client_id)
        logger.info(f"WebSocket connected: {client_id} (admin: {is_admin})")
    
    def disconnect(self, client_id: str):
        if client_id in self.active_connections:
            del self.active_connections[client_id]
        self.admin_connections.discard(client_id)
        logger.info(f"WebSocket disconnected: {client_id}")
    
    async def send_personal_message(self, message: dict, client_id: str):
        if client_id in self.active_connections:
            websocket = self.active_connections[client_id]
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending to {client_id}: {e}")
                self.disconnect(client_id)
    
    async def broadcast(self, message: dict):
        """Broadcast to all connected clients"""
        disconnected = []
        for client_id, websocket in self.active_connections.items():
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Broadcast error to {client_id}: {e}")
                disconnected.append(client_id)
        
        for client_id in disconnected:
            self.disconnect(client_id)
    
    async def broadcast_to_admins(self, message: dict):
        """Broadcast to admin connections only"""
        disconnected = []
        for client_id in self.admin_connections:
            if client_id in self.active_connections:
                try:
                    await self.active_connections[client_id].send_json(message)
                except Exception as e:
                    logger.error(f"Admin broadcast error to {client_id}: {e}")
                    disconnected.append(client_id)
        
        for client_id in disconnected:
            self.disconnect(client_id)


# Global connection manager
manager = ConnectionManager()


# ============== NOTIFICATION SCHEMAS ==============

class NotificationCreate(BaseModel):
    title: str
    message: str
    type: str = "info"  # info, success, warning, error
    category: str = "system"  # system, order, payment, signature, stock, user
    target_user_id: Optional[str] = None  # None = all admins
    action_url: Optional[str] = None
    metadata: Optional[dict] = None


class NotificationResponse(BaseModel):
    id: str
    title: str
    message: str
    type: str
    category: str
    is_read: bool
    created_at: datetime
    action_url: Optional[str] = None


# ============== WEBSOCKET ENDPOINTS ==============

@notifications_router.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str, token: str = Query(None)):
    """WebSocket endpoint for real-time notifications"""
    # Verify token (simplified - in production, decode JWT)
    is_admin = False
    
    if token:
        try:
            from auth import decode_token
            user_id = decode_token(token)
            if user_id:
                user = await db.users.find_one({"id": user_id})
                if user and user.get("is_admin"):
                    is_admin = True
        except Exception as e:
            logger.warning(f"Token verification failed: {e}")
    
    await manager.connect(websocket, client_id, is_admin)
    
    try:
        # Send initial connection confirmation
        await websocket.send_json({
            "type": "connected",
            "client_id": client_id,
            "is_admin": is_admin,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        
        # Keep connection alive and handle messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                message = json.loads(data)
                
                # Handle ping/pong for keepalive
                if message.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": datetime.now(timezone.utc).isoformat()})
                elif message.get("type") == "subscribe":
                    # Handle topic subscription
                    pass
                    
            except asyncio.TimeoutError:
                # Send keepalive ping
                try:
                    await websocket.send_json({"type": "keepalive", "timestamp": datetime.now(timezone.utc).isoformat()})
                except Exception:
                    break
                    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(client_id)


# ============== NOTIFICATION API ENDPOINTS ==============

@notifications_router.get("")
async def get_notifications(
    unread_only: bool = Query(False),
    category: str = Query(None),
    limit: int = Query(50, le=100),
    request: Request = None,
):
    """Get notifications for admin users"""
    query = {}
    
    if unread_only:
        query["is_read"] = False
    if category:
        query["category"] = category
    
    try:
        notifications = await db.admin_notifications.find(
            query,
            {"_id": 0}
        ).sort("created_at", -1).limit(limit).to_list(limit)
        
        unread_count = await db.admin_notifications.count_documents({"is_read": False})
        
        return {
            "notifications": notifications,
            "total": len(notifications),
            "unread_count": unread_count
        }
    except Exception as e:
        logger.error(f"Error fetching notifications: {e}")
        return {"notifications": [], "total": 0, "unread_count": 0}


@notifications_router.post("")
async def create_notification(notification: NotificationCreate):
    """Create a new notification and broadcast to connected admins"""
    now = datetime.now(timezone.utc)
    
    notif_data = {
        "id": str(uuid.uuid4()),
        "title": notification.title,
        "message": notification.message,
        "type": notification.type,
        "category": notification.category,
        "target_user_id": notification.target_user_id,
        "action_url": notification.action_url,
        "metadata": notification.metadata,
        "is_read": False,
        "created_at": now.isoformat(),
    }
    
    # Save to database — insert_one mutates notif_data to add a non-JSON-serializable
    # `_id` ObjectId. We pass a copy so the original dict stays clean for WS + response.
    await db.admin_notifications.insert_one(dict(notif_data))
    
    # Broadcast to connected WebSocket clients
    ws_message = {
        "type": "notification",
        "notification": notif_data
    }
    
    if notification.target_user_id:
        await manager.send_personal_message(ws_message, notification.target_user_id)
    else:
        await manager.broadcast_to_admins(ws_message)
    
    logger.info(f"Notification created: {notification.title}")
    
    return {"success": True, "notification": notif_data}


@notifications_router.put("/{notification_id}/read")
async def mark_as_read(notification_id: str):
    """Mark a notification as read"""
    result = await db.admin_notifications.update_one(
        {"id": notification_id},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    
    return {"success": True}


@notifications_router.put("/mark-all-read")
async def mark_all_as_read():
    """Mark all notifications as read"""
    result = await db.admin_notifications.update_many(
        {"is_read": False},
        {"$set": {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    return {"success": True, "count": result.modified_count}


@notifications_router.delete("/{notification_id}")
async def delete_notification(notification_id: str):
    """Delete a notification"""
    result = await db.admin_notifications.delete_one({"id": notification_id})
    
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Notification non trouvée")
    
    return {"success": True}


# ============== TRIGGER FUNCTIONS (called from other APIs) ==============

async def trigger_notification(
    title: str,
    message: str,
    type: str = "info",
    category: str = "system",
    action_url: str = None,
    metadata: dict = None
):
    """Utility function to trigger a notification from other parts of the app"""
    now = datetime.now(timezone.utc)
    
    notif_data = {
        "id": str(uuid.uuid4()),
        "title": title,
        "message": message,
        "type": type,
        "category": category,
        "action_url": action_url,
        "metadata": metadata,
        "is_read": False,
        "created_at": now.isoformat(),
    }
    
    # Save to database
    if db:
        await db.admin_notifications.insert_one(notif_data)
    
    # Broadcast
    ws_message = {"type": "notification", "notification": notif_data}
    await manager.broadcast_to_admins(ws_message)
    
    return notif_data


# ============== EVENT HANDLERS (to be called when events occur) ==============

async def notify_new_order(order: dict):
    """Notify admins of a new order"""
    await trigger_notification(
        title="Nouvelle commande",
        message=f"Commande {order.get('order_number', 'N/A')} - {order.get('total_ttc_cents', 0) / 100:.2f}€",
        type="success",
        category="order",
        action_url=f"/super-admin?tab=orders&order={order.get('id')}",
        metadata={"order_id": order.get("id"), "order_number": order.get("order_number")}
    )


async def notify_payment_received(order: dict, amount: float):
    """Notify admins of payment received"""
    await trigger_notification(
        title="Paiement reçu",
        message=f"Paiement de {amount:.2f}€ pour la commande {order.get('order_number', 'N/A')}",
        type="success",
        category="payment",
        metadata={"order_id": order.get("id"), "amount": amount}
    )


async def notify_payment_failed(order: dict, error: str):
    """Notify admins of failed payment"""
    await trigger_notification(
        title="Échec de paiement",
        message=f"Paiement échoué pour {order.get('order_number', 'N/A')}: {error[:50]}",
        type="error",
        category="payment",
        metadata={"order_id": order.get("id"), "error": error}
    )


async def notify_low_stock(product_name: str, current_stock: int):
    """Notify admins of low stock"""
    await trigger_notification(
        title="Stock faible",
        message=f"Le produit '{product_name}' n'a plus que {current_stock} unités",
        type="warning",
        category="stock",
        action_url="/super-admin?tab=catalog"
    )


async def notify_new_user(user_email: str, org_name: str = None):
    """Notify admins of new user registration"""
    msg = f"Nouvel utilisateur: {user_email}"
    if org_name:
        msg += f" ({org_name})"
    
    await trigger_notification(
        title="Nouvel utilisateur",
        message=msg,
        type="info",
        category="user",
        action_url="/super-admin?tab=users"
    )


async def notify_signature_completed(order_number: str, signer_email: str):
    """Notify admins of completed signature"""
    await trigger_notification(
        title="Signature complétée",
        message=f"Document signé pour {order_number} par {signer_email}",
        type="success",
        category="signature"
    )


# ============== STATS ENDPOINT FOR DASHBOARD ==============

@notifications_router.get("/stats")
async def get_notification_stats():
    """Get notification statistics"""
    try:
        # Count by category
        cat_pipeline = [
            {"$match": {"is_read": False}},
            {"$group": {"_id": "$category", "count": {"$sum": 1}}}
        ]
        cat_result = await db.admin_notifications.aggregate(cat_pipeline).to_list(20)
        by_category = {c["_id"]: c["count"] for c in cat_result if c["_id"]}
        
        # Count by type
        type_pipeline = [
            {"$match": {"is_read": False}},
            {"$group": {"_id": "$type", "count": {"$sum": 1}}}
        ]
        type_result = await db.admin_notifications.aggregate(type_pipeline).to_list(20)
        by_type = {t["_id"]: t["count"] for t in type_result if t["_id"]}
        
        # Total counts
        total = await db.admin_notifications.count_documents({})
        unread = await db.admin_notifications.count_documents({"is_read": False})
        
        # Today's notifications
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = await db.admin_notifications.count_documents({
            "created_at": {"$gte": today_start.isoformat()}
        })
        
        return {
            "total": total,
            "unread": unread,
            "today": today_count,
            "by_category": by_category,
            "by_type": by_type,
            "connected_admins": len(manager.admin_connections),
            "total_connections": len(manager.active_connections)
        }
    except Exception as e:
        logger.error(f"Error getting notification stats: {e}")
        return {"total": 0, "unread": 0, "today": 0, "by_category": {}, "by_type": {}}
