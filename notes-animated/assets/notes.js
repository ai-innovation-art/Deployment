/* DevOps Notes — shared behaviour: theme toggle, TOC build + scrollspy, copy buttons, reading progress,
   step-through diagrams, module completion tracking. */
(function () {
  const store = {
    get(k) { try { return localStorage.getItem(k); } catch (e) { return null; } },
    set(k, v) { try { localStorage.setItem(k, v); } catch (e) { /* storage unavailable */ } },
  };

  // ---- theme ----
  const savedTheme = store.get("notes-theme");
  if (savedTheme) document.documentElement.setAttribute("data-theme", savedTheme);
  window.toggleTheme = function () {
    const cur = document.documentElement.getAttribute("data-theme") ||
      (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
    const next = cur === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", next);
    store.set("notes-theme", next);
  };

  document.addEventListener("DOMContentLoaded", function () {
    // ---- progress bar ----
    const bar = document.createElement("div");
    bar.className = "progress-bar";
    document.body.appendChild(bar);
    addEventListener("scroll", function () {
      const h = document.documentElement.scrollHeight - innerHeight;
      bar.style.width = (h > 0 ? (scrollY / h) * 100 : 0) + "%";
    }, { passive: true });

    // ---- auto TOC from h2/h3 in .content ----
    const tocList = document.querySelector(".toc ol");
    const heads = Array.from(document.querySelectorAll(".content h2, .content h3"));
    if (tocList && !tocList.children.length) {
      heads.forEach(function (h, i) {
        if (!h.id) h.id = "s-" + i + "-" + h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, "-").slice(0, 40);
        const li = document.createElement("li");
        if (h.tagName === "H3") li.className = "sub";
        const a = document.createElement("a");
        a.href = "#" + h.id;
        a.textContent = h.textContent;
        li.appendChild(a);
        tocList.appendChild(li);
      });
    }
    // scrollspy
    const links = tocList ? Array.from(tocList.querySelectorAll("a")) : [];
    if (links.length && "IntersectionObserver" in window) {
      const map = new Map(links.map(function (a) { return [a.getAttribute("href").slice(1), a]; }));
      const obs = new IntersectionObserver(function (entries) {
        entries.forEach(function (e) {
          if (e.isIntersecting) {
            links.forEach(function (l) { l.classList.remove("active"); });
            const a = map.get(e.target.id);
            if (a) a.classList.add("active");
          }
        });
      }, { rootMargin: "-70px 0px -70% 0px" });
      heads.forEach(function (h) { obs.observe(h); });
    }

    // ---- copy buttons ----
    document.querySelectorAll("pre").forEach(function (pre) {
      const b = document.createElement("button");
      b.className = "copy-btn";
      b.type = "button";
      b.textContent = "Copy";
      b.addEventListener("click", function () {
        const code = pre.querySelector("code") || pre;
        const text = code.innerText;
        (navigator.clipboard ? navigator.clipboard.writeText(text) : Promise.reject())
          .then(function () { b.textContent = "Copied"; })
          .catch(function () { b.textContent = "Select & copy"; })
          .finally(function () { setTimeout(function () { b.textContent = "Copy"; }, 1400); });
      });
      pre.appendChild(b);
    });

    // ---- steppers: <div class="widget stepper" data-steps='[{"title":"..","html":"..","show":["id1"]}]'> ----
    document.querySelectorAll(".stepper[data-steps]").forEach(function (w) {
      let steps;
      try { steps = JSON.parse(w.getAttribute("data-steps")); } catch (e) { return; }
      const stage = w.querySelector(".stage");
      const count = w.querySelector(".count");
      const svg = w.querySelector("svg");
      let i = 0;
      function render() {
        const s = steps[i];
        stage.innerHTML = "<strong>" + (i + 1) + ". " + s.title + "</strong><p>" + s.html + "</p>";
        count.textContent = (i + 1) + " / " + steps.length;
        if (svg) {
          svg.querySelectorAll("[data-step]").forEach(function (el) {
            const on = el.getAttribute("data-step").split(",").map(Number);
            el.style.opacity = on.indexOf(i) >= 0 ? "1" : "0.12";
            el.style.transition = "opacity .3s";
          });
        }
      }
      w.querySelector("[data-prev]").addEventListener("click", function () { i = Math.max(0, i - 1); render(); });
      w.querySelector("[data-next]").addEventListener("click", function () { i = Math.min(steps.length - 1, i + 1); render(); });
      render();
    });

    // ---- module completion (index + module pages) ----
    document.querySelectorAll("[data-done-key]").forEach(function (cb) {
      const key = "notes-done-" + cb.getAttribute("data-done-key");
      cb.checked = store.get(key) === "1";
      cb.addEventListener("change", function () {
        store.set(key, cb.checked ? "1" : "0");
        document.dispatchEvent(new CustomEvent("notes-progress"));
      });
    });
  });
})();
