"""Module 10 — Terraform: configuration vs state vs real world, the workflow, plan symbols, drift, remote state.
Facts follow notes/10-terraform.html (IaC / drift figure, core workflow table, Reading plans, State + GCS backend, Lab 2)."""
from common import *


def symbol_row(sym, text, risk, color, w=12.4):
    s = mono(sym, 26, color)
    s_slot = Rectangle(width=1.1, height=0.5, stroke_width=0).add(s)
    s.move_to(s_slot)
    t = label(text, 22)
    r = label(risk, 18, MUTED)
    row = VGroup(s_slot, t, r)
    s_slot.move_to(LEFT * (w / 2 - 0.6))
    t.next_to(s_slot, RIGHT, buff=0.3)
    r.move_to(RIGHT * (w / 2 - 0.1), aligned_edge=RIGHT).set_y(s_slot.get_y())
    t.set_y(s_slot.get_y())
    return row


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


def tip_arrow(a, b, color=MUTED, buff=0.06):
    return Arrow(a.get_right(), b.get_left(), buff=buff, color=color, stroke_width=3,
                 max_tip_length_to_length_ratio=0.4, max_stroke_width_to_length_ratio=8)


class M10Terraform(Explainer):
    MODULE = "Module 10"
    TITLE = "Terraform: config, state, reality"
    SUBTITLE = "init → plan → apply → destroy, plan symbols, drift and remote state"

    def construct(self):
        self.title_card()

        # ---------- three views ----------
        cfg = box("Configuration (.tf)", "what you WANT · in git", color=WARN, w=3.7, h=1.2).move_to(LEFT * 4.6 + UP * 1.9)
        st = box("State (tfstate)", "what Terraform last SAW / DID", color=INFO, w=3.7, h=1.2).move_to(UP * 1.9)
        real = box("Real world (APIs)", "what EXISTS", color=OK, w=3.7, h=1.2).move_to(RIGHT * 4.6 + UP * 1.9)
        v_cfg = mono('LOG_LEVEL = "info"', 18, WARN).next_to(cfg, DOWN, buff=0.2)
        v_st = mono('LOG_LEVEL = "info"', 18, INFO).next_to(st, DOWN, buff=0.2)
        v_real = mono('LOG_LEVEL = "info"', 18, OK).next_to(real, DOWN, buff=0.2)

        self.caption("Terraform keeps three views apart: configuration, state and the real world.", wait=0.3)
        self.play(LaggedStart(FadeIn(cfg, shift=UP * 0.2), FadeIn(st, shift=UP * 0.2), FadeIn(real, shift=UP * 0.2), lag_ratio=0.3), run_time=1.4)
        self.play(FadeIn(v_cfg), FadeIn(v_st), FadeIn(v_real), run_time=0.6)
        self.caption("Example: ConfigMap reliability-api-config in namespace reliability-tf on kind.", wait=1.6)
        self.caption("State binds each resource address to the real object it manages, plus its attributes.", wait=0.3)
        bind = DashedLine(st.get_right(), real.get_left(), color=INFO, stroke_width=2.5)
        self.play(Create(bind), Indicate(st[0], color=INFO), run_time=1.0)
        self.wait(1.2)

        # ---------- workflow ----------
        steps = [("write", "*.tf", MUTED), ("init", "providers, backend", ACCENT), ("plan", "read-only preview", WARN),
                 ("apply", "changes reality", OK), ("destroy", "= apply -destroy", BAD)]
        wf = VGroup(*[box(n, s, color=c, w=2.1, h=1.0, title_size=22, sub_size=15) for n, s, c in steps]).arrange(RIGHT, buff=0.62)
        wf.move_to(DOWN * 1.35)
        wf_arrows = VGroup(*[tip_arrow(wf[i], wf[i + 1]) for i in range(4)])
        self.caption("The core workflow: write → init → plan → apply → destroy.", wait=0.3)
        self.play(LaggedStart(*[FadeIn(b, shift=UP * 0.15) for b in wf], lag_ratio=0.2), Create(wf_arrows), run_time=1.6)
        self.wait(0.6)

        self.caption("init configures the backend, installs providers and records them in .terraform.lock.hcl.", wait=0.3)
        self.play(Indicate(wf[1][0], color=ACCENT), run_time=0.8)
        lock = mono(".terraform.lock.hcl", 16, ACCENT).next_to(wf[1], DOWN, buff=0.15)
        self.play(FadeIn(lock, shift=UP * 0.1), run_time=0.5)
        self.wait(1.0)

        self.caption("plan first refreshes: the provider reads every real object recorded in state.", wait=0.2)
        self.play(wf[2][0].animate.set_fill(WARN, opacity=0.35), run_time=0.4)
        self.packet([real.get_left() + DOWN * 0.25, st.get_right() + DOWN * 0.25], color=OK, run_time=1.0)
        self.caption("Then it diffs configuration against refreshed state and proposes actions.", wait=0.2)
        self.packet([cfg.get_right() + DOWN * 0.25, st.get_left() + DOWN * 0.25], color=WARN, run_time=1.0)
        res = mono("No changes. Your infrastructure matches the configuration.", 18, OK).next_to(wf, DOWN, buff=0.55)
        self.play(FadeIn(res, shift=UP * 0.1), run_time=0.6)
        self.wait(1.4)
        self.play(FadeOut(res), wf[2][0].animate.set_fill(WARN, opacity=0.12), run_time=0.4)

        self.caption("apply asks for approval, calls providers in graph order, writes state, then unlocks.", wait=0.3)
        self.play(Indicate(wf[3][0], color=OK), run_time=0.8)
        self.wait(0.8)
        self.caption("destroy removes every object managed in this state, not unmanaged ones.", wait=0.3)
        self.play(Indicate(wf[4][0], color=BAD), run_time=0.8)
        self.wait(0.8)

        # ---------- plan symbols ----------
        keep = VGroup(cfg, st, real, v_cfg, v_st, v_real, bind)
        self.play(FadeOut(VGroup(wf, wf_arrows, lock)), FadeOut(keep), run_time=0.6)
        head = label("Reading a plan: action symbols", 30, weight=BOLD).move_to(UP * 2.6)
        rows = VGroup(
            symbol_row("+", "create", "low (cost?)", OK),
            symbol_row("~", "update in-place", "usually low: read which fields", WARN),
            symbol_row("-/+", "destroy and then create replacement", "high: downtime, new IDs", BAD),
            symbol_row("-", "destroy", "high: data loss", BAD),
        ).arrange(DOWN, buff=0.38).next_to(head, DOWN, buff=0.5)
        self.caption("Each resource gets an action, shown with a symbol in the plan.", wait=0.2)
        self.play(FadeIn(head), run_time=0.5)
        for r in rows:
            self.play(FadeIn(r, shift=RIGHT * 0.2), run_time=0.55)
        summary = mono("Plan: 0 to add, 1 to change, 0 to destroy.", 20, TEXT_C).next_to(rows, DOWN, buff=0.45)
        self.play(FadeIn(summary), run_time=0.5)
        self.caption("Read the summary line first. An unexpected destroy count means stop.", wait=1.4)
        self.caption("-/+ appears when an argument can't be updated in place: look for # forces replacement.", wait=1.6)
        self.play(FadeOut(VGroup(head, rows, summary)), run_time=0.5)

        # ---------- drift ----------
        self.play(FadeIn(keep), run_time=0.6)
        self.caption("Drift: during an incident someone runs kubectl edit on the ConfigMap.", wait=0.3)
        oncall = box("on-call engineer", "kubectl edit", color=BAD, w=2.9, h=0.95, title_size=20).move_to(RIGHT * 4.6 + DOWN * 1.15)
        self.play(FadeIn(oncall, shift=UP * 0.2), run_time=0.5)
        self.packet([oncall.get_top(), v_real.get_bottom()], color=BAD, run_time=0.7)
        new_real = mono('LOG_LEVEL = "debug"', 18, BAD).move_to(v_real)
        self.play(Transform(v_real, new_real), Indicate(real[0], color=BAD), run_time=0.8)
        self.caption("Config and state still say info. Only the real object changed.", wait=1.4)

        self.caption("The next plan refreshes, notices the change and reports it before proposing actions.", wait=0.2)
        self.packet([real.get_left() + DOWN * 0.25, st.get_right() + DOWN * 0.25], color=BAD, run_time=1.0)
        note = mono("Note: Objects have changed outside of Terraform", 18, WARN)
        line = mono('~ "LOG_LEVEL" = "debug" -> "info"', 20, WARN)
        out = VGroup(note, line).arrange(DOWN, buff=0.18, aligned_edge=LEFT).move_to(LEFT * 2.2 + DOWN * 1.5)
        out_bg = SurroundingRectangle(out, color=WARN, buff=0.18, corner_radius=0.1, stroke_width=1.5, fill_color=SURFACE, fill_opacity=0.9)
        self.play(FadeIn(out_bg), FadeIn(note), run_time=0.6)
        self.play(FadeIn(line, shift=RIGHT * 0.2), run_time=0.6)
        self.caption("Applying this plan would revert the manual hotfix back to info.", wait=1.4)
        self.caption("Decide: apply to revert, or update the code until plan shows no changes.", wait=1.6)

        # ---------- state is sensitive: remote backend ----------
        self.play(FadeOut(VGroup(keep, oncall, out, out_bg)), run_time=0.6)
        self.caption("State holds every attribute a provider returns, including secrets. Treat it as a secret.", wait=0.3)
        local = zone(5.6, 3.6, "local backend (default)", color=BAD).move_to(LEFT * 3.5 + UP * 0.6)
        laptop = box("your laptop", "terraform.tfstate", color=MUTED, w=2.4, h=0.9, title_size=18).move_to(LEFT * 4.8 + UP * 1.0)
        mate = box("teammate", "own tfstate copy", color=MUTED, w=2.4, h=0.9, title_size=18).move_to(LEFT * 2.2 + UP * 1.0)
        cons = VGroup(label("✗ two truths, no locking", 18, BAD), label("✗ lost laptop = lost state", 18, BAD)).arrange(DOWN, buff=0.12, aligned_edge=LEFT).move_to(LEFT * 3.5 + DOWN * 0.45)
        self.play(Create(local[0]), FadeIn(local[1]), FadeIn(laptop), FadeIn(mate), run_time=0.9)
        self.play(FadeIn(cons), run_time=0.6)
        self.wait(0.8)

        remote = zone(5.9, 3.6, 'remote backend "gcs"', color=OK).move_to(RIGHT * 3.6 + UP * 0.6)
        bucket = box("GCS bucket", "versioning ON · IAM", color=OK, w=3.2, h=1.0).move_to(RIGHT * 3.6 + UP * 1.4)
        path = mono("reliability-lab/gke/default.tfstate", 15, OK).next_to(bucket, DOWN, buff=0.12)
        eng1 = box("you", None, color=ACCENT, w=1.3, h=0.6, title_size=18).move_to(RIGHT * 2.0 + DOWN * 0.55)
        eng2 = box("teammate", None, color=ACCENT, w=1.8, h=0.6, title_size=18).move_to(RIGHT * 4.6 + DOWN * 0.55)
        self.caption("Use a remote GCS backend: one source of truth, IAM-controlled, versioned.", wait=0.3)
        self.play(Create(remote[0]), FadeIn(remote[1]), FadeIn(bucket), FadeIn(path), run_time=0.9)
        self.play(FadeIn(eng1), FadeIn(eng2), run_time=0.5)

        self.caption("Writes take a state lock. A second apply gets 'Error acquiring the state lock'.", wait=0.2)
        self.packet([eng1.get_top(), bucket.get_bottom() + LEFT * 0.8], color=OK, run_time=0.8)
        lk = mono("lock\nheld", 15, WARN).next_to(bucket, RIGHT, buff=0.12)
        self.play(FadeIn(lk), run_time=0.4)
        dot_path = [eng2.get_top(), eng2.get_top() + UP * 0.45]
        self.packet(dot_path, color=BAD, run_time=0.5)
        err = mono("Error acquiring the state lock", 16, BAD).next_to(remote[0], DOWN, buff=0.15)
        self.play(FadeIn(err, shift=UP * 0.1), Indicate(eng2[0], color=BAD), run_time=0.7)
        self.wait(1.6)

        outro_lines(self, "Configuration is what you want, state is what Terraform saw.\nEvery plan shows the gap with reality. Read it before you apply.")
