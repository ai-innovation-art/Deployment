"""Module 12 — the LLM request lifecycle (prefill vs decode, TTFT, ITL, E2E), static vs continuous batching,
and why inference scales on queue depth (KEDA) rather than CPU. Facts follow notes/12-ai-inference.html
(LLM request lifecycle, Inference metrics, Batching, Lab 2, Autoscaling inference)."""
from common import *


def outro_lines(scene, takeaway):
    """Same look as Explainer.outro, but builds one Text per line (Paragraph misplaces glyphs here)."""
    scene.clear_caption()
    scene.play(*[FadeOut(m) for m in scene.mobjects if m is not scene.tag], run_time=0.6)
    k = label("KEY TAKEAWAY", size=20, color=ACCENT, weight=BOLD)
    t = VGroup(*[label(line, 30) for line in takeaway.split("\n")]).arrange(DOWN, buff=0.22)
    if t.width > 12:
        t.scale_to_fit_width(12)
    g = VGroup(k, t).arrange(DOWN, buff=0.4)
    scene.play(FadeIn(k), Write(t), run_time=1.5)
    scene.wait(2.5)
    scene.play(FadeOut(g), FadeOut(scene.tag), run_time=0.6)


def seg(x0, x1, y, color, text, h=0.62, size=18):
    r = RoundedRectangle(corner_radius=0.08, width=x1 - x0, height=h, stroke_color=color, stroke_width=2,
                         fill_color=color, fill_opacity=0.18).move_to([(x0 + x1) / 2, y, 0])
    t = label(text, size, TEXT_C).move_to(r)
    if t.width > r.width - 0.1:
        t.scale_to_fit_width(r.width - 0.15)
    return VGroup(r, t)


def span(x0, x1, y, text, color, size=18):
    """Horizontal dimension line |<---->| with a label underneath."""
    ln = DoubleArrow([x0, y, 0], [x1, y, 0], buff=0, color=color, stroke_width=2.5,
                     tip_length=0.14, max_tip_length_to_length_ratio=0.5)
    ticks = VGroup(Line([x0, y + 0.15, 0], [x0, y - 0.15, 0], color=color, stroke_width=2),
                   Line([x1, y + 0.15, 0], [x1, y - 0.15, 0], color=color, stroke_width=2))
    t = label(text, size, color).next_to(ln, DOWN, buff=0.1)
    if t.get_left()[0] < -6.7:
        t.align_to(ln, LEFT)
    return VGroup(ln, ticks, t)


REQ_COLORS = [OK, ACCENT, WARN, INFO, "#7fd3d3", "#e3a0d0", "#c8d27a", "#f2a37a"]


class M12Inference(Explainer):
    MODULE = "Module 12"
    TITLE = "LLM inference: prefill, decode, batching"
    SUBTITLE = "TTFT and ITL, continuous batching, and scaling on queue depth"

    def construct(self):
        self.title_card()

        # ================= lifecycle timeline =================
        y_seg, y_axis = 2.05, 1.55
        x_send, x_q, x_pf = -6.2, -5.0, -2.6
        axis = Arrow([-6.4, y_axis, 0], [6.5, y_axis, 0], buff=0, color=MUTED, stroke_width=2,
                     max_tip_length_to_length_ratio=0.02)
        tlab = label("time", 16, MUTED).next_to(axis, RIGHT, buff=0.05).shift(LEFT * 0.4 + DOWN * 0.25)
        q = seg(x_send, x_q, y_seg, MUTED, "queue")
        pf = seg(x_q, x_pf, y_seg, WARN, "prefill: 600 prompt tokens")
        tok_x = [x_pf + 0.3 + i * 0.95 for i in range(9)]
        toks = VGroup(*[Square(0.4, stroke_color=OK, stroke_width=2, fill_color=OK, fill_opacity=0.35 if i else 0.75).move_to([x, y_seg, 0])
                        for i, x in enumerate(tok_x)])
        tnums = VGroup(*[label(str(i + 1), 14, TEXT_C).move_to(s) for i, s in enumerate(toks)])
        send = label("request sent", 15, MUTED).next_to([x_send, y_seg + 0.3, 0], UP, buff=0.1)

        kv_lab = label("KV cache", 18, INFO).move_to([-5.6, -0.95, 0])
        kv_cells = VGroup(*[Rectangle(width=0.5, height=0.4, stroke_color=INFO, stroke_width=1.5) for _ in range(18)]).arrange(RIGHT, buff=0.06)
        kv_cells.next_to(kv_lab, RIGHT, buff=0.3)

        self.caption("An LLM request has two phases: prefill, then decode. Watch one streamed request.", wait=0.3)
        self.play(GrowArrow(axis), FadeIn(tlab), FadeIn(send), run_time=0.8)
        self.caption("First it may wait in a queue. No compute happens, but the time still counts.", wait=0.2)
        self.play(GrowFromEdge(q, LEFT), run_time=0.8)
        self.wait(0.8)

        self.caption("Prefill runs all prompt tokens through the model in one parallel pass. It is compute-bound.", wait=0.2)
        self.play(FadeIn(kv_lab), FadeIn(kv_cells), run_time=0.5)
        self.play(GrowFromEdge(pf, LEFT),
                  *[kv_cells[i].animate.set_fill(INFO, opacity=0.6) for i in range(7)], run_time=1.4)
        self.caption("It writes keys and values into the KV cache and produces the first token.", wait=0.2)
        self.play(FadeIn(toks[0], scale=0.5), FadeIn(tnums[0]), run_time=0.6)
        ttft = span(x_send, tok_x[0] - 0.2, 0.95, "TTFT = t_first_token − t_send  (queue + prefill + network)", WARN, 17)
        self.play(FadeIn(ttft), run_time=0.7)
        self.wait(1.4)

        self.caption("Decode then makes one token per step. Each step reads the whole KV cache and adds one entry.", wait=0.1)
        for i in range(1, 9):
            self.play(FadeIn(toks[i], scale=0.5), FadeIn(tnums[i]),
                      kv_cells[6 + i].animate.set_fill(INFO, opacity=0.6), run_time=0.32)
        self.caption("The gap between streamed tokens is the inter-token latency (ITL). Decode is memory-bound.", wait=0.2)
        itl = span(tok_x[3], tok_x[4], y_seg + 0.62, "ITL", OK, 16)
        itl[2].next_to(itl[0], UP, buff=0.08)
        self.play(FadeIn(itl), run_time=0.6)
        self.wait(1.0)

        e2e = span(x_send, tok_x[-1] + 0.2, 0.0, "E2E latency = t_last − t_send", ACCENT, 17)
        self.caption("End-to-end latency runs from sending the request to the last token.", wait=0.2)
        self.play(FadeIn(e2e), run_time=0.7)
        formula = VGroup(label("With N output tokens:", 20, MUTED),
                         mono("ITL = (E2E − TTFT) / (N − 1)", 24, TEXT_C)).arrange(RIGHT, buff=0.35).move_to(DOWN * 2.1)
        self.play(FadeIn(formula, shift=UP * 0.1), run_time=0.7)
        self.caption("Long prompts hurt TTFT. Long outputs and many sequences raise ITL and fill the KV cache.", wait=2.0)

        timeline = VGroup(axis, tlab, q, pf, toks, tnums, send, kv_lab, kv_cells, ttft, itl, e2e, formula)
        self.play(FadeOut(timeline), run_time=0.6)

        # ================= batching =================
        cell_w, cell_h, n_steps = 0.72, 0.36, 12
        x0 = -4.4

        def grid_y(panel_top, row):
            return panel_top - 0.45 - row * (cell_h + 0.08)

        top_s, top_c = 2.75, -0.05
        head_s = label("Static batching", 22, WARN, weight=BOLD).move_to([-5.4, top_s - 0.15, 0])
        head_c = label("Continuous batching", 22, OK, weight=BOLD).move_to([-5.15, top_c - 0.15, 0])
        head_s.align_to(head_c, LEFT).shift(LEFT * 0.0)
        for h in (head_s, head_c):
            h.to_edge(LEFT, buff=0.5)
        slot_labels = VGroup()
        for top in (top_s, top_c):
            for r in range(4):
                slot_labels.add(label(f"slot {r + 1}", 15, MUTED).move_to([x0 - 0.75, grid_y(top, r), 0]))
        frames = VGroup()
        for top in (top_s, top_c):
            for r in range(4):
                for k in range(n_steps):
                    frames.add(Rectangle(width=cell_w, height=cell_h, stroke_color=MUTED, stroke_width=0.6,
                                         stroke_opacity=0.35).move_to([x0 + cell_w / 2 + k * (cell_w + 0.04), grid_y(top, r), 0]))
        step_lab = label("decode steps →", 15, MUTED).move_to([x0 + 7.5 * (cell_w + 0.04), top_c + 0.35, 0])

        lengths = [3, 8, 5, 2, 4, 6, 3, 5, 4, 3, 5, 4, 6, 3]  # request A, B, C, ... output lengths (in steps)

        # static schedule: batch 1 = reqs 0..3 from step 0; batch 2 = reqs 4..7 from max(len) of batch 1
        static_cells = {k: [] for k in range(n_steps)}
        b1_end = max(lengths[:4])
        for r in range(4):
            for k in range(b1_end):
                busy = k < lengths[r]
                static_cells[k].append((r, k, r if busy else None))
        for r in range(4):
            for k in range(b1_end, n_steps):
                busy = (k - b1_end) < lengths[4 + r]
                static_cells[k].append((r, k, 4 + r if busy else None))
        # continuous schedule: a free slot is refilled at the next step from the queue
        cont_cells = {k: [] for k in range(n_steps)}
        slot_req = [0, 1, 2, 3]
        slot_left = [lengths[i] for i in slot_req]
        nxt = 4
        for k in range(n_steps):
            for r in range(4):
                if slot_left[r] == 0 and nxt < len(lengths):
                    slot_req[r], slot_left[r] = nxt, lengths[nxt]
                    nxt += 1
                if slot_left[r] > 0:
                    cont_cells[k].append((r, k, slot_req[r]))
                    slot_left[r] -= 1
                else:
                    cont_cells[k].append((r, k, None))

        def make_cell(top, r, k, req):
            pos = [x0 + cell_w / 2 + k * (cell_w + 0.04), grid_y(top, r), 0]
            if req is None:
                c = Rectangle(width=cell_w, height=cell_h, stroke_width=0, fill_color=BAD, fill_opacity=0.18).move_to(pos)
                return VGroup(c, label("idle", 12, BAD).move_to(pos))
            col = REQ_COLORS[req % len(REQ_COLORS)]
            c = Rectangle(width=cell_w, height=cell_h, stroke_color=col, stroke_width=1.5, fill_color=col, fill_opacity=0.55).move_to(pos)
            return VGroup(c, label("ABCDEFGHIJKLMN"[req], 14, BG, weight=BOLD).move_to(pos))

        self.caption("Batching runs several requests through the model in the same forward pass.", wait=0.2)
        self.play(FadeIn(head_s), FadeIn(head_c), FadeIn(slot_labels), FadeIn(frames), FadeIn(step_lab), run_time=0.9)
        self.caption("Static: the batch runs until its longest request ends. Finished slots sit idle.", wait=0.1)
        cursor = Line([x0, top_s + 0.1, 0], [x0, grid_y(top_c, 3) - 0.3, 0], color=TEXT_C, stroke_width=2)
        self.add(cursor)
        all_cells = VGroup()
        for k in range(n_steps):
            new = [make_cell(top_s, r, kk, rq) for r, kk, rq in static_cells[k]] + \
                  [make_cell(top_c, r, kk, rq) for r, kk, rq in cont_cells[k]]
            all_cells.add(*new)
            self.play(*[FadeIn(c) for c in new],
                      cursor.animate.set_x(x0 + (k + 1) * (cell_w + 0.04)), run_time=0.42)
            if k == 3:
                self.caption("Continuous: membership changes every decode step. A freed slot is refilled at the next step.", wait=0)
            if k == 8:
                self.caption("Static: the next batch waits for the whole batch. Continuous: no idle slots.", wait=0)
        self.wait(1.4)
        self.caption("vLLM uses continuous batching. More sequences per step: more tokens/s, but ITL rises.", wait=2.2)
        self.play(FadeOut(VGroup(head_s, head_c, slot_labels, frames, step_lab, all_cells, cursor)), run_time=0.6)

        # ================= autoscaling =================
        ns = zone(5.0, 4.2, "namespace reliability-lab", color=MUTED).move_to(LEFT * 4.0 + UP * 0.75)
        srv = box("mock-llm", "model server · MAX_BATCH=8", color=OK, w=3.6, h=1.0, title_size=22).move_to(LEFT * 4.0 + UP * 1.75)
        cpu = VGroup(label("CPU", 18, MUTED), Rectangle(width=2.4, height=0.28, stroke_color=MUTED, stroke_width=1.5),
                     ).arrange(RIGHT, buff=0.2).move_to(LEFT * 4.15 + UP * 0.6)
        cpu_fill = Rectangle(width=0.12, height=0.28, stroke_width=0, fill_color=OK, fill_opacity=0.8).align_to(cpu[1], LEFT).set_y(cpu[1].get_y())
        cpu_val = label("near idle", 16, OK).next_to(cpu, RIGHT, buff=0.15)
        qlab = label("waiting:", 18, MUTED).move_to(LEFT * 5.6 + DOWN * 0.3)
        qdots = VGroup(*[Square(0.22, stroke_width=0, fill_color=WARN, fill_opacity=0.85) for _ in range(8)]).arrange(RIGHT, buff=0.08).next_to(qlab, RIGHT, buff=0.2)

        self.caption("Lab 2: 16 users against mock-llm with MAX_BATCH=8. About 8 requests wait in the queue.", wait=0.2)
        self.play(Create(ns[0]), FadeIn(ns[1]), FadeIn(srv), run_time=0.8)
        self.play(FadeIn(cpu), FadeIn(cpu_fill), FadeIn(cpu_val), FadeIn(qlab), run_time=0.5)
        self.play(LaggedStart(*[FadeIn(d, shift=LEFT * 0.2) for d in qdots], lag_ratio=0.15), run_time=1.0)
        self.caption("Latency roughly doubles, yet CPU stays near idle. A CPU-based HPA would never scale.", wait=0.3)
        hpa_cpu = box("HPA on CPU", "metrics-server → CPU %", color=MUTED, w=3.0, h=0.95, title_size=20).move_to(RIGHT * 0.6 + UP * 0.6)
        self.play(FadeIn(hpa_cpu), run_time=0.5)
        self.packet([cpu.get_right() + RIGHT * 1.2, hpa_cpu.get_left()], color=MUTED, run_time=0.6)
        no = label("no scale-out", 18, BAD, weight=BOLD).next_to(hpa_cpu, DOWN, buff=0.15)
        self.play(FadeIn(no), Indicate(hpa_cpu[0], color=BAD), run_time=0.7)
        self.caption("GPU-bound servers keep host CPU low even when saturated. What users feel is queueing.", wait=1.6)

        self.play(FadeOut(hpa_cpu), FadeOut(no), run_time=0.4)
        prom = box("Prometheus", "scrapes /metrics", color=INFO, w=2.6, h=0.9, title_size=20).move_to(RIGHT * 0.5 + UP * 1.75)
        keda = box("KEDA", "ScaledObject query", color=ACCENT, w=2.6, h=0.9, title_size=20).move_to(RIGHT * 4.2 + UP * 1.75)
        hpa = box("HPA", "managed by KEDA", color=ACCENT, w=2.6, h=0.9, title_size=20).move_to(RIGHT * 4.2 + DOWN * 0.1)
        query = mono("query: waiting + running\nthreshold: 6 per replica", 16, WARN).move_to(RIGHT * 1.0 + UP * 0.55)
        self.caption("Scale on queue depth and in-flight requests instead: KEDA turns a PromQL result into a metric.", wait=0.2)
        self.play(FadeIn(prom), FadeIn(keda), FadeIn(hpa), run_time=0.7)
        self.packet([srv.get_right(), prom.get_left()], color=WARN, run_time=0.6)
        self.add(connect(srv, prom))
        self.packet([prom.get_right(), keda.get_left()], color=WARN, run_time=0.6)
        self.add(connect(prom, keda))
        self.play(FadeIn(query), run_time=0.4)
        self.packet([keda.get_bottom(), hpa.get_top()], color=ACCENT, run_time=0.5)
        self.add(connect(keda, hpa))

        reps = VGroup(*[box("mock-llm", None, color=OK, w=1.5, h=0.55, title_size=15) for _ in range(3)]).arrange(RIGHT, buff=0.15)
        reps.move_to(LEFT * 4.0 + DOWN * 1.05)
        rep_lab = label("replicas 1 → 3", 18, OK).next_to(hpa, DOWN, buff=0.15)
        self.packet([hpa.get_left(), hpa.get_left() + LEFT * 2.3 + DOWN * 0.95], color=ACCENT, run_time=0.6)
        self.play(FadeIn(rep_lab), LaggedStart(*[FadeIn(r, scale=0.8) for r in reps], lag_ratio=0.3),
                  LaggedStart(*[FadeOut(d) for d in qdots[2:]], lag_ratio=0.1), run_time=1.2)
        self.caption("New replicas need minutes (image pull, weight loading). Keep warm capacity and scale early.", wait=2.2)

        outro_lines(self, "Prefill sets TTFT; decode sets ITL. Continuous batching refills slots every step.\nScale model servers on queue depth, not CPU.")
