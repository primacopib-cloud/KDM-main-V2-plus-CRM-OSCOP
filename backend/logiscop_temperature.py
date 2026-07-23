"""Analyse du relevé de température joint à l'ePOD : détection des ruptures de consigne (article 12)."""
import logging
import os
import re

logger = logging.getLogger(__name__)


def _parse_temp(s) -> float | None:
    m = re.search(r"(-?\d+(?:[.,]\d+)?)", s or "")
    return float(m.group(1).replace(",", ".")) if m else None


def analyze_temperature_csv(raw: bytes, consigne: float, tolerance: float) -> dict | None:
    """Extrait les lectures numériques d'un CSV et détecte les dépassements de consigne ± tolérance."""
    try:
        text = raw.decode("utf-8", errors="ignore")
    except Exception:
        return None
    readings = []
    for line in text.splitlines()[:5000]:
        for part in reversed(re.split(r"[;,\t]", line)):
            m = re.fullmatch(r"\s*(-?\d+(?:[.,]\d+)?)\s*", part)
            if m:
                readings.append(float(m.group(1).replace(",", ".")))
                break
    if not readings:
        return None
    lo, hi = consigne - tolerance, consigne + tolerance
    violations = [r for r in readings if r < lo or r > hi]
    return {
        "readings_count": len(readings), "min": min(readings), "max": max(readings),
        "consigne": consigne, "tolerance": tolerance, "range": [lo, hi],
        "violations_count": len(violations), "violations_sample": violations[:5],
    }


async def process_temperature_analysis(db, ot: dict, raw: bytes, file_name: str) -> dict | None:
    """Analyse le relevé si l'OT est sous température dirigée ; signale l'incident critique si rupture."""
    consigne = _parse_temp(ot.get("temperature"))
    if consigne is None or not file_name.lower().endswith(".csv"):
        return None
    tolerance = _parse_temp(ot.get("temperature_tolerance"))
    if tolerance is None:
        tolerance = 2.0
    analysis = analyze_temperature_csv(raw, consigne, abs(tolerance))
    if not analysis:
        return None
    if analysis["violations_count"] == 0:
        return {**analysis, "incident": False}
    incident = {**analysis, "incident": True}
    from core_deps import create_notification
    await create_notification(
        "logiscop_temperature_incident", "INCIDENT CRITIQUE — rupture de température",
        f"OT {ot['ref']} : {analysis['violations_count']} lecture(s) hors consigne "
        f"{consigne:+.1f} °C ±{abs(tolerance):.1f} (min {analysis['min']:.1f} / max {analysis['max']:.1f} °C). "
        "Article 12 de la Convention — traçabilité conservée.",
        target_roles=["oscop_super_admin", "kdm_b2b_admin"],
        data={"ot_id": ot["id"], "ref": ot["ref"], "violations": analysis["violations_count"]})
    admin_email = os.environ.get("ADMIN_ALERT_EMAIL")
    if admin_email:
        try:
            from brevo_service import send_email
            await send_email(
                to_email=admin_email, to_name="LOGI'SCOP",
                subject=f"[INCIDENT CRITIQUE] Rupture de température — OT {ot['ref']}",
                html_content=(
                    f"<div style='font-family:Arial;color:#2A1045'><h2 style='color:#B91C1C'>Rupture de température — OT {ot['ref']}</h2>"
                    f"<p>Le relevé joint à l'ePOD ({file_name}) révèle <b>{analysis['violations_count']} lecture(s)</b> "
                    f"hors consigne <b>{consigne:+.1f} °C ± {abs(tolerance):.1f}</b> sur {analysis['readings_count']} lectures "
                    f"(min {analysis['min']:.1f} °C, max {analysis['max']:.1f} °C).</p>"
                    f"<p>Donneur d'Ordre : {ot.get('company_name')} — clôture : {(ot.get('epod') or {}).get('outcome') or 'en cours'}.</p>"
                    "<p>Toute rupture constitue un <b>Incident critique</b> (article 12) : données brutes conservées, "
                    "analyse des responsabilités à engager.</p>"
                    "<p style='color:#D4AF37'><b>KDMARCHÉ × O'SCOP — LOGI'SCOP</b></p></div>"),
                tags=["logiscop-temperature-incident"])
        except Exception as exc:
            logger.warning("Email incident température %s échoué : %s", ot["ref"], exc)
    logger.warning("Incident température OT %s : %d violations", ot["ref"], analysis["violations_count"])
    return incident
