"""Génère la version verticale (9:16, stories/réseaux) du spot LOLODRIVE : 7 scènes images (textes PIL,
zoompan) + séquence des 8 clips produits Veo recadrés 9:16 avec bandeau texte en overlay PNG (pas de drawtext)."""
import os
import subprocess
import urllib.request

import imageio_ffmpeg
from PIL import Image, ImageDraw, ImageFont

FFMPEG = imageio_ffmpeg.get_ffmpeg_exe()
IMG = 'https://static.prod-images.emergentagent.com/jobs/e00f0d9a-9698-4efd-a047-db50a9deb9d1/images/'
VID_DIR = '/app/backend/uploads/videos'
FONT = '/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf'
OUT_DIR = '/tmp/spotv'
W, H = 1240, 2205
os.makedirs(OUT_DIR, exist_ok=True)

SCENES = [
    dict(file='a091c41c190351bb90597d3297306fb13e85be328121e0d12a32f327433143a3.jpeg', dur=4,
         kicker="LOLODRIVE by O'SCOP", title=["L'ÉPICERIE DE", "VOTRE TERRITOIRE"], sub="Des produits du terroir, sélectionnés pour vous."),
    dict(file='115eb4dadb3a253b4bb75394a4001db5a35825fb88fc119f3b06e1bb6dccc307.jpeg', dur=4,
         kicker='LE CONCEPT', title=['EXCLUSIVEMENT', 'PAR LOT DE 3'], sub='Au meilleur prix coopératif négocié.'),
    dict(clip='lolospot_prod_legumes.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['LÉGUMES DU SOLEIL'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_yaourts.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['YAOURTS'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_pates.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['PÂTES'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_riz.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['RIZ'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_cereales.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['CÉRÉALES'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_huiles.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['HUILES'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_beurre.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['BEURRE'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(clip='lolospot_prod_lait.mp4', dur=2.5, kicker='TOUS VOS ESSENTIELS', title=['LAIT'], sub='Par lot de 3 — prix coopératif négocié.'),
    dict(file='3eb7e909af822d8bee4a2945d40a93f4465399b835bbcfcc7a555d57527ac45e.jpeg', dur=5,
         kicker='AVEC VOTRE PASS LOLODRIVE', title=['COMMANDEZ EN LIGNE'], sub='En quelques clics, en ligne et en relais.'),
    dict(file='53e97ce3eeb653344afa45510ff5095de03f6370b1efd973b63dc6b4dd2b3ea9.jpeg', dur=4,
         kicker='VOTRE RELAIS PRÉPARE', title=['VOS PANIERS PRÉPARÉS', 'AVEC SOIN'], sub="L'équipe LOLODRIVE prépare vos paniers."),
    dict(file='e60c1ff0ae184631bc39136afbd62932c14607d478bfb3248910ff67ed5c2791.jpeg', dur=5,
         kicker='PRÈS DE CHEZ VOUS', title=['LIVRAISON OU', 'RETRAIT DRIVE'], sub='Optez pour une livraison ou un retrait drive en relais.'),
    dict(file='5a23665bd1ac32b48f3c636d27c1ec6d4a4564a6105c1671e4a1c0436b4b8388.jpeg', dur=4,
         kicker="LOLODRIVE by O'SCOP", title=['ON VOUS ACCUEILLE', 'AVEC PLAISIR'], sub="L'équipe LOLODRIVE vous attend. Rejoignez la coopérative avec votre PASS."),
]

f_kicker = ImageFont.truetype(FONT, 44)
f_title = ImageFont.truetype(FONT, 80)
f_sub = ImageFont.truetype(FONT, 40)
VW, VH = 1080, 1920
fv_kicker = ImageFont.truetype(FONT, 38)
fv_title = ImageFont.truetype(FONT, 68)
fv_sub = ImageFont.truetype(FONT, 34)


def centered(draw, text, font, y, color, width=W):
    box = draw.textbbox((0, 0), text, font=font)
    draw.text(((width - (box[2] - box[0])) / 2, y), text, font=font, fill=color)


def prepare_image(i, s):
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


def prepare_clip_overlay(i, s):
    """PNG transparent 1080x1920 : dégradé bas + textes, overlay sur le clip recadré."""
    ov = Image.new('RGBA', (VW, VH), (0, 0, 0, 0))
    od = ImageDraw.Draw(ov)
    for y in range(VH):
        a = 0 if y < 1150 else int(165 * (y - 1150) / (VH - 1150))
        od.line([(0, y), (VW, y)], fill=(6, 3, 12, a))
    y0 = 1330
    centered(od, s['kicker'], fv_kicker, y0, (140, 198, 62, 255), VW)
    for j, line in enumerate(s['title']):
        centered(od, line, fv_title, y0 + 60 + j * 80, (255, 255, 255, 255), VW)
    centered(od, s['sub'], fv_sub, y0 + 60 + len(s['title']) * 80 + 16, (232, 232, 232, 255), VW)
    out = f'{OUT_DIR}/ov{i}.png'
    ov.save(out)
    return out


inputs, filters, concat_in = [], [], []
n_in = 0
for i, s in enumerate(SCENES):
    if 'clip' in s:
        clip_path = os.path.join(VID_DIR, s['clip'])
        ov_path = prepare_clip_overlay(i, s)
        inputs += ['-ss', '1.5', '-t', str(s['dur']), '-i', clip_path]
        clip_idx = n_in; n_in += 1
        inputs += ['-i', ov_path]
        ov_idx = n_in; n_in += 1
        filters.append(
            f"[{clip_idx}:v]crop=405:720:437:0,scale={VW}:{VH}:flags=lanczos,fps=25,setsar=1[c{i}];"
            f"[c{i}][{ov_idx}:v]overlay=0:0,fade=t=in:st=0:d=0.3,fade=t=out:st={s['dur'] - 0.3}:d=0.3[v{i}]")
    else:
        path = prepare_image(i, s)
        inputs += ['-framerate', '1', '-loop', '1', '-t', str(s['dur']), '-i', path]
        idx = n_in; n_in += 1
        zoom = (f"zoompan=z='min(zoom+0.0012,1.14)':d=25:x='iw/2-(iw/zoom/2)':"
                f"y='ih*0.42-(ih/zoom*0.42)':s={VW}x{VH}:fps=25")
        filters.append(f'[{idx}:v]{zoom},setsar=1,fade=t=in:st=0:d=0.4,fade=t=out:st={s["dur"] - 0.4}:d=0.4[v{i}]')
    concat_in.append(f'[v{i}]')

total = sum(s['dur'] for s in SCENES)
inputs += ['-f', 'lavfi', '-t', str(total), '-i', 'anullsrc=r=44100:cl=stereo']
audio_idx = n_in
graph = ';'.join(filters) + ';' + ''.join(concat_in) + f'concat=n={len(SCENES)}:v=1:a=0[vout]'
out = '/app/backend/uploads/videos/lolospot_vertical.mp4'
cmd = [FFMPEG, '-y', *inputs, '-filter_complex', graph, '-map', '[vout]', '-map', f'{audio_idx}:a',
       '-c:v', 'libx264', '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
       '-c:a', 'aac', '-shortest', out]
print('running ffmpeg…')
r = subprocess.run(cmd, capture_output=True, text=True)
print('returncode:', r.returncode)
if r.returncode != 0:
    print(r.stderr[-2000:])
else:
    print('OK', out, os.path.getsize(out), 'bytes')
