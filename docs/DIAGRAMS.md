# KDMARCHE × O'SCOP - Diagrammes BPMN & Statecharts

> Documentation technique des processus métier et machines d'états
> Format: Mermaid (compatible GitHub, GitLab, Notion, MkDocs)

---

## 1. BPMN — ONBOARDING B2B KDMARCHE – O'SCOP

### 1.1 Vue Macro (Processus Principal)

```mermaid
flowchart LR
    A[Entreprise candidate] --> B[Formulaire B2B O'SCOP]
    B --> C[Soumission dossier]
    C --> D{Validation O'SCOP}
    D -->|Refus| E[Refus motivé]
    D -->|Validation| F[Choix abonnement O'SCOP]
    F --> G[Paiement abonnement]
    G --> H[Activation droits O'SCOP]
    H --> I[Provisioning compte KDMARCHE]
    I --> J[Accès centrale B2B]
```

### 1.2 Swimlane (Entreprise / O'SCOP / KDMARCHE)

```mermaid
flowchart LR
    subgraph ENTREPRISE
        A1[Demande accès B2B]
        A2[Choix abonnement]
        A3[Accès centrale]
    end

    subgraph OSCOP
        B1[Réception dossier]
        B2[Contrôle conformité]
        B3{Décision}
        B4[Création abonnement]
        B5[Activation wallet]
        B6[Émission event provisioning]
    end

    subgraph KDMARCHE
        C1[Création compte B2B]
        C2[Activation accès zones]
        C3[Affichage catalogue]
    end

    A1 --> B1
    B1 --> B2
    B2 --> B3
    B3 -->|Refus| A1
    B3 -->|Validation| A2
    A2 --> B4
    B4 --> B5
    B5 --> B6
    B6 --> C1
    C1 --> C2
    C2 --> C3
    C3 --> A3
```

### 1.3 Processus Commande B2B (OPA Gating)

```mermaid
flowchart LR
    A[Utilisateur B2B] --> B[Sélection zone]
    B --> C[Consultation catalogue]
    C --> D{OPA : prix autorisés ?}
    D -->|Non| E[Prix masqués]
    D -->|Oui| F[Ajout au panier]
    F --> G[Choix incoterm EXW]
    G --> H{OPA : EXW valide ?}
    H -->|Non| I[Blocage commande]
    H -->|Oui| J[Validation commande]
    J --> K[Facture KDMARCHE]
    K --> L[Paiement KDMARCHE]
    L --> M[Organisation transport par client]
```

---

## 2. STATECHARTS — Machines d'États

### 2.1 Organisation (ORG)

```mermaid
stateDiagram-v2
    [*] --> DRAFT
    DRAFT --> SUBMITTED : submit_application
    SUBMITTED --> PENDING_REVIEW
    PENDING_REVIEW --> APPROVED : approve
    PENDING_REVIEW --> REJECTED : reject
    APPROVED --> SUSPENDED : compliance_issue
    SUSPENDED --> APPROVED : reinstate
    APPROVED --> CLOSED : terminate
```

**Transitions:**
| De | Vers | Événement | Action Backend |
|----|------|-----------|----------------|
| DRAFT | SUBMITTED | Soumission dossier | `POST /applications/{id}/submit` |
| PENDING_REVIEW | APPROVED | Validation compliance | `POST /applications/{id}/decision` |
| APPROVED | SUSPENDED | Problème compliance/impayé | `POST /admin/orgs/{id}/suspend` |

### 2.2 Abonnement (Subscription)

```mermaid
stateDiagram-v2
    [*] --> INACTIVE
    INACTIVE --> ACTIVE : payment_ok
    ACTIVE --> PAST_DUE : payment_failed
    PAST_DUE --> GRACE_PERIOD
    GRACE_PERIOD --> ACTIVE : payment_recovered
    GRACE_PERIOD --> CANCELED : timeout
    ACTIVE --> CANCELED : cancel
```

**Règles métier:**
- `PAST_DUE` après échec prélèvement
- `GRACE_PERIOD` : 7-14 jours de relance
- `CANCELED` → désactivation accès KDMARCHE

### 2.3 Partenaire KDMARCHE (Provisioning)

```mermaid
stateDiagram-v2
    [*] --> NOT_PROVISIONED
    NOT_PROVISIONED --> PROVISIONED : org_approved
    PROVISIONED --> ACCESS_ENABLED : subscription_active
    ACCESS_ENABLED --> ACCESS_DISABLED : suspension
    ACCESS_DISABLED --> ACCESS_ENABLED : reinstated
    ACCESS_ENABLED --> DEPROVISIONED : org_closed
```

**Événements webhook O'SCOP → KDMARCHE:**
- `org.approved` → PROVISIONED
- `subscription.activated` → ACCESS_ENABLED
- `org.suspended` → ACCESS_DISABLED

### 2.4 Wallet (Portefeuille Crédits)

```mermaid
stateDiagram-v2
    [*] --> ACTIVE
    ACTIVE --> FROZEN : compliance_hold
    FROZEN --> ACTIVE : release_hold
```

### 2.5 Ledger Entry (Écriture Comptable)

```mermaid
stateDiagram-v2
    [*] --> PENDING
    PENDING --> COMMITTED : success
    PENDING --> CANCELED : rollback
```

**Invariant:** Toute consommation crédits suit ce cycle atomique.

### 2.6 Commande / Zone EXW

```mermaid
stateDiagram-v2
    [*] --> NO_ZONE_SELECTED
    NO_ZONE_SELECTED --> ZONE_SELECTED : select_zone
    ZONE_SELECTED --> INCOTERM_EXW_REQUIRED : zone.exw_only=true
    INCOTERM_EXW_REQUIRED --> ORDER_ALLOWED : incoterm=EXW
    INCOTERM_EXW_REQUIRED --> ORDER_BLOCKED : incoterm!=EXW
```

---

## 3. Mapping Diagrammes ↔ Policy OPA

| Diagramme | Transition | Rule OPA | Endpoint |
|-----------|------------|----------|----------|
| ORG | APPROVED → SUSPENDED | `org.status` | `/admin/orgs/{id}/suspend` |
| ABONNEMENT | ACTIVE → PAST_DUE | `subscription.status` | Webhook PSP |
| PARTENAIRE | ACCESS_ENABLED | `partner_accounts.status` | Auto-sync |
| COMMANDE | ORDER_ALLOWED | `incoterm_allowed` | `/orders` |
| PRIX | SHOW / HIDE | `show_price` | `/pricing` |

> **Principe clé:** Zéro logique métier en dur dans le front ou l'API. 
> Toute décision d'accès passe par le Policy Engine (ABAC).

---

## 4. Implémentation Backend

### Collections MongoDB correspondantes

```
orgs                    → Statechart ORG
subscriptions           → Statechart ABONNEMENT
partner_accounts        → Statechart PARTENAIRE
wallets                 → Statechart WALLET
wallet_ledger           → Statechart LEDGER
org_runtime_preferences → Zone sélectionnée
```

### Fichiers source

- `schema_v2.py` : Définition des Enums et modèles
- `abac_policy.py` : Policy Engine (équivalent OPA)
- `routes_v2.py` : Endpoints API

---

*Document généré pour KDMARCHE × O'SCOP - Centrale d'achats B2B ESS*
*Version: 1.0 - Janvier 2025*
