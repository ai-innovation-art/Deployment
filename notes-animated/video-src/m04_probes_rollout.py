"""Module 04 — startup / liveness / readiness probes, then a rolling update (2 replicas, maxSurge 1, maxUnavailable 0).
Facts follow notes/04-kubernetes-workloads.html (1. Health probes; 5. Rolling updates, rollout and rollback)."""
from common import *


def pod_mob(name, sub, color, dashed=False, w=2.8, h=1.2):
    rect = RoundedRectangle(corner_radius=0.14, width=w, height=h, stroke_color=color, stroke_width=2.5,
                            fill_color=color, fill_opacity=0.14)
    if dashed:
        rect = VGroup(DashedVMobject(rect.copy().set_fill(opacity=0), num_dashes=28),
                      rect.copy().set_stroke(width=0))
    t = label(name, 23, TEXT_C, weight=BOLD)
    s = label(sub, 18, color)
    c = VGroup(t, s).arrange(DOWN, buff=0.08)
    if c.width > w - 0.2:
        c.scale_to_fit_width(w - 0.25)
    c.move_to(rect)
    return VGroup(rect, c)


def pill(text, color, size=17, w=None):
    t = mono(text, size, color)
    r = RoundedRectangle(corner_radius=0.12, width=w or t.width + 0.4, height=t.height + 0.26,
                         stroke_color=color, stroke_width=1.8, fill_color=color, fill_opacity=0.1)
    t.move_to(r)
    return VGroup(r, t)


class M04ProbesRollout(Explainer):
    MODULE = "Module 04"
    TITLE = "Probes and rolling updates"
    SUBTITLE = "Readiness gates traffic, liveness restarts, rollouts wait for Ready"

    def swap(self, old, new, *extra):
        self.play(FadeTransform(old, new), *extra, run_time=0.8)
        return new

    def construct(self):
        self.title_card()

        # ---------------- Part 1: three probes ----------------
        kubelet = box("kubelet", "runs the probes", color=ACCENT, w=2.6, h=1.0).move_to(LEFT * 5.2 + UP * 1.7)
        p_start = pill("startupProbe   GET /health", WARN, 16, w=3.6).move_to(LEFT * 5.0 + UP * 0.3)
        p_live = pill("livenessProbe  GET /health", BAD, 16, w=3.6).move_to(LEFT * 5.0 + DOWN * 0.45)
        p_ready = pill("readinessProbe GET /ready", OK, 16, w=3.6).move_to(LEFT * 5.0 + DOWN * 1.2)
        probes = VGroup(p_start, p_live, p_ready)

        podz = zone(4.4, 4.4, "Pod · 10.244.1.5", color=OK).move_to(RIGHT * 0.3 + UP * 0.45)
        ctr = box("reliability-api", "container · :8000", color=OK, w=3.4, h=1.0).move_to(RIGHT * 0.3 + UP * 1.3)
        st_ready = mono("Ready: False", 20, WARN).move_to(RIGHT * 0.3 + DOWN * 0.15)
        st_rest = mono("RESTARTS: 0", 20, MUTED).move_to(RIGHT * 0.3 + DOWN * 0.75)

        svc_t = label("Service endpoints", 18, ACCENT, weight=BOLD).move_to(RIGHT * 5.2 + UP * 2.2)
        svc_box = RoundedRectangle(corner_radius=0.12, width=3.4, height=2.6, stroke_color=ACCENT, stroke_width=1.8,
                                   fill_color=ACCENT, fill_opacity=0.06).move_to(RIGHT * 5.2 + UP * 0.6)
        ep_other = mono("10.244.2.7:8000", 18, OK).move_to(svc_box.get_center() + UP * 0.6)
        ep_this = mono("10.244.1.5:8000", 18, OK).move_to(svc_box.get_center() + DOWN * 0.1)

        self.caption("The kubelet runs probes on every container. Same check, three different consequences.", wait=0.3)
        self.play(FadeIn(kubelet), Create(podz[0]), FadeIn(podz[1]), FadeIn(ctr), run_time=1.0)
        self.play(LaggedStart(*[FadeIn(p, shift=RIGHT * 0.2) for p in probes], lag_ratio=0.25), run_time=1.0)
        self.play(FadeIn(st_ready), FadeIn(st_rest), FadeIn(svc_t), FadeIn(svc_box), FadeIn(ep_other))
        self.wait(0.5)

        def probe_hit(p, color, ok_txt, ok_color):
            self.play(Indicate(p, color=color, scale_factor=1.05), run_time=0.4)
            self.packet([p.get_right(), ctr.get_left()], color=color, run_time=0.7)
            r = label(ok_txt, 18, ok_color, weight=BOLD).next_to(ctr, UP, buff=0.12)
            self.play(FadeIn(r, scale=0.8), run_time=0.3)
            self.play(FadeOut(r), run_time=0.3)

        self.caption("Startup probe first: until it succeeds, liveness and readiness are not run.", wait=0.2)
        for p in probes:
            p.save_state()
        self.play(VGroup(p_live, p_ready).animate.fade(0.7), run_time=0.4)
        probe_hit(p_start, WARN, "200 ✓ started", OK)
        self.play(Restore(p_live), Restore(p_ready), p_start.animate.fade(0.7), run_time=0.4)

        self.caption("Readiness asks: should this Pod get traffic now? During warm-up /ready returns 503.", wait=0.2)
        probe_hit(p_ready, OK, "503 ✗", BAD)
        self.caption("Once /ready returns 200, the Pod is Ready and its IP joins the Service endpoints.", wait=0.2)
        probe_hit(p_ready, OK, "200 ✓", OK)
        self.play(st_ready.animate.become(mono("Ready: True", 20, OK).move_to(st_ready)),
                  FadeIn(ep_this, shift=RIGHT * 0.3))
        self.wait(0.8)

        self.caption("Readiness fails 3 times in a row: Ready=False, and the IP is taken out of Service traffic.",
                     wait=0.2)
        for _ in range(3):
            probe_hit(p_ready, OK, "503 ✗", BAD)
        self.play(st_ready.animate.become(mono("Ready: False", 20, WARN).move_to(st_ready)),
                  ep_this.animate.set_opacity(0.0).shift(RIGHT * 0.4), run_time=0.7)
        note = label("RESTARTS stays 0 · traffic only", 16, MUTED).next_to(st_rest, DOWN, buff=0.2)
        self.play(Indicate(st_rest, color=OK), FadeIn(note))
        self.caption("It keeps probing; when /ready passes again, the Pod goes straight back in.", wait=0.2)
        probe_hit(p_ready, OK, "200 ✓", OK)
        ep_this.shift(LEFT * 0.4)
        self.play(st_ready.animate.become(mono("Ready: True", 20, OK).move_to(st_ready)),
                  ep_this.animate.set_opacity(1), FadeOut(note))
        self.wait(0.6)

        self.caption("Liveness asks: is the process stuck so only a restart helps? Say /health times out.", wait=0.2)
        for _ in range(2):
            probe_hit(p_live, BAD, "timeout ✗", BAD)
        self.caption("After failureThreshold (3 × 10 s ≈ 30 s) the kubelet kills and restarts the container.", wait=0.2)
        x = Cross(ctr, stroke_color=BAD, stroke_width=6)
        self.play(Create(x), run_time=0.4)
        ctr2 = box("reliability-api", "restarted · same Pod, same IP", color=OK, w=3.4, h=1.0).move_to(ctr)
        self.play(FadeOut(x), ReplacementTransform(ctr, ctr2),
                  st_rest.animate.become(mono("RESTARTS: 1", 20, BAD).move_to(st_rest)), run_time=0.8)
        ctr = ctr2
        self.caption("Rule: readiness failures are reversible (traffic only); liveness failures restart.", wait=1.8,
                     color=WARN)
        self.play(FadeOut(VGroup(kubelet, probes, podz, ctr, st_ready, st_rest, svc_t, svc_box, ep_other, ep_this)),
                  run_time=0.6)

        # ---------------- Part 2: rolling update ----------------
        head = mono("replicas: 2 · maxSurge: 1 · maxUnavailable: 0", 20, TEXT_C).move_to(UP * 2.95)
        bounds = label("at most 3 Pods in total · at least 2 available", 18, MUTED).next_to(head, DOWN, buff=0.15)
        rs_old = label("ReplicaSet old · reliability-api:0.1.0", 19, ACCENT).move_to(LEFT * 5.7 + UP * 1.75, aligned_edge=LEFT)
        rs_new = label("ReplicaSet new · reliability-api:0.2.0", 19, INFO).move_to(LEFT * 5.7 + DOWN * 0.22, aligned_edge=LEFT)
        slots_old = [LEFT * 4.25 + UP * 0.9, LEFT * 1.15 + UP * 0.9]
        slots_new = [LEFT * 4.25 + DOWN * 1.15, LEFT * 1.15 + DOWN * 1.15]

        cnt_box = RoundedRectangle(corner_radius=0.15, width=4.6, height=2.0, stroke_color=MUTED, stroke_width=1.5,
                                   fill_color=SURFACE, fill_opacity=1).move_to(RIGHT * 4.5 + UP * 0.3)

        def counts(total, avail, color=OK):
            g = VGroup(mono(f"total Pods: {total}  (≤ 3)", 20, TEXT_C if total <= 3 else BAD),
                       mono(f"available:  {avail}  (≥ 2)", 20, color)).arrange(DOWN, aligned_edge=LEFT, buff=0.3)
            return g.move_to(cnt_box)

        cnt = counts(2, 2)

        def old_pod(i, state="ready"):
            if state == "ready":
                return pod_mob(f"old-{i}", "0.1.0 · Ready ✓", ACCENT).move_to(slots_old[i - 1])
            return pod_mob(f"old-{i}", "Terminating", BAD, dashed=True).move_to(slots_old[i - 1])

        def new_pod(i, state):
            if state == "pending":
                return pod_mob(f"new-{i}", "0.2.0 · not Ready", WARN, dashed=True).move_to(slots_new[i - 1])
            if state == "ready":
                return pod_mob(f"new-{i}", "0.2.0 · Ready ✓", OK).move_to(slots_new[i - 1])
            return pod_mob(f"new-{i}", "ImagePullBackOff", BAD, dashed=True).move_to(slots_new[i - 1])

        o1, o2 = old_pod(1), old_pod(2)
        self.caption("Now a rolling update of reliability-api: 2 replicas, maxSurge 1, maxUnavailable 0.", wait=0.3)
        self.play(FadeIn(head), FadeIn(bounds))
        self.play(FadeIn(rs_old), FadeIn(o1), FadeIn(o2), FadeIn(cnt_box), FadeIn(cnt), run_time=0.9)
        self.wait(0.6)

        def upd(new_cnt):
            return cnt.animate.become(new_cnt)

        self.caption("You apply image 0.2.0. A new ReplicaSet is created and scaled to 1 (2 + surge 1 = 3).", wait=0.2)
        n1 = new_pod(1, "pending")
        self.play(FadeIn(rs_new), FadeIn(n1, scale=0.85), upd(counts(3, 2)), run_time=0.9)
        self.caption("new-1 is still warming up (/ready → 503), so it is not available. Old Pods serve traffic.",
                     wait=1.0)
        self.caption("new-1 passes readiness. Available would be 3, so one old Pod may now go.", wait=0.2)
        n1 = self.swap(n1, new_pod(1, "ready"), upd(counts(3, 3)))
        o2 = self.swap(o2, old_pod(2, "term"), upd(counts(3, 2)))
        self.play(FadeOut(o2), run_time=0.5)
        self.caption("Repeat: create new-2, wait until it is Ready, then terminate the last old Pod.", wait=0.2)
        n2 = new_pod(2, "pending")
        self.play(FadeIn(n2, scale=0.85), upd(counts(3, 2)), run_time=0.8)
        self.wait(0.6)
        n2 = self.swap(n2, new_pod(2, "ready"), upd(counts(3, 3)))
        o1 = self.swap(o1, old_pod(1, "term"), upd(counts(3, 2)))
        self.play(FadeOut(o1), upd(counts(2, 2)), run_time=0.5)
        kept = label("old ReplicaSet kept at 0 replicas for rollout undo", 18, MUTED).move_to(LEFT * 2.7 + UP * 0.9)
        self.play(FadeIn(kept))
        self.caption("Done. At no point were fewer than 2 Ready Pods behind the Service.", wait=1.6, color=OK)

        # ---------------- Part 3: bad image stalls the rollout ----------------
        self.play(FadeOut(VGroup(n1, n2, kept)), run_time=0.5)
        o1, o2 = old_pod(1), old_pod(2)
        rs_bad = label("ReplicaSet new · image tag that doesn't exist", 19, BAD).move_to(rs_new, aligned_edge=LEFT)
        self.caption("Failure case: same rollout, but the new image tag can't be pulled.", wait=0.2)
        self.play(FadeIn(o1), FadeIn(o2), Transform(rs_new, rs_bad), upd(counts(2, 2)), run_time=0.8)
        nb = new_pod(1, "pending")
        self.play(FadeIn(nb, scale=0.85), upd(counts(3, 2)), run_time=0.7)
        nb = self.swap(nb, new_pod(1, "bad"))
        self.caption("The new Pod never becomes Ready. With maxUnavailable 0, no old Pod may be removed.", wait=0.3)
        for _ in range(2):
            self.play(Indicate(o1, color=ACCENT, scale_factor=1.05), Indicate(o2, color=ACCENT, scale_factor=1.05),
                      run_time=0.7)
        stuck = VGroup(mono("kubectl rollout status … (waiting)", 17, WARN),
                       mono("Progressing=False · ProgressDeadlineExceeded (600 s)", 17, BAD)
                       ).arrange(DOWN, aligned_edge=LEFT, buff=0.14)
        stuck.move_to(LEFT * 5.7 + DOWN * 2.35, aligned_edge=LEFT)
        self.play(FadeIn(stuck[0]))
        self.caption("Users see no impact: old Pods keep serving. The rollout is stuck, not broken.", wait=0.6)
        self.play(FadeIn(stuck[1]))
        self.caption("It doesn't roll back by itself: rollout status fails, and you fix the tag or run undo.",
                     wait=1.8)

        self.outro("Readiness decides traffic, liveness decides restarts.\n"
                   "An honest readiness probe makes rollouts wait, and stall safely.")
