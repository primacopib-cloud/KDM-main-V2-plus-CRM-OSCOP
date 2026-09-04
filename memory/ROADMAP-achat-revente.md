# ROADMAP — Achat-revente O'SCOP, Investisseurs, CREDI'SCOP-I (cahier des charges utilisateur 2026-09)

Spécification complète fournie par l'utilisateur (25 sections) pour centrale.objectifscopoutremer.com. Migrations NON destructives, conserver design/données. Résumé opérationnel :

## PHASE 1 — Fondations juridiques visibles (P0)
- Enum SaleModel: OSCOP_DIRECT_RESALE | PARTNER_DIRECT_SALE sur chaque offre/produit (ProductOffer enrichi : seller/supplier/invoice_issuer/payment_recipient/stock_owner/delivery_operator entity ids, prix d'achat, coûts, coût de revient complet, prix revente HT/TTC, marge prévisionnelle).
- Migration : offres existantes vendues par KDMARCHÉ/PRIMACOP → PARTNER_DIRECT_SALE (journal de migration + rollback ; ne pas toucher aux vendeurs explicites autres).
- Badges obligatoires sur CHAQUE fiche : « VENDU ET FACTURÉ PAR O'SCOP » ou « VENDU ET FACTURÉ PAR [PARTENAIRE] » + bloc dynamique « Répartition des rôles de cette offre » (vendeur, émetteur facture, bénéficiaire paiement, livraison, CGV applicables).
- Accueil : nouveau titre « LA CENTRALE COOPÉRATIVE D'ACHAT, DE RÉFÉRENCEMENT ET DE DISTRIBUTION », texte deux circuits, bloc 2 cartes « Deux circuits commerciaux transparents », 3 boutons (Découvrir les offres / Accès acheteurs pro / Espace investisseurs).
- SUPPRIMER partout : « O'SCOP ne vend rien / ne facture jamais / one sells the other sells nothing ».
- Snapshot immuable des rôles à la création de commande (les commandes anciennes gardent leur vendeur).
- Footer : distinguer SCIC SAS OBJECTIF SCOP OUTREMER (ventes directes + services) vs KDMARCHÉ/PRIMACOP (offres dont elle est vendeur) ; bloc LegalEntitySettings administrable (pas d'adresse hardcodée).

## PHASE 2 — Module achat-revente O'SCOP (P0/P1)
- Routes : /achat-revente, /espace-acheteur/commandes-oscop, /espace-fournisseur/commandes-oscop, /superadmin/achat-revente + achats-fournisseurs + ventes-clients.
- Modèle PurchaseResaleOperation (réf, territoire, branche, client, fournisseur, investisseur, montants achat/coûts/financement/coût de revient/revente/marges prévue+réalisée, funding_instrument, montants payés/encaissés/remboursés) + SupplierPurchaseOrder/SupplierInvoice/ClientSalesOrder/ClientInvoice/GoodsReceipt/DeliveryRecord/OperationCost/OperationMarginStatement.
- 23 statuts workflow (DRAFT → … → CLOSED/SUSPENDED/CANCELLED/DISPUTED, cf. spec §7).
- Calcul coût de revient complet (§11 : fournisseur + transport + assurance + droits + octroi mer + dédouanement + manutention + stockage + qualité + change + financement + coûts directs) ; BLOQUER si coût incomplet, marge négative, seuil non atteint, financement non confirmé. Afficher taux de majoration/marge, écart prévu/réalisé.
- Checkout O'SCOP direct : facture O'SCOP, encaissement compte O'SCOP uniquement, CGV O'SCOP ; checkout partenaire inchangé (compte du vendeur). JAMAIS CREDI'SCOP en moyen de paiement produit.
- Documents PDF (§18) : BC fournisseur, bon d'engagement, ordre/preuve de paiement, BL, facture revente, relevé remboursement, états coût/marge, décisions, dossier clôture.

## PHASE 3 — Investisseurs & CREDI'SCOP-I (P1)
- /espace-investisseur (+/operations, /credi-scop) : 4 blocs SÉPARÉS — abonnement O'SCOP, compteur CREDI'SCOP-I, investissements réels (Bon d'Engagement signé, instrument juridique), remboursements (principal/rémunération séparés).
- CREDI'SCOP-I = unités internes de SERVICES uniquement : renommer partout « wallet »→« Compteur d'unités de services CREDI'SCOP-I » ; AUCUNE valeur €, ni conversion, ni transfert, ni checkout produit, ni paiement fournisseur. Modèles ServiceCreditAccount + ServiceCreditLedgerEntry (ALLOCATION/RESERVATION/DEBIT/RELEASE/EXPIRY/CORRECTION). Catalogue fermé administrable (§9.3 : data room 10 u, qualification fournisseur 20 u, analyses 25/15 u, rapport 25 u, bon d'engagement 20 u, activation workflow 15 u, reporting 10 u, clôture 5 u).
- SupplierPayment (§10) : modes OSCOP_BANK_TRANSFER/OSCOP_CARD/INVESTOR_*_ON_BEHALF_OF_OSCOP/BANK_DOCUMENTARY_CREDIT/OTHER ; facture toujours au nom d'O'SCOP ; mention « payé par X pour le compte de la SCIC » ; Bon d'Engagement signé requis ; zéro donnée carte stockée (PSP/tokenisation).
- Encaissement/remboursement (§12) : créance 100 % O'SCOP ; cascade 70/10/20 NON automatique (CashWaterfallRule configurable, plafonnée) ; InvestorRepayment/CostSettlement/MarginAllocation.

## PHASE 4 — FOGEDOM, juridique, rôles, audit (P2)
- F.O.G.E.D.O.M : workflow rapport préventif (jamais présenté prêteur/assureur/garant) ; FOGEDOMSupportDecision (fonds interne analytique, facultatif, limité aux ressources — interdire « capital garanti », « assurance », « remboursement automatique »).
- Pages juridiques §19 (/conditions-vente-oscop, /conditions-offres-partenaires, /conditions-credi-scop-investissement, /convention-investisseur, /conditions-fournisseurs-oscop, /politique-paiement-et-remboursement, /role-fogedom-scic).
- Rôles serveur §17 (OSCOP_PURCHASING/SALES/FINANCE/COMPLIANCE, FOGEDOM_REVIEWER, INVESTOR_*, SUPPLIER_OWNER, AUDITOR_READ_ONLY) ; vue 360° superadmin ; notifications §22 ; journal d'audit §23 ; RàR reformulé §21.

## Critères de validation (§24) et livraison (§25) : voir message utilisateur du 2026-09 (fichiers modifiés, migrations, mapping, captures, tests, rollback, distinction connecté PSP vs démo).
