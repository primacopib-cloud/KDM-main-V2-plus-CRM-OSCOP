"""Lightweight HTTP connectors to GED ESS and CRM KDM (sortants).

These connectors are non-blocking on missing config: if the env var is unset,
they return a clear `disabled=True` envelope so calling routes can degrade
gracefully without crashing.
"""
from __future__ import annotations

from typing import Any, Dict

import httpx

from app.core.config import settings


def _post(url: str, token: str, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    if not url:
        return {"disabled": True, "reason": "URL non configurée"}
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    target = url.rstrip("/") + path
    try:
        with httpx.Client(timeout=15.0) as client:
            resp = client.post(target, json=payload, headers=headers)
            try:
                body = resp.json()
            except Exception:
                body = {"text": resp.text}
            return {"status_code": resp.status_code, "ok": resp.is_success, "body": body, "url": target}
    except httpx.HTTPError as exc:
        return {"ok": False, "error": str(exc), "url": target}


# ---------- GED ----------

def push_invoice_to_ged(*, party: Dict[str, Any], receivable: Dict[str, Any], payment: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "title": f"Facture {receivable.get('reference') or receivable.get('id')}",
        "source": "finance",
        "entity_id": receivable.get("id"),
        "context": {"party": party, "receivable": receivable, "payment": payment},
        "template_code": "FINANCE_INVOICE",
    }
    return _post(settings.GED_ESS_API_URL, settings.GED_ESS_API_TOKEN, "/pdf/generate", payload)


# ---------- CRM ----------

def push_receivable_to_crm(*, party: Dict[str, Any], receivable: Dict[str, Any]) -> Dict[str, Any]:
    payload = {
        "party": party,
        "receivable": receivable,
        "event": "RECEIVABLE_CREATED",
    }
    return _post(settings.CRM_API_URL, settings.CRM_API_TOKEN, "/api/finance/inbound/receivable", payload)
