"""Page de partage produit avec balises Open Graph (aperçus riches WhatsApp/LinkedIn)."""
import html as html_mod
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse

share_router = APIRouter(prefix="/api/share")

db = None


def set_share_database(database):
    global db
    db = database


RANK_LABELS = {
    1: ("🥇", "Meilleur parrain du mois"),
    2: ("🥈", "2e du défi parrainage"),
    3: ("🥉", "3e du défi parrainage"),
}

CHALLENGE_OG_IMAGE = "https://static.prod-images.emergentagent.com/jobs/b6ab8bd3-fe62-4bdc-97dc-0a13cc7b27ca/images/0031ec9b89797c708246888faf7d604ada604de340d20cd6b2f7f7f1070b63f2.jpeg"


@share_router.get("/challenge")
async def share_challenge(request: Request, rank: int = 1, code: str = "", month: str = ""):
    """Carte OG « médaille du défi parrainage » + redirection vers l'adhésion avec le code parrain."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto", "https")
    base = f"{proto}://{host}"
    rank = rank if rank in RANK_LABELS else 1
    code = "".join(c for c in code.upper() if c.isalnum() or c == "-")[:20]
    month = "".join(c for c in month if c.isdigit() or c == "-")[:7]
    medal, label = RANK_LABELS[rank]
    target = f"{base}/adhesion-vendeur" + (f"?parrain={code}" if code else "")
    title = html_mod.escape(f"{medal} {label} — KDMARCHÉ × O'SCOP" + (f" ({month})" if month else ""))
    desc = html_mod.escape(
        (f"Rejoignez la coopérative avec le code parrain {code} et recevez un bonus de bienvenue CREDI'SCOP. "
         if code else "") + "Centrale d'achats coopérative B2B2C des Outre-mer — défi parrainage du mois.")
    page = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8" />
<title>{title}</title>
<meta property="og:type" content="website" />
<meta property="og:site_name" content="KDMARCHÉ × O'SCOP" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:url" content="{html_mod.escape(target)}" />
<meta property="og:image" content="{CHALLENGE_OG_IMAGE}" />
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{desc}" />
<meta http-equiv="refresh" content="0;url={html_mod.escape(target)}" />
</head><body style="background:#1F0A33;color:#F7F2E9;font-family:Arial,sans-serif;text-align:center;padding-top:80px;">
<p>Redirection vers l'adhésion…</p>
<a href="{html_mod.escape(target)}" style="color:#D9B35A;">{title}</a>
<script>window.location.replace({target!r});</script>
</body></html>"""
    return HTMLResponse(content=page)


@share_router.get("/product/{product_id}")
async def share_product(product_id: str, request: Request):
    """HTML avec balises OG pour les crawlers + redirection immédiate vers la fiche pour les humains."""
    host = request.headers.get("x-forwarded-host") or request.headers.get("host") or ""
    proto = request.headers.get("x-forwarded-proto", "https")
    base = f"{proto}://{host}"
    product = await db.products.find_one(
        {"id": product_id},
        {"_id": 0, "name": 1, "description": 1, "image_url": 1, "rating_avg": 1, "rating_count": 1})
    if not product:
        return RedirectResponse(url=f"{base}/catalogue")
    target = f"{base}/catalogue?produit={product_id}"
    img = product.get("image_url") or ""
    if img.startswith("/"):
        img = base + img
    title = html_mod.escape(product.get("name") or "Produit KDMARCHÉ")
    rating = ""
    if product.get("rating_count"):
        rating = f"★ {product.get('rating_avg')}/5 ({product.get('rating_count')} avis) — "
    desc = html_mod.escape((rating + (product.get("description") or "Centrale d'achats coopérative des Outre-mer"))[:200])
    og_image = f'<meta property="og:image" content="{html_mod.escape(img)}" />' if img else ""
    page = f"""<!DOCTYPE html>
<html lang="fr"><head>
<meta charset="utf-8" />
<title>{title} — KDMARCHÉ × O'SCOP</title>
<meta property="og:type" content="product" />
<meta property="og:site_name" content="KDMARCHÉ × O'SCOP" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:url" content="{html_mod.escape(target)}" />
{og_image}
<meta name="twitter:card" content="summary_large_image" />
<meta name="twitter:title" content="{title}" />
<meta name="twitter:description" content="{desc}" />
<meta http-equiv="refresh" content="0;url={html_mod.escape(target)}" />
</head><body style="background:#1F0A33;color:#F7F2E9;font-family:Arial,sans-serif;text-align:center;padding-top:80px;">
<p>Redirection vers la fiche produit…</p>
<a href="{html_mod.escape(target)}" style="color:#D9B35A;">{title}</a>
<script>window.location.replace({target!r});</script>
</body></html>"""
    return HTMLResponse(content=page)
