# -*- coding: utf-8 -*-
"""Musique d'ambiance du spot LOLODRIVE : génération CassetteAI (fal.ai, clé FAL_KEY du projet),
calage sur 46 s (durée du spot), mixage bas volume sous la voix off, incrustation dans la story."""
import os
import subprocess
import urllib.request

import fal_client
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv('/app/backend/.env')
FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
OUT = '/app/backend/uploads/videos/voice'
os.makedirs(OUT, exist_ok=True)
MUSIC_RAW = f'{OUT}/music_bed_raw.wav'
MUSIC = f'{OUT}/music_bed.mp3'
NARRATION = f'{OUT}/narration_full.mp3'
MIX = f'{OUT}/narration_music_mix.mp3'
VERT = '/app/backend/uploads/videos/lolospot_vertical.mp4'
SPOT_DUR = 50.0

PROMPT = ("Soft warm uplifting acoustic advertising background music for a tropical Caribbean grocery "
          "co-op ad: gentle marimba and ukulele melody, light acoustic guitar, subtle soft percussion "
          "and shaker, airy pads, feel-good and friendly, steady mid-tempo, no vocals, no drums drop, "
          "clean mix, loops smoothly")

if not os.path.exists(MUSIC_RAW):
    print('génération musique…')
    result = fal_client.subscribe('CassetteAI/music-generator',
                                  arguments={'prompt': PROMPT, 'duration': SPOT_DUR},
                                  with_logs=False)
    url = result['audio_file']['url']
    print('téléchargement', url[:80])
    urllib.request.urlretrieve(url, MUSIC_RAW)

# Normalise à 46 s avec fondu d'entrée/sortie, encode mp3
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-stream_loop', '-1', '-i', MUSIC_RAW,
                '-af', f'atrim=0:{SPOT_DUR},apad,atrim=0:{SPOT_DUR},afade=t=in:st=0:d=1.5,afade=t=out:st={SPOT_DUR-2.5}:d=2.5',
                '-b:a', '160k', MUSIC], check=True)

# Mixage : musique à bas volume sous la voix off (sidechain léger via volume constant)
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', NARRATION, '-i', MUSIC,
                '-filter_complex', '[0:a]volume=1.0[v];[1:a]volume=0.16[m];[v][m]amix=inputs=2:duration=first:normalize=0[out]',
                '-map', '[out]', '-b:a', '192k', MIX], check=True)

# Incrustation du mix dans la story verticale
tmp = VERT + '.tmp.mp4'
subprocess.run([FFMPEG, '-y', '-loglevel', 'error', '-i', VERT, '-i', MIX,
                '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '128k', '-shortest', tmp], check=True)
os.replace(tmp, VERT)
print('story verticale : voix off + musique OK')
