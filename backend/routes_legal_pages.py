"""Pages juridiques administrables (§20) : seed + lecture publique + édition admin."""
from datetime import datetime, timezone
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from routes_v2 import get_current_user_v2

legal_pages_router = APIRouter(prefix="/api", tags=["Pages juridiques"])
db = None


def set_legal_pages_database(database):
    global db
    db = database


SCIC = "SCIC SAS OBJECTIF SCOP OUTREMER"

DEFAULT_PAGES = [
    ("conditions-vente-oscop", "Conditions Générales de Vente O'SCOP",
     f"""Les présentes CGV régissent les ventes directes réalisées par la {SCIC} (« O'SCOP ») dans le cadre du circuit achat-revente. Elles ne s'appliquent pas aux offres vendues par un partenaire référencé, régies par les CGV du partenaire.

1. Formation de la vente — La vente est conclue à la validation de la commande et à la confirmation du paiement. O'SCOP est le vendeur juridique, l'émetteur de la facture et le bénéficiaire du paiement.

2. Prix et taxes — Les prix sont indiqués hors taxes et toutes taxes comprises. La TVA et taxes applicables figurent sur chaque facture.

3. Livraison — Selon l'offre : retrait, logistique organisée par le client ou logistique intégrée LOGI'SCOP, établissement de la {SCIC}.

4. Transfert des risques — Le transfert des risques intervient à la remise des marchandises selon l'incoterm ou la modalité de livraison indiquée sur l'offre.

5. Réserve de propriété — Les marchandises demeurent la propriété d'O'SCOP jusqu'au paiement intégral du prix.

6. Conformité et réclamations — Toute réclamation doit être formulée par écrit dans les délais légaux. O'SCOP assume les obligations attachées à sa qualité de vendeur.

7. Garanties — Les garanties légales de conformité et des vices cachés s'appliquent.

8. Retards de paiement — Tout retard entraîne les pénalités légales et l'indemnité forfaitaire de recouvrement applicable entre professionnels.

9. Annulation — Les conditions d'annulation sont précisées sur chaque offre ou devis.

10. Droit applicable et litiges — Droit français. Compétence des tribunaux du ressort du siège d'O'SCOP, sous réserve des règles impératives."""),
    ("conditions-offres-partenaires", "Conditions des offres partenaires",
     f"""Les offres identifiées « VENDU ET FACTURÉ PAR LE PARTENAIRE » sont vendues, facturées et encaissées directement par le partenaire référencé, seul vendeur juridique. Les CGV du partenaire s'appliquent à ces ventes.

O'SCOP assure uniquement les services coopératifs indiqués sur l'offre : accès, mutualisation, référencement, coordination ou abonnement. O'SCOP n'encaisse jamais le prix des marchandises vendues par un partenaire.

Le vendeur juridique, l'émetteur de la facture et le bénéficiaire du paiement sont indiqués sur chaque fiche avant la validation de la commande et demeurent enregistrés dans l'historique de l'opération."""),
    ("conditions-credi-scop-investissement", "Conditions CREDI'SCOP-INVEST et investissement",
     """Les CREDI'SCOP-INVEST sont des unités internes de services. Ils résultent d'un abonnement ou d'une attribution contractuelle de services.

Les CREDI'SCOP-INVEST : n'ont aucune valeur en euros ; ne sont pas convertibles ; ne sont pas remboursables en espèces ; ne sont pas transférables ; ne sont pas chargés sur une carte bancaire ; ne constituent pas le montant investi ; ne produisent aucun intérêt ni rendement ; ne donnent aucun droit automatique à une opération ; sont utilisables uniquement dans le catalogue fermé de services O'SCOP.

Tout investissement réel fait l'objet d'un Bon d'Engagement déterminant le support juridique applicable (compte courant d'associé, titres participatifs, financement par acteur habilité, société de projet ou autre instrument validé) et d'un paiement distinct en monnaie ayant cours légal."""),
    ("convention-investisseur", "Convention investisseur",
     f"""La convention d'investissement conclue avec la {SCIC} précise pour chaque opération : les plafonds d'engagement par tranche (marchandises, logistique, taxes et assurances), les bénéficiaires des paiements, les moyens de paiement autorisés, les échéances, les conditions suspensives et les modalités de remboursement.

L'investisseur peut payer le fournisseur ou les prestataires logistiques externes directement, pour le compte de la {SCIC}, dans la limite du Bon d'Engagement signé. La facture reste au nom d'O'SCOP.

Le remboursement de l'investisseur (principal marchandises, principal logistique, rémunération contractuelle) est effectué à partir des encaissements clients selon la convention de financement, après constitution des réserves fiscales applicables."""),
    ("conditions-fournisseurs-oscop", "Conditions fournisseurs O'SCOP",
     f"""Pour les opérations d'achat-revente, l'acheteur est la {SCIC}. Le fournisseur facture O'SCOP.

Le payeur matériel peut être O'SCOP ou un investisseur agissant pour le compte d'O'SCOP ; cette mention figure sur la preuve de paiement. Le destinataire des marchandises est O'SCOP ou le client final désigné.

Le fournisseur transmet les documents qualité, origine, douane et conformité requis, ainsi que les poids, volumes, conditionnements et contraintes de transport pour l'organisation logistique LOGI'SCOP."""),
    ("politique-paiement-et-remboursement", "Politique de paiement et de remboursement",
     """Paiements des marchandises et de la logistique : carte bancaire, virement ou solution bancaire habilitée via un prestataire de services de paiement (PSP). CREDI'SCOP-INVEST : unités internes réservées aux services d'analyse, d'activation et de suivi — jamais un moyen de paiement des produits.

Aucun numéro complet de carte ni cryptogramme n'est stocké : les paiements utilisent des pages hébergées et la tokenisation du PSP. Seuls la référence PSP, le statut, le montant, la devise et la date sont conservés.

Les remboursements et rétrofacturations sont gérés par le PSP conformément à ses règles et à la réglementation applicable."""),
    ("role-fogedom-scic", "Rôle de FOGEDOM-SCIC",
     """FOGEDOM-SCIC est un fonds interne analytique d'appui et de prévention. Son intervention est facultative, individualisée et limitée aux ressources disponibles. Elle ne constitue ni une garantie automatique, ni une assurance, ni un engagement de remboursement de l'investisseur.

FOGEDOM-SCIC peut financer, au cas par cas : expertise, contrôle qualité, mesure logistique corrective, stockage exceptionnel, prévention, reconditionnement ou continuité d'une opération.

F.O.G.E.D.O.M assure un rôle de rapport préalable et de suivi (commande client, fournisseur, coût et marge, logistique, assurances, risques douaniers et de change, conditions de financement, mesures préventives). F.O.G.E.D.O.M n'est ni prêteur, ni banque, ni assureur, ni garant."""),
    ("conditions-logistiques-logiscop", "Conditions logistiques LOGI'SCOP",
     f"""LOGI'SCOP est l'établissement logistique de la {SCIC}. Les engagements contractuels et factures sont émis par la {SCIC}, agissant par son établissement LOGI'SCOP. LOGI'SCOP n'est pas une personne morale distincte.

Les prestations couvertes peuvent inclure : enlèvement, pré-acheminement, transport routier, maritime, aérien ou multimodal, affrètement, groupage, assurance transport, transit et dédouanement, manutention, stockage, préparation de commandes, suivi des flux, dernier kilomètre, logistique inverse.

Lorsque la prestation est exécutée en interne, elle fait l'objet d'une affectation analytique au centre de coûts LOGI'SCOP, sans facturation interne. Les prestataires externes contractent avec O'SCOP et facturent O'SCOP."""),
    ("financement-logistique-investisseur", "Financement logistique investisseur",
     f"""L'investisseur peut financer séparément ou conjointement la tranche « marchandises » et la tranche « logistique » d'une opération, dans la limite des montants approuvés au Bon d'Engagement.

Sont affichés : montant marchandises approuvé, montant logistique approuvé, montant taxes et assurances approuvé, engagement total, montant déjà décaissé et montant restant disponible.

Les prestataires logistiques externes facturent la {SCIC} et peuvent être payés directement par l'investisseur pour le compte d'O'SCOP. Le total des décaissements externes et des affectations internes ne peut jamais dépasser le montant logistique approuvé ; toute augmentation exige une validation et, si nécessaire, un avenant au Bon d'Engagement."""),
]


async def seed_legal_pages(database):
    for slug, title, content in DEFAULT_PAGES:
        await database.legal_pages.update_one(
            {"slug": slug},
            {"$setOnInsert": {"id": str(uuid.uuid4()), "slug": slug, "title": title,
                              "content": content,
                              "updated_at": datetime.now(timezone.utc).isoformat()}},
            upsert=True)


class PageUpdate(BaseModel):
    title: str
    content: str


async def _admin(current_user: dict = Depends(get_current_user_v2)) -> dict:
    if not current_user.get("is_admin"):
        raise HTTPException(status_code=403, detail="Admin requis")
    return current_user


@legal_pages_router.get("/public/legal-pages")
async def list_pages():
    pages = await db.legal_pages.find({}, {"_id": 0, "content": 0}).to_list(50)
    return {"pages": pages}


@legal_pages_router.get("/public/legal-pages/{slug}")
async def get_page(slug: str):
    page = await db.legal_pages.find_one({"slug": slug}, {"_id": 0})
    if not page:
        raise HTTPException(status_code=404, detail="Page introuvable")
    return page


@legal_pages_router.put("/admin/legal-pages/{slug}")
async def update_page(slug: str, payload: PageUpdate, admin: dict = Depends(_admin)):
    r = await db.legal_pages.update_one(
        {"slug": slug},
        {"$set": {"title": payload.title, "content": payload.content,
                  "updated_at": datetime.now(timezone.utc).isoformat(),
                  "updated_by": admin.get("email")}})
    if not r.matched_count:
        raise HTTPException(status_code=404, detail="Page introuvable")
    return {"success": True}
