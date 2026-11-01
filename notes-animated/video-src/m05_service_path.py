"""Module 05 — the request path through a Service: DNS → ClusterIP → selector → EndpointSlice → ready Pod.
Facts follow notes/05-kubernetes-networking-config.html (3. Services, 3.1 Selectors → EndpointSlices, 3.2 Readiness,
3.3 Ports, 3.7 Request path, 3.8 Failure cases, 4. Cluster DNS record forms)."""
from common import *


def pod_card(name, ip, state, color, lbl_ok=True, w=3.0):
    rect = RoundedRectangle(corner_radius=0.15, width=w, height=1.15, stroke_color=color, stroke_width=2.5,
                            fill_color=color, fill_opacity=0.12)
    t = label(name, 21, TEXT_C, weight=BOLD)
    s = mono(f"{ip} · {state}", 15, color)
    c = VGroup(t, s).arrange(DOWN, buff=0.1).move_to(rect)
    lt = mono("label ✓" if lbl_ok else "label ✗ (app: other)", 15, OK if lbl_ok else BAD).next_to(rect, DOWN, buff=0.12)
    return VGroup(rect, c, lt)


class M05ServicePath(Explainer):
    MODULE = "Module 05"
    TITLE = "One request through a Service"
    SUBTITLE = "DNS name → ClusterIP → EndpointSlice → a ready Pod"

    def construct(self):
        self.title_card()

        # ---------------- layout ----------------
        client = box("load-gen Pod", "the client", color=MUTED, w=2.5, h=1.0).move_to(LEFT * 5.6 + UP * 1.55)
        svc = box("Service reliability-api", "ClusterIP 10.96.143.20 (stable)", color=ACCENT, w=3.8, h=1.1,
                  title_size=21).move_to(LEFT * 1.4 + UP * 1.55)
        ports = mono("port 80 → targetPort 8000", 16, ACCENT).next_to(svc, DOWN, buff=0.15)
        sel = mono("selector: app.kubernetes.io/name=reliability-api", 15, WARN).next_to(ports, DOWN, buff=0.12)
        sel.set_x(-4.3, direction=LEFT)

        es_rect = RoundedRectangle(corner_radius=0.15, width=4.5, height=2.45, stroke_color=INFO, stroke_width=2.5,
                                   fill_color=INFO, fill_opacity=0.08).move_to(RIGHT * 4.55 + UP * 1.25)
        es_t = label("EndpointSlice", 20, INFO, weight=BOLD).next_to(es_rect.get_top(), DOWN, buff=0.15)
        es_s = mono("service-name=reliability-api", 14, MUTED).next_to(es_t, DOWN, buff=0.08)
        es = VGroup(es_rect, es_t, es_s)
        ep_a = mono("10.244.1.5:8000  ready", 17, OK).move_to(es_rect.get_center() + DOWN * 0.15)
        ep_a.align_to(es_rect, LEFT).shift(RIGHT * 0.3)
        ep_b = mono("10.244.2.7:8000  ready", 17, OK).next_to(ep_a, DOWN, buff=0.15, aligned_edge=LEFT)

        pa = pod_card("Pod a", "10.244.1.5", "Ready", OK).move_to(LEFT * 3.9 + DOWN * 1.55)
        pb = pod_card("Pod b", "10.244.2.7", "Ready", OK).move_to(LEFT * 0.4 + DOWN * 1.55)
        po = pod_card("Pod other-app", "10.244.1.6", "Ready", MUTED, lbl_ok=False).move_to(RIGHT * 3.4 + DOWN * 1.55)

        # ---------------- 1. DNS → ClusterIP ----------------
        self.caption("A client never talks to Pod IPs directly. It uses the Service's DNS name.", wait=0.3)
        self.play(FadeIn(client, shift=RIGHT * 0.2))
        dns = mono("reliability-api.reliability-lab.svc.cluster.local", 18, TEXT_C).move_to(UP * 3.0 + RIGHT * 0.6)
        self.play(Write(dns), run_time=1.2)
        self.caption("Cluster DNS resolves that name to the Service's stable ClusterIP.", wait=0.2)
        self.play(FadeIn(svc, shift=DOWN * 0.2))
        self.packet([client.get_top() + UP * 0.05, [client.get_x(), 3.0, 0], dns.get_left()], color=INFO, run_time=0.8)
        res = mono("→ 10.96.143.20", 18, ACCENT).next_to(dns, DOWN, buff=0.1).align_to(dns, RIGHT)
        self.play(FadeIn(res, shift=LEFT * 0.2))
        self.play(FadeIn(ports))
        self.caption("Clients connect to port 80 on the Service; the container listens on targetPort 8000.", wait=1.4)

        # ---------------- 2. selector → EndpointSlice ----------------
        self.caption("Which Pods? The Service picks them with a label selector.", wait=0.2)
        self.play(FadeIn(sel), FadeIn(pa), FadeIn(pb), FadeIn(po), run_time=1.0)
        self.play(Indicate(pa[2], color=OK), Indicate(pb[2], color=OK), Indicate(po[2], color=BAD), run_time=1.0)
        self.caption("A controller keeps an EndpointSlice: the IPs of matching Pods, each with a ready flag.", wait=0.2)
        self.play(FadeIn(es), run_time=0.7)
        self.packet([pa[0].get_top(), pa[0].get_top() + UP * 0.35, [es_rect.get_left()[0] - 0.3, pa[0].get_top()[1] + 0.35, 0],
                     es_rect.get_left() + DOWN * 0.3], color=INFO, run_time=0.9)
        self.play(FadeIn(ep_a, shift=RIGHT * 0.2), run_time=0.4)
        self.play(FadeIn(ep_b, shift=RIGHT * 0.2), run_time=0.4)
        no_o = mono("other-app: not listed", 15, MUTED).next_to(ep_b, DOWN, buff=0.14, aligned_edge=LEFT)
        self.play(FadeIn(no_o))
        self.caption("The Service object holds no Pod IPs itself. Label match decides membership.", wait=1.4)

        # ---------------- 3. the request path ----------------
        self.caption("A request to 10.96.143.20:80 is forwarded by node rules to a ready Pod IP on 8000.", wait=0.2)
        p1 = [client.get_right(), svc.get_left()]
        self.packet(p1, color=WARN, run_time=0.7)
        self.play(Indicate(ep_b, color=OK), run_time=0.5)
        self.packet([svc.get_bottom() + RIGHT * 1.2 + DOWN * 1.05, pb[0].get_top()], color=WARN, run_time=0.7)
        ok = mono("GET /work → 200", 16, OK).next_to(pb[0], UP, buff=0.12).shift(RIGHT * 0.2)
        self.play(FadeIn(ok, scale=0.8))
        self.play(FadeOut(ok), run_time=0.3)
        self.packet(p1, color=WARN, run_time=0.6)
        self.play(Indicate(ep_a, color=OK), run_time=0.5)
        self.packet([pa[0].get_top() + UP * 0.9 + RIGHT * 1.5, pa[0].get_top()], color=WARN, run_time=0.7)
        ok2 = mono("200", 16, OK).next_to(pa[0], UP, buff=0.12)
        self.play(FadeIn(ok2, scale=0.8))
        self.play(FadeOut(ok2), run_time=0.3)
        self.caption("Each new connection can land on a different ready Pod. That is the load balancing.", wait=1.0)

        # ---------------- 4. Pod a becomes unready ----------------
        self.caption("Now Pod a's readiness probe fails (/ready returns 503). Its Ready condition goes False.",
                     wait=0.2)
        pa_bad = pod_card("Pod a", "10.244.1.5", "NOT ready", WARN).move_to(pa)
        self.play(FadeTransform(pa, pa_bad), run_time=0.8)
        pa = pa_bad
        ep_a_bad = mono("10.244.1.5:8000  ready=false", 17, WARN).move_to(ep_a, aligned_edge=LEFT)
        self.play(FadeTransform(ep_a, ep_a_bad), run_time=0.7)
        ep_a = ep_a_bad
        self.caption("Its endpoint is marked ready=false, so the Pod gets no new Service traffic. No restart.",
                     wait=0.2)
        for _ in range(2):
            self.packet(p1, color=WARN, run_time=0.5)
            self.packet([svc.get_bottom() + RIGHT * 1.2 + DOWN * 1.05, pb[0].get_top()], color=WARN, run_time=0.5)
        self.caption("When /ready returns 200 again, the chain runs in reverse and traffic returns.", wait=0.2)
        pa_ok = pod_card("Pod a", "10.244.1.5", "Ready", OK).move_to(pa)
        ep_a_ok = mono("10.244.1.5:8000  ready", 17, OK).move_to(ep_a, aligned_edge=LEFT)
        self.play(FadeTransform(pa, pa_ok), FadeTransform(ep_a, ep_a_ok), run_time=0.8)
        pa, ep_a = pa_ok, ep_a_ok
        self.wait(0.8)

        # ---------------- 5. selector mismatch ----------------
        self.caption("Failure case: the selector uses a different key than the Pod labels.", wait=0.2)
        sel_bad = mono("selector: app=reliability-api", 15, BAD).move_to(sel, aligned_edge=LEFT)
        self.play(FadeTransform(sel, sel_bad), run_time=0.8)
        sel = sel_bad
        pa2 = pod_card("Pod a", "10.244.1.5", "Ready", OK, lbl_ok=False).move_to(pa)
        pb2 = pod_card("Pod b", "10.244.2.7", "Ready", OK, lbl_ok=False).move_to(pb)
        for p, q in ((pa, pa2), (pb, pb2)):
            q[2].become(mono("no match ✗", 15, BAD).move_to(p[2]))
        self.play(FadeTransform(pa, pa2), FadeTransform(pb, pb2), run_time=0.8)
        pa, pb = pa2, pb2
        self.caption("No Pod matches, so the EndpointSlice is empty, even though both Pods are Ready.", wait=0.2)
        empty = mono("(no endpoints)", 18, BAD).move_to(ep_a, aligned_edge=LEFT).shift(DOWN * 0.2)
        self.play(FadeOut(ep_a), FadeOut(ep_b), FadeOut(no_o), FadeIn(empty), run_time=0.8)
        self.packet(p1, color=WARN, run_time=0.7)
        fail = VGroup(mono("hangs, or", 17, BAD), mono("connection refused", 17, BAD)).arrange(DOWN, buff=0.08)
        fail.next_to(client, UP, buff=0.2)
        x = Cross(scale_factor=0.2, stroke_color=BAD, stroke_width=5).move_to(svc.get_left() + LEFT * 0.3)
        self.play(FadeIn(x), FadeIn(fail))
        self.caption("Check with: kubectl get endpointslices -l kubernetes.io/service-name=reliability-api",
                     wait=2.2)

        self.outro("Service = stable name and IP. EndpointSlice = the Pods actually used.\n"
                   "Labels decide membership; readiness decides traffic.")
