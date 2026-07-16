"""KDMARCHE Export Admin — Enums & helpers (split from routes_export.py)."""
from fastapi import HTTPException, Request
from typing import Optional, List
from datetime import datetime, timezone
from enum import Enum
import logging

logger = logging.getLogger(__name__)

db = None

def set_export_common_database(database):
    global db
    db = database

# ============== ENUMS ==============

class ExportFormat(str, Enum):
    CSV = "csv"
    # EXCEL = "xlsx"  # Would require openpyxl


class ExportType(str, Enum):
    ORGANIZATIONS = "organizations"
    APPLICATIONS = "applications"
    ORDERS = "orders"
    TRANSACTIONS = "transactions"
    AUDIT_LOG = "audit_log"
    PRODUCTS = "products"
    USERS = "users"


# ============== HELPERS ==============

def format_datetime(dt):
    """Format datetime for export"""
    if not dt:
        return ""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    return dt.strftime("%Y-%m-%d %H:%M:%S")


def dict_to_csv_row(data: dict, columns: List[str]) -> List[str]:
    """Convert dict to CSV row with specified columns"""
    row = []
    for col in columns:
        value = data.get(col, "")
        if isinstance(value, datetime):
            value = format_datetime(value)
        elif isinstance(value, (list, dict)):
            value = str(value)
        elif value is None:
            value = ""
        row.append(str(value))
    return row


async def check_admin(request: Request):
    """Check if request is from admin"""
    from auth import decode_token, extract_user_id_from_request
    
    user_id = extract_user_id_from_request(request)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    
    return user


