"""HTTP client for the external `finance-api` microservice.

The bridge runs *inside* the KDM backend (FastAPI) but every call hops to the
isolated `finance-api` service over HTTP. This file is intentionally small and
free of FastAPI deps so it stays unit-testable on its own.

Auth flow:
  • finance-api uses OAuth2 password grant (`POST /auth/token`) → JWT
  • This client logs in lazily with the service-account credentials
    (env `FINANCE_API_EMAIL` / `FINANCE_API_PASSWORD`) and caches the JWT
    in memory. On a 401 we drop the cached token and retry once.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class FinanceExternalError(Exception):
    """Raised for transport / business errors from the finance-api."""

    def __init__(self, message: str, *, status_code: Optional[int] = None, body: Any = None) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.body = body


class FinanceClientConfig:
    def __init__(self) -> None:
        self.base_url: str = (os.environ.get("FINANCE_API_URL") or "").strip().rstrip("/")
        self.email: str = (os.environ.get("FINANCE_API_EMAIL") or "").strip()
        self.password: str = (os.environ.get("FINANCE_API_PASSWORD") or "").strip()
        self.timeout_seconds: int = int(os.environ.get("FINANCE_API_TIMEOUT_SECONDS", "20"))

    @property
    def enabled(self) -> bool:
        return bool(self.base_url and self.email and self.password)


class FinanceExternalClient:
    """Synchronous httpx wrapper. One JWT cached at process level."""

    _token: Optional[str] = None
    _lock = threading.Lock()

    def __init__(self) -> None:
        self.config = FinanceClientConfig()

    # ---------------- low-level HTTP ----------------

    def _login(self) -> str:
        if not self.config.enabled:
            raise FinanceExternalError(
                "FINANCE_API_URL / FINANCE_API_EMAIL / FINANCE_API_PASSWORD non configurés"
            )
        url = f"{self.config.base_url}/auth/token"
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                resp = client.post(
                    url,
                    data={"username": self.config.email, "password": self.config.password},
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
            if not resp.is_success:
                raise FinanceExternalError(
                    f"Login finance-api échoué (HTTP {resp.status_code})",
                    status_code=resp.status_code,
                    body=_safe_body(resp),
                )
            token = resp.json().get("access_token")
            if not token:
                raise FinanceExternalError("Login finance-api: pas de access_token dans la réponse")
            return token
        except httpx.HTTPError as exc:
            raise FinanceExternalError(f"Impossible de joindre finance-api: {exc}") from exc

    def _get_token(self, force_refresh: bool = False) -> str:
        with self._lock:
            if force_refresh or not FinanceExternalClient._token:
                FinanceExternalClient._token = self._login()
            return FinanceExternalClient._token

    def _request(
        self,
        method: str,
        path: str,
        *,
        json_payload: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        _retried: bool = False,
    ) -> Dict[str, Any]:
        if not self.config.enabled:
            raise FinanceExternalError(
                "Finance bridge non configuré (FINANCE_API_URL vide)"
            )
        url = f"{self.config.base_url}{path}"
        token = self._get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                resp = client.request(method, url, json=json_payload, params=params, headers=headers)
            if resp.status_code == 401 and not _retried:
                logger.info("finance-api 401 — refresh token + retry once")
                self._get_token(force_refresh=True)
                return self._request(method, path, json_payload=json_payload, params=params, _retried=True)
            body = _safe_body(resp)
            if not resp.is_success:
                raise FinanceExternalError(
                    f"finance-api {method} {path} → HTTP {resp.status_code}: {_extract_detail(body)}",
                    status_code=resp.status_code,
                    body=body,
                )
            return body if isinstance(body, dict) else {"data": body}
        except httpx.HTTPError as exc:
            raise FinanceExternalError(f"Erreur réseau finance-api: {exc}") from exc

    # ---------------- high-level operations ----------------

    def health(self) -> Dict[str, Any]:
        """Health is unauthenticated — call it directly."""
        if not self.config.enabled:
            raise FinanceExternalError("Finance bridge non configuré")
        url = f"{self.config.base_url}/health"
        try:
            with httpx.Client(timeout=self.config.timeout_seconds) as client:
                resp = client.get(url)
            body = _safe_body(resp)
            if not resp.is_success:
                raise FinanceExternalError(
                    f"finance-api /health HTTP {resp.status_code}", status_code=resp.status_code, body=body,
                )
            return body if isinstance(body, dict) else {"data": body}
        except httpx.HTTPError as exc:
            raise FinanceExternalError(f"Erreur réseau finance-api: {exc}") from exc

    def create_party(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/parties", json_payload=payload)

    def find_party_by_external_id(self, external_customer_id: str) -> Optional[Dict[str, Any]]:
        body = self._request("GET", "/parties", params={"q": external_customer_id, "limit": 5})
        items = body.get("data") if isinstance(body, dict) else body
        if not items:
            return None
        for item in items if isinstance(items, list) else []:
            if (item or {}).get("external_customer_id") == external_customer_id:
                return item
        return None

    def create_receivable(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/receivables", json_payload=payload)

    def create_payment(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/payments", json_payload=payload)

    def create_installment_plan(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/installment-plans", json_payload=payload)

    def create_sepa_mandate(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        return self._request("POST", "/sepa/mandates", json_payload=payload)

    def activate_sepa_mandate(self, mandate_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/sepa/mandates/{mandate_id}/activate")


# ---------------- helpers ----------------

def _safe_body(resp: httpx.Response) -> Any:
    try:
        return resp.json()
    except Exception:
        return {"text": resp.text}


def _extract_detail(body: Any) -> str:
    if isinstance(body, dict):
        d = body.get("detail")
        if isinstance(d, str):
            return d
        if d is not None:
            return str(d)
    return str(body)[:300]
