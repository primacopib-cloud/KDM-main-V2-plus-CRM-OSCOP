"""Ledger service — append-only chained financial journal (audit probant).

Design :
  • Every business-relevant mutation (receivable created, payment succeeded,
    refund, mandate activation, installment paid, …) calls `record()`.
  • Entries are NEVER updated nor deleted. Only INSERT.
  • Each row carries `previous_hash` (sha256 of previous row's `entry_hash`)
    plus its own `entry_hash` = sha256(canonical_json_of_payload + previous_hash).
  • Genesis entry: previous_hash = '0'*64.
  • `verify_chain()` re-computes the chain and returns the first broken row.

The journal is therefore tamper-evident : any UPDATE / DELETE breaks the chain
at verification time, which is exactly what an audit trail requires.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.ledger import LedgerEntry
from app.models._common import new_uuid


GENESIS_HASH = "0" * 64


def _canonical(payload: Dict[str, Any]) -> str:
    """Deterministic JSON encoding (sorted keys, no whitespace, ISO dates)."""
    def _default(o):
        if isinstance(o, datetime):
            return o.replace(tzinfo=o.tzinfo or timezone.utc).isoformat()
        raise TypeError(f"Type non sérialisable pour le ledger: {type(o)}")

    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=_default)


def _hash_entry(payload: Dict[str, Any], previous_hash: str) -> str:
    blob = _canonical(payload) + "|" + previous_hash
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _next_sequence_and_prev_hash(db: Session) -> tuple[int, str]:
    last = db.execute(
        select(LedgerEntry).order_by(LedgerEntry.sequence.desc()).limit(1)
    ).scalar_one_or_none()
    if last is None:
        return 1, GENESIS_HASH
    return last.sequence + 1, last.entry_hash


def record(
    db: Session,
    *,
    kind: str,
    amount_cents: int = 0,
    currency: str = "EUR",
    party_id: str = "",
    receivable_id: str = "",
    payment_id: str = "",
    mandate_id: str = "",
    notes: str = "",
    extra_payload: Optional[Dict[str, Any]] = None,
    occurred_at: Optional[datetime] = None,
) -> LedgerEntry:
    """Append a new entry to the ledger and return it.

    The caller is responsible for committing (this function flushes only
    so the entry hash is final). Typically you call `record()` inside the same
    transaction as the business mutation that triggered it.
    """
    if occurred_at is None:
        occurred_at = datetime.now(timezone.utc)

    sequence, previous_hash = _next_sequence_and_prev_hash(db)

    # `payload_json` is stored in a JSON column → datetimes must be ISO strings.
    occurred_at_iso = occurred_at.replace(tzinfo=occurred_at.tzinfo or timezone.utc).isoformat()

    payload: Dict[str, Any] = {
        "sequence": sequence,
        "occurred_at": occurred_at_iso,
        "kind": kind,
        "party_id": party_id,
        "receivable_id": receivable_id,
        "payment_id": payment_id,
        "mandate_id": mandate_id,
        "amount_cents": amount_cents,
        "currency": currency,
        "notes": notes,
        "extra": extra_payload or {},
    }
    entry_hash = _hash_entry(payload, previous_hash)

    entry = LedgerEntry(
        id=new_uuid(),
        sequence=sequence,
        occurred_at=occurred_at,
        kind=kind,
        party_id=party_id,
        receivable_id=receivable_id,
        payment_id=payment_id,
        mandate_id=mandate_id,
        amount_cents=amount_cents,
        currency=currency,
        payload_json=payload,
        notes=notes,
        previous_hash=previous_hash,
        entry_hash=entry_hash,
    )
    db.add(entry)
    db.flush()
    return entry


def verify_chain(db: Session) -> Dict[str, Any]:
    """Re-walk the entire chain. Return ok=True + total_entries, or first break."""
    entries = db.execute(select(LedgerEntry).order_by(LedgerEntry.sequence.asc())).scalars().all()
    expected_prev = GENESIS_HASH
    for idx, e in enumerate(entries, start=1):
        if e.sequence != idx:
            return {
                "ok": False,
                "total_entries": len(entries),
                "broken_at_sequence": e.sequence,
                "error": f"Sequence trou: attendu {idx}, trouvé {e.sequence}",
            }
        if e.previous_hash != expected_prev:
            return {
                "ok": False,
                "total_entries": len(entries),
                "broken_at_sequence": e.sequence,
                "error": "previous_hash divergent — chaîne rompue",
            }
        recomputed = _hash_entry(e.payload_json, e.previous_hash)
        if recomputed != e.entry_hash:
            return {
                "ok": False,
                "total_entries": len(entries),
                "broken_at_sequence": e.sequence,
                "error": "entry_hash divergent — payload modifié après écriture",
            }
        expected_prev = e.entry_hash
    return {"ok": True, "total_entries": len(entries), "broken_at_sequence": None, "error": None}


def count_entries(db: Session) -> int:
    return int(db.execute(select(func.count(LedgerEntry.id))).scalar() or 0)
