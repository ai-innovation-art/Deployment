"""Module 06 — kind (nodes are Docker containers, kind load docker-image) and Helm
(values precedence → rendered manifests → release revisions → rollback).
Facts follow notes/06-kind-helm.html (A1, A5, A6, B1, B2, B5, B7)."""
from common import *


def chip(text, color=WARN, size=14):
    """Small rounded tag, e.g. an image name inside a node."""
    t = mono(text, size, color)
    r = RoundedRectangle(corner_radius=0.08, width=t.width + 0.25, height=t.height + 0.18,
                         stroke_color=color, stroke_width=1.5, fill_color=color, fill_opacity=0.12)
    t.move_to(r)
    return VGroup(r, t)


def layer(src, keys, color, w=5.4, h=0.82):
    """One values layer: source on top (coloured), keys below."""
    r = RoundedRectangle(corner_radius=0.1, width=w, height=h, stroke_color=color, stroke_width=2,
                         fill_color=color, fill_opacity=0.12)
    a = mono(src, 17, color)
    b = mono(keys, 16, TEXT_C)
    t = VGroup(a, b).arrange(DOWN, aligned_edge=LEFT, buff=0.07)
    if t.width > w - 0.3:
        t.scale_to_fit_width(w - 0.3)
    t.move_to(r).align_to(r, LEFT).shift(RIGHT * 0.18)
    return VGroup(r, t)


class M06Helm(Explainer):
    MODULE = "Module 06"
    TITLE = "kind & Helm"
    SUBTITLE = "Nodes as containers · values → manifests → release revisions"

    def construct(self):
        self.title_card()
        self.part_kind()
        self.part_helm_render()
        self.part_revisions()
        self.outro("kind gives you a real, disposable cluster in Docker.\n"
                   "Helm renders values into manifests and keeps every revision.")

    # ------------------------------------------------------------------ kind
    def part_kind(self):
        laptop = zone(13.6, 5.9, "your laptop · Docker engine", color=MUTED).move_to(UP * 0.2)
        build = box("docker build", "-t reliability-api:0.1.0", color=MUTED, w=2.9, h=1.0,
                    sub_size=16).move_to(LEFT * 5.1 + UP * 1.6)
        store = box("host image store", "Docker on your laptop", color=MUTED, w=2.9, h=1.0,
                    sub_size=16).move_to(LEFT * 5.1 + DOWN * 0.5)

        names = ["control-plane", "worker", "worker2"]
        xs = [-1.55, 1.55, 4.65]
        nodes, imgs, slots = [], [], []
        for n, x in zip(names, xs):
            z = zone(2.9, 4.9, "container: " + n, color=ACCENT).move_to(RIGHT * x + DOWN * 0.15)
            inner = box("kindest/node", "containerd + kubelet", color=ACCENT, w=2.5, h=1.0,
                        title_size=21, sub_size=17).move_to(RIGHT * x + UP * 1.3)
            slot_lbl = label("node image store", 16, MUTED).move_to(RIGHT * x + UP * 0.25)
            slot = RoundedRectangle(corner_radius=0.08, width=2.5, height=0.5, stroke_color=MUTED,
                                    stroke_width=1).set_stroke(opacity=0.6).move_to(RIGHT * x + DOWN * 0.25)
            nodes.append(VGroup(z, inner, slot_lbl, slot))
            slots.append(slot)

        self.caption("kind runs each Kubernetes node as a Docker container on your laptop.", wait=0.3)
        self.play(Create(laptop[0]), FadeIn(laptop[1]), run_time=0.8)
        self.play(LaggedStart(*[FadeIn(n, shift=UP * 0.2) for n in nodes], lag_ratio=0.25), run_time=1.4)
        self.caption("Each node container runs the kindest/node image: its own containerd and kubelet.", wait=1.6)
        self.caption("Node containers share the host's CPU and RAM: '3 nodes' is still one machine.", wait=1.6)

        self.caption("docker build puts reliability-api:0.1.0 in the host's Docker image store…", wait=0.2)
        self.play(FadeIn(build, shift=RIGHT * 0.2))
        self.packet([build.get_bottom(), store.get_top()], color=WARN, run_time=0.7)
        self.play(FadeIn(store))
        host_img = chip("reliability-api:0.1.0", size=16).next_to(store, DOWN, buff=0.15)
        self.play(FadeIn(host_img, scale=0.8))
        self.caption("…but the kubelet inside a node uses its own containerd store and cannot see it.", wait=1.4)

        cmd = mono("kind load docker-image reliability-api:0.1.0 --name reliability-lab", 18, WARN)
        cmd.move_to(DOWN * 2.35)
        cmd_bg = SurroundingRectangle(cmd, color=SURFACE, fill_color=SURFACE, fill_opacity=1, buff=0.1,
                                      corner_radius=0.08)
        self.caption("Side-load it: kind load docker-image copies the image into every node.", wait=0.2)
        self.play(FadeIn(cmd_bg), Write(cmd), run_time=1.0)
        for s in slots:
            self.packet([host_img.get_right(), s.get_left()], color=WARN, run_time=0.55)
            c = chip("reliability-api:0.1.0", size=15).move_to(s)
            imgs.append(c)
            self.play(FadeIn(c, scale=0.8), run_time=0.3)

        pods = []
        for x in xs[1:]:
            p = box("Pod", "uses loaded copy", color=OK, w=2.5, h=0.95, title_size=21,
                    sub_size=17).move_to(RIGHT * x + DOWN * 1.15)
            pods.append(p)
        self.caption("With tag 0.1.0 the pull policy defaults to IfNotPresent, so the loaded copy is used.", wait=0.2)
        self.play(*[FadeIn(p, scale=0.85) for p in pods])
        self.wait(1.2)

        # the :latest trap
        bad = box("Pod", "ImagePullBackOff", color=BAD, w=2.5, h=0.95, title_size=21,
                  sub_size=17).move_to(pods[1])
        self.caption("Trap: with :latest the policy defaults to Always, so the kubelet pulls and fails.",
                     wait=0.2, color=TEXT_C)
        self.play(ReplacementTransform(pods[1], bad), run_time=0.8)
        self.play(Indicate(bad[0], color=BAD), run_time=0.7)
        self.caption("Fix: use a versioned tag (0.1.0 locally, the git SHA in CI). Never rely on :latest.",
                     wait=1.6)

        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag and m is not self.caption_mob],
                  run_time=0.6)

    # ------------------------------------------------------------- helm render
    def part_helm_render(self):
        hdr = label("Helm: chart + values → manifests → release", 26, ACCENT, weight=BOLD).move_to(UP * 3.1)
        tmpl = box("templates/*.yaml", "charts/reliability-api", color=ACCENT, w=3.6, h=0.9,
                   title_size=20, sub_size=14).move_to(LEFT * 4.4 + UP * 2.15)

        l1 = layer("1 · values.yaml (chart defaults)", "replicaCount: 2  tag: \"\"  logLevel: info", MUTED)
        l2 = layer("2 · -f values-lab.yaml", "replicaCount: 3  logLevel: debug", WARN)
        l3 = layer("3 · -f values-ci.yaml (right-most file)", "image.tag: 3f9c2e1", WARN)
        l4 = layer("4 · --set (highest)", "config.logLevel=warning", BAD)
        stack = VGroup(l4, l3, l2, l1).arrange(DOWN, buff=0.12).move_to(LEFT * 3.95 + DOWN * 0.75)
        lo = VGroup()
        hi = VGroup()

        helm = box("helm (client)", "merge · render · send · record", color=INFO, w=3.3, h=1.1,
                   sub_size=16).move_to(RIGHT * 1.1 + UP * 1.0)
        merged = VGroup(
            mono("replicaCount: 3      (lab)", 16),
            mono("image.tag: 3f9c2e1   (ci)", 16),
            mono("logLevel: warning    (--set)", 16),
            mono("service.port: 80     (default)", 16),
        ).arrange(DOWN, aligned_edge=LEFT, buff=0.08)
        merged_t = label("merged .Values", 17, INFO, weight=BOLD)
        merged_g = VGroup(merged_t, merged).arrange(DOWN, aligned_edge=LEFT, buff=0.1)
        merged_bg = SurroundingRectangle(merged_g, color=INFO, buff=0.15, corner_radius=0.1, stroke_width=1.5)
        merged_all = VGroup(merged_bg, merged_g).next_to(helm, DOWN, buff=0.3)

        manifests = VGroup(*[chip(k, ACCENT, 17) for k in
                             ["Deployment", "Service", "ConfigMap", "ServiceAccount", "HPA"]]
                           ).arrange(DOWN, buff=0.16)
        cl = zone(3.2, 4.9, "ns reliability-lab", color=OK).move_to(RIGHT * 5.4 + DOWN * 0.1)
        rel_t = label("release reliability-api", 17, OK, weight=BOLD).next_to(cl[0].get_top(), DOWN, buff=0.5)
        manifests.next_to(rel_t, DOWN, buff=0.2)
        secret = chip("Secret: rev record", INFO, 16).next_to(manifests, DOWN, buff=0.3)

        self.caption("A chart is templates plus default values. Installed in a cluster, it becomes a release.",
                     wait=0.2)
        self.play(FadeIn(hdr), FadeIn(tmpl, shift=DOWN * 0.2))
        self.play(FadeIn(l1, shift=UP * 0.2), FadeIn(lo))
        self.wait(0.6)
        self.caption("Values merge in order: values.yaml, then each -f file left to right, then --set.", wait=0.2)
        for l in (l2, l3):
            self.play(FadeIn(l, shift=UP * 0.2), run_time=0.5)
        self.play(FadeIn(l4, shift=UP * 0.2), FadeIn(hi), run_time=0.5)
        self.caption("Later wins: logLevel goes info → debug → warning. Keys nobody overrides keep defaults.",
                     wait=0.2)
        self.play(FadeIn(helm))
        for l in (l1, l2, l3, l4):
            self.packet([l.get_right(), helm.get_left()], color=WARN, run_time=0.35)
        self.play(FadeIn(merged_all, shift=UP * 0.15))
        self.play(Indicate(merged[2], color=BAD), run_time=0.8)
        self.wait(0.6)

        self.caption("helm renders the Go templates with .Values into plain Kubernetes manifests.", wait=0.2)
        self.packet([tmpl.get_right(), [helm.get_center()[0], tmpl.get_center()[1], 0], helm.get_top()],
                    color=ACCENT, run_time=0.7)
        self.play(Create(cl[0]), FadeIn(cl[1]), FadeIn(rel_t))
        self.packet([helm.get_right(), [cl.get_left()[0] + 0.1, helm.get_center()[1], 0]], color=ACCENT,
                    run_time=0.6)
        self.play(LaggedStart(*[FadeIn(m, shift=LEFT * 0.2) for m in manifests], lag_ratio=0.15), run_time=1.0)
        self.caption("They go to the API server, and Helm records the revision as a Secret in the namespace.",
                     wait=0.2)
        self.play(FadeIn(secret, scale=0.85))
        self.wait(1.4)
        self.play(*[FadeOut(m) for m in self.mobjects if m is not self.tag and m is not self.caption_mob],
                  run_time=0.6)

    # ------------------------------------------------------------- revisions
    def part_revisions(self):
        hdr = label("helm history reliability-api -n reliability-lab", 22, ACCENT, font=MONO).move_to(UP * 2.9)
        xs = [-5.1, -1.7, 1.7, 5.1]
        specs = [("rev 1 · install", "image 0.1.0"), ("rev 2 · upgrade", "image 0.1.1"),
                 ("rev 3 · upgrade", "image 0.1.2-bad"), ("rev 4 · rollback to 2", "image 0.1.1 (copy)")]
        revs = [box(t, s, color=OK, w=3.1, h=1.15, title_size=21, sub_size=17).move_to(RIGHT * x + UP * 1.1)
                for (t, s), x in zip(specs, xs)]

        def status(text, color, rev):
            return label(text, 18, color, weight=BOLD).next_to(rev, DOWN, buff=0.2)

        self.caption("Every install, upgrade and rollback creates a new numbered revision, starting at 1.",
                     wait=0.2)
        self.play(FadeIn(hdr))
        self.play(FadeIn(revs[0], shift=UP * 0.2))
        s1 = status("deployed", OK, revs[0])
        self.play(FadeIn(s1))
        self.wait(0.6)

        self.caption("helm upgrade --install with a new image tag → revision 2. Revision 1 is superseded.",
                     wait=0.2)
        a1 = Arrow(revs[0].get_right(), revs[1].get_left(), buff=0.08, color=MUTED, stroke_width=3,
                   max_tip_length_to_length_ratio=0.25)
        self.play(GrowArrow(a1), FadeIn(revs[1], shift=RIGHT * 0.2))
        s2 = status("deployed", OK, revs[1])
        self.play(FadeIn(s2), s1.animate.become(status("superseded", MUTED, revs[0])))
        self.wait(1.0)

        self.caption("A bad upgrade: revision 3 is recorded with status failed.", wait=0.2, color=TEXT_C)
        a2 = Arrow(revs[1].get_right(), revs[2].get_left(), buff=0.08, color=MUTED, stroke_width=3,
                   max_tip_length_to_length_ratio=0.25)
        bad = box(*specs[2], color=BAD, w=3.1, h=1.15, title_size=21, sub_size=17).move_to(revs[2])
        self.play(GrowArrow(a2), FadeIn(bad, shift=RIGHT * 0.2))
        s3 = status("failed", BAD, bad)
        self.play(FadeIn(s3), Indicate(bad[0], color=BAD))
        self.wait(1.0)

        cmd = mono("helm rollback reliability-api 2 -n reliability-lab", 18, WARN).move_to(DOWN * 1.1)
        self.caption("helm rollback reliability-api 2 copies revision 2's content into a NEW revision 4.",
                     wait=0.2)
        self.play(Write(cmd), run_time=1.0)
        curve = CurvedArrow(revs[1].get_bottom() + DOWN * 0.55, revs[3].get_bottom() + DOWN * 0.55,
                            angle=TAU / 7, color=WARN, stroke_width=3)
        self.play(Create(curve), run_time=0.8)
        self.play(FadeIn(revs[3], shift=UP * 0.2))
        s4 = status("deployed", OK, revs[3])
        self.play(FadeIn(s4), s2.animate.become(status("superseded", MUTED, revs[1])))
        self.wait(0.8)

        self.caption("History only grows: revision 3 stays as evidence of the failure.", wait=1.8)
        note = label("--history-max (default 10) prunes old revisions", 16, MUTED).move_to(DOWN * 2.25)
        self.play(FadeIn(note))
        self.wait(1.2)
