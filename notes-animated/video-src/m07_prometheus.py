"""Module 07 — Prometheus pull model, series = name + labels, classic histogram buckets,
histogram_quantile interpolation, Grafana as a query client, error budget / burn rate.
Facts follow notes/07-observability.html (sections 3, 4, 5, 7, 11, 13)."""
from common import *

LES = ["0.025", "0.05", "0.075", "0.1", "0.25", "0.5", "+Inf"]
FINAL = [0, 120, 930, 970, 995, 1000, 1000]   # Figure 5: 1000 requests to /work?ms=50


class M07Prometheus(Explainer):
    MODULE = "Module 07"
    TITLE = "Prometheus & histograms"
    SUBTITLE = "Pull /metrics · series · buckets · histogram_quantile · Grafana"

    def construct(self):
        self.title_card()
        self.part_scrape()
        self.part_histogram()
        self.part_budget()
        self.outro("Prometheus pulls and stores series; histograms keep buckets.\n"
                   "p95 is an estimate, only as precise as the bucket it lands in.")

    # ---------------------------------------------------------------- scrape
    def part_scrape(self):
        ns = zone(3.6, 4.6, "ns reliability-lab", color=OK).move_to(LEFT * 5.0 + UP * 0.5)
        pa = box("Pod", "reliability-api :8000", color=OK, w=3.0, h=1.0, sub_size=16).move_to(LEFT * 5.0 + UP * 1.3)
        pb = box("Pod", "reliability-api :8000", color=OK, w=3.0, h=1.0, sub_size=16).move_to(LEFT * 5.0 + DOWN * 0.3)
        ma = mono("/metrics", 16, INFO).next_to(pa, DOWN, buff=0.06)
        mb = mono("/metrics", 16, INFO).next_to(pb, DOWN, buff=0.06)

        pz = zone(4.2, 4.6, "Prometheus server", color=INFO).move_to(RIGHT * 0.1 + UP * 0.5)
        ret = box("retrieval", "scraper (pull)", color=INFO, w=3.4, h=0.95, sub_size=16).move_to(RIGHT * 0.1 + UP * 1.5)
        tsdb = box("TSDB", "time series on local disk", color=INFO, w=3.4, h=0.95, sub_size=16).move_to(RIGHT * 0.1 + DOWN * 0.25)
        api = mono("PromQL API :9090", 16, INFO).next_to(tsdb, DOWN, buff=0.25)

        graf = box("Grafana", "stores no metrics", color=WARN, w=2.8, h=1.0, sub_size=16).move_to(RIGHT * 5.0 + UP * 0.5)

        self.caption("reliability-api Pods expose their own numbers as plain text on GET /metrics.", wait=0.3)
        self.play(Create(ns[0]), FadeIn(ns[1]), FadeIn(pa), FadeIn(pb), FadeIn(ma), FadeIn(mb), run_time=1.0)
        self.play(Create(pz[0]), FadeIn(pz[1]), FadeIn(ret), FadeIn(tsdb), run_time=1.0)

        self.caption("Pull model: every scrape_interval Prometheus sends GET /metrics to each target.", wait=0.2)
        for _ in range(2):
            for p, m in ((pa, ma), (pb, mb)):
                self.packet([ret.get_left(), m.get_right()], color=INFO, run_time=0.45)
                self.packet([m.get_right(), ret.get_left()], color=WARN, run_time=0.45)
        up = mono("up = 1", 18, OK).next_to(ret, UP, buff=0.12)
        self.caption("Each scrape also records 'up': 1 if the scrape worked, 0 if it failed.", wait=0.2)
        self.play(FadeIn(up))
        self.wait(1.0)

        self.caption("Samples are appended to the TSDB. A series = metric name + a set of labels.", wait=0.2)
        self.packet([ret.get_bottom(), tsdb.get_top()], color=WARN, run_time=0.5)
        self.play(*[FadeOut(m) for m in (ns, pa, pb, ma, mb, up)], run_time=0.5)
        self.play(VGroup(pz, ret, tsdb).animate.shift(LEFT * 4.6), run_time=0.7)
        name = mono("http_requests_total", 22, ACCENT)
        labels = mono('{path="/work", status="200", pod="…abcde"}', 20, WARN)
        name.move_to(RIGHT * 2.4 + UP * 2.6)
        labels.next_to(name, DOWN, buff=0.95)
        series = VGroup(name, labels)
        b1 = Brace(name, DOWN, color=ACCENT)
        b2 = Brace(labels, DOWN, color=WARN)
        t1 = label("metric name", 18, ACCENT).next_to(b1, DOWN, buff=0.04)
        t2 = label("labels: each unique set = its own series", 18, WARN).next_to(b2, DOWN, buff=0.08)
        samples = VGroup(*[mono(s, 18) for s in ["10:00:00 → 1520", "10:00:30 → 1581",
                                                  "10:01:00 → 1644", "10:01:30 → 1702"]]
                         ).arrange(DOWN, aligned_edge=LEFT, buff=0.1).move_to(RIGHT * 2.4 + DOWN * 1.35)
        st = label("samples (timestamp, float64)", 18, MUTED).next_to(samples, UP, buff=0.2)
        self.play(FadeIn(series), run_time=0.6)
        self.play(GrowFromCenter(b1), FadeIn(t1), GrowFromCenter(b2), FadeIn(t2), run_time=0.8)
        self.play(FadeIn(st), LaggedStart(*[FadeIn(s, shift=LEFT * 0.2) for s in samples], lag_ratio=0.3),
                  run_time=1.4)
        self.caption("Never add unbounded labels (user IDs, raw URLs): every new value is a new series.",
                     wait=1.6)
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag and m is not self.caption_mob],
                  run_time=0.6)

    # ------------------------------------------------------------- histogram
    def part_histogram(self):
        x0, base, H, step, bw = -6.1, -2.3, 3.6, 1.0, 0.72
        axis = Line([x0 - 0.2, base, 0], [x0 + 7 * step, base, 0], color=MUTED, stroke_width=2)
        title = mono("http_request_duration_seconds_bucket{le=…}", 18, INFO).move_to(LEFT * 2.6 + UP * 2.9)
        cols = [x0 + 0.4 + i * step for i in range(7)]
        les = VGroup(*[mono("le=" + l, 13, MUTED).move_to([c, base - 0.25, 0]) for c, l in zip(cols, LES)])

        def bars(counts, highlight=None):
            g = VGroup()
            for i, (c, n) in enumerate(zip(cols, counts)):
                h = max(0.02, H * n / 1000)
                col = INFO if highlight is None or i not in highlight else WARN
                r = Rectangle(width=bw, height=h, stroke_color=col, stroke_width=2, fill_color=col,
                              fill_opacity=0.35).move_to([c, base + h / 2, 0])
                t = mono(str(n), 15, TEXT_C)
                if h > 1.0:
                    t.move_to(r.get_top() + DOWN * 0.3)
                else:
                    t.next_to(r, UP, buff=0.06)
                g.add(VGroup(r, t))
            return g

        counts = [0] * 7
        bg = bars(counts)
        sc = VGroup(mono("_sum   = 0", 18), mono("_count = 0", 18)).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        sc.move_to(RIGHT * 4.6 + UP * 1.6)

        self.caption("A histogram counts observations into buckets with upper bounds 'le' (≤).", wait=0.2)
        self.play(FadeIn(title), Create(axis), FadeIn(les), FadeIn(bg), FadeIn(sc), run_time=1.0)

        # one observation 0.052 s
        obs = mono("observe(0.052)", 20, WARN).move_to(RIGHT * 4.6 + UP * 0.3)
        self.caption("A 52 ms request increments EVERY bucket with le ≥ 0.052, plus _sum and _count.", wait=0.2)
        self.play(FadeIn(obs, shift=DOWN * 0.2))
        dot = Dot(obs.get_left() + LEFT * 0.2, color=WARN, radius=0.1)
        self.play(dot.animate.move_to([cols[2], base + 0.3, 0]), run_time=0.7)
        self.remove(dot)
        counts = [0, 0, 1, 1, 1, 1, 1]
        nb = bars(counts, highlight={2, 3, 4, 5, 6})
        sc2 = VGroup(mono("_sum   = 0.052", 18), mono("_count = 1", 18)).arrange(DOWN, aligned_edge=LEFT,
                                                                                  buff=0.1).move_to(sc, aligned_edge=LEFT)
        self.play(Transform(bg, nb), Transform(sc, sc2), run_time=0.8)
        self.caption("So buckets are cumulative, and le=\"+Inf\" always equals _count.", wait=1.4)

        # fast-forward to 1000 requests
        self.caption("After 1000 requests to /work?ms=50: most land between 0.05 and 0.075 s.", wait=0.2)
        self.play(FadeOut(obs))
        tracker = ValueTracker(1)

        def upd():
            k = tracker.get_value()
            return bars([int(round(f * k / 1000)) if f else 0 for f in FINAL])
        live = always_redraw(upd)
        self.remove(bg)
        self.add(live)
        self.play(tracker.animate.set_value(1000), run_time=2.0, rate_func=smooth)
        live.clear_updaters()
        sc3 = VGroup(mono("_count = 1000", 18)).move_to(sc, aligned_edge=LEFT)
        self.play(Transform(sc, sc3))
        self.wait(0.6)

        # histogram_quantile
        q = VGroup(mono("histogram_quantile(0.95,", 17, TEXT_C),
                   mono("  sum by (le) (", 17, TEXT_C),
                   mono("    rate(..._bucket[5m])))", 17, TEXT_C)).arrange(DOWN, aligned_edge=LEFT, buff=0.06)
        qbg = SurroundingRectangle(q, color=ACCENT, buff=0.15, corner_radius=0.1, stroke_width=1.5)
        qg = VGroup(qbg, q).move_to(RIGHT * 4.75 + UP * 1.75)
        self.caption("p95 query: rate() the bucket counters, sum by (le), then histogram_quantile(0.95, …).",
                     wait=0.2)
        self.play(FadeOut(sc), FadeIn(qg), run_time=0.7)
        self.wait(1.0)

        y950 = base + H * 0.95
        rank_line = DashedLine([x0 - 0.2, y950, 0], [x0 + 7 * step, y950, 0], color=WARN, stroke_width=2)
        rank_t = mono("rank = 0.95 × 1000 = 950", 17, WARN).move_to(RIGHT * 4.75 + UP * 0.3)
        self.caption("Rank = 0.95 × 1000 = 950. The first bucket reaching 950 is le=0.1 (970).", wait=0.2)
        self.play(Create(rank_line), FadeIn(rank_t))
        hl = VGroup(SurroundingRectangle(live[3], color=WARN, buff=0.08),
                    SurroundingRectangle(live[2], color=MUTED, buff=0.08))
        self.play(Create(hl[0]), Create(hl[1]))
        self.wait(1.0)
        f1 = VGroup(mono("0.075 + 0.025 ×", 17, TEXT_C), mono("(950 − 930) / (970 − 930)", 17, TEXT_C)).arrange(DOWN, buff=0.08)
        f2 = mono("p95 ≈ 0.0875 s", 22, OK)
        fg = VGroup(f1, f2).arrange(DOWN, buff=0.2).move_to(RIGHT * 4.75 + DOWN * 0.9)
        self.caption("It assumes values are spread evenly inside (0.075, 0.1] and interpolates linearly.",
                     wait=0.2)
        self.play(FadeIn(f1))
        self.play(Write(f2))
        self.wait(1.2)
        self.caption("An estimate: it can only be as precise as the bucket that contains the rank.", wait=1.6)

        # Grafana + failure
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag and m is not self.caption_mob],
                  run_time=0.6)
        graf = box("Grafana panel", "p95 latency (s)", color=WARN, w=3.4, h=1.1, sub_size=16).move_to(RIGHT * 4.6 + UP * 1.6)
        prom = box("Prometheus", "HTTP API · PromQL", color=INFO, w=3.4, h=1.1, sub_size=16).move_to(LEFT * 0.4 + UP * 1.6)
        tgt = box("Pod", "reliability-api", color=OK, w=2.8, h=1.0, sub_size=16).move_to(LEFT * 5.2 + UP * 1.6)
        self.caption("Grafana stores no metrics: each panel runs a PromQL query against Prometheus.", wait=0.2)
        self.play(FadeIn(prom), FadeIn(graf), FadeIn(tgt))
        self.packet([graf.get_left(), prom.get_right()], color=WARN, run_time=0.6)
        self.packet([prom.get_right(), graf.get_left()], color=INFO, run_time=0.6)
        panel = RoundedRectangle(corner_radius=0.1, width=3.4, height=1.7, stroke_color=WARN,
                                 stroke_width=1.5).move_to(RIGHT * 4.6 + DOWN * 0.35)
        line = VMobject(color=WARN, stroke_width=3).set_points_smoothly(
            [RIGHT * (3.15 + i * 0.36) + DOWN * (0.75 - 0.5 * ((i * 7) % 5) / 4) for i in range(9)])
        self.play(Create(panel), Create(line), run_time=0.8)
        self.wait(0.6)

        bad = box("Pod", "/metrics unreachable", color=BAD, w=2.8, h=1.0, sub_size=16).move_to(tgt)
        self.caption("Failure: a target can't be scraped. Prometheus records up = 0 for it.", wait=0.2)
        self.play(ReplacementTransform(tgt, bad))
        arr = DashedLine(prom.get_left() + LEFT * 0.1, bad.get_right() + RIGHT * 0.1, color=BAD, stroke_width=3)
        x = label("✗ scrape failed", 18, BAD, weight=BOLD).move_to([arr.get_center()[0], 0.65, 0])
        self.play(Create(arr), FadeIn(x))
        up0 = mono('up{namespace="reliability-lab"} == 0', 20, BAD).move_to(LEFT * 2.6 + DOWN * 0.6)
        self.play(FadeIn(up0))
        self.caption("Blank panel? Check up first: missing target, up = 0, or a bad query.", wait=1.8)
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag and m is not self.caption_mob],
                  run_time=0.6)

    # ---------------------------------------------------------- error budget
    def part_budget(self):
        hdr = label("SLO → error budget → burn rate", 28, ACCENT, weight=BOLD).move_to(UP * 2.9)
        r1 = mono("SLO 99.9 %  →  error budget = 1 − SLO = 0.1 %", 20)
        r2 = mono("e.g. 3,000,000 requests in the window  →  ≈ 3,000 errors allowed", 20)
        rows = VGroup(r1, r2).arrange(DOWN, aligned_edge=LEFT, buff=0.25).move_to(UP * 1.8)
        self.caption("An SLO is a target for an SLI over a window. The error budget is 100 % − SLO.", wait=0.2)
        self.play(FadeIn(hdr), FadeIn(r1))
        self.play(FadeIn(r2))
        self.wait(1.0)

        ox, oy, W, Hh = -4.2, -2.3, 8.4, 2.6
        ax = VGroup(Line([ox, oy, 0], [ox + W, oy, 0], color=MUTED), Line([ox, oy, 0], [ox, oy + Hh, 0], color=MUTED))
        yl = label("budget left", 16, MUTED).next_to(ax[1], LEFT, buff=0.1).shift(UP * 0.9)
        xl = VGroup(label("day 0", 16, MUTED).next_to([ox, oy, 0], DOWN, buff=0.08),
                    label("day 30", 16, MUTED).next_to([ox + W, oy, 0], DOWN, buff=0.08))

        def burn(rate, color, txt):
            end_day = min(30, 30 / rate)
            p_end = [ox + W * end_day / 30, oy + Hh * (1 - end_day * rate / 30), 0]
            ln = Line([ox, oy + Hh, 0], p_end, color=color, stroke_width=4)
            return ln, mono(txt, 18, color)

        self.caption("Burn rate = how fast you spend it. Burn 1 runs out exactly at the window's end.", wait=0.2)
        self.play(Create(ax), FadeIn(yl), FadeIn(xl))
        legend_y = [oy + Hh - 0.1, oy + Hh - 0.55, oy + Hh - 1.0]
        for (rate, col, txt), ly in zip(((1, OK, "burn 1 → exhausted at day 30"), (6, WARN, "burn 6 → day 5"),
                                         (14.4, BAD, "burn 14.4 → ≈ 2.1 days")), legend_y):
            ln, t = burn(rate, col, txt)
            t.move_to([ox + 4.4, ly, 0], aligned_edge=LEFT)
            self.play(Create(ln), FadeIn(t), run_time=0.8)
        self.caption("Alert threshold = burn rate × (1 − SLO), e.g. 14.4 × 0.001 for a fast-burn page.", wait=1.8)
