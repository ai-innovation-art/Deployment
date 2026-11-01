# DevOps Notes — Animated edition

This folder is a **copy** of `../notes/` with animation added. The original notes are unchanged.

Open `index.html` in a browser. Everything works offline from the folder.

## What was added
| Path | What it is |
|---|---|
| `videos/m01.mp4` … `m13.mp4` (+ `.jpg` posters) | One animated explainer per module (≈ 50–70 s each, 720p, H.264). Embedded at the top of each module and collected in `videos.html`. |
| `assets/anim.js`, `assets/anim.css` | The in-page animation layer. Every static diagram builds itself in reading order, draws its connectors, then sends data dots along the arrows. Each diagram gets ▶ Replay / ⏸ Pause controls, plays automatically when scrolled into view, and respects reduced-motion settings. It uses only the browser's Web Animations API, so there are no third-party scripts. |
| `videos.html` | Video gallery. |
| `video-src/` | Video sources: the Manim scenes (`mNN_*.py`), the shared style (`common.py`), `build_videos.py` (render + poster), `contact_sheet.py` (review helper) and `inject.py` (adds the layer to the copied pages; it refuses to run on anything other than `notes-animated/`). |

## Tools (free and open source)
- **Manim Community v0.22.1**, MIT licence: https://www.manim.community/ . It bundles FFmpeg through PyAV, so no system ffmpeg is needed.
- **System libraries** cairo and pkg-config, installed via Homebrew. These are needed by pycairo.

## Re-render a video
```bash
uv venv --python 3.12 .venv && uv pip install --python .venv/bin/python manim   # once (needs: brew install cairo pkg-config)
cd video-src
../.venv/bin/python build_videos.py 03        # or no args for all 13
```

## Review performed (29 Oct 2026)
- Original `../notes/` verified unchanged with SHA-256 over all 17 files.
- **Visual review:** every video was checked frame-by-frame on contact sheets at 480p draft and again at 720p final. Fixed: text overlaps, a takeaway-glyph bug in Manim `Paragraph` (now one Text per line), and the zone-label placement.
- **Independent fact review:** all on-screen captions, numbers and formulas were checked against the verified module pages. Result: 0 high, 1 medium, 7 low findings, all fixed and re-rendered.
- **Pages:** all 14 pages load in headless Chrome with no JS errors; animated diagrams build and flow; local links resolve.
