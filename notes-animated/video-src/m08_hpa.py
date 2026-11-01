"""Module 08 — the HPA loop (metrics-server → utilization → ceil formula → tolerance → clamp),
scale-down stabilization, and measuring recovery after deleting a Pod under load.
Facts follow notes/08-scaling-load-failure.html (sections 2, 3, 4, 14 and Figure 10)."""
from common import *

TARGET = 60


def pod_slot(i, filled, color=OK):
    r = RoundedRectangle(corner_radius=0.12, width=1.5, height=0.9, stroke_color=color if filled else MUTED,
                         stroke_width=2.5 if filled else 1.2, fill_color=color, fill_opacity=0.15 if filled else 0)
    if not filled:
        r.set_stroke(opacity=0.5)
    t = label("Pod" if filled else "", 18, TEXT_C, weight=BOLD).move_to(r)
    return VGroup(r, t)


class M08Hpa(Explainer):
    MODULE = "Module 08"
    TITLE = "HPA, load & recovery"
    SUBTITLE = "metrics-server → ceil(n × current / target) → replicas · measuring recovery"

    def construct(self):
        self.title_card()
        self.part_pipeline()
        self.part_math()
        self.part_scaledown()
        self.part_recovery()
        self.outro("The HPA scales on usage ÷ request, every 15 s, within min..max.\n"
                   "Measure failures as fault time → impact window → recovery time.")

    # -------------------------------------------------------------- pipeline
    def part_pipeline(self):
        pods = box("Pods", "requests cpu: 100m", color=OK, w=2.6, h=1.0, sub_size=16).move_to(LEFT * 5.2 + UP * 1.6)
        ms = box("metrics-server", "latest values only", color=INFO, w=2.8, h=1.0, sub_size=16).move_to(LEFT * 1.6 + UP * 1.6)
        api = box("metrics.k8s.io", "Metrics API", color=INFO, w=2.6, h=1.0, sub_size=16).move_to(RIGHT * 1.9 + UP * 1.6)
        hpa = box("HPA", "control loop · every 15 s", color=ACCENT, w=2.8, h=1.0, sub_size=16).move_to(RIGHT * 5.2 + UP * 1.6)
        dep = box("Deployment", "spec.replicas", color=ACCENT, w=2.8, h=1.0, sub_size=16).move_to(RIGHT * 5.2 + DOWN * 0.6)
        arrows = VGroup(connect(pods, ms), connect(ms, api), connect(api, hpa), connect(hpa, dep))
        spec = VGroup(mono("minReplicas: 2", 20), mono("maxReplicas: 6", 20),
                      mono("averageUtilization: 60", 20, WARN)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        spec_t = label("HPA reliability-api", 18, ACCENT, weight=BOLD)
        specg = VGroup(spec_t, spec).arrange(DOWN, aligned_edge=LEFT, buff=0.15).move_to(LEFT * 3.2 + DOWN * 0.9)
        util = VGroup(mono("utilization = usage ÷ request", 20, TEXT_C),
                      mono("60 % of 100m = 60m CPU per Pod", 20, WARN)).arrange(DOWN, aligned_edge=LEFT, buff=0.12)
        util.move_to(RIGHT * 0.9 + DOWN * 0.9)

        self.caption("The HPA doesn't read Prometheus. For CPU it reads the Metrics API via metrics-server.", wait=0.2)
        self.play(FadeIn(pods), FadeIn(ms), FadeIn(api), FadeIn(hpa), run_time=0.9)
        self.play(Create(arrows[0]), Create(arrows[1]), Create(arrows[2]), run_time=0.8)
        for a, b in ((pods, ms), (ms, api), (api, hpa)):
            self.packet([a.get_right(), b.get_left()], color=INFO, run_time=0.4)
        self.caption("Every 15 s the HPA compares average CPU, as a % of the request, with its target.", wait=0.2)
        self.play(FadeIn(specg, shift=UP * 0.2))
        self.play(FadeIn(util, shift=UP * 0.2))
        self.wait(1.0)
        self.caption("Then it writes the new replica count; the Deployment controller does the rest.", wait=0.2)
        self.play(FadeIn(dep), Create(arrows[3]))
        self.packet([hpa.get_bottom(), dep.get_top()], color=ACCENT, run_time=0.5)
        self.wait(0.8)
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag and m is not self.caption_mob],
                  run_time=0.6)

    # ------------------------------------------------------------------ math
    def part_math(self):
        formula = mono("desiredReplicas = ceil(currentReplicas × currentUtil / 60)", 21, ACCENT).move_to(UP * 2.85)

        # utilization meter (1 unit = 100 %)
        bx, by = -5.3, -2.35
        scale = 1.15
        meter_axis = Line([bx - 0.6, by, 0], [bx + 0.6, by, 0], color=MUTED)
        band = Rectangle(width=1.4, height=0.12 * scale, stroke_width=0, fill_color=WARN, fill_opacity=0.35
                         ).move_to([bx, by + 0.60 * scale, 0])
        tline = Line([bx - 0.75, by + 0.6 * scale, 0], [bx + 0.75, by + 0.6 * scale, 0], color=WARN, stroke_width=2)
        tlab = label("60 % ± 0.1", 16, WARN).next_to(tline, RIGHT, buff=0.1)
        mtitle = label("avg CPU / request", 17, MUTED).move_to([bx, by - 0.3, 0])
        ut = ValueTracker(2)

        def meter():
            v = ut.get_value()
            h = max(0.02, scale * v / 100)
            col = OK if abs(v / TARGET - 1) <= 0.1 else (WARN if v < TARGET else BAD)
            r = Rectangle(width=1.0, height=h, stroke_color=col, stroke_width=2, fill_color=col,
                          fill_opacity=0.4).move_to([bx, by + h / 2, 0])
            t = mono(f"{v:.0f} %", 20, col).next_to(r, LEFT, buff=0.12).align_to(r, UP)
            if t.get_bottom()[1] < by:
                t.align_to([0, by, 0], DOWN)
            return VGroup(r, t)
        m = always_redraw(meter)

        load_t = label("load (/work?ms=50)", 17, MUTED).move_to(LEFT * 4.9 + UP * 2.05)
        load_v = mono("idle", 22, TEXT_C).next_to(load_t, DOWN, buff=0.1)

        slots = VGroup(*[pod_slot(i, i < 2) for i in range(6)]).arrange_in_grid(2, 3, buff=(0.3, 0.3))
        slots.move_to(RIGHT * 2.0 + UP * 0.75)
        mn = label("min 2", 16, MUTED).next_to(slots[0], LEFT, buff=0.15)
        mx = label("max 6", 16, MUTED).next_to(slots[5], RIGHT, buff=0.15)
        rep_t = label("replicas", 17, MUTED).next_to(slots, UP, buff=0.15)

        calc = mono("", 20).move_to(RIGHT * 2.0 + DOWN * 1.35)

        def set_calc(text, color=TEXT_C):
            new = mono(text, 20, color).move_to(RIGHT * 2.0 + DOWN * 1.35)
            if new.width > 8.0:
                new.scale_to_fit_width(8.0)
            return Transform(calc, new)

        def set_load(text):
            return Transform(load_v, mono(text, 22, TEXT_C).move_to(load_v))

        self.caption("Worked example: 2 Pods, each /work?ms=50 request burns ≈ 50 ms of CPU.", wait=0.2)
        self.play(FadeIn(formula), FadeIn(load_t), FadeIn(load_v), Create(meter_axis), FadeIn(mtitle),
                  FadeIn(band), Create(tline), FadeIn(tlab), FadeIn(slots), FadeIn(mn), FadeIn(mx),
                  FadeIn(rep_t), run_time=1.0)
        self.add(m, calc)
        self.wait(0.6)

        # step 1: 1 req/s -> 25 %
        self.caption("1 req/s → 25m per Pod = 25 %. ceil(2 × 25/60) = 1, but minReplicas keeps 2.", wait=0.2)
        self.play(set_load("1 req/s"), ut.animate.set_value(25), run_time=1.0)
        self.play(set_calc("ceil(2 × 25/60) = 1  →  clamp to min 2", WARN))
        self.wait(1.4)

        # step 2: 2.4 req/s -> 60 %
        self.caption("2.4 req/s → 60 %. Ratio 1.0 is inside the 0.1 tolerance (54–66 %): no change.", wait=0.2)
        self.play(set_load("2.4 req/s"), ut.animate.set_value(60), run_time=1.0)
        self.play(set_calc("|60/60 − 1| ≤ 0.1  →  stay at 2", OK))
        self.wait(1.4)

        # step 3: 10 req/s -> 250 %
        self.caption("10 req/s → 250m per Pod = 250 %. ceil(2 × 250/60) = 9, clamped to max 6.", wait=0.2)
        self.play(set_load("10 req/s"), ut.animate.set_value(250), run_time=1.2)
        self.play(set_calc("ceil(2 × 250/60) = ceil(8.33) = 9  →  clamp to max 6", BAD))
        self.wait(0.8)
        self.caption("Default scale-up: +100 % or +4 Pods per 15 s, whichever is more: 2 → 6 at once.", wait=0.2)
        new_pods = [pod_slot(i, True).move_to(slots[i]) for i in range(2, 6)]
        self.play(LaggedStart(*[ReplacementTransform(slots[i], new_pods[i - 2]) for i in range(2, 6)],
                              lag_ratio=0.2), run_time=1.2)
        self.play(ut.animate.set_value(83), run_time=1.0)
        self.play(set_calc("0.5 cores ÷ 6 Pods ≈ 83m = 83 %  →  ScalingLimited at max", WARN))
        self.caption("Still above 60 %: the tiny 100m request makes the HPA hit max under modest load.", wait=1.8)
        self.slots_now = VGroup(*slots[:2], *new_pods)
        self.play(*[FadeOut(x) for x in self.mobjects if x is not self.tag and x is not self.caption_mob],
                  run_time=0.6)
        m.clear_updaters()

    # ------------------------------------------------------------- scale down
    def part_scaledown(self):
        ox, oy, W, H = -5.6, -2.0, 11.0, 3.6
        per_min = W / 9
        ax = VGroup(Line([ox, oy, 0], [ox + W, oy, 0], color=MUTED), Line([ox, oy, 0], [ox, oy + H, 0], color=MUTED))
        yv = lambda r: oy + H * r / 7
        xt = lambda t: ox + per_min * t
        ticks = VGroup(*[label(f"{t} min", 15, MUTED).next_to([xt(t), oy, 0], DOWN, buff=0.08) for t in range(0, 10, 2)])
        ylabs = VGroup(*[label(str(r), 15, MUTED).next_to([ox, yv(r), 0], LEFT, buff=0.1) for r in (2, 6)])
        hdr = label("Scale-down stabilization: default 300 s", 24, ACCENT, weight=BOLD).move_to(UP * 2.85)

        recs = VGroup()
        for i in range(0, 37):
            t = i * 0.25
            r = 6 if t < 2 else 2
            recs.add(Dot([xt(t), yv(r), 0], radius=0.045, color=MUTED))
        drop_t = 2 + 5   # last "6" recommendation at ~2 min, window 300 s
        applied = VMobject(color=OK, stroke_width=5).set_points_as_corners([
            [xt(0), yv(6), 0], [xt(drop_t), yv(6), 0], [xt(drop_t), yv(2), 0], [xt(9), yv(2), 0]])
        load_drop = DashedLine([xt(2), oy, 0], [xt(2), oy + H, 0], color=WARN)
        ld = label("load drops", 16, WARN).next_to(load_drop, UP, buff=0.08)
        win = DoubleArrow([xt(2), yv(4.2), 0], [xt(drop_t), yv(4.2), 0], buff=0, color=INFO, stroke_width=3,
                          max_tip_length_to_length_ratio=0.04)
        wl = label("300 s window still contains a '6'", 17, INFO).next_to(win, DOWN, buff=0.1)
        leg = VGroup(VGroup(Dot(radius=0.05, color=MUTED), label("raw recommendation (each 15 s)", 15, MUTED)).arrange(RIGHT, buff=0.1),
                     VGroup(Line(ORIGIN, RIGHT * 0.4, color=OK, stroke_width=5), label("replicas applied", 15, OK)).arrange(RIGHT, buff=0.1)
                     ).arrange(DOWN, aligned_edge=LEFT, buff=0.08).move_to([xt(6.9), yv(6.9), 0])

        self.caption("Load stops. The raw recommendation falls to 2 at the next sync…", wait=0.2)
        self.play(FadeIn(hdr), Create(ax), FadeIn(ticks), FadeIn(ylabs), FadeIn(leg))
        self.play(Create(load_drop), FadeIn(ld))
        self.play(LaggedStart(*[FadeIn(d) for d in recs], lag_ratio=0.03), run_time=1.6)
        self.caption("…but scale-down uses the HIGHEST recommendation of the last 300 s.", wait=0.2)
        self.play(Create(applied), run_time=2.0)
        self.play(GrowFromCenter(win), FadeIn(wl))
        self.caption("Only after 5 minutes of lower recommendations does it drop to minReplicas (2).", wait=1.6)
        self.caption("Scale-up has no window by default: it reacts at the next sync.", wait=1.4)
        self.play(*[FadeOut(x) for x in self.mobjects if x is not self.tag and x is not self.caption_mob],
                  run_time=0.6)

    # -------------------------------------------------------------- recovery
    def part_recovery(self):
        hdr = label("Failure test: delete 1 of 2 Pods under load", 24, ACCENT, weight=BOLD).move_to(UP * 3.15)
        t0, t1 = 40, 100
        ox, W = -6.0, 12.0
        xt = lambda t: ox + W * (t - t0) / (t1 - t0)
        ax = Line([ox, -1.9, 0], [ox + W, -1.9, 0], color=MUTED)
        ticks = VGroup(*[label(f"{t} s", 15, MUTED).next_to([xt(t), -1.9, 0], DOWN, buff=0.08) for t in range(40, 101, 20)])

        # ready pods row
        ry = 1.4
        rl = label("ready Pods", 16, MUTED).move_to([ox + 0.7, ry + 0.75, 0])
        ready = VMobject(color=OK, stroke_width=5).set_points_as_corners([
            [xt(40), ry + 0.35, 0], [xt(60), ry + 0.35, 0], [xt(60), ry - 0.15, 0],
            [xt(72), ry - 0.15, 0], [xt(72), ry + 0.35, 0], [xt(100), ry + 0.35, 0]])
        r2 = VGroup(label("2", 15, OK).next_to([xt(40), ry + 0.35, 0], LEFT, buff=0.1),
                    label("1", 15, OK).next_to([xt(40), ry - 0.15, 0], LEFT, buff=0.1))
        # errors row
        ey = 0.1
        el = label("errors", 16, MUTED).move_to([ox + 0.45, ey + 0.55, 0])
        errs = VGroup(*[Line([xt(t), ey - 0.25, 0], [xt(t), ey + 0.25 + 0.1 * ((t * 3) % 2), 0], color=BAD,
                             stroke_width=4) for t in [60.5, 61.3, 62, 62.8, 63.5, 64]])
        # p95 row
        py = -1.1
        pl = label("p95 vs SLO", 16, MUTED).move_to([ox + 0.7, py + 0.5, 0])
        slo = DashedLine([xt(40), py, 0], [xt(100), py, 0], color=MUTED, stroke_width=1.5)
        p95 = VMobject(color=WARN, stroke_width=3).set_points_smoothly([
            [xt(40), py - 0.3, 0], [xt(58), py - 0.3, 0], [xt(62), py + 0.35, 0], [xt(68), py + 0.3, 0],
            [xt(75), py - 0.2, 0], [xt(80), py - 0.3, 0], [xt(100), py - 0.3, 0]])

        def vmark(t, text, color, y_lab):
            ln = DashedLine([xt(t), -1.9, 0], [xt(t), 2.3, 0], color=color, stroke_width=2)
            lb = label(text, 16, color, weight=BOLD).move_to([xt(t), y_lab, 0])
            return VGroup(ln, lb)

        fault = vmark(60, "fault Tf = 60 s", BAD, 2.45)
        readyc = vmark(72, "Pod C Ready 72 s", OK, 2.45)
        rec = vmark(75, "recovered Tr = 75 s", INFO, 2.45)
        readyc[1].shift(LEFT * 0.95)
        rec[1].shift(RIGHT * 1.25)
        fault[1].shift(LEFT * 0.4)
        readyc[1].shift(DOWN * 0.0)

        self.caption("Hold load steady, record the fault time Tf, then kubectl delete pod.", wait=0.2)
        self.play(FadeIn(hdr), Create(ax), FadeIn(ticks), FadeIn(rl), FadeIn(el), FadeIn(pl), FadeIn(r2),
                  Create(slo))
        self.play(Create(fault[0]), FadeIn(fault[1]))
        self.caption("Ready Pods drop to 1 until the ReplicaSet's replacement Pod C passes readiness.", wait=0.2)
        self.play(Create(ready), run_time=1.6)
        self.play(Create(readyc[0]), FadeIn(readyc[1]))
        self.caption("Some requests fail, and latency rises while one Pod carries all the load.", wait=0.2,
                     color=TEXT_C)
        self.play(LaggedStart(*[Create(e) for e in errs], lag_ratio=0.15), Create(p95), run_time=1.6)
        self.wait(0.6)
        self.caption("Recovery is when ALL agreed SLIs are back in target: here latency, at 75 s.", wait=0.2)
        self.play(Create(rec[0]), FadeIn(rec[1]))
        br = BraceBetweenPoints([xt(75), -2.35, 0], [xt(60), -2.35, 0], color=INFO)
        bt = label("impact window · recovery time = Tr − Tf = 15 s", 17, INFO).next_to(br, DOWN, buff=0.05)
        bt.shift(RIGHT * 1.2)
        self.play(FadeOut(ticks), GrowFromCenter(br), FadeIn(bt))
        self.caption("Illustrative shape, not a measurement: errors stopped at 64 s, latency at 75 s.", wait=1.8)
