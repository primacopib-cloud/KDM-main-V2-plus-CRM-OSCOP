"""Client O'SCOP Outremer — dépôt de demandes publiques (Communityplace Demandes) + gestion des tarifs."""
import logging
import os
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)


def _base() -> str:
    return (os.environ.get("GEDESS_BASE_URL") or "").rstrip("/")


def is_oscop_configured() -> bool:
    return bool(_base() and os.environ.get("GEDESS_EMAIL") and os.environ.get("GEDESS_PASSWORD"))


async def _admin_token(client: httpx.AsyncClient) -> str:
    r = await client.post(f"{_base()}/api/auth/login", json={
        "email": os.environ["GEDESS_EMAIL"],
        "password": os.environ["GEDESS_PASSWORD"],
    })
    r.raise_for_status()
    token = r.json().get("access_token") or r.json().get("token")
    if not token:
        raise RuntimeError("O'SCOP: token absent de la réponse de login")
    return token


async def push_demande_publique(nom: str, email: str, prenom: str = "", telephone: str = "",
                                entreprise: str = "", message: str = "",
                                type_demande: str = "standard") -> dict:
    """Dépose une demande publique sur la plateforme O'SCOP (endpoint public)."""
    async with httpx.AsyncClient(timeout=25) as client:
        r = await client.post(f"{_base()}/api/demandes-publiques", json={
            "nom": nom, "prenom": prenom, "email": email, "telephone": telephone,
            "entreprise": entreprise, "message": message, "type_demande": type_demande,
        })
        r.raise_for_status()
        return r.json()


async def push_quote_to_oscop(database, quote_id: str) -> None:
    """Tâche de fond : pousse une demande de devis vers Communityplace Demandes."""
    quote = await database.quote_requests.find_one({"id": quote_id})
    if not quote or not is_oscop_configured():
        return
    contact = (quote.get("contact_name") or "").strip()
    parts = contact.split(" ", 1)
    prenom, nom = (parts[0], parts[1]) if len(parts) == 2 else ("", contact or quote.get("company", ""))
    message = f"[Communityplace — Demande de devis] Offre : {quote.get('plan') or 'non précisée'}. {quote.get('message') or ''}".strip()
    update = {"oscop_pushed_at": datetime.now(timezone.utc).isoformat()}
    try:
        result = await push_demande_publique(
            nom=nom or contact, prenom=prenom, email=quote.get("email", ""),
            telephone=quote.get("phone", ""), entreprise=quote.get("company", ""),
            message=message,
        )
        update.update({"oscop_status": "PUSHED",
                       "oscop_demande_id": result.get("id") or (result.get("demande") or {}).get("id")})
        logger.info("Devis %s poussé vers Communityplace Demandes (%s)", quote_id, update.get("oscop_demande_id"))
    except Exception as exc:
        update.update({"oscop_status": "ERROR", "oscop_error": str(exc)[:300]})
        logger.warning("Push devis %s vers O'SCOP échoué : %s", quote_id, exc)
    await database.quote_requests.update_one({"id": quote_id}, {"$set": update})


# ===================== Tarifs (proxy admin distant) =====================

async def get_remote_tarifs() -> dict:
    async with httpx.AsyncClient(timeout=25) as client:
        token = await _admin_token(client)
        headers = {"Authorization": f"Bearer {token}"}
        tarifs = (await client.get(f"{_base()}/api/admin/tarifs-demandes", headers=headers)).json()
        achat = (await client.get(f"{_base()}/api/achats/tarif-achat", headers=headers)).json()
        return {"tarifs": tarifs, "tarif_achat": achat}


async def update_remote_tarif(tarif_id: str, payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=25) as client:
        token = await _admin_token(client)
        r = await client.put(f"{_base()}/api/admin/tarifs-demandes/{tarif_id}", json=payload,
                             headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.json()


async def create_remote_tarif(payload: dict) -> dict:
    async with httpx.AsyncClient(timeout=25) as client:
        token = await _admin_token(client)
        r = await client.post(f"{_base()}/api/admin/tarifs-demandes", json=payload,
                              headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.json()


async def toggle_remote_tarif(tarif_id: str, is_active: bool) -> dict:
    async with httpx.AsyncClient(timeout=25) as client:
        token = await _admin_token(client)
        r = await client.patch(f"{_base()}/api/admin/tarifs-demandes/{tarif_id}/toggle",
                               json={"is_active": is_active},
                               headers={"Authorization": f"Bearer {token}"})
        r.raise_for_status()
        return r.json()
