"""KDMARCHE WebSockets — ConnectionManager & helpers de notification (split from routes_websockets.py)."""
from fastapi import WebSocket
from typing import List, Dict, Set
import json
import asyncio
import logging
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

db = None

def set_ws_manager_database(database):
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


