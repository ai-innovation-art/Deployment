"""Review helper: build a contact sheet (grid of frames) from an MP4 so a scene can be reviewed as one image.
Usage: python contact_sheet.py video.mp4 out.png [n_frames]"""
import sys
import av
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
n = int(sys.argv[3]) if len(sys.argv) > 3 else 16

c = av.open(src)
stream = c.streams.video[0]
dur = float(stream.duration * stream.time_base) if stream.duration else float(c.duration / 1e6)
targets = [dur * (i + 0.5) / n for i in range(n)]
frames, ti = [], 0
for frame in c.decode(video=0):
    t = float(frame.pts * stream.time_base)
    if ti < len(targets) and t >= targets[ti]:
        frames.append((t, frame.to_image()))
        ti += 1
c.close()

w, h = frames[0][1].size
scale = 480 / w
tw, th = int(w * scale), int(h * scale)
cols = 4
rows = (len(frames) + cols - 1) // cols
sheet = Image.new("RGB", (cols * tw, rows * (th + 18)), "black")
d = ImageDraw.Draw(sheet)
for i, (t, im) in enumerate(frames):
    x, y = (i % cols) * tw, (i // cols) * (th + 18)
    sheet.paste(im.resize((tw, th)), (x, y + 18))
    d.text((x + 4, y + 2), f"{t:5.1f}s", fill="white")
sheet.save(out)
print(f"{src}: {dur:.1f}s, {len(frames)} frames -> {out}")
