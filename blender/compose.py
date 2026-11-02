"""Compose 3D frames + captions + voice into a 1080x1920 MP4.
python blender/compose.py PROJECT FRAMES_DIR OUT_MP4"""
import sys, os, json, glob, subprocess
from PIL import Image, ImageDraw, ImageFont, ImageFilter
proj, fdir, out = sys.argv[1], sys.argv[2], sys.argv[3]
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), proj)
tl = json.load(open(os.path.join(base, 'timeline.json'))); fps = tl['fps']
caps = json.load(open(os.path.join(base, 'captions.json')))
W, H = 1080, 1920
F = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 74)
FS = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 34)
YEL, WHITE, PINK = (254, 221, 84), (245, 247, 252), (255, 60, 126)
frames = sorted(glob.glob(os.path.join(fdir, 'f_*.png')))
p = subprocess.Popen(['ffmpeg', '-y', '-loglevel', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
     '-i', os.path.join(base, 'voice.wav'), '-af', 'loudnorm=I=-14:TP=-1.5', '-c:v', 'libx264', '-crf', '18', '-preset', 'slow',
     '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
for i, fp in enumerate(frames):
    t = i / fps
    seg = [s for s in tl['segments'] if s['start'] <= t][-1]; lt = t - seg['start']
    im = Image.open(fp).convert('RGB').resize((W, H), Image.LANCZOS)
    txt = caps.get(seg['name'], '')
    if txt and lt > 0.15:
        a = min(1.0, (lt - 0.15) / 0.2)
        ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
        fnt = F; size = 74
        while d.textbbox((0, 0), txt, font=fnt)[2] > 900 and size > 40:
            size -= 4; fnt = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
        b = d.textbbox((0, 0), txt, font=fnt); tw, th = b[2]-b[0], b[3]-b[1]
        x, y = (W - tw) / 2, 300
        d.rounded_rectangle([x-36, y-26, x+tw+36, y+th+34], radius=26, fill=(8, 12, 30, int(205*a)))
        col = YEL if seg['name'] in ('hook', 'payoff', 'why') else WHITE
        d.text((x, y - b[1]), txt, font=fnt, fill=col + (int(255*a),))
        im.paste(ov, (0, 0), ov)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, int(W * (i+1) / len(frames)), 10], fill=(67, 213, 239))
    if seg['name'] != 'hook':
        d.rounded_rectangle([46, 64, 300, 118], radius=14, fill=(12, 12, 16)); d.text((70, 72), 'VIRALYST', font=FS, fill=WHITE)
    p.stdin.write(im.tobytes())
p.stdin.close(); p.wait(); print('composed', out, len(frames), 'frames')
