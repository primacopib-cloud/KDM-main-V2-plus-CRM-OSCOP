"""TVA automatique selon le pays du souscripteur (B2B)."""

# DOM : GP/MQ/RE 8,5 % — GF/YT exonérés — FR métropole 20 %
DOM_85 = {"GP", "MQ", "RE"}
DOM_0 = {"GF", "YT"}
EU = {"AT", "BE", "BG", "HR", "CY", "CZ", "DK", "EE", "FI", "DE", "GR", "HU", "IE",
      "IT", "LV", "LT", "LU", "MT", "NL", "PL", "PT", "RO", "SK", "SI", "ES", "SE"}


def vat_rate(country: str | None) -> float:
    c = (country or "").upper()
    if c in DOM_85:
        return 8.5
    if c in DOM_0:
        return 0.0
    if c == "FR":
        return 20.0
    return 0.0  # UE hors France : autoliquidation B2B — hors UE : exonéré


def vat_label(country: str | None) -> str:
    c = (country or "").upper()
    if c in DOM_85:
        return "TVA DOM 8,5 %"
    if c in DOM_0:
        return "Exonéré (art. 294 CGI)"
    if c == "FR":
        return "TVA 20 %"
    if c in EU:
        return "Autoliquidation UE (art. 196 dir. 2006/112/CE)"
    return "Exonéré — hors UE"


def compute_vat(price_ht_cents: int, country: str | None) -> dict:
    rate = vat_rate(country)
    vat_cents = round(price_ht_cents * rate / 100)
    return {"rate": rate, "ht_cents": price_ht_cents, "vat_cents": vat_cents,
            "ttc_cents": price_ht_cents + vat_cents, "label": vat_label(country)}
