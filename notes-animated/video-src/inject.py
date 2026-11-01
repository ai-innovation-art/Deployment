"""Inject the animated-edition layer into the COPIED notes (notes-animated/ only).
Idempotent: safe to re-run. Never touches ../../notes/.

- adds assets/anim.css + assets/anim.js to every page
- adds an "Animated explainer" video block under each module's header meta row
- adds an edition banner + gallery link on index.html
"""
import pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent          # notes-animated/
assert ROOT.name == "notes-animated", ROOT                       # hard guard: never edit the original notes

VIDEOS = {
    "01": ("Binding, ports & the TCP handshake", "Why an app works inside a container but is refused from outside: 127.0.0.1 vs 0.0.0.0, refused vs timeout."),
    "02": ("Image layers & the build cache", "How Dockerfile instructions become layers, why one changed line rebuilds everything after it, and multi-stage builds."),
    "03": ("The life of kubectl apply", "Desired state flows API server → etcd → controllers → scheduler → kubelet, and the reconciliation loop replaces a deleted Pod."),
    "04": ("Probes & rolling updates", "Readiness vs liveness vs startup, then a maxSurge 1 / maxUnavailable 0 rollout — and what a bad image does."),
    "05": ("A request through a Service", "Client → Service → EndpointSlice of ready Pods → container port, plus unready Pods and selector mismatches."),
    "06": ("kind clusters & Helm releases", "Nodes as containers, loading local images, values precedence, revisions and rollback."),
    "07": ("Prometheus, histograms & PromQL", "Pull-based scraping, time series, histogram buckets and how histogram_quantile estimates p95."),
    "08": ("The HPA control loop & recovery", "The replica formula with a worked example, stabilization, and measuring recovery after a Pod failure."),
    "09": ("A CI/CD pipeline run", "Workflow triggers, the needs: DAG, fail-fast skips, and publishing a SHA-tagged image to GHCR."),
    "10": ("Terraform: config, state & reality", "init → plan → apply, reading plan symbols, drift, and why state needs a locked remote backend."),
    "11": ("GKE & keyless identity", "Managed control plane, Autopilot vs Standard, Workload Identity Federation and what still costs money."),
    "12": ("LLM inference: prefill, decode & batching", "TTFT and inter-token latency, the KV cache, continuous batching and scaling on queue depth."),
    "13": ("Troubleshooting by layers", "The troubleshooting loop, finding the lowest broken layer, and CrashLoopBackOff's back-off timeline."),
}

CSS = '<link rel="stylesheet" href="assets/anim.css">'
JS = '<script src="assets/anim.js"></script>'


def block(num):
    title, desc = VIDEOS[num]
    return (f'\n    <section class="explainer" id="explainer-video"><header>🎬 Animated explainer <span class="pill accent">{title}</span></header>'
            f'<video controls preload="metadata" playsinline poster="videos/m{num}.jpg" src="videos/m{num}.mp4"></video>'
            f'<div class="ex-foot"><strong>Watch first, then read.</strong> {desc} '
            f'Rendered with Manim Community (MIT); source: <code>video-src/</code>. Facts match this page\'s verified sections.</div></section>\n')


changed = 0
for page in sorted(ROOT.glob("*.html")):
    s = page.read_text()
    orig = s
    if CSS not in s:
        s = s.replace('<link rel="stylesheet" href="assets/style.css">', '<link rel="stylesheet" href="assets/style.css">\n' + CSS, 1)
    if JS not in s:
        s = s.replace('<script src="assets/notes.js"></script>', '<script src="assets/notes.js"></script>\n' + JS, 1)
    m = re.match(r"(\d\d)-", page.name)
    if m and m.group(1) in VIDEOS and 'id="explainer-video"' not in s:
        # place right after the first .meta row (module header)
        s = re.sub(r'(<div class="meta">.*?</div>)', lambda mm: mm.group(1) + block(m.group(1)), s, count=1, flags=re.S)
    if page.name == "index.html" and "edition-banner" not in s:
        banner = ('\n      <div class="edition-banner">🎞️ <strong>Animated edition</strong> — every diagram builds itself and shows data flow; '
                  'each module opens with a short explainer video. <a href="videos.html">Open the video gallery →</a> '
                  '<span style="color:var(--muted)">(The original static notes are kept unchanged in <code>../notes/</code>.)</span></div>')
        s = s.replace('<section class="hero">', '<section class="hero">' + banner, 1)
    if s != orig:
        page.write_text(s)
        changed += 1
        print("updated", page.name)
print("pages changed:", changed)
