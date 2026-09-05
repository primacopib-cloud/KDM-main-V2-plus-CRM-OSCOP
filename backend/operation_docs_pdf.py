"""Documents PDF numérotés des opérations achat-revente (BCF / BE / EM)."""
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

GOLD = colors.HexColor("#B8923F")
VIOLET = colors.HexColor("#2A1045")
GREY = colors.HexColor("#666666")

DOC_TYPES = {
    "SUPPLIER_PO": {"prefix": "BCF", "title": "BON DE COMMANDE FOURNISSEUR",
                    "issuer": "SCIC SAS OBJECTIF SCOP OUTREMER — Acheteur"},
    "INVESTOR_COMMITMENT": {"prefix": "BE", "title": "BON D'ENGAGEMENT INVESTISSEUR",
                            "issuer": "SCIC SAS OBJECTIF SCOP OUTREMER"},
    "MARGIN_STATEMENT": {"prefix": "EM", "title": "ÉTAT DE MARGE DE L'OPÉRATION",
                         "issuer": "SCIC SAS OBJECTIF SCOP OUTREMER"},
    "FOGEDOM_REPORT": {"prefix": "RF", "title": "RAPPORT PRÉVENTIF F.O.G.E.D.O.M",
                       "issuer": "F.O.G.E.D.O.M — rapport de suivi (ni prêteur, ni banque, ni assureur, ni garant)"},
    "CLIENT_INVOICE": {"prefix": "FAC", "title": "FACTURE — VENTE DIRECTE O'SCOP",
                       "issuer": "SCIC SAS OBJECTIF SCOP OUTREMER — Vendeur, émetteur et bénéficiaire du paiement"},
    "FREIGHT_QUOTE": {"prefix": "DF", "title": "DEVIS DE FRET MARITIME LOGI'SCOP",
                      "issuer": "SCIC SAS OBJECTIF SCOP OUTREMER, agissant par son établissement LOGI'SCOP"},
    "DATAROOM": {"prefix": "DR", "title": "DATA ROOM DE L'OPÉRATION",
                 "issuer": "SCIC SAS OBJECTIF SCOP OUTREMER — dossier de synthèse (service interne CREDI'SCOP-I)"},
}


async def next_doc_number(db, doc_type: str) -> str:
    prefix = DOC_TYPES[doc_type]["prefix"]
    year = datetime.now(timezone.utc).year
    doc = await db.counters.find_one_and_update(
        {"_id": f"opdoc_{prefix}_{year}"}, {"$inc": {"seq": 1}},
        upsert=True, return_document=True)
    return f"{prefix}-{year}-{doc['seq']:04d}"


def _eur(v):
    return f"{float(v or 0):,.2f} EUR".replace(",", " ").replace(".", ",")


def doc_sections(doc_type: str, op: dict, extra: dict) -> list:
    common = [("Référence opération", op.get("reference")), ("Client", op.get("client_name")),
              ("Fournisseur", op.get("supplier_name")), ("Devise", op.get("currency", "EUR"))]
    if doc_type == "SUPPLIER_PO":
        return common + [
            ("Acheteur", "SCIC SAS OBJECTIF SCOP OUTREMER"),
            ("Montant achat HT", _eur(op.get("purchase_amount_ex_vat"))),
            ("Mode logistique", op.get("logistics_mode")),
            ("Budget logistique HT", _eur(op.get("logistics_budget_ex_vat"))),
            ("Conditions", "Facture fournisseur à établir au nom de la SCIC SAS OBJECTIF SCOP OUTREMER"),
        ]
    if doc_type == "INVESTOR_COMMITMENT":
        return common + [
            ("Investisseur", op.get("investor_name") or extra.get("investor_name", "-")),
            ("Instrument juridique", op.get("funding_instrument") or "Bon d'Engagement — support juridique à préciser"),
            ("Tranche marchandises", _eur(extra.get("goods_amount", op.get("purchase_amount_ex_vat")))),
            ("Tranche logistique", _eur(extra.get("logistics_amount", op.get("logistics_budget_ex_vat")))),
            ("Engagement total", _eur(extra.get("total_amount",
                float(op.get("purchase_amount_ex_vat", 0)) + float(op.get("logistics_budget_ex_vat", 0))))),
            ("Mention", "Paiements réalisés pour le compte de la SCIC SAS OBJECTIF SCOP OUTREMER. "
                        "Les CREDI'SCOP-I ne constituent pas le montant investi."),
        ]
    if doc_type == "DATAROOM":
        rows = common + [
            ("Statut opération", op.get("status")),
            ("Territoire", op.get("territory_id") or "-"),
            ("Offre catalogue liée", op.get("linked_product_name") or "-"),
            ("Achat fournisseur HT", _eur(op.get("purchase_amount_ex_vat"))),
            ("Revente prévue HT", _eur(op.get("resale_amount_ex_vat"))),
            ("Coût de revient complet HT", _eur(op.get("full_cost_price_ex_vat"))),
            ("Marge consolidée prévisionnelle", f"{_eur(op.get('expected_margin_ex_vat'))} ({op.get('expected_margin_rate', 0)} %)"),
            ("Logistique", f"{op.get('logistics_mode')} — statut {op.get('logistics_status') or '-'}"),
            ("Financement", op.get("funding_instrument") or "À confirmer par Bon d'Engagement"),
            ("Investisseur", op.get("investor_name") or "-"),
        ]
        for i, d in enumerate(extra.get("documents", []), 1):
            rows.append((f"Document archivé {i}", f"{d.get('doc_number')} — {d.get('doc_type')} ({str(d.get('created_at', ''))[:10]})"))
        for i, it in enumerate(extra.get("interests", []), 1):
            rows.append((f"Intérêt investisseur {i}", f"{it.get('investor_name')} — statut {it.get('status')}"))
        rows.append(("Mention", "Data room : service interne activable par CREDI'SCOP-I. "
                                "Les CREDI'SCOP-I ne constituent ni un moyen de paiement, ni le montant investi."))
        return rows
    if doc_type == "FOGEDOM_REPORT":
        blockers = extra.get("blockers", [])
        return common + [
            ("Contrôle commande client", op.get("client_name") or "-"),
            ("Fournisseur", op.get("supplier_name")),
            ("Coût de revient complet HT", _eur(op.get("full_cost_price_ex_vat"))),
            ("Marge consolidée prévisionnelle", f"{_eur(op.get('expected_margin_ex_vat'))} ({op.get('expected_margin_rate', 0)} %)"),
            ("Logistique", f"{op.get('logistics_mode')} — statut {op.get('logistics_status')} — budget {_eur(op.get('logistics_budget_ex_vat'))}"),
            ("Financement", op.get("funding_instrument") or "À confirmer par Bon d'Engagement"),
            ("Risques / points bloquants", " ; ".join(blockers) if blockers else "Aucun blocage détecté"),
            ("Mesures préventives", extra.get("preventive_measures", "Suivi standard F.O.G.E.D.O.M")),
            ("Mention", "F.O.G.E.D.O.M n'est ni prêteur, ni banque, ni assureur, ni garant."),
        ]
    return common + [
        ("Prix fournisseur HT", _eur(op.get("purchase_amount_ex_vat"))),
        ("Coûts directs HT", _eur(op.get("direct_costs_ex_vat"))),
        ("Coût de revient complet HT", _eur(op.get("full_cost_price_ex_vat"))),
        ("Revente totale HT", _eur(op.get("resale_total_ex_vat"))),
        ("Marge marchandises prévisionnelle", _eur(op.get("expected_goods_margin_ex_vat"))),
        ("Marge logistique prévisionnelle", _eur(op.get("expected_logistics_margin_ex_vat"))),
        ("Marge consolidée prévisionnelle", _eur(op.get("expected_margin_ex_vat"))),
        ("Taux de marge", f"{op.get('expected_margin_rate', 0)} %"),
        ("Taux de majoration sur coût", f"{op.get('markup_rate', 0)} %"),
        ("Seuil minimal approuvé", f"{op.get('min_margin_rate', 0)} %"),
    ]


def build_operation_pdf(doc: dict) -> bytes:
    """Génère le PDF depuis le snapshot archivé du document."""
    meta = DOC_TYPES[doc["doc_type"]]
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFillColor(VIOLET)
    c.rect(0, h - 30 * mm, w, 30 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 15)
    c.drawString(20 * mm, h - 15 * mm, meta["title"])
    c.setFont("Helvetica", 9)
    c.drawString(20 * mm, h - 22 * mm, meta["issuer"])
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w - 20 * mm, h - 15 * mm, f"N° {doc['doc_number']}")
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 8)
    c.drawRightString(w - 20 * mm, h - 21 * mm, f"Émis le {doc['created_at'][:10]}")

    y = h - 45 * mm
    for label, value in doc["sections"]:
        c.setFillColor(GREY)
        c.setFont("Helvetica", 9)
        c.drawString(20 * mm, y, str(label))
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 9)
        text = str(value if value is not None else "-")
        if len(text) > 80:
            c.setFont("Helvetica", 8)
            c.drawString(75 * mm, y, text[:110])
            if len(text) > 110:
                y -= 4.5 * mm
                c.drawString(75 * mm, y, text[110:220])
        else:
            c.drawString(75 * mm, y, text)
        y -= 8 * mm
        c.setStrokeColor(colors.HexColor("#EEEEEE"))
        c.line(20 * mm, y + 3 * mm, w - 20 * mm, y + 3 * mm)

    c.setFillColor(GREY)
    c.setFont("Helvetica", 7)
    c.drawString(20 * mm, 15 * mm,
                 "LOGI'SCOP est l'établissement logistique de la SCIC SAS OBJECTIF SCOP OUTREMER — aucune facture interne O'SCOP/LOGI'SCOP.")
    c.drawString(20 * mm, 11 * mm,
                 f"Document archivé et numéroté — {doc['doc_number']} — reproduction depuis snapshot immuable.")
    c.showPage()
    c.save()
    return buf.getvalue()
