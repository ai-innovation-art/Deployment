"""Module 01 — a process listening on a port, 127.0.0.1 vs 0.0.0.0, and refused vs timeout.
Facts follow notes/01-linux-networking.html (Ports and sockets, TCP handshake, Binding, Signals, Exit codes)."""
from common import *


def tag_text(text, color, size=20):
    """Small coloured result tag (e.g. '200 OK', 'refused')."""
    t = label(text, size=size, color=color, weight=BOLD)
    bg = RoundedRectangle(corner_radius=0.1, width=t.width + 0.3, height=t.height + 0.2,
                          stroke_color=color, stroke_width=1.5, fill_color=color, fill_opacity=0.12)
    t.move_to(bg)
    return VGroup(bg, t)


class M01Binding(Explainer):
    MODULE = "Module 01"
    TITLE = "Who is listening, and where?"
    SUBTITLE = "Ports, 127.0.0.1 vs 0.0.0.0, refused vs timeout"

    def construct(self):
        self.title_card()

        # ---------------- Part 1: a listening socket ----------------
        stack = zone(8.6, 5.3, "container network stack", color=OK).move_to(RIGHT * 1.6 + UP * 0.35)
        lo = box("lo", "127.0.0.1", color=INFO, w=2.3, h=0.95).move_to(LEFT * 0.9 + UP * 1.2)
        eth0 = box("eth0", "10.0.0.9", color=INFO, w=2.3, h=0.95).move_to(LEFT * 0.9 + DOWN * 1.2)
        uvi = box("uvicorn", "PID 4321 · TCP :8000", color=OK, w=2.9, h=1.1).move_to(RIGHT * 3.9 + DOWN * 0.0)
        inside = box("curl localhost:8000", "from inside the container", color=MUTED, w=3.2, h=0.85,
                     title_size=20, sub_size=14).move_to(RIGHT * 3.9 + UP * 2.0)
        outside = box("outside client", "docker -p / Service", color=MUTED, w=2.7, h=0.95).move_to(LEFT * 5.4 + DOWN * 1.2)

        self.caption("A server is a process that owns a listening socket: bind(address, port), then listen().", wait=0.5)
        self.play(FadeIn(uvi, shift=UP * 0.2))
        sock = mono("listen(?, 8000)", 18, OK).next_to(uvi, DOWN, buff=0.2)
        self.play(FadeIn(sock))
        self.wait(1.0)
        self.caption("The port picks the program. The bind address picks which interfaces it accepts on.", wait=0.3)
        self.play(Create(stack[0]), FadeIn(stack[1]), FadeIn(lo), FadeIn(eth0), run_time=1.0)
        self.wait(1.0)

        # ---- bind 127.0.0.1 ----
        self.caption("Uvicorn's default --host is 127.0.0.1: the socket sits on loopback only.", wait=0.3)
        bind_txt = mono("bind 127.0.0.1:8000", 18, WARN).move_to(sock)
        self.play(ReplacementTransform(sock, bind_txt))
        l_lo = Line(lo.get_right(), uvi.get_left() + UP * 0.25, color=OK, stroke_width=4)
        l_eth = DashedLine(eth0.get_right(), uvi.get_left() + DOWN * 0.25, color=BAD, stroke_width=3)
        x_eth = Cross(scale_factor=0.18, stroke_color=BAD, stroke_width=5).move_to(l_eth.get_center())
        self.play(Create(l_lo), Create(l_eth), FadeIn(x_eth), run_time=0.8)
        self.wait(0.8)

        self.play(FadeIn(inside))
        self.caption("Inside the container, curl localhost:8000 arrives on lo, so it works.", wait=0.2)
        self.packet([inside.get_left(), lo.get_top() + RIGHT * 0.3, lo.get_right(), uvi.get_left() + UP * 0.25], color=OK)
        ok1 = tag_text("200 OK", OK).next_to(inside, LEFT, buff=0.2)
        self.play(FadeIn(ok1, scale=0.8))
        self.wait(0.8)

        self.play(FadeIn(outside, shift=RIGHT * 0.3))
        self.caption("Docker -p and Kubernetes Services deliver to eth0, where nothing listens.", wait=0.2)
        self.packet([outside.get_right(), eth0.get_left()], color=WARN)
        rst = tag_text("RST: refused", BAD).next_to(outside, UP, buff=0.25)
        self.play(Indicate(eth0[0], color=BAD), FadeIn(rst, scale=0.8))
        self.caption("The classic \"works inside, fails outside\": refused, reset or empty reply.", wait=1.5, color=WARN)

        # ---- bind 0.0.0.0 ----
        self.caption("Fix: --host 0.0.0.0 binds all local interfaces, loopback and eth0 alike.", wait=0.3)
        bind2 = mono("bind 0.0.0.0:8000", 18, OK).move_to(bind_txt)
        l_eth2 = Line(eth0.get_right(), uvi.get_left() + DOWN * 0.25, color=OK, stroke_width=4)
        self.play(ReplacementTransform(bind_txt, bind2), FadeOut(x_eth), ReplacementTransform(l_eth, l_eth2),
                  FadeOut(rst), run_time=0.8)
        self.packet([outside.get_right(), eth0.get_left(), eth0.get_right(), uvi.get_left() + DOWN * 0.25], color=OK)
        ok2 = tag_text("200 OK", OK).next_to(outside, UP, buff=0.25)
        self.play(FadeIn(ok2, scale=0.8))
        self.caption("That is why reliability-api always runs with --host 0.0.0.0 --port 8000.", wait=1.8)

        part1 = VGroup(stack, lo, eth0, uvi, inside, outside, bind2, l_lo, l_eth2, ok1, ok2)
        self.play(FadeOut(part1), run_time=0.6)

        # ---------------- Part 2: handshake vs refused vs timeout ----------------
        cols = []
        titles = [("Listener present", OK), ("Nothing listening", BAD), ("Packets dropped", WARN)]
        xs = [-4.7, 0.0, 4.7]
        for (t, c), x in zip(titles, xs):
            head = label(t, 22, c, weight=BOLD).move_to([x, 2.8, 0])
            cl = label("client", 16, MUTED).move_to([x - 1.5, 2.25, 0])
            sv = label(":8000", 16, MUTED, font=MONO).move_to([x + 1.5, 2.25, 0])
            lc = Line([x - 1.5, 2.0, 0], [x - 1.5, -1.5, 0], color=MUTED, stroke_width=2)
            ls = Line([x + 1.5, 2.0, 0], [x + 1.5, -1.5, 0], color=MUTED, stroke_width=2)
            cols.append(VGroup(head, cl, sv, lc, ls))

        def msg(x, y0, y1, text, color, to_right=True):
            a, b = ([x - 1.5, y0, 0], [x + 1.5, y1, 0]) if to_right else ([x + 1.5, y0, 0], [x - 1.5, y1, 0])
            ar = Arrow(a, b, buff=0.02, color=color, stroke_width=3, max_tip_length_to_length_ratio=0.1)
            tx = label(text, 17, color, font=MONO).next_to(ar.get_center(), UP, buff=0.22)
            return VGroup(ar, tx)

        self.caption("Now the network view. A TCP connection starts with a three-way handshake.", wait=0.3)
        self.play(FadeIn(cols[0]))
        x = xs[0]
        for m in [msg(x, 1.7, 1.3, "SYN", OK), msg(x, 1.0, 0.6, "SYN-ACK", OK, False), msg(x, 0.3, -0.1, "ACK", OK),
                  msg(x, -0.5, -0.9, "GET /health", ACCENT)]:
            self.play(GrowArrow(m[0]), FadeIn(m[1]), run_time=0.45)
            cols[0].add(m)
        r0 = tag_text("200 OK", OK, 18).move_to([x, -2.1, 0])
        self.play(FadeIn(r0, scale=0.8))
        cols[0].add(r0)

        self.caption("Nobody on that port? The host answers SYN with RST: 'connection refused', instantly.", wait=0.3)
        self.play(FadeIn(cols[1]))
        x = xs[1]
        for m in [msg(x, 1.7, 1.3, "SYN", WARN), msg(x, 1.0, 0.6, "RST", BAD, False)]:
            self.play(GrowArrow(m[0]), FadeIn(m[1]), run_time=0.45)
            cols[1].add(m)
        r1 = VGroup(tag_text("Connection refused", BAD, 18),
                    label("fast: wrong port, app down, wrong bind", 15, MUTED)).arrange(DOWN, buff=0.12).move_to([x, -2.25, 0])
        self.play(FadeIn(r1, scale=0.9))
        self.wait(1.2)

        self.caption("Firewall or no route? Nothing answers at all, so the client hangs, then times out.", wait=0.3)
        self.play(FadeIn(cols[2]))
        x = xs[2]
        for y in [1.7, 0.6]:
            ar = DashedLine([x - 1.5, y, 0], [x + 0.2, y - 0.25, 0], color=WARN, stroke_width=3)
            xx = Cross(scale_factor=0.12, stroke_color=BAD, stroke_width=4).move_to(ar.get_end())
            s = label("SYN", 17, WARN, font=MONO).next_to(ar.get_center(), UP, buff=0.18)
            self.play(Create(ar), FadeIn(s), run_time=0.5)
            self.play(FadeIn(xx), run_time=0.3)
            cols[2].add(ar, xx, s)
        dots = label("…", 30, MUTED).move_to([x, -0.5, 0])
        self.play(FadeIn(dots))
        r2 = VGroup(tag_text("Connection timed out", WARN, 18),
                    label("slow: firewall, no route, wrong IP", 15, MUTED)).arrange(DOWN, buff=0.12).move_to([x, -2.25, 0])
        self.play(FadeIn(r2, scale=0.9))
        self.caption("Refused = 'the host answered: nobody is here'. Timeout = 'nobody answered at all'.", wait=2.2,
                     color=WARN)
        self.play(FadeOut(VGroup(*cols, r1, r2, dots)), run_time=0.6)

        # ---------------- Part 3: SIGTERM → grace → SIGKILL ----------------
        self.caption("Stopping a process follows one pattern: polite signal, wait, then force.", wait=0.3)
        t0, t1 = -3.2, 3.6

        def lane(y, name, color):
            n = label(name, 20, color, weight=BOLD).move_to([-5.4, y, 0])
            ax = Line([t0, y, 0], [t1 + 1.6, y, 0], color=MUTED, stroke_width=2)
            tick = Line([t0, y - 0.25, 0], [t0, y + 0.25, 0], color=WARN, stroke_width=4)
            st = label("SIGTERM", 18, WARN, weight=BOLD).move_to([t0, y + 0.55, 0])
            return VGroup(n, ax, tick, st)

        la = lane(1.5, "handles it", OK)
        lb = lane(-1.0, "ignores it", BAD)
        self.play(FadeIn(la), FadeIn(lb), run_time=0.8)

        self.caption("Uvicorn handles SIGTERM: it stops accepting, finishes in-flight requests, and exits.", wait=0.2)
        drain = Rectangle(width=2.2, height=0.32, stroke_width=0, fill_color=OK, fill_opacity=0.3).move_to(
            [t0 + 1.1, 1.5, 0])
        dtx = label("drain, then exit", 17, OK).next_to(drain, DOWN, buff=0.15)
        stop = Dot([t0 + 2.2, 1.5, 0], radius=0.09, color=OK)
        ex0 = label("exits before the deadline: no dropped requests", 18, OK).next_to(stop, RIGHT, buff=0.25).shift(UP * 0.4)
        self.play(GrowFromEdge(drain, LEFT), FadeIn(dtx), run_time=0.9)
        self.play(FadeIn(stop), FadeIn(ex0, shift=RIGHT * 0.2))
        self.wait(1.0)

        self.caption("Ignored? Nothing happens until the grace period ends; then SIGKILL, which can't be caught.",
                     wait=0.2)
        grace = Rectangle(width=t1 - t0, height=0.32, stroke_width=0, fill_color=WARN, fill_opacity=0.22).move_to(
            [(t0 + t1) / 2, -1.0, 0])
        gtx = label("grace period: Kubernetes default 30 s · docker stop 10 s", 17, MUTED).next_to(grace, DOWN, buff=0.15)
        self.play(GrowFromEdge(grace, LEFT), FadeIn(gtx), run_time=1.4)
        kill = VGroup(Line([t1, -1.25, 0], [t1, -0.75, 0], color=BAD, stroke_width=4),
                      label("SIGKILL", 18, BAD, weight=BOLD).move_to([t1, -0.45, 0]))
        self.play(FadeIn(kill), Flash([t1, -1.0, 0], color=BAD), run_time=0.6)
        code = VGroup(mono("exit code 137", 26, BAD), label("= 128 + 9 (SIGKILL)", 22, MUTED)).arrange(RIGHT, buff=0.25)
        code.move_to([0.2, -2.45, 0])
        self.play(Write(code[0]), FadeIn(code[1]), run_time=0.9)
        self.caption("137 only says 'SIGKILL'. Check for OOMKilled before blaming memory.", wait=2.0)

        self.outro("Bind 0.0.0.0 inside containers.\nRefused = nobody listening; timeout = nobody answering.")
