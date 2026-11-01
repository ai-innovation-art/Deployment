"""Render explainer scenes at 720p30 and publish them to ../videos/mNN.mp4 with a poster ../videos/mNN.jpg.
Usage: python build_videos.py [NN ...]   (no args = all scenes found)
Run with the Python that has Manim installed."""
import pathlib, re, shutil, subprocess, sys, tempfile
import av

HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE.parent / "videos"
OUT.mkdir(exist_ok=True)
MEDIA = pathlib.Path(tempfile.gettempdir()) / "notes-anim-media"
MANIM = pathlib.Path(sys.executable).parent / "manim"

scenes = {}
for f in sorted(HERE.glob("m[0-9][0-9]_*.py")):
    m = re.search(r"^class (M\d\d\w*)\(", f.read_text(), re.M)
    if m:
        scenes[f.name[1:3]] = (f, m.group(1))

wanted = sys.argv[1:] or sorted(scenes)
for num in wanted:
    f, cls = scenes[num]
    print(f"== rendering {num}: {f.name} {cls}", flush=True)
    r = subprocess.run([str(MANIM), "-qm", "--disable_caching", "--progress_bar", "none",
                        "--media_dir", str(MEDIA), f.name, cls], cwd=HERE, capture_output=True, text=True)
    if r.returncode:
        print(r.stdout[-2000:], r.stderr[-2000:]); continue
    mp4 = next(MEDIA.rglob(f"720p30/{cls}.mp4"))
    dst = OUT / f"m{num}.mp4"
    shutil.copy(mp4, dst)
    # poster: frame at ~35% of the video (diagram built, captions visible)
    c = av.open(str(dst)); s = c.streams.video[0]
    dur = float(s.duration * s.time_base); target = dur * 0.35
    for fr in c.decode(video=0):
        if float(fr.pts * s.time_base) >= target:
            fr.to_image().convert("RGB").save(OUT / f"m{num}.jpg", quality=82); break
    c.close()
    print(f"   -> {dst.name} {dst.stat().st_size/1e6:.1f} MB, {dur:.1f}s", flush=True)
