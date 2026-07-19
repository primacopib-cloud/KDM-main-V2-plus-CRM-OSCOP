"""Client léger pour la GEDESS réelle (objectifscopoutremer.com) — login + upload."""
import os
import logging

import httpx

logger = logging.getLogger(__name__)


def is_gedess_configured() -> bool:
    return bool(os.environ.get("GEDESS_BASE_URL") and os.environ.get("GEDESS_EMAIL") and os.environ.get("GEDESS_PASSWORD"))


async def _login(client: httpx.AsyncClient, base: str) -> str:
    r = await client.post(f"{base}/api/auth/login", json={
        "email": os.environ["GEDESS_EMAIL"],
        "password": os.environ["GEDESS_PASSWORD"],
    })
    r.raise_for_status()
    token = r.json().get("access_token") or r.json().get("token")
    if not token:
        raise RuntimeError("GEDESS: token absent de la réponse de login")
    return token


async def gedess_upload_file(
    filename: str, content: bytes, categorie: str = "rapport",
    description: str = "", tags: str = "", mime_type: str = "text/csv",
) -> dict:
    """Upload un fichier dans la GEDESS. Retourne le document créé."""
    base = os.environ["GEDESS_BASE_URL"].rstrip("/")
    async with httpx.AsyncClient(timeout=30) as client:
        token = await _login(client, base)
        data = {"categorie": categorie}
        if description:
            data["description"] = description
        if tags:
            data["tags"] = tags
        r = await client.post(
            f"{base}/api/ged/upload",
            headers={"Authorization": f"Bearer {token}"},
            files={"file": (filename, content, mime_type)},
            data=data,
        )
        r.raise_for_status()
        doc = r.json()
        logger.info("GEDESS upload OK: %s (%s)", doc.get("id"), filename)
        return doc
