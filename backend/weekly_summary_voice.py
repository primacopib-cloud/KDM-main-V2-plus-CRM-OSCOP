"""Résumé vocal hebdomadaire des chiffres clés, lu par Oracle aux admins — FR/EN/ES/GCF."""

SUMMARY_I18N = {
    "fr": ("Voici le résumé de la semaine : {orders} commandes pour {revenue} euros de chiffre d'affaires, "
           "{quotes} demandes de devis dont {conv} converties, {new_users} nouveaux membres, "
           "{apps} candidatures partenaire, et {oq} questions posées à Oracle."),
    "en": ("Here is the weekly summary: {orders} orders for {revenue} euros in revenue, "
           "{quotes} quote requests including {conv} converted, {new_users} new members, "
           "{apps} partner applications, and {oq} questions asked to Oracle."),
    "es": ("Este es el resumen de la semana: {orders} pedidos por {revenue} euros de facturación, "
           "{quotes} solicitudes de presupuesto de las cuales {conv} convertidas, {new_users} nuevos miembros, "
           "{apps} candidaturas de socios y {oq} preguntas hechas a Oracle."),
    "gcf": ("Mi rézimé a simenn-lan : {orders} komenn pou {revenue} éwo chif dafè, "
            "{quotes} demann devi é {conv} adan yo ki konvèti, {new_users} nouvo manm, "
            "{apps} kandidati patnè, é {oq} kèsyon pozé ba Oracle."),
}

TOP_QUESTION_I18N = {
    "fr": "La question la plus posée à Oracle cette semaine : {q}.",
    "en": "The most asked question to Oracle this week: {q}.",
    "es": "La pregunta más frecuente a Oracle esta semana: {q}.",
    "gcf": "Kèsyon yo pozé plis ba Oracle simenn-lasa : {q}.",
}


def build_weekly_summary(stats: dict, lang: str, apps_week: int = 0) -> str:
    lg = lang if lang in SUMMARY_I18N else "fr"
    revenue = f"{stats.get('revenue_eur', 0):.0f}".replace(",", " ")
    text = SUMMARY_I18N[lg].format(
        orders=stats.get("orders", 0), revenue=revenue,
        quotes=stats.get("quotes", 0), conv=stats.get("quotes_converted_week", 0),
        new_users=stats.get("new_users", 0), apps=apps_week,
        oq=stats.get("oracle_questions_week", 0))
    top = stats.get("oracle_top_questions") or []
    if top:
        text += " " + TOP_QUESTION_I18N[lg].format(q=top[0]["question"])
    return text
