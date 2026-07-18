"""Studio IA média produit : génération d'image (Nano Banana), amélioration photo, spot vidéo (fal.ai)."""
from __future__ import annotations

import base64
import os
import uuid

from dotenv import load_dotenv

load_dotenv()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads", "products")

STUDIO_STYLE = (
    "Professional studio product photography, cinematic lighting, ultra high quality, "
    "clean commercial e-commerce shot, photorealistic, 8k detail. "
    "Keep any text minimal: less than 20% of the image surface may contain text."
)


def _save_png(image_b64: str, prefix: str) -> str:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    filename = f"{prefix}-{uuid.uuid4().hex[:8]}.png"
    with open(os.path.join(UPLOAD_DIR, filename), "wb") as f:
        f.write(base64.b64decode(image_b64))
    return f"/api/uploads/products/{filename}"


async def generate_product_image(prompt: str, product_id: str) -> str:
    """Génère une image produit qualité studio depuis un prompt. Retourne l'URL relative."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage

    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"img-gen-{uuid.uuid4()}",
        system_message="You are a professional product photographer AI.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    msg = UserMessage(text=f"{prompt}. {STUDIO_STYLE}")
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError("Aucune image générée par l'IA")
    return _save_png(images[0]["data"], product_id)


async def enhance_product_image(image_path: str, product_id: str, instructions: str = "") -> str:
    """Remasterise une photo produit téléversée en rendu studio professionnel."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage, ImageContent

    with open(image_path, "rb") as f:
        image_b64 = base64.b64encode(f.read()).decode("utf-8")

    chat = LlmChat(
        api_key=os.environ["EMERGENT_LLM_KEY"],
        session_id=f"img-enh-{uuid.uuid4()}",
        system_message="You are a professional product photo retoucher AI.",
    )
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    prompt = (
        "Enhance this product photo into a professional studio shot: clean neutral background, "
        f"perfect cinematic lighting, sharp focus on the product, commercial quality. {instructions}. {STUDIO_STYLE}"
    )
    msg = UserMessage(text=prompt, file_contents=[ImageContent(image_b64)])
    _text, images = await chat.send_message_multimodal_response(msg)
    if not images:
        raise RuntimeError("Aucune image retournée par l'IA")
    return _save_png(images[0]["data"], product_id)


def is_video_configured() -> bool:
    return bool(os.environ.get("FAL_KEY"))


async def generate_product_video(prompt: str, image_url_abs: str | None = None) -> dict:
    """Spot publicitaire produit via fal.ai (Veo 3). Retourne {video_url}. Nécessite FAL_KEY."""
    if not is_video_configured():
        raise RuntimeError("FAL_KEY non configurée")
    import fal_client

    ad_prompt = (
        f"Cinematic professional product advertisement: {prompt}. "
        "Studio quality, dramatic lighting, smooth camera movement, ultra professional commercial spot. "
        "Minimal on-screen text (less than 20% of frame)."
    )
    if image_url_abs:
        handler = await fal_client.submit_async(
            "fal-ai/veo3/fast/image-to-video",
            arguments={"prompt": ad_prompt, "image_url": image_url_abs},
        )
    else:
        handler = await fal_client.submit_async(
            "fal-ai/veo3/fast",
            arguments={"prompt": ad_prompt},
        )
    result = await handler.get()
    video = result.get("video") or {}
    return {"video_url": video.get("url"), "raw": {k: v for k, v in result.items() if k != "video"}}
