/* Animated edition — generic diagram animator (no dependencies, Web Animations API).
 *
 * For every static diagram (<figure class="diagram"><svg>…</svg></figure>) it:
 *   1. builds the diagram in reading order (top→bottom, left→right): boxes and labels fade/rise in,
 *   2. draws connector lines like a pen stroke,
 *   3. then sends glowing "data" dots along every arrow so the direction of flow is visible.
 * Diagrams auto-play the first time they scroll into view; ▶ Replay and ⏸ Flow buttons are added.
 * Interactive widgets/steppers are left alone (they already animate themselves).
 * Respects prefers-reduced-motion: nothing auto-plays, buttons still work.
 */
(function () {
  const reduce = window.matchMedia && matchMedia("(prefers-reduced-motion: reduce)").matches;
  const NODE_TAGS = new Set(["rect", "circle", "ellipse", "polygon", "text", "image", "polyline"]);
  const SKIP_ANCESTORS = "defs, marker, clipPath, mask, pattern, title, desc";

  function isConnector(el) {
    if (el.tagName !== "path" && el.tagName !== "line") return false;
    const cls = el.getAttribute("class") || "";
    return /\bline\b/.test(cls) || el.hasAttribute("marker-end") || el.hasAttribute("marker-start");
  }
  function isDashed(el) {
    const cls = el.getAttribute("class") || "";
    if (/\bdash\b/.test(cls)) return true;
    const da = getComputedStyle(el).strokeDasharray;
    return da && da !== "none";
  }
  function flowColor(el) {
    const cls = el.getAttribute("class") || "";
    if (/\bbad\b/.test(cls)) return "var(--bad)";
    if (/\bok\b/.test(cls)) return "var(--ok)";
    if (/\baccent\b/.test(cls)) return "var(--accent)";
    return "var(--warn)";
  }
  function bbox(el) {
    try { return el.getBBox(); } catch (e) { return { x: 0, y: 0, width: 0, height: 0 }; }
  }

  function prepare(fig) {
    const svg = fig.querySelector("svg");
    if (!svg || fig.closest(".widget") || svg.closest(".widget")) return null;
    const all = Array.from(svg.querySelectorAll("*")).filter(el => !el.closest(SKIP_ANCESTORS));
    const nodes = [], connectors = [];
    all.forEach(el => {
      if (isConnector(el)) connectors.push(el);
      else if (NODE_TAGS.has(el.tagName) || (el.tagName === "path" && !el.closest("a, g[data-skip]"))) nodes.push(el);
    });
    if (nodes.length + connectors.length < 3) return null;

    const vb = svg.viewBox && svg.viewBox.baseVal && svg.viewBox.baseVal.height ? svg.viewBox.baseVal : { height: 400 };
    const row = Math.max(18, vb.height / 14);
    const key = el => { const b = bbox(el); return [Math.round((b.y + b.height / 2) / row), b.x]; };
    const sortFn = (a, b) => { const ka = key(a), kb = key(b); return ka[0] - kb[0] || ka[1] - kb[1]; };
    nodes.sort(sortFn);
    connectors.sort(sortFn);

    const state = { fig, svg, nodes, connectors, flows: [], raf: 0, flowing: false, played: false, visible: false };

    // toolbar
    const bar = document.createElement("div");
    bar.className = "anim-bar";
    bar.innerHTML = '<button class="btn primary" type="button" data-a="play">▶ Replay build</button>' +
      '<button class="btn" type="button" data-a="flow">⏸ Pause flow</button>' +
      '<span class="hint">animated: build order → connections → data flow</span>';
    const cap = fig.querySelector("figcaption");
    cap ? fig.insertBefore(bar, cap) : fig.appendChild(bar);
    const badge = document.createElement("span");
    badge.className = "anim-badge";
    badge.textContent = "animated";
    fig.appendChild(badge);
    fig.classList.add("anim-ready");
    const flowBtn = bar.querySelector('[data-a="flow"]');
    bar.querySelector('[data-a="play"]').addEventListener("click", () => play(state));
    flowBtn.addEventListener("click", () => {
      if (state.flowing) { stopFlow(state); flowBtn.textContent = "▶ Resume flow"; }
      else { startFlow(state); flowBtn.textContent = "⏸ Pause flow"; }
    });
    state.flowBtn = flowBtn;
    return state;
  }

  function play(state) {
    stopFlow(state);
    state.played = true;
    const { nodes, connectors } = state;
    const nodeStep = Math.min(70, 2200 / Math.max(1, nodes.length));
    nodes.forEach((el, i) => {
      const final = getComputedStyle(el).opacity || "1";
      const frames = el.hasAttribute("transform")
        ? [{ opacity: 0 }, { opacity: final }]
        : [{ opacity: 0, transform: "translateY(6px)" }, { opacity: final, transform: "translateY(0)" }];
      el.animate(frames, { duration: 420, delay: i * nodeStep, easing: "cubic-bezier(.2,.7,.2,1)", fill: "backwards" });
    });
    const start = nodes.length * nodeStep + 150;
    const connStep = Math.min(120, 1800 / Math.max(1, connectors.length));
    connectors.forEach((el, i) => {
      const delay = start + i * connStep;
      if (isDashed(el) || typeof el.getTotalLength !== "function") {
        el.animate([{ opacity: 0 }, { opacity: getComputedStyle(el).opacity || 1 }], { duration: 400, delay, fill: "backwards" });
        return;
      }
      let len = 0;
      try { len = el.getTotalLength(); } catch (e) { len = 0; }
      if (!len) return;
      el.animate([
        { strokeDasharray: len + " " + len, strokeDashoffset: len, opacity: 0 },
        { strokeDasharray: len + " " + len, strokeDashoffset: len * 0.85, opacity: 1, offset: 0.12 },
        { strokeDasharray: len + " " + len, strokeDashoffset: 0, opacity: 1 },
      ], { duration: 650, delay, easing: "ease-in-out", fill: "backwards" });
    });
    const total = start + connectors.length * connStep + 700;
    clearTimeout(state.flowTimer);
    state.flowTimer = setTimeout(() => { if (state.visible) { startFlow(state); state.flowBtn.textContent = "⏸ Pause flow"; } }, total);
  }

  function startFlow(state) {
    if (state.flowing) return;
    const NS = "http://www.w3.org/2000/svg";
    let paths = state.connectors.filter(el => el.hasAttribute("marker-end") || el.hasAttribute("marker-start"));
    if (!paths.length) paths = state.connectors;
    paths = paths.slice(0, 14);
    state.flows = paths.map((el, i) => {
      let len = 0;
      try { len = el.getTotalLength(); } catch (e) { return null; }
      if (len < 12) return null;
      const glow = document.createElementNS(NS, "circle");
      const dot = document.createElementNS(NS, "circle");
      glow.setAttribute("r", "7"); dot.setAttribute("r", "3.6");
      glow.setAttribute("class", "anim-flow-glow"); dot.setAttribute("class", "anim-flow");
      const c = flowColor(el);
      glow.style.fill = c; dot.style.fill = c;
      // follow the connector's own transform context
      const parent = el.parentNode;
      parent.appendChild(glow); parent.appendChild(dot);
      const reverse = !el.hasAttribute("marker-end") && el.hasAttribute("marker-start");
      return { el, len, glow, dot, reverse, offset: (i * 0.37) % 1, speed: 110 + Math.min(80, len / 6) };
    }).filter(Boolean);
    state.flowing = true;
    state.svg.classList.add("anim-flowing");
    let last = performance.now();
    const tick = now => {
      const dt = Math.min(0.05, (now - last) / 1000); last = now;
      state.flows.forEach(f => {
        f.offset = (f.offset + (f.speed * dt) / (f.len + 60)) % 1;
        const along = f.offset * (f.len + 60);
        const visible = along <= f.len;
        const d = Math.min(along, f.len);
        let p;
        try { p = f.el.getPointAtLength(f.reverse ? f.len - d : d); } catch (e) { return; }
        f.dot.setAttribute("cx", p.x); f.dot.setAttribute("cy", p.y);
        f.glow.setAttribute("cx", p.x); f.glow.setAttribute("cy", p.y);
        const o = visible ? 1 : 0;
        f.dot.style.opacity = o; f.glow.style.opacity = o * 0.3;
      });
      state.raf = requestAnimationFrame(tick);
    };
    state.raf = requestAnimationFrame(tick);
  }

  function stopFlow(state) {
    cancelAnimationFrame(state.raf);
    state.flows.forEach(f => { f.dot.remove(); f.glow.remove(); });
    state.flows = [];
    state.flowing = false;
    state.svg.classList.remove("anim-flowing");
  }

  document.addEventListener("DOMContentLoaded", () => {
    const states = Array.from(document.querySelectorAll("figure.diagram")).map(prepare).filter(Boolean);
    if ("IntersectionObserver" in window) {
      const io = new IntersectionObserver(entries => {
        entries.forEach(e => {
          const st = states.find(s => s.fig === e.target);
          if (!st) return;
          st.visible = e.isIntersecting;
          if (e.isIntersecting) {
            if (!st.played && !reduce) play(st);
            else if (st.played && !st.flowing && st.flowBtn.textContent.startsWith("⏸") && !reduce) startFlow(st);
          } else if (st.flowing) {
            stopFlow(st); // save CPU when off-screen; resumes when visible again
          }
        });
      }, { threshold: 0.35 });
      states.forEach(s => io.observe(s.fig));
    }

    // gentle scroll reveal for content blocks
    if (!reduce && "IntersectionObserver" in window) {
      const blocks = document.querySelectorAll(".content > .callout, .content > .lab, .content > .table-wrap, .content > details.q, .content > .grid, .content > .widget, .content > pre, .module-list > .card");
      const ro = new IntersectionObserver(entries => {
        entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add("in"); ro.unobserve(e.target); } });
      }, { rootMargin: "0px 0px -8% 0px" });
      blocks.forEach(b => { b.classList.add("reveal"); ro.observe(b); });
    }
  });
})();
