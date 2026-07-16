export const contratTransportLogiscopContent = {
  id: "contrat-transport",
  title: "CONTRAT DE TRANSPORT DE MARCHANDISES",
  subtitle: "Livraison LOGI'SCOP — B2B Outre-mer",
  version: "1.0",
  dateEffet: "{{DATE_EFFET}}",
  reference: "{{REF_CONTRAT_TRANSPORT}}",
  entity: "LOGI'SCOP",
  accentColor: "#8B5CF6",
  disclaimer: "La livraison LOGI'SCOP est une prestation de transport indépendante, distincte de la vente des marchandises, exécutée par un opérateur logistique ESS.",
  sections: [
    {
      number: "1",
      title: "Objet",
      content: `Le présent contrat définit les conditions dans lesquelles LOGI'SCOP assure, à la demande du Client, une prestation de transport de marchandises depuis un **point EXW local LOGI'SCOP** jusqu'au lieu de livraison indiqué.

Ce contrat est **distinct** de toute vente de marchandises réalisée par un tiers (notamment KDMARCHE).`
    },
    {
      number: "2",
      title: "Nature juridique de la prestation",
      highlight: true,
      content: `- LOGI'SCOP agit exclusivement en qualité de **transporteur/logisticien**.
- LOGI'SCOP **ne vend pas**, **n'achète pas** et **n'encaisse pas** le prix des marchandises.
- Le contrat ne constitue ni mandat de vente, ni commission commerciale, ni intermédiation financière, ni assurance.
- La prestation est réalisée dans le respect de la réglementation applicable au transport routier de marchandises.`
    },
    {
      number: "3",
      title: "Conditions de souscription",
      content: `La livraison LOGI'SCOP est une **option facultative**, proposée après la mise à disposition EXW locale.

Le Client souscrit la prestation :
- soit directement auprès du Transporteur,
- soit via l'interface de commande KDMARCHE, lorsque la refacturation est autorisée.

La souscription vaut acceptation pleine et entière du présent contrat.`
    },
    {
      number: "4",
      title: "Périmètre de la prestation",
      content: `La prestation comprend, selon la zone et l'option souscrite :
- enlèvement des marchandises au point EXW LOGI'SCOP,
- chargement du véhicule,
- transport jusqu'à l'adresse du Client,
- déchargement standard,
- remise de la marchandise contre preuve de livraison.

**Exclusions** (sauf stipulation expresse) :
- montage, installation, manutention spéciale,
- livraison en étage sans ascenseur,
- formalités douanières,
- assurance ad valorem spécifique.`
    },
    {
      number: "5",
      title: "Zones, tournées et délais",
      content: `Les livraisons sont organisées par zone géographique. LOGI'SCOP peut mettre en place des **tournées mutualisées** (logique ESS) afin d'optimiser les coûts et l'empreinte carbone.

Les délais communiqués sont indicatifs et peuvent dépendre :
- de la consolidation,
- des contraintes locales,
- des conditions de circulation et météorologiques.`
    },
    {
      number: "6",
      title: "Tarifs et facturation",
      content: `Les tarifs sont communiqués avant la confirmation de la livraison.

La facturation est émise :
- soit directement par LOGI'SCOP au Client,
- soit par refacturation via KDMARCHE lorsque prévu contractuellement.

**Les frais de transport sont distincts du prix des marchandises.**`
    },
    {
      number: "7",
      title: "Transfert des risques",
      content: `Le transport débute après la prise en charge des marchandises au point EXW locale LOGI'SCOP.

LOGI'SCOP assume la responsabilité des marchandises pendant le transport, dans les limites prévues à l'article 9.

Le transfert des risques intervient à la remise effective au Client, matérialisée par une **preuve de livraison**.`
    },
    {
      number: "8",
      title: "Obligations du Client",
      content: `Le Client s'engage à :
- fournir une adresse exacte et accessible,
- être présent ou représenté au créneau convenu,
- vérifier l'état des marchandises à la livraison,
- formuler toute réserve immédiatement et par écrit sur le bon de livraison.`
    },
    {
      number: "9",
      title: "Responsabilité du Transporteur",
      content: `La responsabilité de LOGI'SCOP est limitée conformément à la réglementation applicable au transport de marchandises (plafonds légaux par kilogramme ou par envoi).

LOGI'SCOP n'est pas responsable :
- des vices propres de la marchandise,
- des emballages fournis par des tiers,
- des dommages indirects (perte d'exploitation, manque à gagner).`
    },
    {
      number: "10",
      title: "Assurances",
      content: `LOGI'SCOP déclare être titulaire d'une **assurance responsabilité civile transporteur** couvrant les dommages aux marchandises transportées.

Une attestation d'assurance est tenue à disposition du Client sur demande.`
    },
    {
      number: "11",
      title: "Impossibilité de livraison",
      content: `En cas d'absence du Client, d'adresse inaccessible ou de refus de livraison :
- la livraison peut être reprogrammée,
- des frais supplémentaires peuvent être facturés,
- ou la marchandise peut être remise à disposition EXW locale.`
    },
    {
      number: "12",
      title: "Force majeure",
      content: `Aucune Partie ne pourra être tenue responsable d'un manquement résultant d'un événement de force majeure tel que défini par la jurisprudence française.`
    },
    {
      number: "13",
      title: "Données & confidentialité",
      content: `Les données personnelles sont traitées exclusivement pour l'exécution de la prestation, conformément au RGPD.

Les informations commerciales et logistiques sont confidentielles.`
    },
    {
      number: "14",
      title: "Durée",
      content: `Le présent contrat s'applique pour chaque prestation de transport souscrite et prend fin à l'issue de la livraison ou de la remise EXW locale.`
    },
    {
      number: "15",
      title: "Droit applicable & litiges",
      content: `- **Droit applicable** : {{DROIT_APPLICABLE}}.
- **Juridiction compétente** : {{JURIDICTION}} (après tentative de résolution amiable).`
    },
    {
      number: "16",
      title: "Acceptation & signature",
      highlight: true,
      content: `La souscription à une livraison LOGI'SCOP vaut **acceptation contractuelle** du présent contrat.

Le Client reconnaît avoir lu et accepté les conditions du présent contrat. Les preuves de signature (certificat, horodatage, empreinte) sont conservées à des fins probantes.`
    }
  ],
  parties: {
    transporteur: {
      name: "LOGI'SCOP",
      form: "Établissement secondaire de la SCIC O'SCOP",
      role: "Opérateur logistique et transporteur",
      address: "{{LOGISCOP_ADDRESS}}",
      siret: "{{LOGISCOP_SIRET}}",
      email: "logistique@oscop.fr"
    },
    client: {
      name: "{{CLIENT_LEGAL_NAME}}",
      role: "Client final B2B",
      address: "{{CLIENT_ADDRESS}}",
      siret: "{{CLIENT_SIRET}}"
    }
  }
};

// Annexe Tournées Mutualisées ESS
export const annexeTourneesESSContent = {
  id: "annexe-tournees-ess",
  title: "ANNEXE — MODE « TOURNÉES MUTUALISÉES ESS »",
  subtitle: "Tournées planifiées, mutualisation des coûts, règles équitables, traçabilité probante",
  version: "1.0",
  dateEffet: "{{DATE_EFFET}}",
  reference: "ANNEXE-ESS-ROUTE-2026-001",
  entity: "LOGI'SCOP",
  accentColor: "#10B981",
  officialClause: `« La livraison en Tournées ESS est une tournée mutualisée planifiée, destinée à réduire les coûts et l'empreinte carbone. Elle implique une fenêtre de livraison et des règles d'accès équitables et traçables. »`,
  sections: [
    {
      number: "1",
      title: "Objet de l'annexe",
      content: `La présente annexe fixe les conditions particulières applicables lorsque le Client souscrit à un mode de livraison en **tournées mutualisées ESS** (« Tournées ESS »), organisé par LOGI'SCOP dans une logique d'intérêt collectif, de réduction des coûts et d'optimisation environnementale.`
    },
    {
      number: "2",
      title: "Définition des Tournées ESS",
      content: `Une Tournée ESS est une tournée planifiée regroupant plusieurs livraisons B2B sur une zone afin de :
- **Mutualiser** les kilomètres et la capacité véhicule
- **Réduire** le coût unitaire de livraison
- **Diminuer** l'empreinte carbone
- **Garantir** un service accessible aux TPE

Cette tournée est une **prestation de transport distincte** de la vente de marchandises.`
    },
    {
      number: "3",
      title: "Conditions d'éligibilité",
      content: `Sont éligibles les clients situés dans les secteurs couverts par la tournée. Les critères de participation peuvent varier selon :
- La densité de livraisons
- La saisonnalité
- Les contraintes opérationnelles de la zone`
    },
    {
      number: "4",
      title: "Planification / créneaux / fenêtres",
      content: `- LOGI'SCOP communique un **calendrier indicatif** (jours et fenêtres horaires)
- Le Client accepte une **fenêtre de livraison** (ex. 09:00–13:00) et non une heure fixe, sauf option spéciale
- Des **cut-off** (fenêtres de consolidation) peuvent s'appliquer : après cut-off, report à la tournée suivante`
    },
    {
      number: "5",
      title: "Tarification ESS (transparence & non-spéculation)",
      highlight: true,
      content: `La tarification Tournées ESS est déterminée par :
- Une **part fixe mutualisée**
- Le cas échéant, une **part variable** (poids/volume/cartons)

Elle est **affichée avant confirmation**, n'est pas indexée sur le montant de marchandises achetées et exclut toute logique spéculative.`
    },
    {
      number: "6",
      title: "Engagements du client",
      content: `- Être **disponible** sur la fenêtre annoncée
- Fournir un **accès de livraison praticable** et un point de dépôt accessible
- **Vérifier la marchandise** immédiatement à la remise et formuler toute réserve sur le POD
- Limiter les modifications tardives hors-process`
    },
    {
      number: "7",
      title: "Absence / refus / impossibilité",
      content: `En cas d'absence, d'adresse erronée ou d'accès impossible :
- La livraison peut être **reprogrammée**
- Des **frais** peuvent s'appliquer selon barème public
- La marchandise peut être remise à disposition **EXW local**`
    },
    {
      number: "8",
      title: "Priorisation équitable (règle ESS)",
      highlight: true,
      content: `En cas de saturation, LOGI'SCOP applique une priorisation **objective et transparente** basée sur :
- Respect des créneaux
- Historique d'absences
- Stabilité du client
- Critères territoriaux publiés le cas échéant

Toute priorisation est **traçable** (log interne audit).`
    },
    {
      number: "9",
      title: "Preuve de livraison (POD) obligatoire",
      content: `Chaque livraison ESS génère un POD probant comprenant :
- **Signature destinataire** + horodatage
- **Code de vérification** + référence tournée (TourID)
- **Réserves** consignées immédiatement si casse/manquant`
    },
    {
      number: "10",
      title: "Responsabilité & assurance",
      content: `La responsabilité pendant le transport suit la réglementation applicable au transport de marchandises. Les limitations et exclusions prévues au contrat principal s'appliquent.`
    },
    {
      number: "11",
      title: "Durée & acceptation",
      content: `La souscription au mode Tournées ESS vaut **acceptation de la présente annexe**. Elle s'applique à chaque prestation sélectionnée et peut être résiliée selon les dispositions du contrat principal.`
    },
    {
      number: "12",
      title: "Annexe technique (API / documents)",
      content: `Champs recommandés pour l'industrialisation :
- **fulfillment_mode** = LOGISCOP_DELIVERY
- **delivery_mode** = ESS_ROUTE
- **tour_id** (identifiant tournée)
- **route_window_start / route_window_end**
- **pod_verify_code** + **pod_timestamp**
- **priority_reason_code** (si applicable)`
    }
  ],
  tarification: {
    title: "Grille tarifaire indicative Tournées ESS",
    description: "Tarifs mutualisés (réduits vs livraison standard)",
    zones: [
      { code: "971", name: "Guadeloupe", base: "1,80€", perKg: "0,35€/kg", perCarton: "1,20€/carton" },
      { code: "972", name: "Martinique", base: "2,00€", perKg: "0,38€/kg", perCarton: "1,30€/carton" },
      { code: "973", name: "Guyane", base: "3,50€", perKg: "0,60€/kg", perCarton: "2,00€/carton" },
      { code: "974", name: "La Réunion", base: "2,50€", perKg: "0,45€/kg", perCarton: "1,50€/carton" },
      { code: "976", name: "Mayotte", base: "3,00€", perKg: "0,55€/kg", perCarton: "1,80€/carton" }
    ],
    benefits: [
      { label: "Économie vs livraison standard", value: "Jusqu'à -30%" },
      { label: "Réduction empreinte carbone", value: "Mutualisation trajets" },
      { label: "Accessibilité TPE", value: "Pas de minimum de commande" }
    ],
    tvaNote: "TVA DOM applicable (8,5% ou exonération selon zone)"
  }
};

// All legal documents list
