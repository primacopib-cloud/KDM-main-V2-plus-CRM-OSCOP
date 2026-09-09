"""Génère 8 clips Veo 3 (main qui saisit un produit en rayon, lot de 3) pour le spot LOLODRIVE."""
import asyncio
import os
import sys

import httpx
from dotenv import load_dotenv

load_dotenv('/app/backend/.env', override=True)
import fal_client

OUT = '/app/backend/uploads/videos'

PRODUCTS = [
    ('legumes', "fresh vegetables", "three small wicker baskets filled with colorful fresh vegetables (tomatoes, carrots, peppers) standing side by side on a bright supermarket produce shelf"),
    ('yaourts', "yogurts", "three glass jars of white yogurt with cream-colored lids grouped together on a refrigerated supermarket shelf"),
    ('pates', "pasta", "three transparent bags of penne pasta with small kraft labels standing side by side on a bright supermarket shelf"),
    ('riz', "rice", "three transparent bags of long grain white rice with small kraft labels standing side by side on a bright supermarket shelf"),
    ('cereales', "breakfast cereals", "three identical kraft cereal boxes with a wheat icon standing side by side on a bright supermarket breakfast aisle shelf"),
    ('huiles', "cooking oil", "three glass bottles of golden cooking oil with minimal kraft labels standing side by side on a bright supermarket shelf"),
    ('beurre', "butter", "three butter blocks wrapped in parchment-style paper with a small kraft band grouped together on a refrigerated dairy shelf"),
    ('lait', "milk", "three glass bottles of fresh milk with white caps standing side by side on a refrigerated supermarket dairy shelf"),
]

PROMPT = (
    "Ultra-realistic cinematic supermarket footage, shallow depth of field, warm natural lighting. "
    "Close-up on a shelf where {scene}. A customer's hand enters the frame and confidently grabs "
    "one item of the lot of three, then lifts it out of frame. Photorealistic 8k commercial quality, "
    "subtle handheld camera motion, grocery store ambience."
)


async def gen_one(slug, scene_desc):
    prompt = PROMPT.format(scene=scene_desc)
    print(f'[{slug}] submit…', flush=True)
    handler = await fal_client.submit_async(
        'fal-ai/veo3',
        arguments={'prompt': prompt, 'aspect_ratio': '16:9', 'duration': '8s',
                   'generate_audio': True, 'resolution': '720p'},
    )
    result = await handler.get()
    url = (result.get('video') or {}).get('url')
    if not url:
        raise RuntimeError(f'pas d’URL vidéo: {str(result)[:300]}')
    path = os.path.join(OUT, f'lolospot_prod_{slug}.mp4')
    async with httpx.AsyncClient(timeout=120) as c:
        r = await c.get(url)
        r.raise_for_status()
        with open(path, 'wb') as f:
            f.write(r.content)
    print(f'[{slug}] OK -> {path} ({os.path.getsize(path)//1024} Ko)', flush=True)


async def main():
    os.makedirs(OUT, exist_ok=True)
    for slug, _label, scene_desc in PRODUCTS:
        dest = os.path.join(OUT, f'lolospot_prod_{slug}.mp4')
        if os.path.exists(dest):
            print(f'[{slug}] déjà présent, skip', flush=True)
            continue
        try:
            await gen_one(slug, scene_desc)
        except Exception as exc:
            print(f'[{slug}] ÉCHEC: {exc}', flush=True)
    print('TERMINE', flush=True)

asyncio.run(main())
