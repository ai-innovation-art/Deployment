"""Module 03 — the life of `kubectl apply` and the reconciliation loop.
Facts follow notes/03-kubernetes-architecture.html (verified against kubernetes.io)."""
from common import *


class M03KubectlApply(Explainer):
    MODULE = "Module 03"
    TITLE = "The life of kubectl apply"
    SUBTITLE = "Desired state → controllers → scheduler → kubelet → running Pods"

    def construct(self):
        self.title_card()

        # ---- layout ----
        user = box("kubectl", "apply -f deploy.yaml", color=MUTED, w=2.6).move_to(LEFT * 5.2 + UP * 2.0)
        api = box("kube-apiserver", "the only front door", color=ACCENT, w=3.0).move_to(LEFT * 1.2 + UP * 2.0)
        etcd = box("etcd", "stores desired + actual", color=ACCENT, w=2.8).move_to(RIGHT * 3.6 + UP * 2.0)
        dctl = box("Deployment ctrl", "creates ReplicaSet", color=INFO, w=2.9).move_to(LEFT * 4.3 + UP * 0.1)
        rsctl = box("ReplicaSet ctrl", "creates 2 Pods", color=INFO, w=2.9).move_to(LEFT * 1.0 + UP * 0.1)
        sched = box("kube-scheduler", "picks a node", color=INFO, w=2.9).move_to(RIGHT * 2.3 + UP * 0.1)
        cp = zone(13.2, 4.6, "control plane", color=ACCENT).move_to(UP * 0.85)

        node = zone(7.4, 1.7, "worker node", color=OK).move_to(RIGHT * 1.6 + DOWN * 2.5)
        kubelet = box("kubelet", "CRI → containerd", color=OK, w=2.6, h=1.0).move_to(LEFT * 0.7 + DOWN * 2.45)
        pod1 = box("Pod", "reliability-api", color=OK, w=1.9, h=0.9).move_to(RIGHT * 2.0 + DOWN * 2.45)
        pod2 = box("Pod", "reliability-api", color=OK, w=1.9, h=0.9).move_to(RIGHT * 4.1 + DOWN * 2.45)

        self.caption("You declare desired state: 'run 2 replicas of reliability-api'.", wait=1.0)
        self.play(FadeIn(user, shift=RIGHT * 0.3))
        self.play(Create(cp[0]), FadeIn(cp[1]), FadeIn(api), FadeIn(etcd), run_time=1.0)

        # 1. apply -> apiserver -> etcd
        self.caption("1 · kubectl sends the object to the API server (authn, authz, admission, validation).", wait=0.3)
        self.packet([user.get_right(), api.get_left()], color=WARN)
        self.play(Indicate(api[0], color=ACCENT), run_time=0.6)
        self.caption("2 · The API server persists it in etcd. Nothing is running yet: only intent is stored.", wait=0.3)
        self.packet([api.get_right(), etcd.get_left()], color=WARN)
        spec = mono("spec.replicas: 2", 18, WARN).next_to(etcd, DOWN, buff=0.15)
        self.play(FadeIn(spec, shift=UP * 0.1))
        self.wait(1.0)

        # 2. controllers watch
        self.play(FadeIn(dctl), FadeIn(rsctl), FadeIn(sched), run_time=0.8)
        self.caption("3 · Controllers WATCH the API. The Deployment controller creates a ReplicaSet.", wait=0.3)
        self.packet([api.get_bottom(), api.get_bottom() + DOWN * 0.5, dctl.get_top() + UP * 0.5, dctl.get_top()], color=INFO)
        self.play(Indicate(dctl[0], color=INFO), run_time=0.6)
        self.caption("4 · The ReplicaSet controller sees 0 of 2 Pods and creates 2 Pod objects (unscheduled).", wait=0.3)
        self.packet([dctl.get_right(), rsctl.get_left()], color=INFO)
        ghost1 = box("Pod", "nodeName: —", color=WARN, w=1.6, h=0.8).scale(0.7).next_to(rsctl, DOWN, buff=0.08).shift(LEFT * 0.75)
        ghost2 = ghost1.copy().shift(RIGHT * 1.5)
        self.play(FadeIn(ghost1, scale=0.8), FadeIn(ghost2, scale=0.8))
        self.wait(0.8)

        # 3. scheduler
        self.caption("5 · The scheduler filters and scores nodes, then binds each Pod to a node.", wait=0.3)
        self.packet([rsctl.get_right(), sched.get_left()], color=INFO)
        self.play(Indicate(sched[0], color=INFO), run_time=0.6)
        self.play(FadeIn(node[0]), FadeIn(node[1]), FadeIn(kubelet), run_time=0.8)

        # 4. kubelet
        self.caption("6 · The kubelet on that node sees Pods bound to it and asks the runtime to start containers.", wait=0.3)
        self.packet([sched.get_bottom(), kubelet.get_top()], color=OK)
        self.play(ReplacementTransform(ghost1, pod1), ReplacementTransform(ghost2, pod2), run_time=1.0)
        self.caption("7 · The kubelet reports status back. Actual state now matches desired state.", wait=0.3)
        self.packet([kubelet.get_top() + RIGHT * 0.5, api.get_bottom() + RIGHT * 0.6], color=OK)
        status = mono("status.readyReplicas: 2", 18, OK).next_to(spec, DOWN, buff=0.1)
        self.play(FadeIn(status, shift=UP * 0.1))
        self.wait(1.2)

        # 5. reconciliation on failure
        self.caption("Now delete a Pod. Nothing 'restarts' it: a controller notices the difference.", wait=0.5)
        x = Cross(pod2, stroke_color=BAD, stroke_width=6)
        self.play(Create(x), run_time=0.5)
        self.play(FadeOut(pod2), FadeOut(x), status.animate.become(mono("status.readyReplicas: 1", 18, BAD).move_to(status)))
        self.caption("Desired 2 ≠ actual 1 → the ReplicaSet controller creates a replacement Pod.", wait=0.3)
        self.packet([rsctl.get_bottom(), rsctl.get_bottom() + DOWN * 0.6, pod2.get_top() + UP * 0.4, pod2.get_top()], color=INFO)
        pod2b = box("Pod", "new name, new IP", color=OK, w=1.9, h=0.9).move_to(pod2)
        self.play(FadeIn(pod2b, scale=0.8))
        self.play(status.animate.become(mono("status.readyReplicas: 2", 18, OK).move_to(status)))
        self.wait(1.0)

        # loop graphic
        self.caption("This observe → compare → act cycle is the reconciliation loop. It never stops.", wait=0.2)
        loop = VGroup(
            label("observe", 22, ACCENT), label("compare", 22, WARN), label("act", 22, OK)
        ).arrange(RIGHT, buff=1.4).move_to(UP * 2.2)
        self.play(*[FadeOut(m) for m in [user, api, etcd, spec, status, cp]], run_time=0.6)
        arrows = VGroup(
            Arrow(loop[0].get_right(), loop[1].get_left(), color=MUTED, buff=0.15),
            Arrow(loop[1].get_right(), loop[2].get_left(), color=MUTED, buff=0.15),
            CurvedArrow(loop[2].get_bottom() + DOWN * 0.1, loop[0].get_bottom() + DOWN * 0.1, angle=-TAU / 4, color=MUTED),
        )
        self.play(FadeIn(loop), Create(arrows), run_time=1.2)
        for _ in range(2):
            self.play(*[Indicate(m, scale_factor=1.15) for m in loop], run_time=0.9)
        self.wait(1.0)

        self.outro("Kubernetes doesn't run commands — it stores intent.\nControllers keep pushing actual state toward it.")
