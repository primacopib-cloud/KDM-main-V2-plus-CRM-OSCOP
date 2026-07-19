# Conception — Module Consultations Compétitives & CPC (Phase 1)
Version 1.0 — 2026-07-19 — Soumis à validation client avant développement

## 1. Rôles et permissions

| Action | O'SCOP Super Admin / Conformité | KDMARCHE Organisateur | Vendeur Pro actif | Acheteur / autres |
|---|---|---|---|---|
| Gérer packs CPC (tarifs, validité) | ✅ | ❌ | ❌ | ❌ |
| Attribution CPC promo/solidaire (motivée) | ✅ | ❌ | ❌ | ❌ |
| Correction administrative CPC (motivée) | ✅ | ❌ | ❌ | ❌ |
| Gérer matrice juridique (ROUGE/ORANGE/VERT) | ✅ | ❌ | ❌ | ❌ |
| Valider juridiquement un lot ORANGE | ✅ (nominatif, daté, motivé) | ❌ | ❌ | ❌ |
| Créer consultation (BROUILLON) | ✅ | ✅ | ❌ | ❌ |
| Validation commerciale | ❌ | ✅ | ❌ | ❌ |
| Validation plateforme/juridique | ✅ | ❌ | ❌ | ❌ |
| Publier (si conditions remplies) | ✅ | ✅ (sauf ORANGE non validée → blocage technique) | ❌ | ❌ |
| Acheter pack CPC | ❌ | ❌ | ✅ | ❌ |
| S'inscrire à une consultation (débit CPC) | ❌ | ❌ | ✅ (si éligible) | ❌ |
| Déposer une offre (EUR HT) | ❌ | ❌ | ✅ (inscrit) | ❌ |
| Voir contenu offres scellées avant clôture | ❌ (bloqué techniquement) | ❌ (bloqué) | Sa propre offre uniquement | ❌ |
| Valider l'attribution définitive | co-validation dérogation | ✅ | ❌ | ❌ |
| Attribution dérogatoire (≠ 1er du classement) | ✅ (2e validation) | ✅ (1re validation + motivation) | ❌ | ❌ |
| Consulter/exporter journal d'audit | ✅ | Ses consultations | Ses propres événements | ❌ |
| Modifier/supprimer journal d'audit | ❌ PERSONNE | ❌ | ❌ | ❌ |
| Demander identité du candidat retenu | — | — | ✅ (participant, tracé) | ❌ |

Éligibilité Vendeur Pro (contrôle cumulatif à l'inscription) : abonnement actif non suspendu + statut approved + acceptation règlement CPC & règlement de la consultation + territoire/catégorie autorisés par le lot. Statut « Fournisseur invité » : prévu dans le modèle (`participant_type: "invited"`) mais NON activé en V1.
KDMARCHE peut mettre des produits aux enchères (rôle Organisateur). Acheteurs, admins, collaborateurs : jamais d'offres.

## 2. Machine à états — Consultation

```
BROUILLON → EN_VALIDATION → VALIDEE → PUBLIEE → INSCRIPTIONS_OUVERTES → EN_COURS
   → CLOTUREE → EN_EVALUATION → ATTRIBUEE → ARCHIVEE
Sorties possibles : SANS_SUITE (depuis CLOTUREE/EN_EVALUATION), ANNULEE (depuis PUBLIEE..EN_COURS, recrédit CPC automatique)
```
Gardes de publication (bloquantes) : classification juridique versionnée présente ; ROUGE → procédure=SCELLEE forcée (aucun override) ; ORANGE → validation juridique nominative enregistrée sinon publication techniquement refusée (HTTP 409) ; critères = 100 % ; coût CPC fixé ; dates cohérentes (open < close, close > now) ; cahier des charges complet ; double validation (commerciale KDMARCHE + plateforme O'SCOP) pour ORANGE et interterritoriale.
Après PUBLIEE : type, statut juridique, produits, volumes, territoires, dates, critères, pondérations, coût CPC, tours, règles clôture/départage/attribution → verrouillés (snapshot immuable `published_snapshot` + hash SHA-256). Modification substantielle = ANNULEE + recrédit auto + nouvelle version (`version+1`, nouveau consentement participants).
Clôture : heure serveur fixe, job scheduler + vérification à chaque lecture (pas de prolongation V1).

## 3. Machine à états — Solde CPC & mouvement

Solde = somme du registre append-only (jamais de champ "balance" modifiable seul ; un champ dénormalisé `cpc_balance` est recalculable et vérifié).
```
Mouvement : PENDING(uniquement achat, avant webhook) → SETTLED  |  achat non payé → EXPIRED
Compte CPC : ACTIF → GELE (chargeback avec solde insuffisant) → REGULARISE
```
Types de mouvements : `PACK_PURCHASE` (+, après webhook Stripe uniquement), `PROMO_GRANT` (+, motif+auteur), `CONSULTATION_ENTRY` (−), `REPORT_PURCHASE` (−), `REFUND_CANCELLATION` (+, annulation consultation), `REFUND_INCIDENT` (+, incident technique avéré), `EXPIRY` (−, validité 12 mois paramétrable), `ADMIN_CORRECTION` (±, motif+auteur+réf obligatoires), `STRIPE_REVERSAL` (−, remboursement/chargeback : annule les CPC non consommés du pack).
Chaque mouvement : `{id, user_id, type, qty(±), balance_before, balance_after, consultation_id?, pack_id?, stripe_session_id?, stripe_event_id?, idempotency_key, reason, author(user|system), created_at}` — collection `cpc_ledger`, aucun UPDATE/DELETE (append-only), correction = contre-écriture.

## 4. Modèle de données (MongoDB)

- `cpc_packs` : `{id, label, credits, price_ht_cents, vat_applicable(bool), active, validity_months(12), stripe_product_id?, created_at}` + `cpc_pack_price_history` : `{pack_id, price_ht_cents, credits, changed_by, changed_at}`
- `cpc_ledger` : cf. §3 (index unique sur `idempotency_key`)
- `cpc_accounts` : `{user_id, status: ACTIF|GELE|REGULARISE, cpc_balance(dénormalisé), updated_at}`
- `legal_matrix` : `{id, scope: category|sku, category?, sku_ean?, status: ROUGE|ORANGE|VERT, legal_reason, legal_reference("L.442-8 III"...), author, validated_at, next_review_at, version, attachments[]}` — versionné, jamais écrasé (nouvelle version)
- `consultations` : `{id, ref("CONS-2026-0001"), version, title, type: STANDARD|INTERTERRITORIALE, procedure: SCELLEE|ENCHERE_INVERSEE, legal_status(ROUGE/ORANGE/VERT), legal_matrix_version, orange_validation:{author,date,reason}?, products[{sku,ean,label,volume,unit}], territories[], specs_md, cpc_cost, max_rounds(3), criteria[{key,label,weight,formula,scale,sources,evidence_required}], tie_break_order[quality,logistics,availability,traceability,first_timestamp], opens_at, closes_at, status, validations:{commercial:{by,at}?, platform:{by,at}?}, published_snapshot_hash, rcr_applicable(bool), created_by, created_at}`
- `consultation_entries` : `{id, consultation_id, vendor_user_id, participant_type: vendor_pro|invited, accepted_rules_at, cpc_ledger_id, status: INSCRIT|RETIRE, created_at}`
- `bids` : `{id, consultation_id, entry_id, round(1-3), amount_ht_cents, currency:"EUR", details{delivery_days, availability_pct, ...}, sealed_payload?(chiffré AES-GCM clé serveur, scellée), payload_sha256, server_ts, superseded_by?(scellée : remplacement versionné), status: VALIDE|REMPLACEE}` — enchère inversée : 1 offre validée par tour, ni modifiable ni supprimable ; scellée : remplacement autorisé avant clôture avec historique.
- `consultation_awards` : `{consultation_id, ranking[{entry_id, scores{...}, total}], awarded_entry_id, derogation?:{reason, validated_by:[kdm,oscop], at}, validated_by, validated_at, pv_pdf_ref, pv_sha256}`
- `audit_journal` : `{id, consultation_id?, event_type, actor, payload, sha256_chain(hash de l'événement précédent → chaîne d'intégrité), created_at}` — append-only, conservation 5 ans (paramètre `AUDIT_RETENTION_YEARS=5`, min légal 1 an)
- `winner_identity_requests` : `{consultation_id, requester_entry_id, requested_at, answered_at, response}` (obligation L.442-8)
- `nominative_attestations` (projet post-attribution) : `{consultation_id, supplier, products[], volumes, unit_prices_ht, totals_ht, territory, valid_from, valid_until, schedule, consultation_ref, fogedom_rcr_ref?}` — document PROJET, ne vaut ni paiement, ni facture, ni RCR.

Séparation stricte : `cpc_ledger` ⟂ commandes/marchandises ⟂ registre FOGEDOM-RCR (aucune référence croisée sauf champ informatif `fogedom_rcr_ref` sur l'attestation).

## 5. Stripe — événements et webhooks

- Compte : **O'SCOP** (`get_stripe_key("oscop")`) — jamais le compte KDMARCHE, transaction séparée de l'abonnement (même customer possible).
- Checkout Session `mode=payment` (ponctuel), montants lus depuis `cpc_packs` en base (aucun prix en dur), TVA calculée via `vat.py` selon pays du vendeur.
- `metadata` : `{kind:"CPC_PACK", user_id, pack_id, credits, territory, internal_ref}`
- Webhooks traités (endpoint existant `/api/checkout/webhook` + dispatcher `kind=CPC_PACK`) :
  - `checkout.session.completed` (payment_status=paid) → crédit CPC
  - `charge.refunded` → `STRIPE_REVERSAL`
  - `charge.dispute.created` → `STRIPE_REVERSAL` + gel si solde insuffisant + alerte admin
- **Le crédit n'a JAMAIS lieu sur la page de succès** : la page succès affiche « paiement en cours de confirmation » et poll le solde ; seul le webhook vérifié (signature) crédite.
- Facture de service O'SCOP générée (PDF interne numéroté série `FACT-CPC-YYYY-XXXX`, distincte de la série adhésion) + email Brevo.

## 6. Idempotence

- Clé : `stripe_event_id` + index unique `cpc_ledger.idempotency_key` (= `evt_xxx:credit` / `sess_xxx:credit`). Un événement rejoué → insertion refusée par l'index → no-op journalisé.
- Inscription consultation : clé `entry:{consultation_id}:{user_id}` → double clic impossible, un seul débit.
- Recrédit annulation : clé `refund:{consultation_id}:{entry_id}` → recrédit unique.
- Transactions : débit + création entry dans l'ordre débit→entry avec compensation automatique en cas d'échec (contre-écriture journalisée).

## 7. Journal d'audit — format

Événements (minimum) : `LOT_CREATED, LOT_UPDATED, LEGAL_CLASSIFIED, LEGAL_VALIDATED_ORANGE, VALIDATION_COMMERCIAL, VALIDATION_PLATFORM, PUBLISHED, ENTRY_REGISTERED, CPC_DEBIT, CPC_CREDIT, BID_SUBMITTED, BID_REPLACED(scellée), SEALED_OPENED, RANKING_COMPUTED, INCIDENT, ADMIN_SENSITIVE_ACCESS, CLOSED, SCORED, AWARD_VALIDATED, DEROGATION, WINNER_IDENTITY_REQUESTED, CANCELLED, NO_FOLLOW_UP, EXPORTED`.
Chaque entrée : `{seq, event_type, actor{id,role}, consultation_id?, payload(JSON), ts_server, sha256_prev, sha256_self}` — chaînage de hachage : toute altération casse la chaîne, vérifiable par un endpoint d'intégrité. Export CSV + JSON par consultation ou par période.

## 8. Procès-verbal de clôture (PDF)

Généré à l'attribution (ou SANS_SUITE/ANNULEE) — reportlab, charte violet/or :
1. Référence + version du règlement + hash du snapshot publié
2. Catégorie juridique appliquée (statut, version matrice, référence légale)
3. Participants admis (raison sociale, date d'inscription)
4. Chronologie horodatée (publication → clôture → évaluation)
5. Offres finales par participant (EUR HT) — pour scellée : empreintes + date d'ouverture
6. Grille de critères, pondérations, scores détaillés, classement
7. Attributaire + motivation (+ dérogation le cas échéant avec double validation)
8. Incidents éventuels
9. Validations électroniques (nom, rôle, horodatage) + empreinte SHA-256 du PDF
Archivé en base + poussé vers la GED (circuit d'archivage existant) ; accessible aux participants (version sans données confidentielles des tiers).

## 9. Critères de recette (tests d'acceptation)

1. **Blocage ROUGE** : création d'une consultation sur un lot ROUGE → le champ procédure est forcé SCELLEE ; tentative API de passer en enchère → 409, même en Super Admin.
2. **Blocage ORANGE** : publication refusée (409) tant que la validation juridique nominative n'est pas enregistrée ; après validation → publication OK et validation tracée.
3. **Idempotence CPC** : rejeu du même webhook `checkout.session.completed` 3× → un seul crédit ; retour page succès sans webhook → solde inchangé.
4. **Débit unique** : double clic inscription → un seul débit, une seule entry.
5. **Pay-per-bid interdit** : 3 tours d'offres sur une enchère → aucun débit CPC supplémentaire après l'inscription.
6. **Recrédit annulation** : annulation par l'organisateur → 100 % des inscrits recrédités automatiquement, une seule fois, journalisé.
7. **Scellée étanche** : GET admin sur le contenu des offres avant clôture → 403 + événement `ADMIN_SENSITIVE_ACCESS` journalisé ; après clôture → ouverture simultanée journalisée.
8. **Clôture serveur** : offre soumise après closes_at → 410 refusée.
9. **Classement** : scores conformes aux pondérations (cas de test chiffré fourni) ; égalité → départage déterministe dans l'ordre validé ; CPC détenus sans effet sur le rang.
10. **Verrouillage** : PUT sur critères d'une consultation publiée → 409.
11. **Chargeback** : simulation `charge.dispute.created` → CPC non consommés annulés ; solde insuffisant → compte GELE.
12. **PV & journal** : PV généré avec hash ; chaîne d'audit vérifiée intègre ; export CSV/JSON OK.
13. **Identité gagnant** : participant demande l'identité du retenu → réponse fournie + demande/réponse conservées.
14. **Anonymat** : pendant l'enchère un vendeur voit son rang et l'écart, jamais l'identité des concurrents.

## 10. Découpage Phase 1 (ordre de réalisation)

- **Lot 1.1 — Socle CPC** : packs (CRUD admin + historique prix), Stripe Checkout + webhook + idempotence, registre append-only, facture service O'SCOP, UI vendeur (solde + achat + historique), UI admin (packs, corrections motivées, attributions promo).
- **Lot 1.2 — Matrice juridique** : collection versionnée, UI admin (catégories/SKU, statuts, motifs, pièces), validation ORANGE nominative.
- **Lot 1.3 — Consultations** : machine à états, double validation, verrouillage/snapshot/hash, création KDMARCHE Organisateur, publication avec gardes.
- **Lot 1.4 — Participation** : éligibilité, affichage règlement + coût avant confirmation, inscription/débit, offres scellées (chiffrées, remplaçables, empreintes) et enchère inversée (rang + écart anonymes, 3 tours, horodatage serveur, clôture fixe).
- **Lot 1.5 — Évaluation & attribution** : scoring multicritère, départage déterministe, validation attribution KDMARCHE, dérogation double-validée, demande d'identité du gagnant, projet d'Attestation nominative.
- **Lot 1.6 — Audit & PV** : journal chaîné, exports CSV/JSON, PV PDF, archivage GED, endpoint intégrité.
- Chaque lot testé (curl + testing agent) avant le suivant. Règle d'Or < 500 lignes respectée (fichiers dédiés : `routes_cpc.py`, `cpc_ledger.py`, `routes_legal_matrix.py`, `routes_consultations.py`, `routes_bids.py`, `consultation_scoring.py`, `consultation_pv_pdf.py`, `routes_consultation_audit.py`).

Phase 2 (après recette Phase 1) : Réponse Rapide (popover messagerie avec rattachement consultation/commande/facture, permissions par rôle, journalisation) + Factures Acheteur (séparation stricte émetteur KDMARCHE marchandises / O'SCOP services, jamais fusionnées).
