"""Téléchargement du ticket de caisse en PDF (archivage comptable)."""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from lolodrive_helpers import get_current_user
from routes_relay_products import _manager_point

ticket_pdf_router = APIRouter(prefix="/api/lolodrive", tags=["Ticket PDF"])
db = None


def set_ticket_pdf_database(database):
    global db
    db = database


@ticket_pdf_router.get("/pos/counter-sale/{order_id}/ticket.pdf")
async def download_ticket_pdf(order_id: str, user: dict = Depends(get_current_user)):
    point = await _manager_point(user["id"])
    order = await db.lolodrive_orders.find_one(
        {"id": order_id, "lolo_point_id": point["id"], "channel": "COUNTER"}, {"_id": 0})
    if not order:
        raise HTTPException(status_code=404, detail="Vente introuvable pour ce relais")
    from ticket_pdf import build_ticket_pdf
    pdf = build_ticket_pdf(order, point)
    return Response(content=pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f"attachment; filename=ticket-{order.get('order_number')}.pdf"})
