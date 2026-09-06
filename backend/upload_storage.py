"""Stockage persistant des fichiers uploadés — Emergent Object Storage.

Les nouveaux uploads partent dans le bucket (préfixe kdmarche/uploads/…) et sont
servis par GET /api/uploads/{path} (fallback disque local pour les anciens fichiers).
"""
from __future__ import annotations

import logging
import os
import threading

import requests
from starlette.concurrency import run_in_threadpool

logger = logging.getLogger(__name__)

STORAGE_BASE = (os.environ.get("INTEGRATION_PROXY_URL") or "").strip() or "https://integrations.emergentagent.com"
STORAGE_URL = STORAGE_BASE.rstrip("/") + "/objstore/api/v1/storage"
EMERGENT_KEY = os.environ.get("EMERGENT_LLM_KEY")
APP_NAME = "kdmarche"

_storage_key = None
_lock = threading.Lock()

MIME_TYPES = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "gif": "image/gif",
    "webp": "image/webp", "svg": "image/svg+xml", "pdf": "application/pdf",
    "heic": "image/heic", "csv": "text/csv", "txt": "text/plain",
    "mp4": "video/mp4", "webm": "video/webm", "mp3": "audio/mpeg",
}


def mime_for_ext(ext: str) -> str:
    return MIME_TYPES.get((ext or "").lower().lstrip("."), "application/octet-stream")


def _init_storage(force: bool = False) -> str:
    global _storage_key
    with _lock:
        if _storage_key and not force:
            return _storage_key
        resp = requests.post(f"{STORAGE_URL}/init", json={"emergent_key": EMERGENT_KEY}, timeout=30)
        resp.raise_for_status()
        _storage_key = resp.json()["storage_key"]
        return _storage_key


def _put_object_sync(path: str, data: bytes, content_type: str) -> dict:
    key = _init_storage()
    resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                        headers={"X-Storage-Key": key, "Content-Type": content_type},
                        data=data, timeout=120)
    if resp.status_code == 404:
        key = _init_storage(force=True)
        resp = requests.put(f"{STORAGE_URL}/objects/{path}",
                            headers={"X-Storage-Key": key, "Content-Type": content_type},
                            data=data, timeout=120)
    resp.raise_for_status()
    return resp.json()


def _get_object_sync(path: str) -> tuple[bytes, str]:
    key = _init_storage()
    resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    if resp.status_code == 404:
        key = _init_storage(force=True)
        resp = requests.get(f"{STORAGE_URL}/objects/{path}", headers={"X-Storage-Key": key}, timeout=60)
    resp.raise_for_status()
    return resp.content, resp.headers.get("Content-Type", "application/octet-stream")


async def save_upload(relative_path: str, data: bytes, content_type: str) -> str:
    """Stocke `data` sous kdmarche/uploads/{relative_path} et renvoie l'URL relative /api/uploads/…"""
    relative_path = relative_path.lstrip("/")
    result = await run_in_threadpool(
        _put_object_sync, f"{APP_NAME}/uploads/{relative_path}", data, content_type)
    logger.info("Upload objstore : %s (%s octets)", result.get("path"), result.get("size"))
    return f"/api/uploads/{relative_path}"


async def fetch_upload(relative_path: str) -> tuple[bytes, str]:
    relative_path = relative_path.lstrip("/")
    return await run_in_threadpool(_get_object_sync, f"{APP_NAME}/uploads/{relative_path}")
