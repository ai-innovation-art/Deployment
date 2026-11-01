"""Module 02 — image layers, the build cache, multi-stage builds, and container = image + writable layer.
Facts follow notes/02-docker.html (Layers/union FS/copy-on-write, Build cache, Multi-stage builds, Dockerfile)."""
from common import *


def step_row(instr, w=5.9, h=0.52, color=MUTED, size=17):
    """One Dockerfile step drawn as a layer bar with the instruction on the left."""
    r = RoundedRectangle(corner_radius=0.08, width=w, height=h, stroke_color=color, stroke_width=1.8,
                         fill_color=color, fill_opacity=0.10)
    t = mono(instr, size)
    if t.width > w * 0.62:
        t.scale_to_fit_width(w * 0.62)
    t.move_to(r).align_to(r, LEFT).shift(RIGHT * 0.18)
    return VGroup(r, t)


def status(text, color, size=16):
    t = label(text, size, color, weight=BOLD)
    bg = RoundedRectangle(corner_radius=0.08, width=t.width + 0.24, height=t.height + 0.14,
                          stroke_width=0, fill_color=color, fill_opacity=0.22)
    t.move_to(bg)
    return VGroup(bg, t)


def set_status(row, text, color):
    s = status(text, color)
    s.move_to(row[0]).align_to(row[0], RIGHT).shift(LEFT * 0.12)
    return s


class M02Layers(Explainer):
    MODULE = "Module 02"
    TITLE = "Images are stacks of layers"
    SUBTITLE = "Build cache, multi-stage builds, and the writable layer"

    def construct(self):
        self.title_card()

        # ---------------- Part 1: Dockerfile → layers ----------------
        lines = ["FROM python:3.12-slim", "WORKDIR /app", "COPY requirements.txt .",
                 "RUN pip install -r requirements.txt", "COPY app/ ./app/", 'CMD ["uvicorn", ...]']
        code = VGroup(*[mono(l, 21) for l in lines]).arrange(DOWN, aligned_edge=LEFT, buff=0.26)
        panel = RoundedRectangle(corner_radius=0.15, width=code.width + 0.6, height=code.height + 0.9,
                                 stroke_color=MUTED, stroke_width=1.5, fill_color=SURFACE, fill_opacity=1)
        ptitle = label("Dockerfile", 16, MUTED)
        df = VGroup(panel, code).move_to(LEFT * 3.3 + UP * 0.4)
        code.move_to(panel).shift(DOWN * 0.15)
        ptitle.next_to(panel.get_corner(UL), DR, buff=0.12)
        df.add(ptitle)

        self.caption("A Dockerfile is a list of build steps. Each step is applied on top of the previous one.", wait=0.3)
        self.play(FadeIn(df, shift=RIGHT * 0.2))

        stack_x = 3.9
        layer_names = ["base OS + Python", "WORKDIR /app", "requirements.txt", "deps: fastapi, uvicorn, …",
                       "app/ (your code)", "CMD (metadata)"]
        colors = [MUTED, MUTED, WARN, INFO, OK, MUTED]
        layers = VGroup()
        for i, (n, c) in enumerate(zip(layer_names, colors)):
            r = RoundedRectangle(corner_radius=0.08, width=4.6, height=0.56, stroke_color=c, stroke_width=2,
                                 fill_color=c, fill_opacity=0.16)
            t = label(n, 19, TEXT_C)
            t.move_to(r)
            layers.add(VGroup(r, t).move_to([stack_x, -1.5 + i * 0.66, 0]))
        img_lbl = label("image reliability-api:0.1.0", 18, ACCENT, weight=BOLD).next_to(layers, DOWN, buff=0.25)

        self.caption("Each layer is a set of filesystem changes: additions, deletions, or modifications.", wait=0.1)
        for i in range(len(lines)):
            hl = SurroundingRectangle(code[i], color=WARN, buff=0.06, stroke_width=2)
            self.play(Create(hl), run_time=0.25)
            self.play(FadeIn(layers[i], shift=DOWN * 0.3), FadeOut(hl), run_time=0.4)
        self.play(FadeIn(img_lbl))
        self.caption("Stacked together, these read-only layers form the image's filesystem.", wait=1.5)

        # ---------------- Part 2: build cache, bad vs good order ----------------
        self.play(FadeOut(VGroup(df, layers, img_lbl)), run_time=0.6)
        bad_lines = ["FROM python:3.12-slim", "WORKDIR /app", "COPY . .", "RUN pip install -r req…", "CMD [...]"]
        good_lines = ["FROM python:3.12-slim", "WORKDIR /app", "COPY requirements.txt .", "RUN pip install -r req…",
                      "COPY app/ ./app/", "CMD [...]"]
        bad = VGroup(*[step_row(l) for l in bad_lines]).arrange(DOWN, buff=0.12).move_to(LEFT * 3.45 + UP * 0.25)
        good = VGroup(*[step_row(l) for l in good_lines]).arrange(DOWN, buff=0.12).move_to(RIGHT * 3.45 + UP * 0.25)
        bad.align_to(good, UP)
        bh = label("✘ Bad order: COPY everything first", 20, BAD, weight=BOLD).next_to(bad, UP, buff=0.3)
        gh = label("✔ Good order: dependencies first", 20, OK, weight=BOLD).next_to(good, UP, buff=0.3)

        self.caption("Rebuilding? The builder checks each step against its cache of earlier layers.", wait=0.3)
        self.play(FadeIn(bad), FadeIn(good), FadeIn(bh), FadeIn(gh), run_time=0.9)
        edit = VGroup(label("✎", 26, WARN), mono("edit app/main.py", 20, WARN)).arrange(RIGHT, buff=0.15)
        edit.move_to(DOWN * 2.45)
        self.play(FadeIn(edit, shift=UP * 0.1))
        self.caption("Now edit one line of app/main.py, the file that changes most often.", wait=0.8)

        def run(rows, changed_idx, slow_idx=None):
            tags = VGroup()
            for i, row in enumerate(rows):
                if i < changed_idx:
                    s = set_status(row, "CACHED", OK)
                    anims = [FadeIn(s)]
                elif i == changed_idx:
                    s = set_status(row, "changed ✎", WARN)
                    anims = [FadeIn(s), row[0].animate.set_stroke(WARN, width=3)]
                else:
                    txt = "REBUILD ~30 s" if i == slow_idx else "REBUILD"
                    s = set_status(row, txt, BAD)
                    anims = [FadeIn(s), row[0].animate.set_stroke(BAD, width=3).set_fill(BAD, opacity=0.12)]
                self.play(*anims, run_time=0.32)
                tags.add(s)
            return tags

        self.caption("Bad order: COPY . . sees a changed file, so pip install re-runs from scratch.", wait=0.2)
        bt = run(bad, 2, slow_idx=3)
        self.wait(0.6)
        self.caption("Good order: requirements.txt is unchanged, so the slow pip layer stays cached.", wait=0.2)
        gt = run(good, 4)
        pip_tag = set_status(good[3], "CACHED ⚡", OK)
        self.play(Transform(gt[3], pip_tag), Indicate(good[3], color=OK, scale_factor=1.04), run_time=0.6)
        self.caption("Rule: once a layer changes, every layer after it is rebuilt, even if nothing differs.", wait=2.0,
                     color=WARN)
        self.caption("So put what changes least at the top, and what changes most at the bottom.", wait=1.6)
        self.play(FadeOut(VGroup(bad, good, bh, gh, bt, gt, edit)), run_time=0.6)

        # ---------------- Part 3: multi-stage ----------------
        bz = zone(5.0, 4.6, 'stage "builder" (discarded)', color=WARN).move_to(LEFT * 3.7 + UP * 0.4)
        rz = zone(5.0, 4.6, 'stage "runtime" (the image you ship)', color=OK).move_to(RIGHT * 3.7 + UP * 0.4)

        def items(names, x, color):
            g = VGroup(*[box(n, color=color, w=4.4, h=0.55, title_size=17) for n in names]).arrange(DOWN, buff=0.14)
            return g.move_to([x, 0.15, 0])

        b_items = items(["python:3.12-slim", "pip, build tools", "requirements.txt, temp files", "/opt/venv"], -3.7, WARN)
        r_items = items(["python:3.12-slim (same base)", "user app (10001)", "/opt/venv", "/app/app/main.py",
                         "CMD uvicorn … (exec form)"], 3.7, OK)

        self.caption("Multi-stage build: each FROM starts a new stage with its own base.", wait=0.3)
        self.play(Create(bz[0]), FadeIn(bz[1]), FadeIn(b_items), run_time=1.0)
        self.caption("The builder stage installs dependencies into a virtualenv at /opt/venv.", wait=1.0)
        self.play(Create(rz[0]), FadeIn(rz[1]), FadeIn(r_items[0]), FadeIn(r_items[1]), run_time=0.9)
        self.caption("The runtime stage copies only /opt/venv across with COPY --from=builder.", wait=0.2)
        venv_copy = b_items[3].copy()
        cf_t = VGroup(mono("COPY", 17, ACCENT), mono("--from=builder", 17, ACCENT)).arrange(DOWN, buff=0.08)
        cf_a = Arrow([-1.0, r_items[2].get_y() - 0.75, 0], [1.0, r_items[2].get_y() - 0.75, 0], buff=0,
                     color=ACCENT, stroke_width=3, max_tip_length_to_length_ratio=0.2)
        cf_t.next_to(cf_a, DOWN, buff=0.12)
        cf = VGroup(cf_a, cf_t)
        self.play(FadeIn(cf))
        self.play(venv_copy.animate.move_to(r_items[2]).set_color(OK), run_time=1.2)
        self.remove(venv_copy)
        self.add(r_items[2])
        self.play(FadeIn(r_items[3]), FadeIn(r_items[4]), run_time=0.7)
        self.caption("Build tools and pip leftovers stay behind in the builder. Only the runtime stage ships.", wait=0.3)
        self.play(VGroup(bz, b_items).animate.set_opacity(0.25), FadeOut(cf), run_time=1.0)
        self.wait(1.2)
        self.play(FadeOut(VGroup(bz, b_items, rz, r_items)), run_time=0.6)

        # ---------------- Part 4: container = image + writable layer ----------------
        img = VGroup()
        for i, n in enumerate(["python:3.12-slim layers", "RUN groupadd/useradd app", "COPY --from=builder /opt/venv",
                               "COPY app/ ./app/"]):
            r = RoundedRectangle(corner_radius=0.08, width=8.6, height=0.52, stroke_color=ACCENT, stroke_width=2,
                                 fill_color=ACCENT, fill_opacity=0.12)
            t = mono(n, 18).move_to(r)
            img.add(VGroup(r, t).move_to([0, -1.0 + i * 0.62, 0]))
        ro = label("read-only image layers · reliability-api:0.1.0 · stored once", 17, ACCENT).next_to(img, DOWN, buff=0.18)

        self.caption("A container = the image's read-only layers + one thin writable layer of its own.", wait=0.2)
        self.play(LaggedStart(*[FadeIn(l, shift=UP * 0.2) for l in img], lag_ratio=0.15), FadeIn(ro), run_time=1.0)

        def wl(name, x):
            r = RoundedRectangle(corner_radius=0.08, width=4.1, height=0.62, stroke_color=OK, stroke_width=2.5,
                                 fill_color=OK, fill_opacity=0.2)
            t = label(name, 17, TEXT_C).move_to(r).align_to(r, LEFT).shift(RIGHT * 0.2)
            return VGroup(r, t).move_to([x, img.get_top()[1] + 0.55, 0])

        wa = wl("writable layer: container A", -2.2)
        wb = wl("writable layer: container B", 2.2)
        self.play(FadeIn(wa, shift=DOWN * 0.2), FadeIn(wb, shift=DOWN * 0.2), run_time=0.8)
        self.caption("Both containers share the same image layers. Each only adds its own writable layer.", wait=1.4)

        self.caption("Copy-on-write: the first write to a file copies it up into the writable layer.", wait=0.2)
        f = mono("file", 15, WARN).move_to(img[1][1].get_right() + RIGHT * 0.6)
        f_bg = SurroundingRectangle(f, color=WARN, buff=0.06, stroke_width=1.5)
        fg = VGroup(f_bg, f)
        self.play(FadeIn(fg))
        fc = fg.copy()
        self.play(fc.animate.move_to(wa[0].get_right() + LEFT * 0.45), run_time=1.0)
        self.wait(0.8)
        self.caption("Delete the container and its writable layer is gone. The image layers are untouched.", wait=0.2)
        self.play(FadeOut(wa), FadeOut(fc), run_time=0.8)
        self.play(Indicate(img, color=ACCENT, scale_factor=1.02), run_time=0.8)
        self.caption("Data that must survive belongs in a volume, not in the writable layer.", wait=1.6)

        self.outro("Order the Dockerfile from rarely-changing to often-changing,\nship a slim runtime stage, "
                   "and treat the writable layer as disposable.")
