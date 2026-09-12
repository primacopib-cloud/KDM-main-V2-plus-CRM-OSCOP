"""Export ZIP de relecture juridique : un PDF par page légale (contenus JS + pages dynamiques DB) — superadmin."""
import io
import json
import logging
import re
import zipfile
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate

from lolodrive_helpers import require_admin

logger = logging.getLogger(__name__)

legal_review_router = APIRouter(prefix="/api/admin", tags=["Relecture juridique"])

db = None


def set_legal_review_database(database):
    global db
    db = database


LEGAL_DIR = "/app/frontend/src/data/legal"
FILES = {
    "cgv-kdmarche": f"{LEGAL_DIR}/cgv.js",
    "cgu-communityplace-et-mentions": f"{LEGAL_DIR}/cgu_mentions.js",
    "convention-partenariat": f"{LEGAL_DIR}/convention.js",
    "charte-ess-et-annexe-logiscop": f"{LEGAL_DIR}/ess.js",
    "contrats-logiscop": f"{LEGAL_DIR}/logiscop.js",
    "politique-confidentialite": f"{LEGAL_DIR}/privacy.js",
}

_T = ParagraphStyle("t", fontName="Helvetica-Bold", fontSize=13, textColor=colors.HexColor("#2A1045"), spaceAfter=8, leading=16)
_H = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=10.5, textColor=colors.HexColor("#451F6B"), spaceBefore=10, spaceAfter=3)
_B = ParagraphStyle("b", fontName="Helvetica", fontSize=9, leading=13, textColor=colors.HexColor("#2a2233"), spaceAfter=4)


def _load_variables() -> dict:
    src = open(f"{LEGAL_DIR}/variables.js", encoding="utf-8").read()
    return dict(re.findall(r'^\s*([A-Z_0-9]+):\s*"((?:[^"\\]|\\.)*)"', src, re.M))


def _substitute(text: str, variables: dict) -> str:
    return re.sub(r"\{\{(\w+)\}\}", lambda m: variables.get(m.group(1), m.group(0)), text)


def _md_to_rl(text: str) -> str:
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text, flags=re.S)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text, flags=re.S)
    return text.replace("\n", "<br/>")


def _extract_docs(js_source: str) -> list[dict]:
    """Extrait titres et sections {number,title,content} des exports JS légaux (template literals)."""
    docs = []
    for m in re.finditer(r"export const (\w+)\s*=\s*\{", js_source):
        name = m.group(1)
        chunk = js_source[m.end():]
        title_m = re.search(r'title:\s*"((?:[^"\\]|\\.)*)"', chunk)
        sections = []
        for sm in re.finditer(
                r'number:\s*"([^"]*)",\s*title:\s*"((?:[^"\\]|\\.)*)"(?:,\s*highlight:\s*\w+)?,\s*content:\s*`((?:[^`\\]|\\.)*)`',
                chunk[:js_source.find("export const", m.end()) - m.end() if js_source.find("export const", m.end()) > 0 else len(chunk)],
                re.S):
            sections.append({"number": sm.group(1), "title": sm.group(2), "content": sm.group(3)})
        if sections:
            docs.append({"name": name, "title": title_m.group(1) if title_m else name, "sections": sections})
    return docs


def _doc_pdf(title: str, sections: list[dict], variables: dict) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm, leftMargin=17 * mm, rightMargin=17 * mm)
    el = [Paragraph(_md_to_rl(_substitute(title, variables)), _T),
          Paragraph(f"Export de relecture juridique — généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M')} UTC. Document indicatif, à valider par un conseil juridique avant publication.", _B)]
    for s in sections:
        head = f"{s['number']}. {s['title']}" if s.get("number") else s["title"]
        el.append(Paragraph(_md_to_rl(_substitute(head, variables)), _H))
        el.append(Paragraph(_md_to_rl(_substitute(s["content"], variables)), _B))
    doc.build(el)
    return buf.getvalue()


def _text_pdf(title: str, text: str) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=16 * mm, bottomMargin=14 * mm, leftMargin=17 * mm, rightMargin=17 * mm)
    el = [Paragraph(_md_to_rl(title), _T)]
    for para in text.split("\n\n"):
        if para.strip():
            el.append(Paragraph(_md_to_rl(para.strip()), _B))
    doc.build(el)
    return buf.getvalue()


@legal_review_router.get("/legal-review-pack.zip")
async def legal_review_pack(admin: dict = Depends(require_admin)):
    """ZIP : un PDF par document légal (fichiers JS avec variables résolues + pages dynamiques DB)."""
    variables = _load_variables()
    zbuf = io.BytesIO()
    with zipfile.ZipFile(zbuf, "w", zipfile.ZIP_DEFLATED) as z:
        for slug, path in FILES.items():
            try:
                for d in _extract_docs(open(path, encoding="utf-8").read()):
                    z.writestr(f"{slug}--{d['name']}.pdf", _doc_pdf(d["title"], d["sections"], variables))
            except Exception as exc:
                logger.warning("Relecture %s : %s", slug, exc)
        async for page in db.legal_pages.find({}, {"_id": 0, "slug": 1, "title": 1, "content": 1}):
            z.writestr(f"dynamique--{page['slug']}.pdf", _text_pdf(page.get("title") or page["slug"], page.get("content") or ""))
    return Response(content=zbuf.getvalue(), media_type="application/zip",
                    headers={"Content-Disposition": 'attachment; filename="relecture-juridique.zip"'})
