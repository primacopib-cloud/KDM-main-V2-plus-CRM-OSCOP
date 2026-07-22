"""Core admin routes: stats, users, quotes moderation, credits, organizations
listing, vendor alias (split from server.py)."""
import logging
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, HTTPException, Depends, status

from models import (
    UserResponse, QuoteRequestResponse, AdminStats, UserListResponse,
    OrganizationResponse,
)
from db import get_database
from core_deps import get_current_user, get_user_by_id, check_admin

logger = logging.getLogger(__name__)

admin_core_router = APIRouter(prefix="/api")


@admin_core_router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(current_user: dict = Depends(get_current_user)):
    """Get admin dashboard statistics."""
    await check_admin(current_user)
    db = get_database()

    total_users = await db.users.count_documents({})
    total_quotes = await db.quote_requests.count_documents({})
    total_orders = await db.orders.count_documents({})

    pipeline = [{"$group": {"_id": None, "total": {"$sum": "$credits"}}}]
    credits_result = await db.users.aggregate(pipeline).to_list(1)
    total_credits = credits_result[0]["total"] if credits_result else 0

    quotes_pipeline = [{"$group": {"_id": "$status", "count": {"$sum": 1}}}]
    quotes_by_status_list = await db.quote_requests.aggregate(quotes_pipeline).to_list(10)
    quotes_by_status = {q["_id"]: q["count"] for q in quotes_by_status_list}

    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    new_users_this_month = await db.users.count_documents({"created_at": {"$gte": month_start}})
    new_quotes_this_month = await db.quote_requests.count_documents({"created_at": {"$gte": month_start}})

    return AdminStats(
        total_users=total_users,
        total_quotes=total_quotes,
        total_orders=total_orders,
        total_credits_distributed=total_credits,
        quotes_by_status=quotes_by_status,
        new_users_this_month=new_users_this_month,
        new_quotes_this_month=new_quotes_this_month
    )


@admin_core_router.get("/admin/users", response_model=UserListResponse)
async def get_all_users(
    current_user: dict = Depends(get_current_user),
    page: int = 1,
    per_page: int = 20,
    search: str = None
):
    """Get all users (admin only)."""
    await check_admin(current_user)
    db = get_database()

    query = {}
    if search:
        query = {
            "$or": [
                {"email": {"$regex": search, "$options": "i"}},
                {"company_name": {"$regex": search, "$options": "i"}},
                {"contact_name": {"$regex": search, "$options": "i"}}
            ]
        }

    total = await db.users.count_documents(query)
    skip = (page - 1) * per_page

    users = await db.users.find(query).sort("created_at", -1).skip(skip).limit(per_page).to_list(per_page)

    return UserListResponse(
        users=[UserResponse(
            id=u["id"],
            email=u["email"],
            company_name=u["company_name"],
            siret=u["siret"],
            contact_name=u["contact_name"],
            phone=u["phone"],
            subscription=u["subscription"],
            credits=u["credits"],
            is_admin=u.get("is_admin", False),
            created_at=u["created_at"]
        ) for u in users],
        total=total,
        page=page,
        per_page=per_page
    )


@admin_core_router.get("/admin/quotes", response_model=List[QuoteRequestResponse])
async def get_all_quotes(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50
):
    """Get all quote requests (admin only)."""
    await check_admin(current_user)
    db = get_database()

    query = {}
    if status_filter:
        query["status"] = status_filter

    quotes = await db.quote_requests.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [QuoteRequestResponse(**q) for q in quotes]


@admin_core_router.get("/admin/quotes/stats")
async def quote_pipeline_stats(current_user: dict = Depends(get_current_user)):
    """KPIs du pipeline devis (taux de conversion)."""
    await check_admin(current_user)
    db = get_database()
    quotes = await db.quote_requests.find(
        {}, {"_id": 0, "status": 1, "status_history": 1, "created_at": 1}).to_list(2000)
    counts = {"pending": 0, "contacted": 0, "converted": 0, "lost": 0}
    month_start = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    month_iso = month_start.isoformat()
    converted_this_month = 0
    for q in quotes:
        s = q.get("status")
        key = "contacted" if s == "processed" else (s if s in counts else "pending")
        counts[key] += 1
        if key == "converted":
            hist = q.get("status_history") or []
            conv_at = next((h.get("at") for h in reversed(hist) if h.get("to") == "converted"), None)
            if conv_at:
                if conv_at >= month_iso:
                    converted_this_month += 1
            else:
                created = q.get("created_at")
                if created is not None and hasattr(created, "tzinfo"):
                    if created.tzinfo is None:
                        created = created.replace(tzinfo=timezone.utc)
                    if created >= month_start:
                        converted_this_month += 1
    total = len(quotes)
    closed = counts["converted"] + counts["lost"]
    target_doc = await db.system_flags.find_one({"key": "quote_monthly_target"}, {"_id": 0, "target": 1})
    return {"total": total, **counts,
            "conversion_rate": round(counts["converted"] / total * 100, 1) if total else 0,
            "close_rate": round(counts["converted"] / closed * 100, 1) if closed else 0,
            "converted_this_month": converted_this_month,
            "monthly_target": (target_doc or {}).get("target", 0)}


@admin_core_router.get("/admin/quotes/export")
async def export_quotes_csv(current_user: dict = Depends(get_current_user)):
    """Export CSV du pipeline des demandes de devis."""
    await check_admin(current_user)
    db = get_database()
    import csv
    import io
    from fastapi.responses import StreamingResponse
    quotes = await db.quote_requests.find({}, {"_id": 0}).sort("created_at", -1).to_list(1000)
    labels = {"pending": "Nouveau", "processed": "Contacté", "contacted": "Contacté",
              "converted": "Converti", "lost": "Perdu"}
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";")
    w.writerow(["Date", "Société", "Contact", "Email", "Téléphone", "Langue", "Statut", "Note interne", "Relancé le", "Message"])
    for q in quotes:
        created = q.get("created_at")
        w.writerow([
            created.strftime("%d/%m/%Y %H:%M") if hasattr(created, "strftime") else str(created or ""),
            q.get("company", ""),
            f"{q.get('first_name', '')} {q.get('last_name', '')}".strip(),
            q.get("email", ""), f"{q.get('phone_country', '')} {q.get('phone', '')}".strip(),
            (q.get("lang") or "fr").upper(), labels.get(q.get("status"), q.get("status", "")),
            q.get("internal_note", ""), (q.get("followup_sent_at") or "")[:10], (q.get("message") or "").replace("\n", " ")[:300],
        ])
    buf.seek(0)
    return StreamingResponse(
        iter(["\ufeff" + buf.getvalue()]), media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=pipeline-devis.csv"})


@admin_core_router.put("/admin/quotes/{quote_id}/note", response_model=dict)
async def update_quote_note(quote_id: str, body: dict, current_user: dict = Depends(get_current_user)):
    """Note interne équipe sur une demande de devis."""
    await check_admin(current_user)
    db = get_database()
    note = (body.get("note") or "").strip()[:500]
    result = await db.quote_requests.update_one(
        {"id": quote_id},
        {"$set": {"internal_note": note, "note_by": current_user.get("email"),
                  "note_at": datetime.now(timezone.utc).isoformat()}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Demande introuvable")
    return {"ok": True, "note": note}


@admin_core_router.put("/admin/quotes/{quote_id}/status", response_model=dict)
async def update_quote_status(
    quote_id: str,
    new_status: str,
    current_user: dict = Depends(get_current_user)
):
    """Update quote request status (admin only)."""
    await check_admin(current_user)
    db = get_database()

    prev = await db.quote_requests.find_one({"id": quote_id}, {"_id": 0, "status": 1})
    if not prev:
        raise HTTPException(status_code=404, detail="Quote request not found")
    result = await db.quote_requests.update_one(
        {"id": quote_id},
        {"$set": {"status": new_status},
         "$push": {"status_history": {
             "from": prev.get("status"), "to": new_status,
             "by": current_user.get("email"),
             "at": datetime.now(timezone.utc).isoformat()}}}
    )

    if result.modified_count == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Demande non trouvée"
        )

    return {"message": "Statut mis à jour", "status": new_status}


@admin_core_router.put("/admin/users/{user_id}/credits", response_model=dict)
async def admin_update_credits(
    user_id: str,
    amount: int,
    current_user: dict = Depends(get_current_user)
):
    """Update user credits (admin only)."""
    await check_admin(current_user)
    db = get_database()

    user = await get_user_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur non trouvé"
        )

    new_credits = user["credits"] + amount
    if new_credits < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Les crédits ne peuvent pas être négatifs"
        )

    await db.users.update_one(
        {"id": user_id},
        {"$set": {"credits": new_credits, "updated_at": datetime.utcnow()}}
    )

    await db.credits_history.insert_one({
        "id": str(uuid.uuid4()),
        "user_id": user_id,
        "type": "added" if amount > 0 else "used",
        "amount": abs(amount),
        "description": f"Ajusté par admin ({current_user['email']})",
        "created_at": datetime.utcnow()
    })

    logger.info(f"Admin {current_user['email']} updated credits for {user['email']}: {amount}")

    return {"credits": new_credits, "message": f"Crédits mis à jour: {'+' if amount > 0 else ''}{amount}"}


@admin_core_router.get("/admin/organizations", response_model=List[OrganizationResponse])
async def get_all_organizations(
    current_user: dict = Depends(get_current_user),
    status_filter: str = None,
    skip: int = 0,
    limit: int = 50
):
    """Get all organizations (admin only)."""
    await check_admin(current_user)
    db = get_database()

    query = {}
    if status_filter:
        query["status"] = status_filter

    orgs = await db.organizations.find(query).sort("created_at", -1).skip(skip).limit(limit).to_list(limit)
    return [OrganizationResponse(**o) for o in orgs]


@admin_core_router.get("/admin/products/pending")
async def admin_products_pending_alias():
    """Alias for /api/vendor/admin/products/pending"""
    from routes_vendor_admin import admin_list_pending_products
    return await admin_list_pending_products()
