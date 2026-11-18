// Noted: steward mode and the replay scrubber. Everything works without this file;
// it only hides the answer until the reader has ruled, and draws the replay.

(() => {
  "use strict";

  const WEIGHT = {
    "NFA": 0, "Warning": 1, "Reprimand": 2, "Fine": 2.5, "5 s": 3.05, "10 s": 3.1,
    "Drive-thru": 4, "Grid drop": 4.05, "Stop-go": 4.5, "DSQ": 6,
  };
  const KEY = "noted:rulings";

  const store = {
    all() {
      try { return JSON.parse(localStorage.getItem(KEY) || "{}"); } catch { return {}; }
    },
    put(id, entry) {
      const all = store.all();
      all[id] = entry;
      try { localStorage.setItem(KEY, JSON.stringify(all)); } catch { /* private mode: keep going */ }
    },
  };

  function compare(mine, theirs) {
    const d = mine - theirs;
    if (Math.abs(d) < 0.5) return "same";
    return d > 0 ? "harsher" : "lighter";
  }

  // ------------------------------------------------------------ steward mode

  function steward(section) {
    const article = section.closest("[data-ruling]");
    const id = section.dataset.id;
    const answer = section.dataset.answer;
    const theirs = Number(section.dataset.weight || 0);
    const result = section.querySelector(".steward__result");
    const buttons = [...section.querySelectorAll("[data-choice]")];

    function reveal(choice) {
      article.classList.remove("is-ruling");
      article.classList.add("is-revealed");
      buttons.forEach((b) => {
        b.disabled = true;
        b.setAttribute("aria-pressed", String(b.dataset.choice === choice));
      });
      section.querySelector("[data-reveal]").hidden = true;
      if (choice) {
        const verdict = compare(WEIGHT[choice], theirs);
        const words = { same: "You ruled the same as the stewards.", harsher: "You were harsher than the stewards.", lighter: "You were more lenient than the stewards." };
        result.innerHTML = `You: <b>${choice}</b> · Stewards: <b>${answer}</b>. ${words[verdict]}`;
        result.dataset.verdict = verdict;
      } else {
        result.textContent = "You skipped this one.";
      }
    }

    const saved = store.all()[id];
    if (saved) { reveal(saved.choice); return; }
    article.classList.add("is-ruling");
    buttons.forEach((b) => b.addEventListener("click", () => {
      const choice = b.dataset.choice;
      store.put(id, { choice, theirs, verdict: compare(WEIGHT[choice], theirs), at: Date.now() });
      reveal(choice);
    }));
    section.querySelector("[data-reveal]").addEventListener("click", () => {
      store.put(id, { choice: null, theirs, at: Date.now() });
      reveal(null);
    });
  }

  function record(el) {
    const all = Object.values(store.all()).filter((r) => r.choice);
    if (!all.length) return;
    const n = (k) => all.filter((r) => r.verdict === k).length;
    const lean = n("harsher") > n("lighter") ? "harsher" : n("lighter") > n("harsher") ? "more lenient" : "level";
    el.hidden = false;
    el.innerHTML = `<b class="num">${all.length}</b> ruled · <b class="num">${n("same")}</b> same as the stewards · <b class="num">${n("harsher")}</b> harsher · <b class="num">${n("lighter")}</b> lighter. On balance you are <b>${lean}</b>.`;
  }

  // ------------------------------------------------------------ replay

  const SVG = "http://www.w3.org/2000/svg";

  function el(name, attrs = {}) {
    const node = document.createElementNS(SVG, name);
    for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
    return node;
  }

  function replay(stage) {
    const data = JSON.parse(stage.parentElement.querySelector(".replay__data").textContent);
    // Frame the corner: the box around where the cars went, at least 300 m across.
    // The track is drawn whole underneath and clipped by the frame.
    const seen = [].concat(...data.cars.map((c) => c.points.map((p) => [p[1], p[2]])));
    const xs = seen.map((p) => p[0]), ys = seen.map((p) => p[1]);
    const cx = (Math.min(...xs) + Math.max(...xs)) / 2, cy = (Math.min(...ys) + Math.max(...ys)) / 2;
    const half = Math.max(1500, (Math.max(...xs) - Math.min(...xs)) * 0.6, (Math.max(...ys) - Math.min(...ys)) * 0.6);
    const hw = half * 1.4, hh = half; // a little wider than tall
    const minX = cx - hw, minY = cy - hh, maxY = cy + hh;
    const flip = (y) => maxY - (y - minY); // OpenF1's y grows upwards
    const u = half / 100; // one unit of drawing size, so marks look the same at any zoom
    const svg = el("svg", { viewBox: `${minX} ${minY} ${2 * hw} ${2 * hh}`, class: "replay__svg", role: "img" });
    svg.setAttribute("aria-label", `Track outline with ${data.cars.length} car${data.cars.length > 1 ? "s" : ""}`);
    const d = data.track.map((p, i) => `${i ? "L" : "M"}${p[0]} ${flip(p[1])}`).join(" ") + " Z";
    svg.append(el("path", { d, class: "replay__track", "stroke-width": 5 * u }));

    const end = Math.max(...data.cars.map((c) => c.points[c.points.length - 1][0]));
    const cars = data.cars.map((c, k) => {
      const trail = el("polyline", { class: `replay__trail replay__trail--${k}`, "stroke-width": 2 * u });
      const dot = el("circle", { r: 3.2 * u, "stroke-width": u, class: `replay__car replay__car--${k}` });
      const label = el("text", { class: `replay__label replay__label--${k}`, "font-size": 7 * u, "stroke-width": 1.6 * u });
      label.textContent = c.name ? c.name.split(" ").pop().slice(0, 3).toUpperCase() : `#${c.number}`;
      svg.append(trail, dot, label);
      return { c, trail, dot, label };
    });

    const controls = document.createElement("div");
    controls.className = "replay__controls";
    controls.innerHTML = `
      <button type="button" class="replay__btn" data-step="-1" aria-label="Back one second">−1 s</button>
      <button type="button" class="replay__btn replay__play" aria-pressed="false">Play</button>
      <button type="button" class="replay__btn" data-step="1" aria-label="Forward one second">+1 s</button>
      <input class="replay__range" type="range" min="0" max="${end}" step="0.1" value="0" aria-label="Time">
      <output class="replay__t num">0.0 s</output>`;
    stage.append(svg, controls);
    const range = controls.querySelector(".replay__range");
    const out = controls.querySelector(".replay__t");
    const play = controls.querySelector(".replay__play");

    function at(points, t) {
      let i = points.findIndex((p) => p[0] >= t);
      if (i <= 0) i = i === 0 ? 0 : points.length - 1;
      return points[i];
    }

    function draw(t) {
      for (const [k, { c, trail, dot, label }] of cars.entries()) {
        const seen = c.points.filter((p) => p[0] <= t && p[0] >= t - 6);
        trail.setAttribute("points", seen.map((p) => `${p[1]},${flip(p[2])}`).join(" "));
        const p = at(c.points, t);
        dot.setAttribute("cx", p[1]); dot.setAttribute("cy", flip(p[2]));
        // first car labelled above its dot, the others below, so close cars stay legible
        label.setAttribute("x", p[1] + 5 * u); label.setAttribute("y", flip(p[2]) + (k ? 9 + 8 * (k - 1) : -4) * u);
      }
      out.textContent = `${Number(t).toFixed(1)} s`;
    }

    let timer = null;
    function stop() { clearInterval(timer); timer = null; play.textContent = "Play"; play.setAttribute("aria-pressed", "false"); }
    play.addEventListener("click", () => {
      if (timer) return stop();
      play.textContent = "Pause"; play.setAttribute("aria-pressed", "true");
      if (Number(range.value) >= end) range.value = 0;
      timer = setInterval(() => {
        const t = Math.min(end, Number(range.value) + 0.1);
        range.value = t; draw(t);
        if (t >= end) stop();
      }, 100);
    });
    controls.querySelectorAll("[data-step]").forEach((b) => b.addEventListener("click", () => {
      stop();
      const t = Math.max(0, Math.min(end, Number(range.value) + Number(b.dataset.step)));
      range.value = t; draw(t);
    }));
    range.addEventListener("input", () => { stop(); draw(Number(range.value)); });
    draw(0);
  }

  document.querySelectorAll("[data-steward]").forEach(steward);
  document.querySelectorAll("[data-record]").forEach(record);
  document.querySelectorAll("[data-replay]").forEach(replay);
})();
