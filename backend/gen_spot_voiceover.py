# -*- coding: utf-8 -*-
"""Voix off FR du spot LOLODRIVE : génère 7 clips TTS (nova, tts-1-hd), les ajuste aux
durées de scènes (atempo si dépassement), puis les incruste dans la story verticale.
Le texte concaténé reproduit exactement le narratif validé."""
import asyncio
import os
import subprocess

import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = '/app/backend/uploads/videos/voice'
os.makedirs(OUT, exist_ok=True)

# (clé, texte lu, durée de la scène en secondes)
FRAGMENTS = [
    ('intro', "LOLODRIVE, l'épicerie, propose des produits du terroir.", 4.0),
    ('concept', "Des articles exclusivement accessibles par lot de trois,", 4.0),
    ('produits', "au meilleur prix coopératif négocié.", 20.0),
    ('commande', "Commandez en ligne et en relais, avec votre PASS LOLODRIVE,", 5.0),
    ('preparation', "L'équipe LOLODRIVE prépare vos paniers,", 4.0),
    ('retrait', "et optez pour une livraison ou un retrait drive.", 5.0),
    ('final', "et vous accueille avec plaisir !", 4.0),
]

VOICE = 'nova'
MODEL = 'tts-1-hd'


def _probe(path):
    r = subprocess.run([FFMPEG, '-i', path], capture_output=True, text=True)
    import re
    m = re.search(r'Duration: (\d+):(\d+):([\d.]+)', r.stderr)
    h, mnt, sec = int(m.group(1)), int(m.group(2)), float(m.group(3))
    return h * 3600 + mnt * 60 + sec


def _fit(path, slot):
    """Ajuste le clip au créneau : atempo si dépassement (max 1.3x), sinon laisse tel quel."""
    dur = _probe(path)
    if dur <= slot - 0.15:
        return dur
    ratio = min(dur / (slot - 0.15), 1.3)
    tmp = path + '.tmp.mp3'
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', path,
                    '-filter:a', f'atempo={ratio:.3f}', tmp], check=True)
    os.replace(tmp, path)
    return _probe(path)


async def main():
    from emergentintegrations.llm.openai import OpenAITextToSpeech
    tts = OpenAITextToSpeech(api_key=os.environ['EMERGENT_LLM_KEY'])

    paths = []
    for key, text, slot in FRAGMENTS:
        path = f'{OUT}/voice_{key}.mp3'
        if not os.path.exists(path):
            audio = await tts.generate_speech(text=text, model=MODEL, voice=VOICE, response_format='mp3')
            with open(path, 'wb') as f:
                f.write(audio)
            print('généré', key)
        dur = _fit(path, slot)
        paths.append((path, slot))
        print(f'{key}: {dur:.2f}s / slot {slot}s')

    # Piste complète : chaque clip calé sur son créneau, silence ailleurs (concat, zéro chevauchement)
    inputs, filt, labels = [], [], []
    for i, (path, slot) in enumerate(paths):
        inputs += ['-i', path]
        filt.append(f'[{i}:a]apad,atrim=0:{slot}[s{i}]')
        labels.append(f'[s{i}]')
    full = f'{OUT}/narration_full.mp3'
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', *inputs,
                    '-filter_complex', ';'.join(filt) + ';' + ''.join(labels) + f'concat=n={len(paths)}:v=0:a=1[out]',
                    '-map', '[out]', full], check=True)
    print('narration_full:', f'{_probe(full):.2f}s')

    # Incrustation dans la story verticale (vidéo inchangée, piste audio AAC)
    vert = '/app/backend/uploads/videos/lolospot_vertical.mp4'
    tmp = vert + '.tmp.mp4'
    subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', vert, '-i', full,
                    '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', tmp], check=True)
    os.replace(tmp, vert)
    print('story verticale avec voix off OK')


asyncio.run(main())
