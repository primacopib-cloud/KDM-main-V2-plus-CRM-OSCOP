"""Adaptateur générique pour les apps connectées (auth login → Bearer ou cookie de session).

Ajouter une app = 1 entrée dans GENERIC_APPS + 3 variables .env ({PREFIX}_URL/EMAIL/PASSWORD).
"""
from __future__ import annotations

import os
from typing import Any, Dict, Optional

import httpx

GENERIC_APPS = [
    {
        "name": "oscop-ia-bois",
        "label": "OSCOP IA Bois — Générateur ossature bois",
        "kind": "ia",
        "env_prefix": "IABOIS",
        "token_field": "token",
        "health_path": "/api/health",
        "description": "Générateur IA de maisons ossature bois. Flux à définir (devis, plans).",
    },
    {
        "name": "oscop-ge",
        "label": "O'SCOP GE — Groupement d'Employeurs",
        "kind": "rh",
        "env_prefix": "OSCOPGE",
        "token_field": "access_token",
        "health_path": "/api/auth/me",
        "description": "Groupement d'employeurs coopératif. Flux à définir (mises à disposition, contrats).",
    },
    {
        "name": "coppam",
        "label": "COPPAM — SaaS trésorerie interne",
        "kind": "finance",
        "env_prefix": "COPPAM",
        "token_field": None,  # session cookie
        "health_path": "/api/auth/session",
        "description": "Trésorerie interne COPPAM. Flux à définir (écritures, rapprochements).",
    },
    {
        "name": "crm-ess",
        "label": "CRM ESS — Objectif SCOP",
        "kind": "crm",
        "env_prefix": "CRMESS",
        "token_field": "ws_token",
        "health_path": "/api/health",
        "description": "CRM ESS (dossiers, documents, PDF). Flux à définir (docs, opportunités).",
    },
]


def app_def(name: str) -> Optional[Dict[str, Any]]:
    return next((a for a in GENERIC_APPS if a["name"] == name), None)


def app_config(definition: Dict[str, Any]) -> Dict[str, Any]:
    prefix = definition["env_prefix"]
    base_url = (os.environ.get(f"{prefix}_URL") or "").strip().rstrip("/")
    email = (os.environ.get(f"{prefix}_EMAIL") or "").strip()
    password = (os.environ.get(f"{prefix}_PASSWORD") or "").strip()
    return {
        "base_url": base_url,
        "email": email,
        "password": password,
        "enabled": bool(base_url and email and password),
    }


class GenericAppError(RuntimeError):
    pass


async def request(
    name: str,
    method: str,
    path: str,
    *,
    json_payload: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    form_data: Optional[Dict[str, Any]] = None,
) -> Any:
    """Appel authentifié vers une app générique (Bearer ou cookie de session)."""
    definition = app_def(name)
    if not definition:
        raise GenericAppError(f"Connecteur inconnu: {name}")
    cfg = app_config(definition)
    if not cfg["enabled"]:
        raise GenericAppError(f"Connecteur {name} désactivé : variables {definition['env_prefix']}_* manquantes")

    async with httpx.AsyncClient(timeout=25) as client:
        login = await client.post(
            f"{cfg['base_url']}/api/auth/login",
            json={"email": cfg["email"], "password": cfg["password"]},
        )
        if login.status_code != 200:
            raise GenericAppError(f"{name}: login refusé ({login.status_code})")

        headers = {}
        if definition["token_field"]:
            token = login.json().get(definition["token_field"])
            if not token:
                raise GenericAppError(f"{name}: champ {definition['token_field']} absent du login")
            headers["Authorization"] = f"Bearer {token}"

        resp = await client.request(
            method, f"{cfg['base_url']}{path}",
            headers=headers, json=json_payload, files=files, data=form_data,
        )

    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text[:200]
        raise GenericAppError(f"{name} {method} {path} -> {resp.status_code}: {str(detail)[:250]}")
    try:
        return resp.json()
    except ValueError:
        return resp.text[:300]


async def health(name: str) -> Dict[str, Any]:
    definition = app_def(name)
    if not definition:
        return {"name": name, "status": "ERROR", "error": "Connecteur inconnu"}
    cfg = app_config(definition)
    if not cfg["enabled"]:
        return {"name": name, "status": "DISABLED", "detail": f"Variables {definition['env_prefix']}_* manquantes dans .env"}

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            login = await client.post(
                f"{cfg['base_url']}/api/auth/login",
                json={"email": cfg["email"], "password": cfg["password"]},
            )
            if login.status_code != 200:
                return {"name": name, "status": "ERROR", "error": f"Login refusé ({login.status_code})"}

            headers = {}
            if definition["token_field"]:
                token = login.json().get(definition["token_field"])
                if not token:
                    return {"name": name, "status": "ERROR", "error": f"Champ {definition['token_field']} absent du login"}
                headers["Authorization"] = f"Bearer {token}"

            resp = await client.get(f"{cfg['base_url']}{definition['health_path']}", headers=headers)
            if resp.status_code == 200:
                try:
                    external = resp.json()
                except ValueError:
                    external = {"raw": resp.text[:100]}
                return {"name": name, "status": "OK", "external": external}
            return {"name": name, "status": "ERROR", "error": f"{definition['health_path']} -> {resp.status_code}"}
    except Exception as exc:
        return {"name": name, "status": "ERROR", "error": str(exc)[:300]}
