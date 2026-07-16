"""Adaptateur CRM Objectif SCOP Outremer (GED ESS + paiements).

Contrat réel vérifié :
  POST /api/auth/login              -> {access_token, ...} (JWT ~1h)
  GET  /api/ged/health              -> {status: healthy, ...}
  GET  /api/ged/categories          -> {categories: [...]}
  POST /api/ged/documents/upload    -> multipart (file + champs Form)
  POST /api/paiements               -> {id, montant, moyen_paiement, statut, reference}
  DELETE /api/paiements/{id}
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class OscopCrmError(RuntimeError):
    def __init__(self, message: str, *, status_code: Optional[int] = None, body: Any = None):
        super().__init__(message)
        self.status_code = status_code
        self.body = body


def oscop_config() -> Dict[str, Any]:
    base_url = (os.environ.get("OSCOP_CRM_URL") or "").strip().rstrip("/")
    email = (os.environ.get("OSCOP_CRM_EMAIL") or "").strip()
    password = (os.environ.get("OSCOP_CRM_PASSWORD") or "").strip()
    timeout = float(os.environ.get("OSCOP_CRM_TIMEOUT_SECONDS", "25"))
    return {
        "base_url": base_url,
        "email": email,
        "password": password,
        "timeout": timeout,
        "enabled": bool(base_url and email and password),
    }


_token: Optional[str] = None
_lock = threading.Lock()


async def _login(cfg: Dict[str, Any]) -> str:
    global _token
    async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
        resp = await client.post(
            f"{cfg['base_url']}/api/auth/login",
            json={"email": cfg["email"], "password": cfg["password"]},
        )
    if resp.status_code != 200:
        raise OscopCrmError(
            f"Login CRM refusé ({resp.status_code})", status_code=resp.status_code, body=_safe_body(resp)
        )
    token = resp.json().get("access_token")
    if not token:
        raise OscopCrmError("Login CRM: access_token absent de la réponse")
    with _lock:
        _token = token
    return token


async def _request(
    method: str,
    path: str,
    *,
    json_payload: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, Any]] = None,
    _retried: bool = False,
) -> Any:
    cfg = oscop_config()
    if not cfg["enabled"]:
        raise OscopCrmError("Connecteur O'SCOP désactivé : OSCOP_CRM_URL / EMAIL / PASSWORD manquants dans .env")

    global _token
    token = _token or await _login(cfg)
    headers = {"Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient(timeout=cfg["timeout"]) as client:
        resp = await client.request(
            method,
            f"{cfg['base_url']}{path}",
            headers=headers,
            json=json_payload,
            files=files,
            data=form_data,
            params=params,
        )

    if resp.status_code == 401 and not _retried:
        with _lock:
            _token = None
        return await _request(
            method, path, json_payload=json_payload, files=files,
            form_data=form_data, params=params, _retried=True,
        )

    if resp.status_code >= 400:
        raise OscopCrmError(
            f"CRM {method} {path} -> {resp.status_code}: {_extract_detail(_safe_body(resp))}",
            status_code=resp.status_code,
            body=_safe_body(resp),
        )
    return _safe_body(resp)


def _safe_body(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except ValueError:
        return resp.text[:300]


def _extract_detail(body: Any) -> str:
    if isinstance(body, dict):
        return str(body.get("detail") or body)[:300]
    return str(body)[:300]


# ---------------------------------------------------------------------------
# Opérations métier
# ---------------------------------------------------------------------------

async def health() -> Any:
    return await _request("GET", "/api/ged/health")


async def ged_categories() -> Any:
    return await _request("GET", "/api/ged/categories")


async def upload_document(
    *,
    filename: str,
    content: bytes,
    content_type: str,
    categorie: str = "factures",
    description: str = "",
    tags: str = "kdmarche",
) -> Any:
    files = {"file": (filename, content, content_type)}
    form = {"categorie": categorie, "description": description, "tags": tags}
    return await _request("POST", "/api/ged/documents/upload", files=files, form_data=form)


async def create_paiement(payload: Dict[str, Any]) -> Any:
    return await _request("POST", "/api/paiements", json_payload=payload)
