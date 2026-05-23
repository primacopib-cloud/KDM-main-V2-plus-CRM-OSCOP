"""
Client de connexion GED ESS externe.

Ce module connecte le code KDMARCHE / O'SCOP existant au microservice GED ESS
industrialisable : PostgreSQL + S3/R2 + audit probant + PDF institutionnels.

Le code existant conserve sa GED MongoDB interne sous /api/ged.
Ce client ajoute une couche de synchronisation vers le microservice GED externe.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional

import httpx


class GedExternalError(RuntimeError):
    """Erreur de communication avec le microservice GED externe."""


@dataclass(frozen=True)
class GedExternalConfig:
    base_url: str
    api_token: Optional[str]
    webhook_secret: Optional[str]
    timeout_seconds: float = 20.0

    @classmethod
    def from_env(cls) -> "GedExternalConfig":
        return cls(
            base_url=(os.getenv("GED_ESS_API_URL") or os.getenv("GED_API_URL") or "").rstrip("/"),
            api_token=os.getenv("GED_ESS_API_TOKEN") or os.getenv("GED_API_TOKEN"),
            webhook_secret=os.getenv("GED_ESS_WEBHOOK_SECRET") or os.getenv("GED_WEBHOOK_SECRET"),
            timeout_seconds=float(os.getenv("GED_ESS_TIMEOUT_SECONDS", "20")),
        )

    @property
    def enabled(self) -> bool:
        return bool(self.base_url)


class GedExternalClient:
    """Client async minimal et robuste pour le microservice GED ESS."""

    def __init__(self, config: Optional[GedExternalConfig] = None):
        self.config = config or GedExternalConfig.from_env()

    def _headers(self, payload: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.config.api_token:
            headers["Authorization"] = f"Bearer {self.config.api_token}"
        if payload is not None and self.config.webhook_secret:
            raw = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
            signature = hmac.new(
                self.config.webhook_secret.encode("utf-8"),
                raw,
                hashlib.sha256,
            ).hexdigest()
            headers["X-GED-ESS-Signature"] = signature
        return headers

    async def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.config.enabled:
            raise GedExternalError("GED_ESS_API_URL non configurée")

        url = f"{self.config.base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                response = await client.request(
                    method,
                    url,
                    json=payload,
                    headers=self._headers(payload),
                )
        except httpx.HTTPError as exc:
            raise GedExternalError(f"GED externe inaccessible: {exc}") from exc

        if response.status_code >= 400:
            raise GedExternalError(f"GED externe erreur {response.status_code}: {response.text[:800]}")

        if not response.content:
            return {"status": "OK"}
        try:
            return response.json()
        except ValueError:
            return {"status": "OK", "raw": response.text}

    async def health(self) -> Dict[str, Any]:
        return await self._request("GET", "/health")

    async def list_scopes(self) -> Dict[str, Any] | list:
        return await self._request("GET", "/activity-scopes")

    async def create_document(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/documents", payload)

    async def generate_pdf(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._request("POST", "/pdf/generate", payload)

    async def push_to_external_connector(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Déclenche un push depuis le microservice GED vers un connecteur aval si disponible."""
        return await self._request("POST", "/connectors/push", payload)


# -----------------------------
# Mapping métier KDM/O'SCOP -> GED ESS
# -----------------------------

SCOPE_BY_SOURCE = {
    "coppam": "COPPAM",
    "oscop": "OSCOP",
    "o_scop": "OSCOP",
    "kdmarche": "KDMARCHE",
    "lolodrive": "KDMARCHE",
    "fogedom": "FOGEDOM",
    "ftpe": "FTPE",
    "logiscop": "LOGISCOP",
    "batiscop": "BATISCOP",
    "general": "GENERAL",
}

PDF_TEMPLATE_BY_SCOPE = {
    "COPPAM": "COPPAM_ATTESTATION_CAPACITE",
    "OSCOP": "OSCOP_CONTRAT_COOPERATIF",
    "KDMARCHE": "KDMARCHE_APPEL_CONTRIBUTION",
    "FOGEDOM": "FOGEDOM_CONVENTION_FINANCEMENT",
    "GENERAL": "GENERIQUE_ESS",
}


def resolve_scope_code(value: Optional[str]) -> str:
    if not value:
        return "GENERAL"
    normalized = value.strip().lower().replace("'", "").replace("-", "_")
    return SCOPE_BY_SOURCE.get(normalized, value.strip().upper())


def build_ged_business_metadata(*, source: str, source_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "source_system": "KDM_MAIN_V2_PLUS_CRM_OSCOP",
        "source": source,
        "source_id": source_id,
        "synced_at": datetime.utcnow().isoformat(),
        "payload": payload,
    }
