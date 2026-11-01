"""Module 13 — the troubleshooting loop, the layer model (find the lowest broken layer), a CrashLoopBackOff
walkthrough with the restart back-off, and mapping STATUS to a layer. Facts follow
notes/13-troubleshooting-capstone.html (Part A loop, layer model, Pod phases table, Restart back-off,
symptom playbook 3/4, Scenario F)."""
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


LAYERS = [
    ("1 · Node / cluster / cloud", "kubectl get nodes ; kubectl top nodes"),
    ("2 · Scheduling", "describe pod → FailedScheduling"),
    ("3 · Image", "describe pod → Events: Failed to pull"),
    ("4 · Container process", "kubectl logs … --previous"),
    ("5 · Pod readiness / probes", "describe pod → Readiness probe failed"),
    ("6 · Service → EndpointSlices", "kubectl get endpointslices -l …"),
    ("7 · Ingress / Gateway / port-forward", "kubectl port-forward svc/reliability-api 8080:80"),
    ("8 · Client / load generator", "curl -v http://localhost:8080/ready"),
]


def layer_y(i):
    return -2.45 + i * 0.7


class M13Troubleshoot(Explainer):
    MODULE = "Module 13"
    TITLE = "Troubleshooting reliability-api"
    SUBTITLE = "A loop, a layer model, CrashLoopBackOff and the STATUS → layer map"

    def construct(self):
        self.title_card()

        # ================= the loop =================
        names = ["Observe", "Triage", "Hypothesise", "Test", "Fix", "Verify", "Record", "Prevent"]
        subs = ["symptom + when", "which layer?", "one testable cause", "command / metric / log",
                "smallest safe change", "symptom gone?", "runbook / postmortem", "test, alert, guardrail"]
        center = UP * 0.25
        rx, ry = 4.6, 2.2
        nodes = VGroup()
        for i, (n, s) in enumerate(zip(names, subs)):
            ang = PI / 2 - i * TAU / 8
            pos = center + np.array([rx * np.cos(ang), ry * np.sin(ang), 0])
            nodes.add(box(f"{i + 1} · {n}", s, color=ACCENT, w=2.75, h=0.85, title_size=19, sub_size=14).move_to(pos))
        arcs = VGroup(*[CurvedArrow(nodes[i].get_center(), nodes[(i + 1) % 8].get_center(), angle=-TAU / 14,
                                    color=MUTED, stroke_width=2, tip_length=0.15) for i in range(8)])
        for i, a in enumerate(arcs):
            a.set_opacity(0)
        # straight connectors between box edges look cleaner than arcs through boxes
        links = VGroup(*[connect(nodes[i], nodes[(i + 1) % 8], buff=0.08) for i in range(8)])
        self.caption("Don't debug by trying random commands. Follow a loop.", wait=0.2)
        self.play(LaggedStart(*[FadeIn(n, scale=0.9) for n in nodes], lag_ratio=0.12), run_time=1.6)
        self.play(LaggedStart(*[GrowArrow(l) for l in links], lag_ratio=0.1), run_time=1.0)
        for i in range(8):
            self.play(nodes[i][0].animate.set_fill(ACCENT, opacity=0.45), run_time=0.18)
            self.play(nodes[i][0].animate.set_fill(ACCENT, opacity=0.12), run_time=0.12)
        self.caption("Change one thing at a time. Facts come from output; inferences need evidence.", wait=0.3)
        back = CurvedArrow(nodes[3].get_left() + UP * 0.1, nodes[2].get_bottom() + LEFT * 0.2, angle=-TAU / 6,
                           color=WARN, stroke_width=3, tip_length=0.18)
        back_l = label("disproved → new hypothesis", 17, WARN).move_to(center + RIGHT * 0.9 + UP * 0.1)
        self.caption("A test that disproves a hypothesis is progress: form a new one and test again.", wait=0.2)
        self.play(Create(back), FadeIn(back_l), run_time=0.9)
        self.wait(1.4)
        self.play(FadeOut(VGroup(nodes, links, back, back_l)), run_time=0.6)

        # ================= the layer stack =================
        rows = VGroup()
        cmds = VGroup()
        for i, (name, cmd) in enumerate(LAYERS):
            r = RoundedRectangle(corner_radius=0.08, width=5.0, height=0.56, stroke_color=OK, stroke_width=2,
                                 fill_color=OK, fill_opacity=0.12).move_to([-3.9, layer_y(i), 0])
            t = label(name, 19).move_to(r).align_to(r, LEFT).shift(RIGHT * 0.2)
            rows.add(VGroup(r, t))
            cmds.add(mono(cmd, 16, MUTED).move_to([0, layer_y(i), 0]).align_to(RIGHT * -1.0, LEFT))
        self.caption("Triage with the layer model: each layer depends on the ones below it.", wait=0.2)
        self.play(LaggedStart(*[FadeIn(r, shift=UP * 0.15) for r in rows], lag_ratio=0.1), run_time=1.6)
        self.caption("Each layer has one first command that tells you whether it is healthy.", wait=0.2)
        self.play(LaggedStart(*[FadeIn(c, shift=LEFT * 0.15) for c in cmds], lag_ratio=0.08), run_time=1.4)
        self.wait(0.8)

        self.caption("A broken layer makes every layer above it look broken too.", wait=0.2)
        self.play(rows[3][0].animate.set_stroke(BAD).set_fill(BAD, opacity=0.3), run_time=0.5)
        self.play(*[rows[i][0].animate.set_stroke(WARN).set_fill(WARN, opacity=0.15) for i in range(4, 8)], run_time=0.8)
        self.caption("So find the LOWEST broken layer. Fixing it fixes the symptoms above.", wait=0.2)
        ptr = Arrow(LEFT * 7.0, LEFT * 6.5, color=BAD, stroke_width=5, buff=0, max_tip_length_to_length_ratio=0.5).set_y(layer_y(3))
        self.play(GrowArrow(ptr), Indicate(rows[3], color=BAD, scale_factor=1.05), run_time=0.8)
        self.wait(1.4)
        stack = VGroup(rows, cmds, ptr)
        self.play(FadeOut(stack), run_time=0.6)

        # ================= CrashLoopBackOff walkthrough =================
        table = mono("NAME                              READY   STATUS             RESTARTS\n"
                     "reliability-api-6d9f7c8b5d-4kq2m  0/1     CrashLoopBackOff   4", 19, TEXT_C)
        hdr = VGroup(*[ch for ch in table if ch.get_y() > table.get_y()])
        hdr.set_color(MUTED)
        row = VGroup(*[ch for ch in table if ch.get_y() <= table.get_y()])
        row.shift(DOWN * 0.12)
        getp = VGroup(mono("$ kubectl -n reliability-lab get pods", 20, ACCENT), hdr, row)
        getp[0].next_to(table, UP, buff=0.18).align_to(table, LEFT)
        getp.to_edge(LEFT, buff=0.9).set_y(2.3)
        self.caption("Walkthrough: reliability-api is in CrashLoopBackOff. The process keeps exiting.", wait=0.2)
        self.play(FadeIn(getp[0]), run_time=0.4)
        self.play(FadeIn(getp[1]), FadeIn(getp[2]), run_time=0.5)
        hl = SurroundingRectangle(row, color=BAD, buff=0.07, stroke_width=2)
        self.play(Create(hl), run_time=0.4)
        self.wait(0.6)

        logs = VGroup(mono("$ kubectl -n reliability-lab logs <pod> --previous", 20, ACCENT),
                      label("current logs may be empty: it just restarted. Read the previous instance.", 19, MUTED)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        logs.next_to(getp, DOWN, buff=0.4).align_to(getp, LEFT)
        self.caption("Step 1: read the logs of the previous container with --previous.", wait=0.2)
        self.play(FadeIn(logs, shift=UP * 0.1), run_time=0.6)
        self.wait(1.0)
        last = VGroup(mono("$ kubectl get pod <pod> -o jsonpath='{…lastState.terminated}'", 20, ACCENT),
                      mono('{"exitCode":137, "reason":"OOMKilled"}', 22, BAD)).arrange(DOWN, buff=0.12, aligned_edge=LEFT)
        last.next_to(logs, DOWN, buff=0.4).align_to(getp, LEFT)
        self.caption("Step 2: read lastState.terminated for the exit code and reason.", wait=0.2)
        self.play(FadeIn(last[0], shift=UP * 0.1), run_time=0.5)
        self.play(FadeIn(last[1], shift=UP * 0.1), run_time=0.5)
        expl = label("137 = 128 + 9 = SIGKILL, usually OOM  ·  memory usage went above limits.memory", 20, WARN).next_to(last, DOWN, buff=0.3).align_to(getp, LEFT)
        self.caption("Exit 137 = 128 + 9 = SIGKILL; reason OOMKilled confirms memory. Exit 1 = app error.", wait=0.2)
        self.play(FadeIn(expl), run_time=0.5)
        self.wait(1.4)
        self.caption("Measure real memory usage under load before raising the limit. A raised limit is a guess.", wait=1.6)
        self.play(FadeOut(VGroup(getp, hl, logs, last, expl)), run_time=0.6)

        # ---- back-off timeline ----
        delays = [10, 20, 40, 80, 160, 300, 300]
        scale = 3.6 / 300
        base_y = -2.35
        bars = VGroup()
        bl = VGroup()
        for i, d in enumerate(delays):
            b = Rectangle(width=0.8, height=max(d * scale, 0.04), stroke_color=WARN, stroke_width=2,
                          fill_color=WARN, fill_opacity=0.4)
            b.move_to([-5.2 + i * 1.25, base_y, 0], aligned_edge=DOWN)
            bars.add(b)
            bl.add(label(f"{d} s", 17, TEXT_C).next_to(b, UP, buff=0.08))
        base = Line([-6.0, base_y, 0], [6.2, base_y, 0], color=MUTED, stroke_width=2)
        xl = label("restart delay after each crash", 16, MUTED).next_to(base, DOWN, buff=0.12).align_to(base, LEFT)
        cap = DashedLine([-6.0, base_y + 300 * scale, 0], [3.2, base_y + 300 * scale, 0], color=BAD, stroke_width=2)
        cap_l = label("cap: 300 s (5 min)", 18, BAD).next_to(cap, LEFT, buff=0.1).shift(RIGHT * 2.2 + UP * 0.25)
        self.caption("CrashLoopBackOff means the kubelet is waiting out a restart back-off before trying again.", wait=0.2)
        self.play(Create(base), FadeIn(xl), run_time=0.5)
        self.caption("The delay starts at 10 s and doubles after each crash…", wait=0)
        for i in range(5):
            self.play(GrowFromEdge(bars[i], DOWN), FadeIn(bl[i]), run_time=0.45)
        self.caption("…and is capped at 5 minutes (300 s).", wait=0)
        self.play(Create(cap), FadeIn(cap_l), run_time=0.5)
        for i in range(5, 7):
            self.play(GrowFromEdge(bars[i], DOWN), FadeIn(bl[i]), run_time=0.45)
        self.wait(0.6)
        okrun = RoundedRectangle(corner_radius=0.08, width=1.5, height=0.8, stroke_color=OK, fill_color=OK, fill_opacity=0.3)
        okrun.move_to([-5.2 + 7 * 1.25 + 0.35, base_y + 0.5, 0])
        okl = label("runs OK\n10 min", 18, OK).move_to(okrun)
        rb = Rectangle(width=0.8, height=10 * scale, stroke_color=WARN, stroke_width=2, fill_color=WARN, fill_opacity=0.4)
        rb.move_to([-5.2 + 7 * 1.25 + 1.6, base_y, 0], aligned_edge=DOWN)
        rbl = label("10 s", 17, TEXT_C).next_to(rb, UP, buff=0.08)
        self.caption("After the container runs successfully for 10 minutes, the delay resets to 10 s.", wait=0.2)
        self.play(FadeIn(okrun), FadeIn(okl), run_time=0.6)
        self.play(GrowFromEdge(rb, DOWN), FadeIn(rbl), run_time=0.5)
        self.wait(1.4)
        self.play(FadeOut(VGroup(bars, bl, base, xl, cap, cap_l, okrun, okl, rb, rbl)), run_time=0.6)

        # ================= STATUS → layer =================
        for i, rr in enumerate(rows):
            rr[0].set_stroke(OK).set_fill(OK, opacity=0.12)
        rows.shift(RIGHT * 7.4)
        self.caption("The STATUS string tells you which layer to inspect first.", wait=0.2)
        self.play(FadeIn(rows), run_time=0.8)
        maps = [("Pending", 1, "FailedScheduling: requests, taints"),
                ("ErrImagePull / ImagePullBackOff", 2, "wrong name/tag, not loaded, auth"),
                ("CrashLoopBackOff", 3, "logs --previous, exit code"),
                ("Running, READY 0/1", 4, "readiness: /ready fails, port/path")]
        for st, li, why in maps:
            chip = VGroup(mono(st, 18, WARN), label(why, 16, MUTED)).arrange(DOWN, buff=0.06, aligned_edge=LEFT)
            chip.move_to([-3.8, layer_y(li), 0])
            chip.align_to(LEFT * 6.6, LEFT)
            a = Arrow(chip.get_right() + RIGHT * 0.1, rows[li].get_left(), buff=0.1, color=WARN, stroke_width=2.5,
                      max_tip_length_to_length_ratio=0.08)
            a.put_start_and_end_on([chip.get_right()[0] + 0.15, layer_y(li), 0], [rows[li].get_left()[0] - 0.1, layer_y(li), 0])
            self.play(FadeIn(chip, shift=RIGHT * 0.2), run_time=0.4)
            self.play(GrowArrow(a), rows[li][0].animate.set_stroke(WARN).set_fill(WARN, opacity=0.3), run_time=0.5)
            self.wait(0.6)
        self.caption("Running does not mean ready: check the READY column and the EndpointSlices.", wait=2.0)

        outro_lines(self, "Follow the loop and change one thing at a time.\nRead STATUS, find the lowest broken layer, then prove it with evidence.")
