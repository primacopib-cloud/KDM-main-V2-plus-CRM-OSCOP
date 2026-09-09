"""Génère la version verticale (9:16, stories/réseaux) du spot LOLODRIVE : textes incrustés via PIL (pas de drawtext), montage ffmpeg."""
import os
import subprocess
import urllib.request

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
IMG = 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/'
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
OUT_DIR = '/tmp/spotv'
W, H = 1240, 2205
os.makedirs(OUT_DIR, exist_ok=True)

SCENES = [
    dict(file='a091c41c190351bb90597d3297306fb13e85be328121e0d12a32f327433143a3.jpeg', dur=4,
         kicker="LOLODRIVE by O'SCOP", title=['VOTRE TERRITOIRE,', 'VOS PRODUITS'], sub="L'épicerie, par lot de 3."),
    dict(file='115eb4dadb3a253b4bb75394a4001db5a35825fb88fc119f3b06e1bb6dccc307.jpeg', dur=4,
         kicker='LE CONCEPT', title=['ACHETEZ PAR LOT ×3'], sub="3 fois plus malin, 3 fois moins cher à l'unité."),
    dict(file='e57486ece7d5da11eb12d89fd66def5a8cd77cad5d927c17ea2b25e0e583752a.jpeg', dur=4,
         kicker='TOUS VOS ESSENTIELS', title=['TOUJOURS PAR 3'], sub='Des volumes groupés, des prix négociés par la coopérative.'),
    dict(file='3eb7e909af822d8bee4a2945d40a93f4465399b835bbcfcc7a555d57527ac45e.jpeg', dur=5,
         kicker='EN LIGNE', title=['COMMANDEZ EN 3 CLICS'], sub='Tout le catalogue à prix mini, depuis votre canapé.'),
    dict(file='53e97ce3eeb653344afa45510ff5095de03f6370b1efd973b63dc6b4dd2b3ea9.jpeg', dur=4,
         kicker='VOTRE RELAIS PRÉPARE', title=['VOS COURSES PRÉPARÉES', 'AVEC SOIN'], sub='Vos essentiels regroupés et préparés pour vous.'),
    dict(file='e60c1ff0ae184631bc39136afbd62932c14607d478bfb3248910ff67ed5c2791.jpeg', dur=5,
         kicker='PRÈS DE CHEZ VOUS', title=['RETRAIT EN POINT RELAIS'], sub='Votre relais LOLODRIVE vous attend au coin de la rue.'),
    dict(file='5a23665bd1ac32b48f3c636d27c1ec6d4a4564a6105c1671e4a1c0436b4b8388.jpeg', dur=4,
         kicker="LOLODRIVE by O'SCOP", title=['LA VIE MOINS CHÈRE,', 'ENSEMBLE'], sub='Le PASS qui change vos courses. Rejoignez la coopérative.'),
]

f_kicker = ImageFont.truetype(FONT, 44)
f_title = ImageFont.truetype(FONT, 80)
f_sub = ImageFont.truetype(FONT, 40)


def centered(draw, text, font, y, color):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((W - (box[2] - box[0])) / 2, y), text, font=font, fill=color)


def prepare(i, s):
    src = f'{OUT_DIR}/s{i}.jpg'
    if not os.path.exists(src):
        urllib.request.urlretrieve(IMG + s['file'], src)
    im = Image.open(src).convert('RGB')
    ratio = max(W / im.width, H / im.height)
    im = im.resize((round(im.width * ratio), round(im.height * ratio)), Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width + W) // 2, (im.height + H) // 2))
    overlay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for y in range(H):
        a = 0 if y < 1250 else int(150 * (y - 1250) / (H - 1250))
        od.line([(0, y), (W, y)], fill=(6, 3, 12, a))
    im = Image.alpha_composite(im.convert('RGBA'), overlay)
    draw = ImageDraw.Draw(im)
    y0 = 1420
    centered(draw, s['kicker'], f_kicker, y0, (140, 198, 62, 255))
    for j, line in enumerate(s['title']):
        centered(draw, line, f_title, y0 + 70 + j * 92, (255, 255, 255, 255))
    centered(draw, s['sub'], f_sub, y0 + 70 + len(s['title']) * 92 + 18, (232, 232, 232, 255))
    out = f'{OUT_DIR}/t{i}.jpg'
    im.convert('RGB').save(out, quality=90)
    return out


inputs, filters, concat_in = [], [], []
total = sum(s['dur'] for s in SCENES)
for i, s in enumerate(SCENES):
    path = prepare(i, s)
    inputs += ['-framerate', '1', '-loop', '1', '-t', str(s['dur']), '-i', path]
    frames = int(s['dur'] * 25)
    zoom = (f"zoompan=z='min(zoom+0.0012,1.14)':d=25:x='iw/2-(iw/zoom/2)':"
            f"y='ih*0.42-(ih/zoom*0.42)':s=1080x1920:fps=25")
    filters.append(f'[{i}:v]{zoom},setsar=1,fade=t=in:st=0:d=0.4,fade=t=out:st={s["dur"] - 0.4}:d=0.4[v{i}]')
    concat_in.append(f'[v{i}]')
inputs += ['-f', 'lavfi', '-t', str(total), '-i', 'anullsrc=r=44100:cl=stereo']
graph = ';'.join(filters) + ';' + ''.join(concat_in) + f'concat=n={len(SCENES)}:v=1:a=0[vout]'
out = '/app/backend/uploads/videos/lolospot_vertical.mp4'
cmd = [FFMPEG, '-y', *inputs, '-filter_complex', graph, '-map', '[vout]', '-map', f'{len(SCENES)}:a',
       '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
       '-c:a', 'aac', '-shortest', out]
print('running ffmpeg…')
r = subprocess.run(cmd, capture_output=True, text=True)
print('returncode:', r.returncode)
if r.returncode != 0:
    print(r.stderr[-2000:])
else:
    print('OK', out, os.path.getsize(out), 'bytes')
