"""Shared visual language for the DevOps Notes explainer videos (Manim Community, MIT licence).

Every scene imports from here so all 13 videos look like one series and match the
dark theme of the HTML notes. Keep text short: the narration lives in on-screen captions.
"""
from manim import *

# ---- palette (mirrors notes/assets/style.css dark theme) ----
BG = "#141413"
SURFACE = "#1f1f1c"
TEXT_C = "#ecebe6"
MUTED = "#a9a79f"
ACCENT = "#8aa8ff"   # blue: control plane / Kubernetes objects
OK = "#6fcf97"       # green: healthy / pods / success
WARN = "#f0b35a"     # amber: waiting / config / caution
BAD = "#f28b82"      # red: failure
INFO = "#b9a4ff"     # violet: observability / data

SANS = "Helvetica Neue"
MONO = "Menlo"

config.background_color = BG


def label(text, size=24, color=TEXT_C, weight=NORMAL, font=SANS):
    return Text(text, font=font, font_size=size, color=color, weight=weight)


def mono(text, size=20, color=TEXT_C):
    return Text(text, font=MONO, font_size=size, color=color)


def box(title, sub=None, color=ACCENT, w=2.8, h=1.1, title_size=24, sub_size=16):
    """Rounded node with a bold title and optional muted subtitle."""
    rect = RoundedRectangle(corner_radius=0.15, width=w, height=h,
                            stroke_color=color, stroke_width=2.5,
                            fill_color=color, fill_opacity=0.12)
    t = label(title, size=title_size, weight=BOLD)
    if sub:
        s = label(sub, size=sub_size, color=MUTED)
        content = VGroup(t, s).arrange(DOWN, buff=0.08)
    else:
        content = t
    content.move_to(rect)
    if content.width > w - 0.2:
        content.scale_to_fit_width(w - 0.25)
    return VGroup(rect, content)


def zone(width, height, title, color=MUTED):
    """Dashed boundary (cluster, node, namespace) with a corner title."""
    r = DashedVMobject(RoundedRectangle(corner_radius=0.2, width=width, height=height,
                                        stroke_color=color, stroke_width=1.5), num_dashes=60)
    t = label(title, size=16, color=color)
    t.next_to(r.get_corner(UL), DR, buff=0.12)
    return VGroup(r, t)


def arrow(a, b, color=MUTED, buff=0.1, **kw):
    """Arrow between two mobjects (or points)."""
    start = a.get_right() if hasattr(a, "get_right") else a
    end = b.get_left() if hasattr(b, "get_left") else b
    return Arrow(start, end, buff=buff, color=color, stroke_width=3,
                 max_tip_length_to_length_ratio=0.12, **kw)


def connect(a, b, color=MUTED, buff=0.12):
    """Arrow from the nearest edges of a to b."""
    return Arrow(a.get_center(), b.get_center(), buff=0, color=color, stroke_width=3,
                 max_tip_length_to_length_ratio=0.1).put_start_and_end_on(
        _edge_toward(a, b, buff), _edge_toward(b, a, buff))


def _edge_toward(m, other, buff):
    d = other.get_center() - m.get_center()
    if abs(d[0]) * m.height > abs(d[1]) * m.width:
        p = m.get_right() if d[0] > 0 else m.get_left()
        return p + (RIGHT if d[0] > 0 else LEFT) * buff
    p = m.get_top() if d[1] > 0 else m.get_bottom()
    return p + (UP if d[1] > 0 else DOWN) * buff


class Explainer(Scene):
    """Base scene: title card, persistent module tag, caption bar helpers."""
    MODULE = "Module 00"
    TITLE = "Title"
    SUBTITLE = ""

    def setup(self):
        self.caption_mob = None
        self.tag = label(self.MODULE + " · " + self.TITLE, size=16, color=MUTED).to_corner(UL, buff=0.3)

    def title_card(self):
        mod = label(self.MODULE.upper(), size=22, color=ACCENT, weight=BOLD)
        title = label(self.TITLE, size=48, weight=BOLD)
        sub = label(self.SUBTITLE, size=24, color=MUTED) if self.SUBTITLE else VGroup()
        g = VGroup(mod, title, sub).arrange(DOWN, buff=0.3)
        if g.width > 12.5:
            g.scale_to_fit_width(12.5)
        line = Line(LEFT * 3, RIGHT * 3, color=ACCENT, stroke_width=3).next_to(g, DOWN, buff=0.4)
        self.play(FadeIn(mod, shift=DOWN * 0.2), Write(title), run_time=1.2)
        self.play(FadeIn(sub), Create(line), run_time=0.8)
        self.wait(1.2)
        self.play(FadeOut(VGroup(g, line)), run_time=0.6)
        self.add(self.tag)

    def caption(self, text, wait=2.0, color=TEXT_C):
        """Replace the bottom caption (the 'narration')."""
        new = label(text, size=24, color=color)
        if new.width > 12.6:
            new.scale_to_fit_width(12.6)
        bg = RoundedRectangle(corner_radius=0.12, width=min(13.4, new.width + 0.6), height=new.height + 0.35,
                              fill_color=SURFACE, fill_opacity=0.92, stroke_width=0)
        cap = VGroup(bg, new).to_edge(DOWN, buff=0.25)
        new.move_to(bg)
        if self.caption_mob is None:
            self.play(FadeIn(cap, shift=UP * 0.15), run_time=0.4)
        else:
            self.play(FadeOut(self.caption_mob, run_time=0.25), FadeIn(cap, run_time=0.35))
        self.caption_mob = cap
        if wait:
            self.wait(wait)

    def clear_caption(self):
        if self.caption_mob is not None:
            self.play(FadeOut(self.caption_mob), run_time=0.3)
            self.caption_mob = None

    def packet(self, path_points, color=WARN, run_time=1.2, radius=0.09):
        """Animate a glowing dot along a polyline of points. Returns the dot (removed at end)."""
        dot = Dot(path_points[0], radius=radius, color=color)
        glow = Dot(path_points[0], radius=radius * 2.2, color=color).set_opacity(0.25)
        g = VGroup(glow, dot)
        self.add(g)
        path = VMobject().set_points_as_corners(path_points)
        self.play(MoveAlongPath(g, path), run_time=run_time, rate_func=linear)
        self.remove(g)
        return g

    def outro(self, takeaway):
        self.clear_caption()
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag], run_time=0.6)
        k = label("KEY TAKEAWAY", size=20, color=ACCENT, weight=BOLD)
        # one Text per line: Manim's Paragraph can misplace glyphs on later lines
        t = VGroup(*[Text(line, font=SANS, font_size=30, color=TEXT_C) for line in takeaway.split("\n")]
                   ).arrange(DOWN, buff=0.22)
        if t.width > 12:
            t.scale_to_fit_width(12)
        g = VGroup(k, t).arrange(DOWN, buff=0.4)
        self.play(FadeIn(k), Write(t), run_time=1.5)
        self.wait(2.5)
        self.play(FadeOut(g), FadeOut(self.tag), run_time=0.6)
