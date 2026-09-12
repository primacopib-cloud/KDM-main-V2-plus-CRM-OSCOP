"""Convention de financement ponctuel — signature eIDAS des parties + PDF bilingue + vérification publique par QR."""
import logging
import secrets
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from auth import get_current_user_id
from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

financing_contract_router = APIRouter(prefix="/api", tags=["Convention financement"])

db = None


def set_financing_contract_database(database):
    global db
    db = database


class FunderSignBody(BaseModel):
    denomination: str = Field(min_length=2, max_length=200)
    forme_capital: Optional[str] = Field(default=None, max_length=200)
    immatriculation: Optional[str] = Field(default=None, max_length=100)
    adresse: Optional[str] = Field(default=None, max_length=300)
    rep_nom: str = Field(min_length=2, max_length=120)
    rep_qualite: str = Field(min_length=2, max_length=120)
    lu_approuve: bool


class CountersignBody(BaseModel):
    rep_nom: str = Field(min_length=2, max_length=120)
    rep_qualite: str = Field(min_length=2, max_length=120)
    lu_approuve: bool


async def _load_op(fp_id: str) -> dict:
    op = await db.financing_products.find_one({"id": fp_id}, {"_id": 0})
    if not op:
        raise HTTPException(status_code=404, detail="Opération de financement introuvable")
    return op


async def _investor_or_admin(user_id: str) -> dict:
    user = await db.users.find_one({"id": user_id}, {"_id": 0})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur introuvable")
    role = (user.get("role") or "").upper()
    if not (user.get("is_investor") or user.get("is_admin") or role in {"SUPER_ADMIN", "ADMIN"}):
        raise HTTPException(status_code=403, detail="Accès réservé aux investisseurs")
    return user


def _verify_base() -> str:
    import os
    return (os.environ.get("FRONTEND_PUBLIC_URL") or os.environ.get("FRONTEND_URL") or "").rstrip("/")


@financing_contract_router.post("/product-financing/{fp_id}/contract/sign")
async def sign_contract(fp_id: str, body: FunderSignBody, request: Request, user_id: str = Depends(get_current_user_id)):
    """Signature du Financeur (investisseur ayant payé) — remplit son identité dans la convention."""
    user = await _investor_or_admin(user_id)
    op = await _load_op(fp_id)
    if op.get("status") != "PAID":
        raise HTTPException(status_code=400, detail="La convention n'est disponible qu'après paiement de l'opération")
    is_admin = bool(user.get("is_admin")) or (user.get("role") or "").upper() in {"SUPER_ADMIN", "ADMIN"}
    if not is_admin and op.get("paid_by") != user.get("email"):
        raise HTTPException(status_code=403, detail="Seul l'investisseur payeur peut signer cette convention")
    if not body.lu_approuve:
        raise HTTPException(status_code=400, detail="La mention « Lu et approuvé » est obligatoire")
    code = f"FIN-{secrets.token_hex(4).upper()}"
    now = datetime.now(timezone.utc).isoformat()
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "contract.funder": {
            "denomination": body.denomination, "forme_capital": body.forme_capital,
            "immatriculation": body.immatriculation, "adresse": body.adresse,
            "rep_nom": body.rep_nom, "rep_qualite": body.rep_qualite, "email": op.get("paid_by"),
        },
        "contract.signatures.investor": {
            "nom": body.rep_nom, "qualite": body.rep_qualite, "signed_at": now,
            "ip": request.client.host if request.client else "", "verification_code": code,
            "lu_approuve": True,
        },
        "contract.updated_at": now,
    }})
    return {"ok": True, "verification_code": code}


@financing_contract_router.post("/product-financing/{fp_id}/contract/countersign")
async def countersign_contract(fp_id: str, body: CountersignBody, request: Request, admin: dict = Depends(require_admin)):
    """Contresignature O'SCOP (Débiteur) par un administrateur."""
    op = await _load_op(fp_id)
    if op.get("status") != "PAID":
        raise HTTPException(status_code=400, detail="Opération non payée")
    if not body.lu_approuve:
        raise HTTPException(status_code=400, detail="La mention « Lu et approuvé » est obligatoire")
    code = f"OSC-{secrets.token_hex(4).upper()}"
    now = datetime.now(timezone.utc).isoformat()
    await db.financing_products.update_one({"id": fp_id}, {"$set": {
        "contract.signatures.oscop": {
            "nom": body.rep_nom, "qualite": body.rep_qualite, "signed_at": now,
            "ip": request.client.host if request.client else "", "verification_code": code,
            "lu_approuve": True, "signed_by": admin.get("email"),
        },
        "contract.updated_at": now,
    }})
    op = await _load_op(fp_id)
    if (op.get("contract") or {}).get("signatures", {}).get("investor"):
        try:
            await _email_signed_contract(op, admin.get("email"))
        except Exception as exc:
            logger.warning("Email convention signée %s : %s", fp_id, exc)
    return {"ok": True, "verification_code": code}


async def _email_signed_contract(op: dict, admin_email: str | None):
    """Envoie le PDF intégralement signé aux deux parties (Financeur + O'SCOP)."""
    import base64
    from brevo_service import send_email
    from financing_contract import build_financing_contract_pdf
    pdf = build_financing_contract_pdf(op, lang="fr", verify_base=_verify_base())
    att = [{"content": base64.b64encode(pdf).decode(),
            "name": f"convention-financement-{op.get('reference', op['id'][:8])}-signee.pdf"}]
    funder_email = ((op.get("contract") or {}).get("funder") or {}).get("email") or op.get("paid_by")
    verify_url = f"{_verify_base()}/verifier-financement/{op['id']}"
    html = (f"<p>Bonjour,</p><p>La <b>convention de financement ponctuel {op.get('reference')}</b> "
            f"(« {op.get('name')} ») est désormais <b>signée par les deux parties</b> (Financeur et O'SCOP).</p>"
            f"<p>Vous trouverez ci-joint l'exemplaire PDF signé, portant les codes de vérification et le QR code d'authenticité.</p>"
            f"<p>Vérification publique : <a href=\"{verify_url}\">{verify_url}</a></p>"
            f"<p>Cordialement,<br/><b>SCIC SAS OBJECTIF SCOP OUTREMER</b></p>")
    subject = f"Convention {op.get('reference')} signée par les deux parties"
    for to in filter(None, {funder_email, admin_email, "contact@objectifscopoutremer.com"}):
        await send_email(to_email=to, to_name=None, subject=subject, html_content=html,
                         tags=["financing-contract-signed"], attachments=att)


@financing_contract_router.get("/product-financing/{fp_id}/contract.pdf")
async def contract_pdf(fp_id: str, lang: str = "fr", user_id: str = Depends(get_current_user_id)):
    """PDF de la convention (FR/EN), rempli dynamiquement — investisseur payeur ou admin."""
    user = await _investor_or_admin(user_id)
    op = await _load_op(fp_id)
    is_admin = bool(user.get("is_admin")) or (user.get("role") or "").upper() in {"SUPER_ADMIN", "ADMIN"}
    if not is_admin and op.get("paid_by") != user.get("email"):
        raise HTTPException(status_code=403, detail="Accès réservé à l'investisseur payeur")
    from financing_contract import build_financing_contract_pdf
    pdf = build_financing_contract_pdf(op, lang=lang, verify_base=_verify_base())
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="convention-financement-{op.get("reference", fp_id[:8])}-{lang}.pdf"'})


@financing_contract_router.get("/public/financing-contract/verify/{fp_id}")
async def verify_contract(fp_id: str):
    """Vérification publique (QR code) : statut des signatures, sans données financières."""
    op = await _load_op(fp_id)
    contract = op.get("contract") or {}
    sigs = contract.get("signatures") or {}
    def _s(s):
        return {"nom": s.get("nom"), "qualite": s.get("qualite"), "signed_at": s.get("signed_at"),
                "verification_code": s.get("verification_code")} if s else None
    return {
        "reference": op.get("reference"),
        "objet": op.get("name"),
        "debiteur": "SCIC SAS OBJECTIF SCOP OUTREMER (O'SCOP) — SIRET 903 459 139 00015",
        "financeur": (contract.get("funder") or {}).get("denomination"),
        "signature_financeur": _s(sigs.get("investor")),
        "signature_oscop": _s(sigs.get("oscop")),
        "fully_signed": bool(sigs.get("investor") and sigs.get("oscop")),
    }
