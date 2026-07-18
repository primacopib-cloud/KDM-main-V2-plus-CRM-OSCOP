"""Guard admin réutilisable pour les routes protégées."""
from __future__ import annotations

from typing import Any, Dict

from fastapi import HTTPException

db = None


def set_admin_guard_database(database) -> None:
    global db
    db = database


async def require_admin(user_id: str) -> Dict[str, Any]:
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    if user.get("is_admin"):
        return user
    role = (user.get("role") or "").upper()
    if role in {"SUPER_ADMIN", "ADMIN", "COOP_BOARD", "OSCOP_SUPER_ADMIN", "KDM_B2B_ADMIN"}:
        return user
    raise HTTPException(status_code=403, detail="Réservé aux administrateurs")


async def require_cooper(user_id: str) -> Dict[str, Any]:
    """Admin OU membre d'équipe COOPER."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0, "password_hash": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    role = (user.get("role") or "").upper()
    if user.get("is_admin") or role in {"SUPER_ADMIN", "ADMIN", "COOP_BOARD", "OSCOP_SUPER_ADMIN", "KDM_B2B_ADMIN", "COOPER"}:
        return user
    raise HTTPException(status_code=403, detail="Réservé aux COOPER'S et administrateurs")
