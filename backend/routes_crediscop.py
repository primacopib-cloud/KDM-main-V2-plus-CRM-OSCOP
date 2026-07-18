"""CREDI'SCOP — solde unifié selon le profil connecté (badge barre de navigation)."""
import logging

from fastapi import APIRouter, Depends

from auth import get_current_user_id

logger = logging.getLogger(__name__)
crediscop_router = APIRouter(prefix="/api/me", tags=["CREDI'SCOP"])

db = None


def set_crediscop_database(database) -> None:
    global db
    db = database


@crediscop_router.get("/crediscop")
async def my_crediscop(user_id: str = Depends(get_current_user_id)):
    """Solde CREDI'SCOP du profil connecté : crédits IA vendeur, ou crédits du wallet org/perso."""
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        return {"balance": None}

    if user.get("role") == "vendor" and user.get("vendor_id"):
        vendor = await db.vendors.find_one({"id": user["vendor_id"]}, {"_id": 0, "credits": 1})
        if vendor is not None:
            return {"balance": int(vendor.get("credits") or 0), "kind": "vendor",
                    "href": "/espace-vendeur", "label": "CREDI'SCOP"}

    membership = await db.org_memberships.find_one({"user_id": user_id}, {"_id": 0, "org_id": 1})
    if membership:
        wallet = await db.wallets.find_one({"org_id": membership["org_id"]}, {"_id": 0, "balance_credits": 1})
        if wallet is not None:
            return {"balance": int(wallet.get("balance_credits") or 0), "kind": "org",
                    "href": "/wallet", "label": "CREDI'SCOP"}

    wallet = await db.wallets.find_one({"user_id": user_id}, {"_id": 0, "balance_credits": 1})
    if wallet is not None:
        return {"balance": int(wallet.get("balance_credits") or 0), "kind": "user",
                "href": "/wallet", "label": "CREDI'SCOP"}
    return {"balance": 0, "kind": "user", "href": "/wallet", "label": "CREDI'SCOP"}


async def _collect_statement(user_id: str) -> dict:
    """Relevé unifié : crédits IA vendeur + wallet org + crédits personnels."""
    from datetime import datetime, timezone

    user = await db.users.find_one({"id": user_id}, {"_id": 0}) or {}
    balances, entries = [], []

    if user.get("vendor_id"):
        vendor = await db.vendors.find_one({"id": user["vendor_id"]}, {"_id": 0, "credits": 1})
        if vendor is not None:
            balances.append({"kind": "vendor", "balance": int(vendor.get("credits") or 0)})
            txs = await db.credit_transactions.find(
                {"vendor_id": user["vendor_id"]}, {"_id": 0}).sort("at", -1).to_list(60)
            for t in txs:
                entries.append({"at": t.get("at"), "source": "vendor",
                                "label": t.get("detail") or t.get("action", ""),
                                "amount": -int(t.get("cost") or 0),
                                "balance_after": t.get("balance_after")})

    membership = await db.org_memberships.find_one({"user_id": user_id}, {"_id": 0, "org_id": 1})
    if membership:
        wallet = await db.wallets.find_one({"org_id": membership["org_id"]}, {"_id": 0, "balance_credits": 1})
        if wallet is not None:
            balances.append({"kind": "org", "balance": int(wallet.get("balance_credits") or 0)})
            ledger = await db.wallet_ledger.find(
                {"org_id": membership["org_id"]}, {"_id": 0}).sort("created_at", -1).to_list(60)
            for entry in ledger:
                sign = 1 if entry.get("direction") == "CREDIT" else -1
                entries.append({"at": str(entry.get("created_at") or ""), "source": "org",
                                "label": entry.get("reason_code", ""),
                                "amount": sign * int(entry.get("amount_credits") or 0),
                                "balance_after": entry.get("balance_after", "")})

    personal = await db.wallets.find_one({"user_id": user_id}, {"_id": 0, "balance_credits": 1})
    history = await db.credit_history.find({"user_id": user_id}, {"_id": 0}).sort("created_at", -1).to_list(60)
    if personal is not None or history:
        balances.append({"kind": "user", "balance": int((personal or {}).get("balance_credits") or 0)})
        for h in history:
            entries.append({"at": h.get("created_at"), "source": "user",
                            "label": h.get("reason", ""), "amount": int(h.get("amount") or 0),
                            "balance_after": h.get("balance_after")})

    entries.sort(key=lambda e: str(e.get("at") or ""), reverse=True)
    return {
        "holder": user.get("contact_name") or user.get("email", ""),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "balances": balances,
        "entries": entries,
    }


@crediscop_router.get("/crediscop/statement")
async def my_crediscop_statement(user_id: str = Depends(get_current_user_id)):
    """Relevé CREDI'SCOP unifié (JSON)."""
    return await _collect_statement(user_id)


@crediscop_router.get("/crediscop/statement.pdf")
async def my_crediscop_statement_pdf(user_id: str = Depends(get_current_user_id)):
    """Relevé CREDI'SCOP unifié téléchargeable (PDF)."""
    from fastapi.responses import Response
    from pdf_crediscop_statement import generate_crediscop_statement_pdf

    statement = await _collect_statement(user_id)
    pdf = generate_crediscop_statement_pdf(statement)
    return Response(content=pdf, media_type="application/pdf", headers={
        "Content-Disposition": 'attachment; filename="releve-crediscop.pdf"'})
