"""PROSPECT'IA — génération LLM de scripts de prospection (emails, messages, scripts vidéo, storyboard)."""
import logging
import os
import uuid

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

BRAND_CONTEXT = (
    "Tu écris pour la Communityplace KDMARCHÉ × O'SCOP : plateforme coopérative B2B2C de "
    "l'Économie Sociale et Solidaire des Outre-mer (Guadeloupe, Martinique, Guyane, La Réunion, Mayotte). "
    "Atouts : prix structurels négociés, achats groupés, logistique inter-îles LOGICOOP (EXW/CIF), "
    "enchères inversées entre fournisseurs, monnaie coopérative CREDI'SCOP, gouvernance SCIC. "
    "Priorité actuelle : recruter des vendeurs (producteurs, grossistes, artisans) et des acheteurs "
    "professionnels (restaurateurs, collectivités, commerces). Le B2C viendra ensuite."
)

TYPE_PROMPTS = {
    "email": "Rédige un email de prospection prêt à envoyer : objet accrocheur (ligne 'OBJET :'), corps 120-180 mots, personnalisable avec {prenom} et {entreprise}, un seul appel à l'action clair vers le lien {lien}. Ton professionnel et chaleureux.",
    "whatsapp": "Rédige un message court de prospection WhatsApp/LinkedIn (60-90 mots max), tutoiement léger professionnel, avec {prenom} et {entreprise}, un appel à l'action vers {lien}. Pas d'objet.",
    "video_script": "Rédige un script vidéo de prospection prêt à tourner (60-90 secondes) au format structuré : pour chaque scène, indique SCÈNE N (durée), VISUEL (description précise du plan) et VOIX OFF (texte exact à dire). Termine par un CTA écran final. 5 à 7 scènes.",
}


async def generate_script(target: str, territory: str, sector: str, lang: str, tone: str, content_type: str) -> str:
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    audience = "de potentiels VENDEURS (fournisseurs/producteurs) à rejoindre la plateforme pour vendre" \
        if target == "vendor" else "de potentiels ACHETEURS professionnels à rejoindre la plateforme pour acheter aux meilleurs prix"
    lang_name = {"fr": "français", "en": "anglais", "es": "espagnol"}.get(lang, "français")
    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"prospectia-{uuid.uuid4()}",
        system_message=f"{BRAND_CONTEXT}\nTu es PROSPECT'IA, copywriter senior en prospection B2B. Réponds uniquement avec le contenu demandé, sans commentaire.",
    ).with_model("openai", "gpt-5.4")
    prompt = (
        f"{TYPE_PROMPTS.get(content_type, TYPE_PROMPTS['email'])}\n"
        f"Cible : convaincre {audience}.\n"
        f"Territoire visé : {territory or 'tous les Outre-mer'}. Secteur : {sector or 'tous secteurs'}.\n"
        f"Ton : {tone or 'professionnel et chaleureux'}. Langue de rédaction : {lang_name}."
    )
    answer = await chat.send_message(UserMessage(text=prompt))
    return str(answer).strip()


async def generate_storyboard_images(script: str, campaign_hint: str) -> list:
    """Génère jusqu'à 3 images d'illustration de storyboard à partir du script vidéo."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    scenes = [l for l in script.split("\n") if "VISUEL" in l.upper()][:3] or [campaign_hint or "Marché coopératif caribéen B2B moderne"]
    urls = []
    upload_dir = os.path.join(os.path.dirname(__file__), "uploads", "prospectia")
    os.makedirs(upload_dir, exist_ok=True)
    for i, scene in enumerate(scenes):
        try:
            chat = LlmChat(
                api_key=os.environ["EMERGENT_LLM_KEY"],
                session_id=f"prospectia-img-{uuid.uuid4()}",
                system_message="You are a professional storyboard illustrator.",
            )
            chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
            msg = UserMessage(text=(
                f"Storyboard illustration, cinematic 16:9 frame, professional B2B marketing video for a Caribbean "
                f"cooperative marketplace (purple and gold brand colors). Scene: {scene[:300]}. "
                f"Clean, modern, photorealistic, no text overlays."))
            _t, images = await chat.send_message_multimodal_response(msg)
            if images:
                import base64
                fname = f"storyboard-{uuid.uuid4().hex[:10]}.png"
                with open(os.path.join(upload_dir, fname), "wb") as f:
                    f.write(base64.b64decode(images[0]["data"]))
                urls.append(f"/api/uploads/prospectia/{fname}")
        except Exception as exc:
            logger.error("Storyboard image %s échouée : %s", i, exc)
    return urls
