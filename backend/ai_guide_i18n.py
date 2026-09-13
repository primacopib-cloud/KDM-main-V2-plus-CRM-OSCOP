"""Textes multilingues Oracle — français, anglais, espagnol, créole antillais (gcf)."""

SUPPORTED_LANGS = ["fr", "en", "es", "gcf"]

GREETINGS = {
    "fr": {"hello": "Bonjour{name} 👋 Je suis Oracle, votre copilote Communityplace.",
           "note": " À noter aujourd'hui : {facts}.", "ask": " Comment puis-je vous guider ?"},
    "en": {"hello": "Hello{name} 👋 I'm Oracle, your Communityplace copilot.",
           "note": " Worth noting today: {facts}.", "ask": " How can I help you?"},
    "es": {"hello": "Hola{name} 👋 Soy Oracle, su copiloto de Communityplace.",
           "note": " A tener en cuenta hoy: {facts}.", "ask": " ¿Cómo puedo ayudarle?"},
    "gcf": {"hello": "Bonjou{name} 👋 Sé mwen Oracle, kopilòt a'w asi Communityplace.",
            "note": " Jòdi-la, gadé sa : {facts}.", "ask": " Ki jan an pé édé'w ?"},
}

FACT_TEMPLATES = {
    "buyer": {
        "fr": "{unpaid} facture(s) transport en attente de règlement, {ots} OT émis",
        "en": "{unpaid} transport invoice(s) awaiting payment, {ots} transport orders issued",
        "es": "{unpaid} factura(s) de transporte pendiente(s) de pago, {ots} órdenes emitidas",
        "gcf": "{unpaid} fakti transpò poko péyé, {ots} OT voyé",
    },
    "admin": {
        "fr": "{pending} OT en attente d'acceptation, {disputes} litige(s) ouvert(s)",
        "en": "{pending} transport orders awaiting acceptance, {disputes} open dispute(s)",
        "es": "{pending} órdenes pendientes de aceptación, {disputes} litigio(s) abierto(s)",
        "gcf": "{pending} OT ka atann aksèptasyon, {disputes} litij ouvè",
    },
    "vendor": {
        "fr": "{pending} produit(s) en attente de validation",
        "en": "{pending} product(s) awaiting validation",
        "es": "{pending} producto(s) pendiente(s) de validación",
        "gcf": "{pending} pwodui ka atann validasyon",
    },
}

SUGGESTIONS_I18N = {
    "en": {
        "buyer": ["How does the 45% CREDI'SCOP guarantee for pay-on-delivery work?",
                  "How do I top up my credits in one click from checkout?",
                  "How do I filter my notifications by category?", "How do I launch a competitive consultation?"],
        "vendor": ["How do I add a product to the catalog?", "Why should I fill in product weight and volume?",
                   "Where can I track my received orders?"],
        "admin": ["Summarize the platform's financial health", "How does the 30/60/90-day treasury work?",
                  "What to do about a 45-day unpaid transport invoice?"],
        "member": ["How does the PASS Vie Chère work?", "How do I top up my UC?",
                   "How do I pick up my order at a Lolo Point?"],
        "general": ["What can I do on Communityplace?", "How do I join the cooperative?"],
    },
    "es": {
        "buyer": ["¿Cómo funciona la garantía CREDI'SCOP del 45 % para el pago a la recepción?",
                  "¿Cómo recargo mis créditos en un clic desde el checkout?",
                  "¿Cómo filtro mis notificaciones por categoría?", "¿Cómo lanzo una consulta competitiva?"],
        "vendor": ["¿Cómo añado un producto al catálogo?", "¿Por qué indicar el peso y el volumen de mis productos?",
                   "¿Dónde sigo mis pedidos recibidos?"],
        "admin": ["Resume la salud financiera de la plataforma", "¿Cómo funciona la tesorería 30/60/90 días?",
                  "¿Qué hacer con una factura de transporte impagada a 45 días?"],
        "member": ["¿Cómo funciona el PASS Vie Chère?", "¿Cómo recargo mis UC?",
                   "¿Cómo retiro mi pedido en un Lolo Point?"],
        "general": ["¿Qué puedo hacer en Communityplace?", "¿Cómo me adhiero a la cooperativa?"],
    },
    "gcf": {
        "buyer": ["Ki jan garanti CREDI'SCOP 45 % la ka maché pou péyé a résèpsyon ?",
                  "Ki jan pou richajé krédi an mwen an on sèl klik dépi checkout-la ?",
                  "Ki jan pou filtré notifikasyon an mwen pa katégori ?", "Ki jan pou lansé on konsiltasyon ?"],
        "vendor": ["Ki jan pou mèt on pwodui adan katalòg-la ?", "Poukisa pou mèt pwa é volim a pwodui an mwen ?",
                   "Ki koté pou suiv komann an mwen ?"],
        "admin": ["Ba mwen on rezimé asi lajan a platfòm-la", "Ki jan trézorèri 30/60/90 jou ka maché ?",
                  "Ka pou fè èvè on fakti transpò poko péyé a 45 jou ?"],
        "member": ["Ki jan PASS Vie Chère-la ka maché ?", "Ki jan pou richajé UC an mwen ?",
                   "Ki jan pou pran komann an mwen adan on Lolo Point ?"],
        "general": ["Ka an pé fè asi Communityplace ?", "Ki jan pou antré adan koopérativ-la ?"],
    },
}

LANG_NAMES = {"fr": "français", "en": "anglais (English)", "es": "espagnol (español)",
              "gcf": "créole antillais (kréyòl)"}


def norm_lang(lang: str) -> str:
    lang = (lang or "fr").lower()[:3]
    if lang.startswith("en"):
        return "en"
    if lang.startswith("es"):
        return "es"
    if lang in ("gcf", "cre", "kre"):
        return "gcf"
    return "fr"
