"""PV de clôture PDF — reportlab, charte violet/or, empreinte SHA-256."""
from datetime import datetime, timezone

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

VIOLET = colors.HexColor("#451F6B")
eur = lambda c: f"{(c or 0) / 100:.2f} €".replace(".", ",")


def build_pv_pdf(c: dict, entries: list, award: dict, events: list) -> bytes:
    st = ParagraphStyle("b", fontName="Helvetica", fontSize=9, leading=13)
    h1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, textColor=VIOLET, spaceAfter=4)
    h2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11, textColor=VIOLET, spaceBefore=10, spaceAfter=3)
    small = ParagraphStyle("s", fontName="Helvetica", fontSize=7.5, textColor=colors.HexColor("#6b5a7a"))
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, leftMargin=16 * mm, rightMargin=16 * mm)
    story = [
        Paragraph(f"PROCÈS-VERBAL DE CLÔTURE — {c['ref']}", h1),
        Paragraph(f"{c['title']} · Statut final : {c['status']} · Généré le {datetime.now(timezone.utc).isoformat()[:16].replace('T', ' ')} UTC", small),
        Paragraph("1. Cadre juridique et règlement", h2),
        Paragraph(f"Catégorie juridique : <b>{c['legal_status']}</b> (matrice v{c.get('legal_matrix_version')}) · "
                  f"Procédure : <b>{'Offres scellées' if c['procedure'] == 'SCELLEE' else 'Enchère inversée'}</b> · "
                  f"Type : {c['type']} · Coût d'accès : {c['cpc_cost']} CPC · Tours max : {c.get('max_rounds', 3)}", st),
        Paragraph(f"Empreinte du règlement publié (SHA-256) : {c.get('published_snapshot_hash') or '—'}", small),
    ]
    if c.get("orange_validation"):
        ov = c["orange_validation"]
        story.append(Paragraph(f"Validation juridique ORANGE : {ov['author']} le {ov['date'][:16]} — {ov['reason']}", st))
    story.append(Paragraph("2. Participants admis et offres finales", h2))
    rows = [["Participant", "Offre finale HT", "Horodatage", "Empreinte"]]
    for e in entries:
        b = e.get("bid") or {}
        rows.append([e["company"] or "—", eur(b.get("amount_ht_cents")) if b.get("amount_ht_cents") else "(aucune offre)",
                     (b.get("server_ts") or "")[:19].replace("T", " "), (b.get("payload_sha256") or "")[:16]])
    t = Table(rows, colWidths=[60 * mm, 32 * mm, 42 * mm, 40 * mm])
    t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), VIOLET), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                           ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
                           ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
    story.append(t)
    if award and award.get("ranking"):
        story.append(Paragraph("3. Classement multicritère", h2))
        weights = {cr["key"]: cr["weight"] for cr in c.get("criteria", [])}
        story.append(Paragraph("Pondérations : " + " · ".join(f"{k} {w}%" for k, w in weights.items()), small))
        rows = [["Rang", "Participant", "Offre HT", "Score total"]]
        for i, r in enumerate(award["ranking"]):
            rows.append([str(i + 1), r["company"], eur(r["amount_ht_cents"]), f"{r['total']:.2f}"])
        t = Table(rows, colWidths=[14 * mm, 76 * mm, 32 * mm, 30 * mm])
        t.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, 0), VIOLET), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                               ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbb8e0")),
                               ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4)]))
        story.append(t)
        if award.get("awarded_entry_id"):
            winner = next((r for r in award["ranking"] if r["entry_id"] == award["awarded_entry_id"]), {})
            story.append(Paragraph("4. Attribution", h2))
            story.append(Paragraph(f"Attributaire : <b>{winner.get('company')}</b> — {eur(winner.get('amount_ht_cents'))} HT. "
                                   f"Validée par {award.get('validated_by')} le {(award.get('validated_at') or '')[:16].replace('T', ' ')}.", st))
            if award.get("derogation"):
                d = award["derogation"]
                story.append(Paragraph(f"<b>Dérogation au classement</b> : {d['reason']} (validée par {', '.join(d['validated_by'])} le {d['at'][:16]})", st))
    story.append(Paragraph("5. Chronologie horodatée (journal d'audit chaîné)", h2))
    for e in events[:60]:
        story.append(Paragraph(f"{e['ts'][:19].replace('T', ' ')} — <b>{e['event_type']}</b> ({e['actor']})", small))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Document généré automatiquement par la plateforme Communityplace (O'SCOP × KDMARCHÉ). "
                           "L'intégrité du journal est garantie par chaînage SHA-256. Conservation : 5 ans (min. légal 1 an, art. L.442-8 C. com.).", small))
    doc.build(story)
    return buf.getvalue()
