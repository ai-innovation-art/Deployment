"""Module 09 — the reliability-api GitHub Actions pipeline: trigger → needs DAG →
image artifact hand-off → publish to GHCR on main → least-privilege permissions → fail-fast.
Facts follow notes/09-cicd-github-actions.html (pipeline stages, concepts, needs graph,
permissions, artifacts, GHCR tags, the complete ci.yml and the run visualizer)."""
from common import *

GREY = "#6b6a64"


def job(title, sub, color=MUTED, w=2.45, h=1.1):
    return box(title, sub, color=color, w=w, h=h, title_size=20, sub_size=16)


class M09Pipeline(Explainer):
    MODULE = "Module 09"
    TITLE = "The CI/CD pipeline"
    SUBTITLE = "push / PR → test → build → scan → kind-integration → publish (main)"

    def construct(self):
        self.title_card()
        self.build_dag()
        self.happy_run()
        self.permissions()
        self.failing_run()
        self.outro("Cheap checks first; any red job skips everything after it.\n"
                   "Build once, test those exact bytes, publish only from main.")

    # --------------------------------------------------------------- helpers
    def state(self, key, color, text):
        j = self.jobs[key]
        title, sub = self.specs[key]
        new = job(title, sub, color=color).move_to(j)
        st = label(text, 16, color, weight=BOLD).next_to(new, DOWN, buff=0.12)
        anims = [Transform(j, new)]
        if key in self.st:
            anims.append(Transform(self.st[key], st))
        else:
            self.st[key] = st
            anims.append(FadeIn(st))
        return anims

    # ------------------------------------------------------------------- DAG
    def build_dag(self):
        ev = box("event", "push / pull_request → main", color=WARN, w=3.6, h=0.95, sub_size=16).move_to(LEFT * 4.6 + UP * 2.7)
        wf = box(".github/workflows/ci.yml", "on: matches → workflow run", color=ACCENT, w=4.2, h=0.95,
                 title_size=20, sub_size=16).move_to(RIGHT * 0.6 + UP * 2.7)
        vm = label("each job → its own fresh runner VM", 17, MUTED).next_to(wf, RIGHT, buff=0.3)
        if vm.get_right()[0] > 6.9:
            vm.scale_to_fit_width(6.9 - vm.get_left()[0])

        self.specs = {
            "t12": ("test (py3.12)", "ruff + pytest"),
            "t13": ("test (py3.13)", "ruff + pytest"),
            "build": ("build", "needs: test"),
            "scan": ("scan", "needs: build"),
            "kind": ("kind-integration", "needs: build, scan"),
            "pub": ("publish", "if: push to main"),
        }
        y = 0.35
        pos = {"t12": [-5.6, y + 0.8, 0], "t13": [-5.6, y - 0.8, 0], "build": [-2.85, y, 0],
               "scan": [-0.05, y, 0], "kind": [2.75, y, 0], "pub": [5.6, y, 0]}
        self.jobs = {k: job(*self.specs[k]).move_to(pos[k]) for k in self.specs}
        self.st = {}
        J = self.jobs
        edges = VGroup(connect(J["t12"], J["build"]), connect(J["t13"], J["build"]),
                       connect(J["build"], J["scan"]), connect(J["scan"], J["kind"]),
                       connect(J["kind"], J["pub"]))
        self.edges = edges

        self.caption("A push or pull request to main triggers the workflow defined in ci.yml.", wait=0.2)
        self.play(FadeIn(ev, shift=RIGHT * 0.2))
        self.packet([ev.get_right(), wf.get_left()], color=WARN, run_time=0.6)
        self.play(FadeIn(wf), FadeIn(vm))
        self.wait(0.8)
        self.caption("Jobs form a DAG through needs:. Two test legs (a matrix) run in parallel.", wait=0.2)
        self.play(FadeIn(J["t12"]), FadeIn(J["t13"]))
        for k, e in (("build", (0, 1)), ("scan", (2,)), ("kind", (3,)), ("pub", (4,))):
            self.play(FadeIn(J[k], shift=RIGHT * 0.15), *[Create(edges[i]) for i in e], run_time=0.55)
        self.caption("Cheapest, fastest checks first; the slow kind cluster boot comes last.", wait=1.4)
        self.ev, self.wf, self.vm = ev, wf, vm

    # ------------------------------------------------------------- happy run
    def happy_run(self):
        J = self.jobs
        self.caption("A push to main: both test legs pass, so build starts.", wait=0.2)
        self.play(*self.state("t12", WARN, "running"), *self.state("t13", WARN, "running"), run_time=0.5)
        self.wait(0.4)
        self.play(*self.state("t12", OK, "success"), *self.state("t13", OK, "success"), run_time=0.5)
        self.play(*self.state("build", WARN, "running"), run_time=0.4)

        art = box("artifact", "image.tar (docker save)", color=INFO, w=3.3, h=0.85, title_size=18,
                  sub_size=15).move_to(LEFT * 1.5 + DOWN * 1.75)
        self.caption("build builds the image once, smoke-tests it, and uploads it as an artifact.", wait=0.2)
        self.play(*self.state("build", OK, "success"), run_time=0.5)
        self.play(FadeIn(art, shift=UP * 0.15))
        self.packet([J["build"].get_bottom() + DOWN * 0.45, [J["build"].get_center()[0], art.get_center()[1], 0],
                     art.get_left()], color=INFO, run_time=0.6)

        self.caption("Jobs are separate VMs: scan downloads the tarball, loads it, and runs Trivy.", wait=0.2)
        self.packet([art.get_top(), J["scan"].get_bottom() + DOWN * 0.45], color=INFO, run_time=0.5)
        self.play(*self.state("scan", WARN, "running"), run_time=0.4)
        self.play(*self.state("scan", OK, "success"), run_time=0.4)
        self.caption("kind-integration side-loads the same image, deploys it, and probes /ready.", wait=0.2)
        self.packet([art.get_right(), [J["kind"].get_center()[0], art.get_center()[1], 0],
                     J["kind"].get_bottom() + DOWN * 0.45], color=INFO, run_time=0.6)
        self.play(*self.state("kind", WARN, "running"), run_time=0.4)
        self.play(*self.state("kind", OK, "success"), run_time=0.4)

        ghcr = mono("ghcr.io/<you>/reliability-api:<git-sha>", 19, OK)
        gbg = SurroundingRectangle(ghcr, color=OK, buff=0.15, corner_radius=0.1, stroke_width=2)
        gg = VGroup(gbg, ghcr).move_to(RIGHT * 3.6 + DOWN * 2.35)
        self.caption("publish (main only) pushes those tested bytes, tagged with the full git SHA.", wait=0.2)
        self.play(*self.state("pub", WARN, "running"), run_time=0.4)
        self.packet([J["pub"].get_bottom() + DOWN * 0.45, [J["pub"].get_center()[0], gg.get_top()[1] + 0.05, 0]],
                    color=OK, run_time=0.5)
        self.play(*self.state("pub", OK, "success"), FadeIn(gg, shift=UP * 0.15), run_time=0.6)
        self.wait(0.6)
        self.caption("Built once: the bytes that were scanned and integration-tested are the bytes pushed.",
                     wait=1.8)
        self.caption("On a pull request, publish's if: is false: it is skipped, so untested images never ship.",
                     wait=1.8)
        self.art, self.gg = art, gg

    # ----------------------------------------------------------- permissions
    def permissions(self):
        J = self.jobs
        top = VGroup(mono("permissions:", 20, ACCENT), mono("  contents: read", 20)).arrange(
            DOWN, aligned_edge=LEFT, buff=0.05)
        topbg = SurroundingRectangle(top, color=ACCENT, buff=0.15, corner_radius=0.1, stroke_width=1.5)
        topg = VGroup(topbg, top).move_to(LEFT * 3.6 + DOWN * 2.1)
        pubp = VGroup(mono("jobs.publish.permissions:", 20, OK), mono("  contents: read", 20), mono("  packages: write", 20, WARN)
                      ).arrange(DOWN, aligned_edge=LEFT, buff=0.05)
        pubbg = SurroundingRectangle(pubp, color=OK, buff=0.15, corner_radius=0.1, stroke_width=1.5)
        pubg = VGroup(pubbg, pubp).move_to(RIGHT * 3.9 + DOWN * 2.0)

        self.caption("Least privilege: workflow-level permissions give every job contents: read only.", wait=0.2)
        self.play(FadeOut(self.art), FadeOut(self.gg))
        self.play(FadeIn(topg, shift=UP * 0.15))
        self.wait(0.8)
        self.caption("Only publish adds packages: write, to push to GHCR. Unlisted scopes become none.",
                     wait=0.2)
        self.play(FadeIn(pubg, shift=UP * 0.15), Indicate(J["pub"][0], color=WARN))
        self.wait(1.2)
        self.caption("The token is created at job start and expires when the job ends.", wait=1.6)
        self.play(FadeOut(topg), FadeOut(pubg))

    # ----------------------------------------------------------- failing run
    def failing_run(self):
        J = self.jobs
        reset = []
        for k in self.specs:
            reset += self.state(k, MUTED, "queued")
        self.caption("Next push: a unit test fails on Python 3.13.", wait=0.2, color=TEXT_C)
        self.play(*reset, run_time=0.6)
        self.play(*self.state("t12", WARN, "running"), *self.state("t13", WARN, "running"), run_time=0.5)
        self.wait(0.3)
        self.play(*self.state("t13", BAD, "failed: pytest exit 1"), run_time=0.6)
        self.play(Indicate(J["t13"][0], color=BAD), run_time=0.6)
        self.caption("fail-fast: true cancels the still-running py3.12 leg.", wait=0.2)
        self.play(*self.state("t12", GREY, "cancelled"), run_time=0.6)
        self.wait(0.6)
        self.caption("build needs test, which failed, so build, scan, kind-integration and publish are skipped.",
                     wait=0.2)
        for k in ("build", "scan", "kind", "pub"):
            self.play(*self.state(k, GREY, "skipped"), run_time=0.35)
        note = label("No image was built, scanned, deployed or pushed.", 20, MUTED).move_to(DOWN * 2.1)
        self.play(FadeIn(note))
        self.caption("You get the earliest, cheapest red signal. Read it with gh run view --log-failed.",
                     wait=1.8)
