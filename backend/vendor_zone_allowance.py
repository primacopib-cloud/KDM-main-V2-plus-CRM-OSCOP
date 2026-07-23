"""Nombre de zones autorisées par l'abonnement d'un vendeur."""


async def get_vendor_zone_allowance(db, vendor_id: str) -> dict:
    """Retourne {count, codes} : zones entitlées de l'org du vendeur, sinon 1 zone libre."""
    user = await db.users.find_one({"vendor_id": vendor_id}, {"_id": 0, "id": 1})
    if user:
        membership = await db.org_memberships.find_one({"user_id": user["id"]})
        if membership:
            ents = await db.org_zone_entitlements.find(
                {"org_id": membership["org_id"], "status": "ACTIVE"}).to_list(20)
            if ents:
                zone_ids = [e["zone_id"] for e in ents]
                codes = []
                async for z in db.zones_v2.find({"id": {"$in": zone_ids}}):
                    codes.append((z.get("code") or "").upper())
                return {"count": len(codes), "codes": codes}
    return {"count": 1, "codes": []}
