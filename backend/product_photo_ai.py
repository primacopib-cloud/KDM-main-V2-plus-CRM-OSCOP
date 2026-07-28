"""Génération IA d'une photo d'illustration produit (Gemini Nano Banana via Emergent LLM key)."""
import base64
import os
import uuid

from dotenv import load_dotenv

load_dotenv()


async def generate_product_photo(name: str, category: str = None, brand: str = None) -> str:
    """Génère une photo packshot du produit et retourne l'image_url locale."""
    from emergentintegrations.llm.chat import LlmChat, UserMessage
    api_key = os.environ["EMERGENT_LLM_KEY"]
    chat = LlmChat(api_key=api_key, session_id=f"product-photo-{uuid.uuid4().hex[:8]}",
                   system_message="Tu génères des photos packshot e-commerce de produits d'épicerie.")
    chat.with_model("gemini", "gemini-3.1-flash-image-preview").with_params(modalities=["image", "text"])
    prompt = (f"Photo packshot professionnelle du produit alimentaire : {name}"
              f"{f' ({category})' if category else ''}{f', marque {brand}' if brand else ''}. "
              "Produit centré sur fond neutre clair, éclairage studio doux, style photo e-commerce "
              "d'épicerie antillaise, réaliste, aucun texte ni logo ajouté.")
    _, images = await chat.send_message_multimodal_response(UserMessage(text=prompt))
    if not images:
        raise RuntimeError("Aucune image générée")
    data = base64.b64decode(images[0]["data"])
    up_dir = os.path.join(os.path.dirname(__file__), "uploads", "products")
    os.makedirs(up_dir, exist_ok=True)
    fname = f"product-ia-{uuid.uuid4().hex[:8]}.png"
    with open(os.path.join(up_dir, fname), "wb") as f:
        f.write(data)
    return f"/api/uploads/products/{fname}"
