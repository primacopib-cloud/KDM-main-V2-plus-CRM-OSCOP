"""Garde-fous d'abonnement : un vendeur ne peut pas acheter, un acheteur ne peut pas vendre."""
from fastapi import HTTPException, Request


def _roles(user: dict):
    return ((user.get("role") or "").lower(), (user.get("account_type") or "").lower())


def ensure_can_buy(user: dict):
    """Bloque les comptes Vendeur Pro sur les parcours d'achat (panier, commandes)."""
    if user.get("is_admin"):
        return
    role, acct = _roles(user)
    if role == "vendor" or acct == "vendor":
        raise HTTPException(
            status_code=403,
            detail="Votre abonnement Vendeur Pro ne permet pas d'effectuer des achats. "
                   "Souscrivez un abonnement Acheteur Pro pour accéder à la centrale d'achats.")


async def ensure_seller_request(db, request: Request, vendor_id: str) -> dict:
    """Exige un compte Vendeur Pro connecté et propriétaire du vendor_id (ou admin)."""
    from auth import extract_user_id_from_request
    uid = extract_user_id_from_request(request) if request else None
    if not uid:
        raise HTTPException(status_code=401, detail="Connexion requise pour vendre sur la plateforme")
    user = await db.users.find_one(
        {"id": uid}, {"_id": 0, "role": 1, "account_type": 1, "is_admin": 1, "vendor_id": 1, "email": 1})
    if not user:
        raise HTTPException(status_code=401, detail="Utilisateur non trouvé")
    if user.get("is_admin"):
        return user
    role, acct = _roles(user)
    if role == "buyer" or acct == "buyer":
        raise HTTPException(
            status_code=403,
            detail="Votre abonnement Acheteur Pro ne permet pas de vendre. "
                   "Souscrivez un abonnement Vendeur Pro pour soumettre des produits.")
    if not user.get("vendor_id"):
        raise HTTPException(
            status_code=403,
            detail="Seuls les membres Vendeur Pro peuvent soumettre des produits.")
    if user["vendor_id"] != vendor_id:
        raise HTTPException(status_code=403, detail="Ce compte vendeur ne vous appartient pas")
    return user
