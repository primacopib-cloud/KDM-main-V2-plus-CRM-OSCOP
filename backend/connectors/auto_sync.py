"""Orchestrations de synchronisation automatique vers les apps connectées.

Déclencheurs :
  - commande payée  -> facture PDF vers GED O'SCOP + paiement vers Finance O'SCOP
  - contrat signé   -> document contrat vers GED O'SCOP
"""
from __future__ import annotations

import asyncio
import logging
from typing import Optional

from connectors import base
from connectors import oscop_crm

logger = logging.getLogger(__name__)

db = None


def set_auto_sync_database(database) -> None:
    global db
    db = database


def _schedule(coro) -> None:
    task = asyncio.ensure_future(coro)
    task.add_done_callback(lambda t: t.exception() and logger.error(f"Connector sync task failed: {t.exception()}"))


def schedule_order_sync(order_id: str) -> None:
    _schedule(sync_order_paid(order_id))


def schedule_contract_sync(contract_id: str) -> None:
    _schedule(sync_contract_signed(contract_id))


# ---------------------------------------------------------------------------
# Commande payée
# ---------------------------------------------------------------------------

async def sync_order_paid(order_id: str) -> dict:
    ged = await push_order_invoice_to_ged(order_id)
    fin = await push_order_paiement_to_finance(order_id)
    coppam = await push_order_paiement_to_coppam(order_id)
    crmess = await push_order_invoice_to_crmess(order_id)
    return {"ged": ged, "finance": fin, "coppam": coppam, "crmess": crmess}


async def _build_invoice_pdf(order_id: str, order: dict):
    from routes_invoices import generate_invoice_for_order
    from pdf_generators import generate_invoice_pdf

    invoice = await generate_invoice_for_order(order_id)
    return invoice, generate_invoice_pdf(invoice, order)


async def push_order_invoice_to_ged(order_id: str, event_id: Optional[str] = None) -> dict:
    order = await db.orders.find_one({"id": order_id})
    if not order:
        return {"status": "ERROR", "error": f"Commande introuvable: {order_id}"}
    detail = f"Facture commande {order.get('order_number', order_id)}"
    if not event_id:
        event_id = await base.record_event(
            connector="oscop-ged", action="push_invoice", source="order",
            source_id=order_id, detail=detail,
        )
    try:
        invoice, pdf_bytes = await _build_invoice_pdf(order_id, order)
        filename = f"{invoice.get('invoice_number', order_id)}.pdf"
        resp = await oscop_crm.upload_document(
            filename=filename,
            content=pdf_bytes,
            content_type="application/pdf",
            categorie="factures",
            description=f"KDMARCHE — {detail}",
            tags="kdmarche,facture",
        )
        await base.mark_event(event_id, "SUCCESS", response_excerpt=_excerpt(resp))
        return {"status": "SUCCESS", "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"GED push invoice failed for order {order_id}: {exc}")
        return {"status": "ERROR", "event_id": event_id, "error": str(exc)[:300]}


async def push_order_paiement_to_finance(order_id: str, event_id: Optional[str] = None) -> dict:
    order = await db.orders.find_one({"id": order_id})
    if not order:
        return {"status": "ERROR", "error": f"Commande introuvable: {order_id}"}
    reference = order.get("order_number") or order_id
    amount_cents = order.get("amount_paid_cents") or order.get("total_ttc_cents") or 0
    if not event_id:
        event_id = await base.record_event(
            connector="oscop-finance", action="push_paiement", source="order",
            source_id=order_id, detail=f"Paiement {reference} — {amount_cents / 100:.2f} €",
        )
    try:
        resp = await oscop_crm.create_paiement({
            "montant": round(amount_cents / 100, 2),
            "moyen_paiement": "cb",
            "statut": "valide",
            "reference": f"KDM-{reference}",
        })
        await base.mark_event(event_id, "SUCCESS", response_excerpt=_excerpt(resp))
        return {"status": "SUCCESS", "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"Finance push paiement failed for order {order_id}: {exc}")
        return {"status": "ERROR", "event_id": event_id, "error": str(exc)[:300]}


# ---------------------------------------------------------------------------
# Contrat signé
# ---------------------------------------------------------------------------

async def sync_contract_signed(contract_id: str) -> dict:
    ged = await push_contract_to_ged(contract_id)
    crmess = await push_contract_to_crmess(contract_id)
    return {"ged": ged, "crmess": crmess}


async def push_contract_to_ged(contract_id: str, event_id: Optional[str] = None) -> dict:
    contract = await db.transport_contracts.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return {"status": "ERROR", "error": f"Contrat introuvable: {contract_id}"}
    reference = contract.get("reference") or contract_id
    if not event_id:
        event_id = await base.record_event(
            connector="oscop-ged", action="push_contract", source="contract",
            source_id=contract_id, detail=f"Contrat signé {reference}",
        )
    try:
        from routes_contracts import get_transport_contract_html

        html_response = await get_transport_contract_html(contract_id)
        html = html_response.body.decode() if hasattr(html_response, "body") else str(html_response)
        resp = await oscop_crm.upload_document(
            filename=f"contrat-{reference}.html",
            content=html.encode("utf-8"),
            content_type="text/html",
            categorie="autres",
            description=f"KDMARCHE — Contrat de transport signé {reference}",
            tags="kdmarche,contrat",
        )
        await base.mark_event(event_id, "SUCCESS", response_excerpt=_excerpt(resp))
        return {"status": "SUCCESS", "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"GED push contract failed for {contract_id}: {exc}")
        return {"status": "ERROR", "event_id": event_id, "error": str(exc)[:300]}


# ---------------------------------------------------------------------------
# COPPAM (trésorerie) & CRM ESS (documents)
# ---------------------------------------------------------------------------

async def push_order_paiement_to_coppam(order_id: str, event_id: Optional[str] = None) -> dict:
    import os

    from connectors import generic_app

    order = await db.orders.find_one({"id": order_id})
    if not order:
        return {"status": "ERROR", "error": f"Commande introuvable: {order_id}"}
    reference = order.get("order_number") or order_id
    amount_cents = order.get("amount_paid_cents") or order.get("total_ttc_cents") or 0
    if not event_id:
        event_id = await base.record_event(
            connector="coppam", action="push_paiement", source="order",
            source_id=order_id, detail=f"Encaissement {reference} — {amount_cents / 100:.2f} €",
        )
    try:
        resp = await generic_app.request("coppam", "POST", "/api/invoices", json_payload={
            "memberId": os.environ.get("COPPAM_MEMBER_ID", "kdmarche"),
            "amount": round(amount_cents / 100, 2),
            "description": f"Encaissement KDMARCHÉ — commande {reference}",
            "reference": f"KDM-{reference}",
            "status": "paid",
        })
        await base.mark_event(event_id, "SUCCESS", response_excerpt=_excerpt(resp))
        return {"status": "SUCCESS", "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"COPPAM push paiement failed for order {order_id}: {exc}")
        return {"status": "ERROR", "event_id": event_id, "error": str(exc)[:300]}


async def _upload_to_crmess(filename: str, content: bytes, content_type: str, titre: str, type_document: str):
    from connectors import generic_app

    return await generic_app.request(
        "crm-ess", "POST", "/api/documents/upload",
        files={"file": (filename, content, content_type)},
        form_data={"titre": titre, "type_document": type_document},
    )


async def push_order_invoice_to_crmess(order_id: str, event_id: Optional[str] = None) -> dict:
    order = await db.orders.find_one({"id": order_id})
    if not order:
        return {"status": "ERROR", "error": f"Commande introuvable: {order_id}"}
    reference = order.get("order_number") or order_id
    if not event_id:
        event_id = await base.record_event(
            connector="crm-ess", action="push_invoice", source="order",
            source_id=order_id, detail=f"Facture commande {reference}",
        )
    try:
        invoice, pdf_bytes = await _build_invoice_pdf(order_id, order)
        resp = await _upload_to_crmess(
            f"{invoice.get('invoice_number', order_id)}.pdf", pdf_bytes, "application/pdf",
            f"KDMARCHÉ — Facture {reference}", "facture",
        )
        await base.mark_event(event_id, "SUCCESS", response_excerpt=_excerpt(resp))
        return {"status": "SUCCESS", "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"CRM ESS push invoice failed for order {order_id}: {exc}")
        return {"status": "ERROR", "event_id": event_id, "error": str(exc)[:300]}


async def push_contract_to_crmess(contract_id: str, event_id: Optional[str] = None) -> dict:
    contract = await db.transport_contracts.find_one({"id": contract_id}, {"_id": 0})
    if not contract:
        return {"status": "ERROR", "error": f"Contrat introuvable: {contract_id}"}
    reference = contract.get("reference") or contract_id
    if not event_id:
        event_id = await base.record_event(
            connector="crm-ess", action="push_contract", source="contract",
            source_id=contract_id, detail=f"Contrat signé {reference}",
        )
    try:
        from routes_contracts import get_transport_contract_html

        html_response = await get_transport_contract_html(contract_id)
        html = html_response.body.decode() if hasattr(html_response, "body") else str(html_response)
        resp = await _upload_to_crmess(
            f"contrat-{reference}.html", html.encode("utf-8"), "text/html",
            f"KDMARCHÉ — Contrat de transport signé {reference}", "contrat",
        )
        await base.mark_event(event_id, "SUCCESS", response_excerpt=_excerpt(resp))
        return {"status": "SUCCESS", "event_id": event_id}
    except Exception as exc:
        await base.mark_event(event_id, "ERROR", error=str(exc)[:500])
        logger.error(f"CRM ESS push contract failed for {contract_id}: {exc}")
        return {"status": "ERROR", "event_id": event_id, "error": str(exc)[:300]}


# ---------------------------------------------------------------------------
# Retry (depuis la page admin Connecteurs)
# ---------------------------------------------------------------------------

_RETRY_HANDLERS = {
    ("oscop-ged", "push_invoice"): push_order_invoice_to_ged,
    ("oscop-finance", "push_paiement"): push_order_paiement_to_finance,
    ("oscop-ged", "push_contract"): push_contract_to_ged,
    ("coppam", "push_paiement"): push_order_paiement_to_coppam,
    ("crm-ess", "push_invoice"): push_order_invoice_to_crmess,
    ("crm-ess", "push_contract"): push_contract_to_crmess,
}


async def retry_event(event: dict) -> dict:
    handler = _RETRY_HANDLERS.get((event["connector"], event["action"]))
    if not handler:
        return {"status": "ERROR", "error": f"Action inconnue: {event['connector']}/{event['action']}"}
    await base.mark_event(event["id"], "PENDING", increment_attempt=True)
    return await handler(event["source_id"], event_id=event["id"])


def _excerpt(resp) -> dict:
    if isinstance(resp, dict):
        return {k: str(resp[k])[:300] for k in list(resp)[:6]}
    return {"raw": str(resp)[:200]}
