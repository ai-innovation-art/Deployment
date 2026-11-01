"""Module 11 — GKE architecture, Autopilot vs Standard billing, Workload Identity Federation (Pods and GitHub Actions),
and what survives a cluster delete. Facts follow notes/11-gke-cloud.html (GKE architecture, Autopilot vs Standard,
Workload Identity Federation for GKE, Workload Identity Federation for GitHub Actions, Cost controls)."""
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


def harrow(a, b, color=MUTED, buff=0.08):
    return Arrow(a.get_right(), b.get_left(), buff=buff, color=color, stroke_width=3,
                 max_tip_length_to_length_ratio=0.3, max_stroke_width_to_length_ratio=8)


def pod(name="Pod", color=OK, w=1.3, h=0.6):
    return box(name, None, color=color, w=w, h=h, title_size=16)


class M11GkeIdentity(Explainer):
    MODULE = "Module 11"
    TITLE = "GKE: identity without keys"
    SUBTITLE = "Managed control plane, Autopilot billing, Workload Identity Federation, cleanup"

    def construct(self):
        self.title_card()

        # ================= architecture =================
        gz = zone(4.6, 4.6, "Google-managed", color=ACCENT).move_to(LEFT * 4.3 + UP * 0.55)
        cp = box("Control plane", None, color=ACCENT, w=3.8, h=0.6, title_size=22).move_to(LEFT * 4.3 + UP * 2.05)
        comps = VGroup(*[label(t, 18, MUTED) for t in ["kube-apiserver (endpoint)", "etcd / cluster state", "scheduler", "controller managers", "upgrades via release channel"]]).arrange(DOWN, buff=0.13, aligned_edge=LEFT)
        comps.next_to(cp, DOWN, buff=0.25)
        yz = zone(7.6, 4.6, "your project: reliability-lab-1234 (VPC, nodes)", color=OK).move_to(RIGHT * 2.55 + UP * 0.55)
        n1 = zone(3.3, 2.4, "node VM", color=OK).move_to(RIGHT * 0.75 + UP * 0.2)
        n2 = zone(3.3, 2.4, "node VM", color=OK).move_to(RIGHT * 4.35 + UP * 0.2)
        nlab = label("kubelet · containerd", 15, MUTED)
        p1 = pod("api Pod").move_to(n1).shift(DOWN * 0.3 + LEFT * 0.75)
        p2 = pod("system", color=MUTED).move_to(n1).shift(DOWN * 0.3 + RIGHT * 0.75)
        p3 = pod("api Pod").move_to(n2).shift(DOWN * 0.3 + LEFT * 0.75)
        k1 = nlab.copy().move_to(n1).shift(UP * 0.4)
        k2 = nlab.copy().move_to(n2).shift(UP * 0.4)
        pool_lab = label('node pool "default" = nodes with the same configuration', 16, MUTED).move_to(RIGHT * 2.55 + UP * 2.2)

        self.caption("In GKE, Google Cloud manages the control plane and system components for you.", wait=0.3)
        self.play(Create(gz[0]), FadeIn(gz[1]), FadeIn(cp), run_time=0.9)
        self.play(LaggedStart(*[FadeIn(c, shift=RIGHT * 0.1) for c in comps], lag_ratio=0.15), run_time=1.0)
        self.caption("Nodes are Compute Engine VMs in your project. Your workloads are ordinary Pods.", wait=0.3)
        self.play(Create(yz[0]), FadeIn(yz[1]), run_time=0.7)
        self.play(FadeIn(n1), FadeIn(n2), FadeIn(k1), FadeIn(k2), FadeIn(pool_lab), run_time=0.8)
        self.play(FadeIn(p1, scale=0.8), FadeIn(p2, scale=0.8), FadeIn(p3, scale=0.8), run_time=0.6)
        self.packet([n1.get_left() + UP * 0.4, cp.get_right() + DOWN * 1.2 + RIGHT * 0.05], color=ACCENT, run_time=0.8)
        self.wait(0.8)

        # ---- Standard billing ----
        arch = VGroup(gz, cp, comps, yz, n1, n2, k1, k2, p1, p2, p3, pool_lab)
        self.caption("Standard: you create and size node pools, and pay for node VMs whether Pods use them or not.", wait=0.2)
        bill1 = VGroup(SurroundingRectangle(n1[0], color=WARN, buff=0.05, stroke_width=4),
                       SurroundingRectangle(n2[0], color=WARN, buff=0.05, stroke_width=4))
        tag1 = label("billed: whole node VMs", 20, WARN, weight=BOLD).next_to(yz, DOWN, buff=0.2)
        self.play(Create(bill1), FadeIn(tag1), run_time=0.8)
        self.wait(1.6)

        # ---- Autopilot billing ----
        self.caption("Autopilot: Google provisions, scales and upgrades nodes. You never size node pools.", wait=0.3)
        self.play(FadeOut(bill1), FadeOut(tag1), n1[0].animate.set_opacity(0.3), n2[0].animate.set_opacity(0.3), run_time=0.6)
        self.caption("General-purpose Pods are billed for the CPU, memory and storage they request, per second.", wait=0.2)
        bill2 = VGroup(*[SurroundingRectangle(p[0], color=WARN, buff=0.06, stroke_width=4) for p in (p1, p2, p3)])
        req = mono("requests: cpu 100m, memory 128Mi", 17, WARN)
        tag2 = VGroup(label("billed: Pod requests", 20, WARN, weight=BOLD), req).arrange(RIGHT, buff=0.4).next_to(yz, DOWN, buff=0.2)
        self.play(Create(bill2), FadeIn(tag2), run_time=0.8)
        self.wait(1.2)
        self.caption("A Pod in CrashLoopBackOff is still scheduled with resources allocated, so it is billed.", wait=0.3)
        self.play(p3[0].animate.set_stroke(BAD).set_fill(BAD, opacity=0.2), run_time=0.5)
        cl = label("CrashLoopBackOff", 15, BAD).next_to(p3, DOWN, buff=0.1)
        self.play(FadeIn(cl), run_time=0.4)
        self.wait(1.2)
        fee = label("Cluster fee: $0.10/cluster/hour; first cluster usually offset by free-tier credit (29 Oct 2026)", 18, MUTED).move_to(DOWN * 2.45)
        self.play(FadeIn(fee), run_time=0.5)
        self.wait(1.4)
        self.play(FadeOut(VGroup(arch, bill2, tag2, cl, fee)), run_time=0.6)

        # ================= Workload Identity Federation for GKE =================
        node = zone(6.4, 3.4, "GKE node · namespace reliability-lab", color=OK).move_to(LEFT * 3.5 + UP * 1.0)
        app = box("reliability-api Pod", "KSA reliability-api", color=OK, w=2.8, h=1.05, title_size=20).move_to(LEFT * 5.0 + UP * 1.3)
        mds = box("GKE metadata server", "knows Pod → ns / KSA", color=INFO, w=2.8, h=1.05, title_size=20).move_to(LEFT * 1.9 + UP * 1.3)
        gapi = zone(6.0, 3.4, "Google Cloud APIs", color=ACCENT).move_to(RIGHT * 3.6 + UP * 1.0)
        sts = box("Security Token Service", "token exchange", color=ACCENT, w=2.7, h=1.05, title_size=19).move_to(RIGHT * 2.1 + UP * 1.3)
        gcs = box("Cloud Storage", "IAM check", color=ACCENT, w=2.4, h=1.05, title_size=20).move_to(RIGHT * 5.2 + UP * 1.3)

        self.caption("Workload Identity Federation lets a Pod call Google APIs with no JSON key file.", wait=0.3)
        self.play(Create(node[0]), FadeIn(node[1]), FadeIn(app), run_time=0.8)
        nokey = mono("key.json", 20, MUTED).next_to(app, DOWN, buff=0.2)
        xk = VGroup(Cross(nokey, stroke_color=BAD, stroke_width=4), label("no key file mounted", 16, BAD).next_to(nokey, DOWN, buff=0.1))
        self.play(FadeIn(nokey), run_time=0.3)
        self.play(Create(xk), run_time=0.4)
        self.wait(0.6)

        self.caption("1 · The client library asks metadata.google.internal for a token. The node intercepts it.", wait=0.2)
        self.play(FadeIn(mds), run_time=0.5)
        self.packet([app.get_right(), mds.get_left()], color=OK, run_time=0.8)
        a1 = connect(app, mds)
        self.add(a1)
        self.caption("2 · The metadata server knows the Pod's namespace and KSA and gets a Kubernetes token for it.", wait=0.3)
        ktok = label("KSA token", 16, INFO).next_to(mds, DOWN, buff=0.2)
        self.play(FadeIn(ktok, shift=UP * 0.1), Indicate(mds[0], color=INFO), run_time=0.8)
        self.wait(0.6)

        self.caption("3 · STS exchanges the KSA token for a short-lived federated access token.", wait=0.2)
        self.play(Create(gapi[0]), FadeIn(gapi[1]), FadeIn(sts), run_time=0.7)
        self.packet([mds.get_right(), sts.get_left()], color=INFO, run_time=0.8)
        a2 = connect(mds, sts)
        self.add(a2)
        stok = label("short-lived token", 16, ACCENT).next_to(sts, DOWN, buff=0.2)
        self.play(FadeIn(stok, shift=UP * 0.1), run_time=0.5)
        principal = VGroup(label("federated principal (one per namespace + KSA):", 18, MUTED),
                           mono("principal://…/subject/ns/reliability-lab/sa/reliability-api", 19, TEXT_C)).arrange(DOWN, buff=0.15).move_to(DOWN * 1.35)
        self.play(FadeIn(principal), run_time=0.6)
        self.wait(1.0)

        self.caption("4 · The app calls Cloud Storage. IAM checks the principal for roles/storage.objectViewer.", wait=0.2)
        self.play(FadeIn(gcs), run_time=0.5)
        self.packet([sts.get_right(), gcs.get_left()], color=ACCENT, run_time=0.8)
        a3 = connect(sts, gcs)
        self.add(a3)
        ok = label("allowed → 200", 18, OK, weight=BOLD).next_to(gcs, DOWN, buff=0.2)
        self.play(FadeIn(ok), run_time=0.4)
        self.caption("No binding, or a typo in the principal string → 403 naming the missing permission.", wait=1.6)
        self.play(FadeOut(VGroup(node, app, mds, gapi, sts, gcs, nokey, xk, ktok, stok, principal, ok, a1, a2, a3)), run_time=0.6)

        # ================= GitHub Actions OIDC =================
        gh = zone(4.6, 3.4, "GitHub", color=MUTED).move_to(LEFT * 4.5 + UP * 1.0)
        run = box("workflow run", "permissions: id-token: write", color=MUTED, w=3.8, h=1.0, title_size=20).move_to(LEFT * 4.5 + UP * 1.75)
        iss = box("GitHub OIDC issuer", "signs a short ID token", color=MUTED, w=3.8, h=1.0, title_size=20).move_to(LEFT * 4.5 + DOWN * 0.05)
        gc = zone(8.6, 3.4, "Google Cloud (project reliability-lab-1234)", color=ACCENT).move_to(RIGHT * 2.45 + UP * 1.0)
        pool = box('pool "github" provider', "issuer + mapping + condition", color=ACCENT, w=3.6, h=1.0, title_size=20).move_to(RIGHT * 0.45 + UP * 1.75)
        sts2 = box("Security Token Service", "short-lived token", color=ACCENT, w=3.6, h=1.0, title_size=19).move_to(RIGHT * 0.45 + DOWN * 0.05)
        ar = box('Artifact Registry "reliability"', "repo-scoped writer role", color=OK, w=3.8, h=1.0, title_size=18).move_to(RIGHT * 4.6 + UP * 0.85)

        self.caption("CI uses the same idea: GitHub Actions OIDC to Google Cloud, with nothing secret in GitHub.", wait=0.3)
        self.play(Create(gh[0]), FadeIn(gh[1]), Create(gc[0]), FadeIn(gc[1]), run_time=0.8)
        self.play(FadeIn(run), FadeIn(iss), run_time=0.6)
        self.packet([run.get_bottom(), iss.get_top()], color=MUTED, run_time=0.6)
        b1 = connect(run, iss)
        self.add(b1)
        self.caption("1 · The workflow presents GitHub's ID token to the workload identity pool provider.", wait=0.2)
        self.play(FadeIn(pool), run_time=0.5)
        self.packet([iss.get_right(), iss.get_right() + RIGHT * 0.5, pool.get_left() + LEFT * 0.5, pool.get_left()], color=WARN, run_time=0.9)
        b2 = connect(iss, pool)
        self.add(b2)
        cond = mono("assertion.repository_owner == '<you>'", 15, WARN).next_to(gc[0], DOWN, buff=0.15).align_to(gc[0], LEFT)
        self.play(FadeIn(cond), run_time=0.5)
        self.caption("It checks the issuer, maps claims, and enforces an attribute condition.", wait=1.0)
        self.caption("2 · STS returns a short-lived token.  3 · The workflow pushes reliability-api:<git-sha>.", wait=0.2)
        self.play(FadeIn(sts2), FadeIn(ar), run_time=0.6)
        self.packet([pool.get_bottom(), sts2.get_top()], color=ACCENT, run_time=0.6)
        b3 = connect(pool, sts2)
        self.add(b3)
        self.packet([sts2.get_right(), ar.get_left() + DOWN * 0.3], color=OK, run_time=0.8)
        b4 = connect(sts2, ar)
        self.add(b4)
        self.play(Indicate(ar[0], color=OK), run_time=0.6)
        self.caption("A token from another org fails the attribute condition and gets no Google token.", wait=0.2)
        bad = box("other-org repo", None, color=BAD, w=2.4, h=0.6, title_size=17).next_to(gh[0], DOWN, buff=0.15).align_to(gh[0], LEFT)
        self.play(FadeIn(bad), run_time=0.4)
        rej_end = pool.get_left() + DOWN * 0.3
        self.packet([bad.get_right(), bad.get_right() + RIGHT * 0.9, rej_end + LEFT * 0.4], color=BAD, run_time=0.8)
        rx = Cross(Square(0.3).move_to(rej_end + LEFT * 0.4), stroke_color=BAD, stroke_width=5)
        self.play(Create(rx), run_time=0.4)
        self.wait(1.0)
        self.play(FadeOut(VGroup(gh, run, iss, gc, pool, sts2, ar, cond, bad, rx, b1, b2, b3, b4)), run_time=0.6)

        # ================= cost reminder =================
        self.caption("Cost reminder: deleting the cluster does not delete everything you are billed for.", wait=0.3)
        cl_box = box("cluster reliability-lab", "control plane · nodes · Pods", color=ACCENT, w=4.2, h=1.1).move_to(LEFT * 4.2 + UP * 1.4)
        self.play(FadeIn(cl_box), run_time=0.5)
        gone = label("deleted with the cluster", 18, OK).next_to(cl_box, DOWN, buff=0.2)
        self.play(Create(Cross(cl_box, stroke_color=BAD, stroke_width=5)), FadeIn(gone), run_time=0.7)
        items = [("persistent disks (PVCs)", "retained: billed by size", BAD),
                 ("load balancers / forwarding rules", "cleanup can fail", WARN),
                 ("reserved static IPs", "still billed if unattached", BAD),
                 ("Artifact Registry repos", "project resource", BAD),
                 ("GCS buckets (incl. Terraform state)", "project resource", BAD)]
        rows = VGroup()
        for name, why, c in items:
            r = VGroup(label(name, 21, TEXT_C), label(why, 17, c)).arrange(RIGHT, buff=0.3)
            rows.add(r)
        rows.arrange(DOWN, buff=0.28, aligned_edge=LEFT).move_to(RIGHT * 2.9 + UP * 0.6)
        surv = label("still there afterwards:", 20, BAD, weight=BOLD).next_to(rows, UP, buff=0.3).align_to(rows, LEFT)
        self.play(FadeIn(surv), LaggedStart(*[FadeIn(r, shift=LEFT * 0.2) for r in rows], lag_ratio=0.25), run_time=1.8)
        self.caption("Delete LoadBalancer Services and Gateways before the cluster, then verify with list commands.", wait=0.3)
        cmd = mono("gcloud compute disks list · forwarding-rules list · addresses list", 16, MUTED).move_to(DOWN * 1.9)
        self.play(FadeIn(cmd), run_time=0.5)
        self.wait(1.8)

        outro_lines(self, "Google runs the control plane; on Autopilot your Pod requests are the bill.\nPods and CI get short-lived tokens via federation, never JSON keys.")
