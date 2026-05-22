"""
KDMARCHE × O'SCOP - Data Export API
Export CSV/Excel for admin reports

Features:
- Organizations export
- Applications export
- Orders export
- Transactions/Ledger export
- Audit log export
"""

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from typing import Optional, List
from datetime import datetime, timezone, timedelta
from enum import Enum
import csv
import io
import logging

logger = logging.getLogger(__name__)

# Router
export_router = APIRouter(prefix="/api/admin/export")

# Database reference (set by server.py)
db = None


def set_export_database(database):
    """Set database reference from main server"""
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
    from auth import decode_token
    
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token manquant")
    
    token = auth_header.split(" ")[1]
    user_id = decode_token(token)
    
    if not user_id:
        raise HTTPException(status_code=401, detail="Token invalide")
    
    user = await db.users.find_one({"id": user_id})
    if not user or not user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Accès administrateur requis")
    
    return user


# ============== EXPORT ENDPOINTS ==============

@export_router.get("/organizations")
async def export_organizations(
    request: Request,
    status_filter: Optional[str] = None,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export organizations to CSV"""
    await check_admin(request)
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    orgs = await db.orgs.find(query).sort("created_at", -1).to_list(5000)
    
    columns = [
        "id", "legal_name", "registration_id", "registration_country",
        "territory", "status", "contact_email", "contact_name", "contact_phone",
        "address", "created_at", "updated_at"
    ]
    
    # Create CSV
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    
    # Header
    writer.writerow(columns)
    
    # Data rows
    for org in orgs:
        writer.writerow(dict_to_csv_row(org, columns))
    
    output.seek(0)
    
    filename = f"organisations_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@export_router.get("/applications")
async def export_applications(
    request: Request,
    status_filter: Optional[str] = None,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export B2B applications to CSV"""
    await check_admin(request)
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    apps = await db.b2b_applications.find(query).sort("created_at", -1).to_list(5000)
    
    # Enrich with org data
    org_ids = list(set([app.get("org_id") for app in apps if app.get("org_id")]))
    orgs = await db.orgs.find({"id": {"$in": org_ids}}).to_list(len(org_ids))
    org_map = {org["id"]: org for org in orgs}
    
    columns = [
        "id", "org_id", "org_name", "org_siret", "org_territory",
        "status", "submitted_at", "reviewed_by", "reviewed_at",
        "decision", "reason_code", "comment", "documents_count", "created_at"
    ]
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    
    for app in apps:
        org = org_map.get(app.get("org_id"), {})
        row_data = {
            **app,
            "org_name": org.get("legal_name", ""),
            "org_siret": org.get("registration_id", ""),
            "org_territory": org.get("territory", ""),
            "documents_count": len(app.get("documents", [])),
        }
        writer.writerow(dict_to_csv_row(row_data, columns))
    
    output.seek(0)
    filename = f"demandes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@export_router.get("/orders")
async def export_orders(
    request: Request,
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export orders to CSV"""
    await check_admin(request)
    
    query = {}
    if status_filter:
        query["status"] = status_filter
    
    if date_from:
        query["created_at"] = {"$gte": datetime.fromisoformat(date_from)}
    if date_to:
        if "created_at" in query:
            query["created_at"]["$lte"] = datetime.fromisoformat(date_to)
        else:
            query["created_at"] = {"$lte": datetime.fromisoformat(date_to)}
    
    orders = await db.orders.find(query).sort("created_at", -1).to_list(10000)
    
    # Enrich with org data
    org_ids = list(set([o.get("org_id") for o in orders if o.get("org_id")]))
    orgs = await db.orgs.find({"id": {"$in": org_ids}}).to_list(len(org_ids))
    org_map = {org["id"]: org for org in orgs}
    
    columns = [
        "order_number", "org_id", "org_name", "zone_code",
        "status", "items_count", "total_ht_cents", "total_ht_eur",
        "pickup_location_id", "pickup_city", "notes",
        "created_at", "confirmed_at", "completed_at", "canceled_at"
    ]
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    
    for order in orders:
        org = org_map.get(order.get("org_id"), {})
        pickup = order.get("pickup_location", {})
        
        row_data = {
            **order,
            "org_name": org.get("legal_name", ""),
            "items_count": len(order.get("items", [])),
            "total_ht_eur": f"{order.get('total_ht_cents', 0) / 100:.2f}",
            "pickup_city": pickup.get("city", "") if isinstance(pickup, dict) else "",
        }
        writer.writerow(dict_to_csv_row(row_data, columns))
    
    output.seek(0)
    filename = f"commandes_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@export_router.get("/transactions")
async def export_transactions(
    request: Request,
    org_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export wallet transactions/ledger to CSV"""
    await check_admin(request)
    
    query = {}
    if org_id:
        query["org_id"] = org_id
    
    if date_from:
        query["created_at"] = {"$gte": datetime.fromisoformat(date_from)}
    if date_to:
        if "created_at" in query:
            query["created_at"]["$lte"] = datetime.fromisoformat(date_to)
        else:
            query["created_at"] = {"$lte": datetime.fromisoformat(date_to)}
    
    transactions = await db.wallet_ledger.find(query).sort("created_at", -1).to_list(20000)
    
    # Enrich with org data
    org_ids = list(set([t.get("org_id") for t in transactions if t.get("org_id")]))
    orgs = await db.orgs.find({"id": {"$in": org_ids}}).to_list(len(org_ids))
    org_map = {org["id"]: org for org in orgs}
    
    columns = [
        "id", "org_id", "org_name", "type", "amount",
        "balance_before", "balance_after", "description",
        "reference_type", "reference_id", "created_at"
    ]
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    
    for tx in transactions:
        org = org_map.get(tx.get("org_id"), {})
        row_data = {
            **tx,
            "org_name": org.get("legal_name", ""),
        }
        writer.writerow(dict_to_csv_row(row_data, columns))
    
    output.seek(0)
    filename = f"transactions_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@export_router.get("/audit-log")
async def export_audit_log(
    request: Request,
    org_id: Optional[str] = None,
    action: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export audit log to CSV"""
    await check_admin(request)
    
    query = {}
    if org_id:
        query["org_id"] = org_id
    if action:
        query["action"] = action
    
    if date_from:
        query["created_at"] = {"$gte": datetime.fromisoformat(date_from)}
    if date_to:
        if "created_at" in query:
            query["created_at"]["$lte"] = datetime.fromisoformat(date_to)
        else:
            query["created_at"] = {"$lte": datetime.fromisoformat(date_to)}
    
    logs = await db.audit_log.find(query).sort("created_at", -1).to_list(50000)
    
    columns = [
        "id", "org_id", "user_id", "action", "entity_type", "entity_id",
        "old_value", "new_value", "ip_address", "user_agent", "created_at"
    ]
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    
    for log in logs:
        writer.writerow(dict_to_csv_row(log, columns))
    
    output.seek(0)
    filename = f"audit_log_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@export_router.get("/products")
async def export_products(
    request: Request,
    category_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export products catalog to CSV"""
    await check_admin(request)
    
    query = {}
    if category_id:
        query["category_id"] = category_id
    if status_filter:
        query["status"] = status_filter
    
    products = await db.products.find(query).sort("name", 1).to_list(10000)
    
    # Get categories for names
    cat_ids = list(set([p.get("category_id") for p in products if p.get("category_id")]))
    categories = await db.categories.find({"id": {"$in": cat_ids}}).to_list(len(cat_ids))
    cat_map = {cat["id"]: cat for cat in categories}
    
    # Get zone prices
    prod_ids = [p["id"] for p in products]
    prices = await db.zone_prices.find({"product_id": {"$in": prod_ids}}).to_list(50000)
    
    # Group prices by product
    prices_by_product = {}
    for price in prices:
        pid = price["product_id"]
        if pid not in prices_by_product:
            prices_by_product[pid] = {}
        prices_by_product[pid][price["zone_code"]] = price["price_ht_cents"]
    
    # Get all zone codes
    zone_codes = list(set([p["zone_code"] for p in prices]))
    
    columns = [
        "sku", "name", "description", "category_id", "category_name",
        "unit", "unit_quantity", "min_order_qty", "max_order_qty",
        "status", "tags"
    ] + [f"price_{zc}" for zc in sorted(zone_codes)]
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    
    for product in products:
        cat = cat_map.get(product.get("category_id"), {})
        prod_prices = prices_by_product.get(product["id"], {})
        
        row_data = {
            **product,
            "category_name": cat.get("name", ""),
            "tags": ", ".join(product.get("tags", [])),
        }
        
        # Add zone prices
        for zc in sorted(zone_codes):
            price = prod_prices.get(zc)
            row_data[f"price_{zc}"] = f"{price / 100:.2f}" if price else ""
        
        writer.writerow(dict_to_csv_row(row_data, columns))
    
    output.seek(0)
    filename = f"produits_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@export_router.get("/users")
async def export_users(
    request: Request,
    format: ExportFormat = ExportFormat.CSV,
):
    """Export users to CSV"""
    await check_admin(request)
    
    users = await db.users.find({}).sort("created_at", -1).to_list(10000)
    
    columns = [
        "id", "email", "company_name", "contact_name", "siret",
        "phone", "is_admin", "is_active", "created_at"
    ]
    
    output = io.StringIO()
    writer = csv.writer(output, delimiter=';', quoting=csv.QUOTE_MINIMAL)
    writer.writerow(columns)
    
    for user in users:
        # Remove sensitive data
        user_safe = {k: v for k, v in user.items() if k != "password"}
        writer.writerow(dict_to_csv_row(user_safe, columns))
    
    output.seek(0)
    filename = f"utilisateurs_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ============== SUMMARY ENDPOINT ==============

@export_router.get("/summary")
async def get_export_summary(request: Request):
    """Get export options and counts"""
    await check_admin(request)
    
    # Get counts
    orgs_count = await db.orgs.count_documents({})
    apps_count = await db.b2b_applications.count_documents({})
    orders_count = await db.orders.count_documents({})
    tx_count = await db.wallet_ledger.count_documents({})
    audit_count = await db.audit_log.count_documents({})
    products_count = await db.products.count_documents({})
    users_count = await db.users.count_documents({})
    
    return {
        "exports_available": [
            {"type": "organizations", "label": "Organisations", "count": orgs_count, "endpoint": "/api/admin/export/organizations"},
            {"type": "applications", "label": "Demandes d'adhésion", "count": apps_count, "endpoint": "/api/admin/export/applications"},
            {"type": "orders", "label": "Commandes", "count": orders_count, "endpoint": "/api/admin/export/orders"},
            {"type": "transactions", "label": "Transactions", "count": tx_count, "endpoint": "/api/admin/export/transactions"},
            {"type": "audit_log", "label": "Journal d'audit", "count": audit_count, "endpoint": "/api/admin/export/audit-log"},
            {"type": "products", "label": "Produits", "count": products_count, "endpoint": "/api/admin/export/products"},
            {"type": "users", "label": "Utilisateurs", "count": users_count, "endpoint": "/api/admin/export/users"},
        ],
        "formats": ["csv"],
        "filters": {
            "date_from": "YYYY-MM-DD",
            "date_to": "YYYY-MM-DD",
            "status_filter": "Filter by status",
            "org_id": "Filter by organization ID",
        }
    }
