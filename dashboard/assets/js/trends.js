// Month-by-month trend charts for the planner dashboard (window.CSTrends).
// Plain SVG: columns for single measures, two-series lines with a legend, a hover/keyboard
// readout on every chart, and a table view so no value depends on hovering.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  // CS-IRCFS palette: green and amber series, blue for rainfall, and quiet chart chrome.
  const C = { s1: "#138d58", s2: "#f5a43b", rain: "#2f8fd0", grid: "#e4ebe6", axis: "#cfdad3", muted: "#9aaba1", ink: "#18362b", ink2: "#52514e", surface: "#ffffff" };
  let gradientId = 0;

  // Vertical gradient for a column or an area fill; returns the url() to use as fill.
  function gradient(svg, color, topOpacity, bottomOpacity) {
    const defs = svg.querySelector("defs") || el("defs", {}, svg);
    const id = `trend-grad-${++gradientId}`;
    const grad = el("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
    el("stop", { offset: "0%", "stop-color": color, "stop-opacity": topOpacity }, grad);
    el("stop", { offset: "100%", "stop-color": color, "stop-opacity": bottomOpacity }, grad);
    return `url(#${id})`;
  }

  // Monotone cubic curve through the points: smooth, and never overshoots between months.
  function smoothPath(points) {
    const n = points.length;
    if (n < 2) return n ? `M${points[0][0]},${points[0][1]}` : "";
    const dx = [], slope = [], tangent = [];
    for (let i = 0; i < n - 1; i += 1) {
      dx[i] = points[i + 1][0] - points[i][0];
      slope[i] = (points[i + 1][1] - points[i][1]) / dx[i];
    }
    tangent[0] = slope[0];
    tangent[n - 1] = slope[n - 2];
    for (let i = 1; i < n - 1; i += 1) tangent[i] = slope[i - 1] * slope[i] <= 0 ? 0 : (slope[i - 1] + slope[i]) / 2;
    for (let i = 0; i < n - 1; i += 1) {
      if (slope[i] === 0) { tangent[i] = 0; tangent[i + 1] = 0; continue; }
      const a = tangent[i] / slope[i], b = tangent[i + 1] / slope[i], len = a * a + b * b;
      if (len > 9) { const k = 3 / Math.sqrt(len); tangent[i] = k * a * slope[i]; tangent[i + 1] = k * b * slope[i]; }
    }
    let d = `M${points[0][0]},${points[0][1]}`;
    for (let i = 0; i < n - 1; i += 1) {
      const [x0, y0] = points[i], [x1, y1] = points[i + 1], h = dx[i] / 3;
      d += `C${x0 + h},${y0 + tangent[i] * h} ${x1 - h},${y1 - tangent[i + 1] * h} ${x1},${y1}`;
    }
    return d;
  }
  const H = 210, M = { top: 14, right: 46, bottom: 26, left: 40 };
  let W = 520;  // set to the real chart width on each render, so text stays at its CSS size
  const fmt = (v, digits = 0) => (v === null || v === undefined ? "–" : Number(v).toLocaleString(undefined, { maximumFractionDigits: digits }));
  let data = null;

  function el(tag, attrs, parent) {
    const node = document.createElementNS(NS, tag);
    Object.entries(attrs).forEach(([key, value]) => node.setAttribute(key, value));
    if (parent) parent.append(node);
    return node;
  }

  function niceMax(value) {
    if (!(value > 0)) return 1;
    const power = 10 ** Math.floor(Math.log10(value));
    const n = value / power;
    return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * power;
  }

  // Axes, gridlines, month labels and a tooltip box. Returns scales for the marks.
  function frame(host, months, max) {
    host.replaceChildren();
    const svg = el("svg", { viewBox: `0 0 ${W} ${H}`, role: "img" }, host);
    const tip = document.createElement("div");
    tip.className = "trend-tip";
    tip.hidden = true;
    host.append(tip);
    const plotW = W - M.left - M.right, plotH = H - M.top - M.bottom;
    const band = plotW / months.length;
    const x = (i) => M.left + band * (i + 0.5);
    const y = (v) => M.top + plotH - (v / max) * plotH;
    [0, max / 2, max].forEach((tick, index) => {
      el("line", { x1: M.left, x2: W - M.right, y1: y(tick), y2: y(tick), stroke: index === 0 ? C.axis : C.grid, "stroke-width": 1, "stroke-dasharray": index === 0 ? "" : "4 5" }, svg);
      const label = el("text", { x: M.left - 6, y: y(tick) + 4, "text-anchor": "end", class: "trend-axis" }, svg);
      label.textContent = fmt(tick, tick < 10 && tick % 1 ? 1 : 0);
    });
    const every = W < 420 ? 3 : months.length > 8 ? 2 : 1;
    months.forEach((month, i) => {
      if ((months.length - 1 - i) % every) return;  // always label the latest month
      const label = el("text", { x: x(i), y: H - 8, "text-anchor": "middle", class: "trend-axis" }, svg);
      label.textContent = month.label.slice(0, 3);
    });
    return { svg, tip, x, y, band, plotTop: M.top, plotBottom: M.top + plotH };
  }

  function showTip(host, tip, xPos, title, lines) {
    tip.replaceChildren();
    const head = document.createElement("strong");
    head.textContent = title;
    tip.append(head);
    lines.forEach(({ value, label, color }) => {
      const row = document.createElement("div");
      if (color) {
        const key = document.createElement("i");
        key.style.background = color;
        row.append(key);
      }
      const b = document.createElement("b");
      b.textContent = value;
      row.append(b, document.createTextNode(` ${label}`));
      tip.append(row);
    });
    tip.hidden = false;
    const width = host.clientWidth;
    const px = (xPos / W) * width;
    tip.style.left = `${Math.min(Math.max(px - tip.offsetWidth / 2, 0), width - tip.offsetWidth)}px`;
  }

  function columns(host, months, key, unitLabel, digits = 0, color = C.s1) {
    const values = months.map((m) => m[key]);
    const f = frame(host, months, niceMax(Math.max(0, ...values.filter((v) => v !== null))));
    const width = Math.min(26, f.band * 0.62);
    const fill = gradient(f.svg, color, 1, 0.55);
    const latestFill = gradient(f.svg, color, 1, 0.9);
    const lastIndex = values.length - 1;
    values.forEach((v, i) => {
      const x0 = f.x(i) - width / 2, x1 = f.x(i) + width / 2;
      el("rect", { x: x0, y: f.plotTop, width, height: f.plotBottom - f.plotTop, rx: Math.min(8, width / 2), fill: "#f1f5f2" }, f.svg);
      if (v) {
        const top = f.y(v), base = f.plotBottom, r = Math.min(7, (base - top) / 2, width / 2);
        el("path", { d: `M${x0},${base}V${top + r}Q${x0},${top} ${x0 + r},${top}H${x1 - r}Q${x1},${top} ${x1},${top + r}V${base}Z`,
                     fill: i === lastIndex ? latestFill : fill, class: "trend-col", style: `animation-delay:${i * 35}ms` }, f.svg);
      }
      const hit = el("rect", { x: f.x(i) - f.band / 2, y: f.plotTop, width: f.band, height: f.plotBottom - f.plotTop, fill: "transparent", tabindex: 0,
                               "aria-label": `${months[i].label}: ${v === null ? "no data" : `${fmt(v, digits)} ${unitLabel}`}` }, f.svg);
      const show = () => showTip(host, f.tip, f.x(i), months[i].label, [{ value: v === null ? "No data" : fmt(v, digits), label: v === null ? "" : unitLabel }]);
      hit.addEventListener("pointermove", show);
      hit.addEventListener("focus", show);
      hit.addEventListener("pointerleave", () => { f.tip.hidden = true; });
      hit.addEventListener("blur", () => { f.tip.hidden = true; });
    });
    const last = values.length - 1;
    if (values[last] !== null) {
      const label = el("text", { x: f.x(last), y: f.y(values[last] || 0) - 6, "text-anchor": "middle", class: "trend-value" }, f.svg);
      label.textContent = fmt(values[last], digits);
    }
  }

  function lines(host, months, series, unitLabel, digits = 0) {
    const max = niceMax(Math.max(0, ...series.flatMap((s) => months.map((m) => m[s.key] || 0))));
    const legend = document.createElement("div");
    legend.className = "trend-legend";
    series.forEach((s) => {
      const item = document.createElement("span");
      const key = document.createElement("i");
      key.style.background = s.color;
      item.append(key, document.createTextNode(s.label));
      legend.append(item);
    });
    const f = frame(host, months, max);
    host.prepend(legend);
    const last = months.length - 1;
    const ends = series.map((s) => f.y(months[last][s.key] || 0));
    series.forEach((s, index) => {
      const points = months.map((m, i) => [f.x(i), f.y(m[s.key] || 0)]);
      const curve = smoothPath(points);
      el("path", { d: `${curve}L${points[last][0]},${f.plotBottom}L${points[0][0]},${f.plotBottom}Z`, fill: gradient(f.svg, s.color, index === 0 ? 0.28 : 0.2, 0), class: "trend-area" }, f.svg);
      el("path", { d: curve, fill: "none", stroke: s.color, "stroke-width": 2.6, "stroke-linejoin": "round", "stroke-linecap": "round", class: "trend-line", pathLength: 1 }, f.svg);
      points.forEach(([px, py], i) => {
        if (i !== last) el("circle", { cx: px, cy: py, r: 2.4, fill: C.surface, stroke: s.color, "stroke-width": 1.6 }, f.svg);
      });
      el("circle", { cx: f.x(last), cy: ends[index], r: 5, fill: s.color, stroke: C.surface, "stroke-width": 2.5 }, f.svg);
    });
    if (Math.abs(ends[0] - ends[1]) >= 14) {  // end labels only when they don't collide; legend + tooltip carry the rest
      series.forEach((s, index) => {
        const label = el("text", { x: f.x(last) + 8, y: ends[index] + 4, class: "trend-value" }, f.svg);
        label.textContent = fmt(months[last][s.key], digits);
      });
    }
    // Crosshair readout: snaps to the nearest month; arrow keys move it.
    const cross = el("line", { y1: f.plotTop, y2: f.plotBottom, stroke: C.muted, "stroke-width": 1, visibility: "hidden" }, f.svg);
    const dots = series.map((s) => el("circle", { r: 4, fill: s.color, stroke: C.surface, "stroke-width": 2, visibility: "hidden" }, f.svg));
    const overlay = el("rect", { x: M.left, y: f.plotTop, width: W - M.left - M.right, height: f.plotBottom - f.plotTop, fill: "transparent", tabindex: 0,
                                 "aria-label": `${series.map((s) => s.label).join(" and ")} by month. Use arrow keys to read values.` }, f.svg);
    let current = last;
    const show = (i) => {
      current = Math.max(0, Math.min(last, i));
      const cx = f.x(current);
      cross.setAttribute("x1", cx); cross.setAttribute("x2", cx); cross.setAttribute("visibility", "visible");
      series.forEach((s, index) => {
        dots[index].setAttribute("cx", cx); dots[index].setAttribute("cy", f.y(months[current][s.key] || 0)); dots[index].setAttribute("visibility", "visible");
      });
      showTip(host, f.tip, cx, months[current].label, series.map((s) => ({ value: fmt(months[current][s.key], digits), label: `${s.label}${unitLabel ? ` (${unitLabel})` : ""}`, color: s.color })));
    };
    const hide = () => { cross.setAttribute("visibility", "hidden"); dots.forEach((d) => d.setAttribute("visibility", "hidden")); f.tip.hidden = true; };
    overlay.addEventListener("pointermove", (event) => {
      const box = f.svg.getBoundingClientRect();
      const svgX = ((event.clientX - box.left) / box.width) * W;
      show(Math.round((svgX - M.left) / f.band - 0.5));
    });
    overlay.addEventListener("pointerleave", hide);
    overlay.addEventListener("focus", () => show(current));
    overlay.addEventListener("blur", hide);
    overlay.addEventListener("keydown", (event) => {
      if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); show(current + (event.key === "ArrowRight" ? 1 : -1)); }
    });
  }

  function renderTable() {
    const host = document.querySelector("#trends-table");
    if (!data) return;
    const cols = [["label", "Month"], ["reports", "Reports"], ["severe_pests", "Severe pests"], ["rainfall_mm", "Rain mm"], ["rain_readings", "Rain readings"],
                  ["asset_faults", "Asset faults"], ["cases_opened", "Cases opened"], ["cases_resolved", "Cases resolved"], ["expected_tons", "Expected t"],
                  ["reported_tons", "Reported t"], ["plantings", "Plantings"], ["grievances", "Grievances"], ["households", "Households"], ["average_risk", "Avg. risk"]];
    const table = document.createElement("table");
    table.className = "trend-table";
    const head = table.createTHead().insertRow();
    cols.forEach(([, label]) => { const th = document.createElement("th"); th.textContent = label; head.append(th); });
    const body = table.createTBody();
    [...data.months].reverse().forEach((m) => {
      const row = body.insertRow();
      cols.forEach(([key]) => { row.insertCell().textContent = key === "label" ? m.label : fmt(m[key], 1); });
    });
    host.replaceChildren(table);
  }

  let drawnOnce = false;
  function render() {
    if (!data) return;
    // Entrance animation on the first draw only; resizes and refreshes redraw without it.
    document.querySelector(".trend-grid")?.classList.toggle("trend-animate", !drawnOnce);
    drawnOnce = true;
    const months = data.months;
    W = Math.max(300, Math.round(document.querySelector("#trend-reports").clientWidth || 520));
    columns(document.querySelector("#trend-reports"), months, "reports", "reports");
    columns(document.querySelector("#trend-rain"), months, "rainfall_mm", "mm per gauge", 1, C.rain);
    lines(document.querySelector("#trend-cases"), months, [{ key: "cases_opened", label: "Opened", color: C.s1 }, { key: "cases_resolved", label: "Resolved", color: C.s2 }], "cases");
    lines(document.querySelector("#trend-harvest"), months, [{ key: "expected_tons", label: "Expected", color: C.s1 }, { key: "reported_tons", label: "Reported", color: C.s2 }], "t", 1);
    columns(document.querySelector("#trend-plantings"), months, "plantings", "planting updates", 0, C.s2);
    if (!document.querySelector("#trends-table").hidden) renderTable();
    document.querySelector("#trends-status").textContent = "";
  }

  async function load() {
    try {
      data = await window.CS.apiJson("analytics/trends?months=12");
      render();
      document.dispatchEvent(new CustomEvent("cs:trends", { detail: data }));
    } catch (error) {
      clear(error.status === 401 ? "Sign in to see month-by-month trends." : "Trends are not available right now.");
    }
  }

  function clear(message) {
    data = null;
    ["#trend-reports", "#trend-rain", "#trend-cases", "#trend-harvest", "#trend-plantings"].forEach((id) => document.querySelector(id)?.replaceChildren());
    document.querySelector("#trends-table")?.replaceChildren();
    const status = document.querySelector("#trends-status");
    if (status) status.textContent = message;
  }

  document.addEventListener("DOMContentLoaded", () => {
    const toggle = document.querySelector("#trends-table-toggle");
    toggle?.addEventListener("click", () => {
      const table = document.querySelector("#trends-table");
      table.hidden = !table.hidden;
      toggle.innerHTML = `<i class="bi bi-${table.hidden ? "table" : "graph-up"}" aria-hidden="true"></i> ${table.hidden ? "Show as table" : "Show charts"}`;
      if (!table.hidden) renderTable();
    });
    let resizeTimer;
    window.addEventListener("resize", () => { window.clearTimeout(resizeTimer); resizeTimer = window.setTimeout(render, 200); });
  });

  window.CSTrends = { load, clear };
})();
