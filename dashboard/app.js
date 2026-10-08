// CS-IRCFS planner dashboard. Shared API/session/language helpers live in shared.js (window.CS).
const { apiFetch, apiJson, escapeHtml, toast, t } = window.CS;
const $ = (selector) => document.querySelector(selector);
const BUGESERA_VIEW = { center: [-2.28, 30.15], zoom: 10, features: [] };
const REFRESH_MS = 15000;

let mode = "demo";
let refreshTimer = null;
let liveMap;
let bugeseraBoundaryLayer;
let heatLayer = null;
let currentMapData = null;
let queueFilter = "all";
let openRecord = null; // { kind: "case" | "feedback", id, item }
const cache = {};
// Citizen Science Monitors see the same live data read-only; acting on it stays with planners.
const PLANNER_ROLES = ["district_officer", "district_planner", "administrator"];
const signedIn = CS.session.account();
const readOnly = Boolean(signedIn) && !PLANNER_ROLES.includes(signedIn.role);
const layers = {};

// Illustrative numbers so the story can be told before the API is connected.
const demo = {
  summary: { registered_farmers: 250, total_reports: 1250, active_schemes: 2, open_complaints: 35, faulty_or_offline_assets: 3, households_surveyed: 184, average_stunting_risk: 2.6, rewards_paid_rwf: 4800, field_messages: 312 },
  queue: [
    { item_type: "infrastructure", item_id: 21, priority: "critical", title: "PADAB Pumping Station 1 is offline", status: "open", scheme_id: 1, cell_id: 12, created_at: "2026-09-08T07:25:00", details: "Technical: motor overheats and trips after 20 minutes." },
    { item_type: "pest_or_disease", item_id: 47, priority: "critical", title: "Fall armyworm reported for Maize", status: "open", scheme_id: 2, cell_id: 19, created_at: "2026-09-08T06:40:00", details: "SMS keyword alert: NGERUKA NZANA 5." },
    { item_type: "infrastructure", item_id: 22, priority: "high", title: "APEFA solar pump - Mareba is faulty", status: "triaged", scheme_id: 2, cell_id: 31, created_at: "2026-09-07T15:10:00", details: "Two solar panels cracked; output reduced." },
    { item_type: "community_feedback", item_id: 58, priority: "medium", title: "Water Pricing", status: "open", scheme_id: 1, cell_id: 10, created_at: "2026-09-07T12:00:00", details: "The irrigation water fee doubled this season without explanation." }
  ],
  performance: [
    { scheme_id: 1, name: "PADAB", implementing_partner: "AfDB", hectares_developed: 650, target_tons: 140, target_source: "Demonstration value", expected_tons: 151, reported_tons: 98.4, basis: "reported", achievement_percent: 70.3, status: "watch", crop_reports: 64, pest_alerts: 3, infrastructure_faults: 5, open_grievances: 4, bottlenecks: { technical: 3, environmental: 1, social: 1 }, flagged_bottlenecks: ["technical"] },
    { scheme_id: 2, name: "APEFA Solar", implementing_partner: "APEFA", hectares_developed: null, target_tons: 75, target_source: "Demonstration value", expected_tons: 82, reported_tons: 69.1, basis: "reported", achievement_percent: 92.1, status: "on_track", crop_reports: 51, pest_alerts: 4, infrastructure_faults: 1, open_grievances: 2, bottlenecks: { technical: 1 }, flagged_bottlenecks: [] }
  ],
  health: { feedback_total: 53, feedback_resolved: 38, feedback_open: 15, resolution_rate: 72, median_days_to_resolve: 1.8, cases_total: 41, cases_resolved: 29, cases_notified: 22, close_loop_messages: 214, by_category: { "Water Pricing": 17, "Input Distribution": 14, "Resettlement/Downstream Impact": 9, "Operational Challenge": 8 } },
  schedule: [
    { sector_id: 1, sector: "Ngeruka", level: "irrigate_more", rainfall_mm_7d: 6.1, readings: 21, message_rw: "Inama: imvura yabaye nke (6.1 mm mu minsi 7). Ongera kuhira ho 10% muri iki cyumweru.", message_en: "Rainfall was low (6.1 mm in 7 days). Increase irrigation cycles by 10% this week." },
    { sector_id: 2, sector: "Mareba", level: "irrigate_more", rainfall_mm_7d: 7.7, readings: 21, message_rw: "Inama: imvura yabaye nke (7.7 mm mu minsi 7). Ongera kuhira ho 10% muri iki cyumweru.", message_en: "Rainfall was low (7.7 mm in 7 days). Increase irrigation cycles by 10% this week." },
    { sector_id: 3, sector: "Nyamata", level: "normal", rainfall_mm_7d: 22.0, readings: 21, message_rw: "Inama: imvura isanzwe (22 mm mu minsi 7). Komeza gahunda isanzwe yo kuhira.", message_en: "Rainfall is normal (22 mm in 7 days). Keep the usual irrigation schedule." }
  ],
  nutrition: { households: 184, average_risk: 2.6, high_risk_households: 31, one_meal_households: 18, food_insufficient: 52, by_cell: [{ cell: "Kagenge", households: 14, average_risk: 3.6, high_risk: 5 }, { cell: "Rango", households: 11, average_risk: 3.2, high_risk: 3 }, { cell: "Gihembe", households: 16, average_risk: 2.8, high_risk: 2 }, { cell: "Nyamata y'Umujyi", households: 19, average_risk: 2.1, high_risk: 1 }] },
  activity: { inbound: [
    { channel: "ussd", phone_number: "+250788550011", text: "2*2*1*5", reply: "END Murakoze! Raporo #47 ya Nzana yakiriwe. Abashinzwe ubuhinzi bamenyeshejwe.", record_type: "crop_report", created_at: "2026-09-08T06:40:00" },
    { channel: "sms", phone_number: "+250788550021", text: "IMVURA 0.5", reply: "Murakoze! Imvura 0.5 mm yanditswe. Wahawe 100 RWF y'itumanaho.", record_type: "irrigation_report", created_at: "2026-09-08T06:15:00" },
    { channel: "ussd", phone_number: "+250788550003", text: "5*2*Amafaranga y'amazi yikubye kabiri", reply: "END Murakoze. Ikibazo cyawe FB-058 cyakiriwe.", record_type: "community_feedback", created_at: "2026-09-07T12:00:00" }
  ], outbound: [], rewards: [] }
};

const formatDate = (value) => new Intl.DateTimeFormat(CS.lang === "rw" ? "rw" : "en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
const humanize = (value) => String(value ?? "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const number = (value, digits = 0) => (value === null || value === undefined ? "–" : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }));

function setGreeting() {
  const hour = new Date().getHours();
  const key = hour < 12 ? "greet.morning" : hour < 17 ? "greet.afternoon" : "greet.evening";
  $("#greeting").dataset.i18n = key;
  $("#greeting").textContent = t(key);
  if (signedIn) {
    const name = $("#greet-name");
    delete name.dataset.i18n;
    name.textContent = (signedIn.full_name || signedIn.email).split(/[\s@]/)[0];
  }
}

function countUp(element, target, suffix = "") {
  const end = Number(target) || 0;
  const start = Number(String(element.dataset.value || 0)) || 0;
  element.dataset.value = end;
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches || start === end) { element.textContent = end.toLocaleString() + suffix; return; }
  const began = performance.now();
  const step = (now) => {
    const progress = Math.min(1, (now - began) / 700);
    element.textContent = Math.round(start + (end - start) * (1 - Math.pow(1 - progress, 3))).toLocaleString() + suffix;
    if (progress < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function showSummary(summary) {
  countUp($("#metric-farmers"), summary.registered_farmers);
  countUp($("#metric-reports"), summary.total_reports);
  countUp($("#metric-schemes"), summary.active_schemes);
  countUp($("#metric-complaints"), summary.open_complaints);
  countUp($("#metric-households"), summary.households_surveyed ?? 0);
  countUp($("#metric-rewards"), summary.rewards_paid_rwf ?? 0, " RWF");
  $("#metric-complaints-note").textContent = `${summary.faulty_or_offline_assets} asset report${summary.faulty_or_offline_assets === 1 ? "" : "s"} need attention`;
  $("#metric-households-note").textContent = summary.average_stunting_risk ? `Average stunting risk ${summary.average_stunting_risk} / 5` : "Collected through USSD option 6";
}

/* ---------- Act Now queue ---------- */
function showQueue(items) {
  cache.queue = items;
  const list = $("#act-now-list");
  $("#nav-alert-count").textContent = items.length;
  const counts = { all: items.length, infrastructure: 0, pest_or_disease: 0, community_feedback: 0 };
  items.forEach((item) => { counts[item.item_type] = (counts[item.item_type] || 0) + 1; });
  document.querySelectorAll("[data-queue-count]").forEach((badge) => { badge.textContent = counts[badge.dataset.queueCount] || 0; });
  if (!items.length) {
    list.innerHTML = '<div class="alert-row"><div class="alert-band medium"></div><div><h3>No urgent reports</h3><p>The current queue is clear.</p></div></div>';
    return;
  }
  const typeLabel = { infrastructure: "Infrastructure", pest_or_disease: "Pest / disease", community_feedback: "Community feedback" };
  list.innerHTML = items.map((item, index) => `
    <article class="alert-row" data-scheme="${item.scheme_id ?? "other"}" data-type="${escapeHtml(item.item_type)}">
      <div class="alert-band ${escapeHtml(item.priority)}"></div>
      <div><p class="row-type">${escapeHtml(typeLabel[item.item_type] || item.item_type)}</p><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.details || "No additional details provided.")}</p></div>
      <div class="alert-meta"><span class="priority ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span><br />${escapeHtml(humanize(item.status))} · ${formatDate(item.created_at)}<br /><button type="button" class="case-open secondary-button" data-index="${index}">${escapeHtml(t("btn.open"))} →</button></div>
    </article>`).join("");
  applyQueueFilters();
}

const QUEUE_PREVIEW = 6;
let queueExpanded = false;

function applyQueueFilters() {
  const scheme = $("#scheme-filter").value;
  let shown = 0;
  let matching = 0;
  document.querySelectorAll("#act-now-list .alert-row[data-type]").forEach((row) => {
    const match = !((scheme !== "all" && row.dataset.scheme !== scheme) || (queueFilter !== "all" && row.dataset.type !== queueFilter));
    matching += match ? 1 : 0;
    row.hidden = !match || (!queueExpanded && shown >= QUEUE_PREVIEW);
    if (!row.hidden) shown += 1;
  });
  $("#act-now-list .show-more")?.remove();
  if (matching > QUEUE_PREVIEW) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button show-more";
    button.textContent = queueExpanded ? "Show fewer" : `Show all ${matching} items`;
    button.addEventListener("click", () => { queueExpanded = !queueExpanded; applyQueueFilters(); });
    $("#act-now-list").append(button);
  }
}

/* ---------- Scheme performance (Objectives 1-2) ---------- */
const STATUS_LABEL = { on_track: "On track", watch: "Watch", below_target: "Below target", no_target: "Target needed", no_data: "No harvest data" };

function renderPerformance(rows) {
  cache.performance = rows;
  const scheme = $("#scheme-filter").value;
  const visible = rows.filter((row) => scheme === "all" || String(row.scheme_id) === scheme);
  const host = $("#scheme-performance");
  if (!visible.length) {
    host.innerHTML = '<div class="empty-insight"><span>▤</span><div><strong>No schemes yet</strong><p>Add PADAB and APEFA Solar in Platform Management to start outcome verification.</p></div></div>';
    return;
  }
  host.innerHTML = visible.map((row) => {
    const achieved = row.basis === "reported" ? row.reported_tons : row.expected_tons;
    const scale = Math.max(row.target_tons || 0, achieved || 0) * 1.15 || 1;
    const fill = Math.min(100, ((achieved || 0) / scale) * 100);
    const marker = row.target_tons ? (row.target_tons / scale) * 100 : null;
    const bottlenecks = Object.entries(row.bottlenecks || {});
    const maxBottleneck = Math.max(1, ...bottlenecks.map(([, n]) => n));
    return `<div class="perf-card status-${escapeHtml(row.status)}">
      <div class="perf-head">
        <div><strong>${escapeHtml(row.name)}</strong><small>${escapeHtml([row.implementing_partner, row.hectares_developed ? `${number(row.hectares_developed)} ha` : null].filter(Boolean).join(" · ") || "Details to verify")}${row.is_active === false ? " · reference only" : ""}</small></div>
        <span class="status-chip ${escapeHtml(row.status)}">${escapeHtml(STATUS_LABEL[row.status] || row.status)}</span>
      </div>
      ${row.target_tons ? `
      <div class="bar-label"><span>${row.basis === "reported" ? "Reported harvest" : "Forecast harvest"} <b>${number(achieved, 1)} t</b></span><span>Target <b>${number(row.target_tons, 1)} t</b> · <b>${number(row.achievement_percent, 1)}%</b></span></div>
      <div class="track big" role="img" aria-label="${escapeHtml(`${row.name}: ${number(achieved, 1)} of ${number(row.target_tons, 1)} tons`)}"><div class="fill ${escapeHtml(row.status)}" style="width:${fill}%"></div><span class="target" style="left:${marker}%"></span></div>
      <p class="perf-source">Target source: ${escapeHtml(row.target_source || "not recorded")}</p>`
      : `<p class="perf-missing">Forecast so far: <b>${number(row.expected_tons, 1)} t</b>. Add the feasibility-study yield target in <a href="management.html">Platform Management → Irrigation schemes</a> to verify this outcome.</p>`}
      <div class="perf-stats"><span><b>${number(row.crop_reports)}</b> crop reports</span><span><b>${number(row.pest_alerts)}</b> pest alerts</span><span><b>${number(row.infrastructure_faults)}</b> asset faults</span><span><b>${number(row.open_grievances)}</b> open grievances</span></div>
      ${bottlenecks.length ? `<div class="bottlenecks"><p class="mini-title">Bottlenecks reported (90 days)</p>${bottlenecks.map(([name, n]) => `<div class="bn-row ${row.flagged_bottlenecks.includes(name) ? "flagged" : ""}"><span>${escapeHtml(humanize(name))}${row.flagged_bottlenecks.includes(name) ? " ⚑" : ""}</span><i style="width:${(n / maxBottleneck) * 100}%"></i><b>${n}</b></div>`).join("")}
      ${row.flagged_bottlenecks.length ? `<p class="flag-note">⚑ Auto-flagged: recurring ${escapeHtml(row.flagged_bottlenecks.join(", "))} bottleneck. Review before the next season.</p>` : ""}</div>` : ""}
    </div>`;
  }).join("");
}

/* ---------- Response health (Module 3) ---------- */
function renderHealth(health) {
  cache.health = health;
  const host = $("#response-health");
  if (!health.feedback_total && !health.cases_total) {
    host.innerHTML = '<div class="empty-insight compact-empty"><span>✉</span><div><strong>No feedback cases yet</strong><p>Grievances sent by USSD option 5 or SMS IKIBAZO will appear here.</p></div></div>';
    return;
  }
  const rate = health.resolution_rate ?? 0;
  const categories = Object.entries(health.by_category || {}).slice(0, 4);
  host.innerHTML = `
    <div class="ring" style="--rate:${rate}%"><span><b>${rate}%</b><small>grievances resolved</small></span></div>
    <div class="response-stats"><span><b>${health.median_days_to_resolve ?? "–"}</b>median days</span><span><b>${number(health.feedback_open)}</b>still open</span><span><b>${number(health.close_loop_messages)}</b>loop-closing SMS</span></div>
    <div class="category-list">${categories.map(([name, n]) => `<div><span>${escapeHtml(name)}</span><b>${n}</b></div>`).join("")}</div>
    <p class="data-note">${number(health.cases_resolved)} of ${number(health.cases_total)} crop/infrastructure cases resolved · ${number(health.cases_notified)} communities notified.</p>`;
}

/* ---------- Irrigation Scheduling Assistant ---------- */
const ADVICE_LABEL = { irrigate_more: ["Irrigate more", "Ongera kuhira"], normal: ["Normal schedule", "Gahunda isanzwe"], reduce: ["Reduce irrigation", "Gabanya kuhira"], no_data: ["No readings", "Nta bipimo"] };

function renderAdvice(rows) {
  cache.schedule = rows;
  const order = { irrigate_more: 0, reduce: 1, normal: 2, no_data: 3 };
  const withData = rows.filter((row) => row.level !== "no_data").sort((a, b) => order[a.level] - order[b.level]);
  const missing = rows.length - withData.length;
  const forecasts = rows.filter((row) => row.level === "no_data" && row.forecast_mm_7d != null).map((row) => row.forecast_mm_7d);
  const forecastRange = forecasts.length ? ` Forecast for them: ${number(Math.min(...forecasts), 0)}–${number(Math.max(...forecasts), 0)} mm over the next 7 days.` : "";
  const host = $("#advice-list");
  host.innerHTML = withData.length
    ? withData.map((row) => `<div class="advice-row level-${row.level}">
        <div class="advice-rain"><b>${number(row.rainfall_mm_7d, 1)}</b><small>mm / 7 days</small></div>
        <div><strong>${escapeHtml(row.sector)}</strong> <span class="level-chip ${row.level}">${escapeHtml(ADVICE_LABEL[row.level][CS.lang === "rw" ? 1 : 0])}</span><p>${escapeHtml(CS.lang === "rw" ? row.message_rw : row.message_en)}</p><small>${row.readings} gauge reading${row.readings === 1 ? "" : "s"}${row.forecast_mm_7d != null ? ` · forecast ${number(row.forecast_mm_7d, 1)} mm next 7 days` : ""}</small></div>
      </div>`).join("") + (missing ? `<p class="data-note">${missing} sector${missing === 1 ? "" : "s"} without rain-gauge readings this week.${forecastRange}</p>` : "")
    : '<div class="empty-insight"><span>☂</span><div><strong>No rain-gauge readings this week</strong><p>Cooperative leaders text IMVURA &lt;mm&gt; or use USSD option 3.${escapeHtml(forecastRange)}</p></div></div>';
  $("#send-advice").disabled = !withData.length;
}

/* ---------- Household nutrition ---------- */
function renderFood(data) {
  cache.nutrition = data;
  const host = $("#food-summary");
  if (!data.households) {
    host.innerHTML = '<div class="empty-insight"><span>♥</span><div><strong>No household surveys yet</strong><p>Households answer three questions through USSD option 6.</p></div></div>';
    return;
  }
  const level = data.average_risk >= 3.5 ? "high" : data.average_risk >= 2.5 ? "medium" : "low";
  host.innerHTML = `
    <div class="food-top">
      <div class="risk-gauge ${level}" style="--risk:${(data.average_risk / 5) * 100}%"><b>${data.average_risk}</b><small>average risk (1–5)</small></div>
      <div class="food-stats"><span><b>${number(data.households)}</b> households</span><span class="warn"><b>${number(data.high_risk_households)}</b> high risk (4–5)</span><span><b>${number(data.one_meal_households)}</b> ate once a day</span><span><b>${number(data.food_insufficient)}</b> short of food until harvest</span></div>
    </div>
    <p class="mini-title">Cells needing attention</p>
    ${data.by_cell.slice(0, 5).map((row) => `<div class="cell-risk"><span>${escapeHtml(row.cell)}</span><i style="width:${(row.average_risk / 5) * 100}%" class="${row.average_risk >= 3.5 ? "high" : row.average_risk >= 2.5 ? "medium" : "low"}"></i><b>${row.average_risk}</b><small>${row.households} hh</small></div>`).join("")}`;
}

/* ---------- Field channel feed ---------- */
const RECORD_LABEL = { crop_report: "Crop report", irrigation_report: "Water report", community_feedback: "Grievance", nutrition_survey: "Nutrition survey" };

function renderFeed(activity) {
  cache.activity = activity;
  const items = [
    ...activity.inbound.map((m) => ({ ...m, kind: m.channel })),
    ...activity.outbound.filter((m) => m.purpose !== "auto_reply").map((m) => ({ ...m, kind: "out", text: m.message })),
    ...activity.rewards.map((r) => ({ ...r, kind: "reward", text: `${r.amount_rwf} RWF airtime — ${r.reason}` }))
  ].sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 10);
  const feed = $("#channel-feed");
  if (!items.length) { feed.innerHTML = `<li class="feed-empty">${escapeHtml(t("channels.empty"))}</li>`; return; }
  const icon = { ussd: "#", sms: "✉", out: "↗", reward: "₣" };
  const label = { ussd: "USSD *801#", sms: "SMS 8448", out: "SMS sent", reward: "Airtime reward" };
  feed.innerHTML = items.map((m) => `<li class="feed-item ${m.kind}">
    <span class="feed-icon">${icon[m.kind]}</span>
    <div><p><strong>${label[m.kind]}</strong> · ${escapeHtml(maskPhone(m.phone_number))}${m.purpose ? ` · ${escapeHtml(humanize(m.purpose))}` : ""}${m.record_type ? ` → <em>${escapeHtml(RECORD_LABEL[m.record_type] || m.record_type)}</em>` : ""}</p>
    <code>${escapeHtml(m.text || "")}</code>${m.reply ? `<small>${escapeHtml(m.reply.replace(/^(CON|END) /, ""))}</small>` : ""}</div>
    <time>${formatDate(m.created_at)}</time></li>`).join("");
}

const maskPhone = (phone) => String(phone || "").replace(/(\+?\d{6})\d{3}(\d{3})/, "$1•••$2");

/* ---------- Map ---------- */
function markerStyle(feature) {
  if (feature.feature_type === "scheme") return { color: "#ffffff", fillColor: "#167052" };
  if (feature.feature_type === "farmer") return { color: "#ffffff", fillColor: "#6b5ca5" };
  if (feature.feature_type === "crop") return { color: "#ffffff", fillColor: feature.status === "pest alert" ? "#c75248" : "#d59223" };
  if (feature.feature_type === "rainfall") return { color: "#ffffff", fillColor: "#2878a9" };
  return { color: "#ffffff", fillColor: feature.status === "offline" ? "#c75248" : feature.status === "faulty" ? "#e08a2c" : "#2f9e6e" };
}
const FEATURE_LAYER = { scheme: "schemes", irrigation: "infrastructure", crop: "crops", rainfall: "rain", farmer: "farmers" };

function ensureMap(center = BUGESERA_VIEW.center, zoom = BUGESERA_VIEW.zoom) {
  if (liveMap || !window.L) return;
  liveMap = L.map("map-canvas", { zoomControl: false, scrollWheelZoom: false }).setView(center, zoom);
  L.control.zoom({ position: "topright" }).addTo(liveMap);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", { attribution: "&copy; OpenStreetMap contributors", maxZoom: 19 }).addTo(liveMap);
  ["schemes", "infrastructure", "crops", "rain", "food", "farmers"].forEach((name) => { layers[name] = L.layerGroup(); });
  syncLayerVisibility();
  loadBugeseraBoundary();
}

async function loadBugeseraBoundary() {
  if (!liveMap || bugeseraBoundaryLayer) return;
  try {
    const boundary = await fetch("bugesera-boundary.geojson").then((response) => { if (!response.ok) throw new Error("Boundary unavailable"); return response.json(); });
    bugeseraBoundaryLayer = L.geoJSON(boundary, { style: { color: "#0d6b4f", weight: 3, opacity: 1, fillColor: "#3a9b72", fillOpacity: 0.08 } })
      .bindTooltip("Bugesera District", { permanent: true, direction: "center", className: "district-label" }).addTo(liveMap);
    try {
      const [sectorResponse, cellResponse] = await Promise.all([apiFetch("geography/sectors"), apiFetch("geography/cells")]);
      if (sectorResponse.ok) {
        const sectors = await sectorResponse.json();
        L.geoJSON(sectors.map((item) => ({ type: "Feature", properties: { name: item.name }, geometry: item.geometry })), { style: { color: "#167052", weight: 1, fillOpacity: 0.02 } }).bindTooltip((layer) => layer.feature.properties.name).addTo(liveMap);
      }
      if (cellResponse.ok) {
        const cells = await cellResponse.json();
        L.geoJSON(cells.map((item) => ({ type: "Feature", properties: { name: item.name }, geometry: item.geometry })), { style: { color: "#4d8aa3", weight: 0.5, fillOpacity: 0 } }).bindTooltip((layer) => layer.feature.properties.name).addTo(liveMap);
      }
    } catch (_) { /* sector and cell overlays need PostGIS; the district outline is enough without it */ }
    resetBugeseraView();
  } catch (_) {
    liveMap.setView([-2.20, 30.10], 10);
  }
}

function resetBugeseraView() {
  if (bugeseraBoundaryLayer) liveMap.fitBounds(bugeseraBoundaryLayer.getBounds(), { padding: [18, 18] });
  else liveMap?.setView([-2.20, 30.10], 10);
}

function renderMap(data) {
  currentMapData = data;
  ensureMap(data.center, data.zoom);
  const scheme = $("#scheme-filter").value;
  const visible = data.features.filter((feature) => scheme === "all" || feature.feature_type === "farmer" || String(feature.scheme_id) === scheme);
  const status = $("#map-status");
  status.classList.toggle("empty", visible.length === 0);
  status.textContent = visible.length === 0
    ? (mode === "live" ? "No mapped locations yet. Reports appear once they are linked to a cell or have coordinates." : "Connect live data to show schemes, reports, and farmers on the map. The base map shows Bugesera.")
    : `${visible.length} mapped location${visible.length === 1 ? "" : "s"}${scheme === "all" ? " across Bugesera" : " for this scheme"}. Use the layer chips to compare pests, rainfall, and nutrition risk.`;
  if (!liveMap) return;
  ["schemes", "infrastructure", "crops", "farmers"].forEach((name) => layers[name].clearLayers());
  layers.rain.eachLayer((layer) => { if (layer.options.gauge) layers.rain.removeLayer(layer); });
  visible.forEach((feature) => {
    const group = layers[FEATURE_LAYER[feature.feature_type] || "infrastructure"];
    const radius = feature.feature_type === "scheme" ? 10 : feature.feature_type === "rainfall" ? 4 : 7;
    L.circleMarker([feature.latitude, feature.longitude], { radius, weight: 2, fillOpacity: 0.9, gauge: feature.feature_type === "rainfall", ...markerStyle(feature) })
      .bindPopup(`<strong>${escapeHtml(feature.name)}</strong>${feature.status ? `<br />${escapeHtml(feature.status)}` : ""}${feature.details ? `<br /><small>${escapeHtml(feature.details)}</small>` : ""}`)
      .addTo(group);
  });
  window.setTimeout(() => liveMap.invalidateSize(), 0);
}

function renderAnalysisLayers({ heat = [], rain = [], food = [] }) {
  if (!liveMap) return;
  if (heatLayer) liveMap.removeLayer(heatLayer);
  heatLayer = null;
  if (window.L.heatLayer && heat.length) {
    heatLayer = L.heatLayer(heat.map((p) => [p.latitude, p.longitude, p.weight]), { radius: 30, blur: 22, maxZoom: 13, minOpacity: 0.35, gradient: { 0.3: "#f3d36b", 0.6: "#e08a2c", 0.9: "#c0392b" } });
  } else if (heat.length) {
    heatLayer = L.layerGroup(heat.map((p) => L.circle([p.latitude, p.longitude], { radius: 600 + p.weight * 900, color: "#c0392b", weight: 0, fillOpacity: 0.25 })));
  }
  layers.rain.eachLayer((layer) => { if (!layer.options.gauge) layers.rain.removeLayer(layer); });
  const rainColour = { irrigate_more: "#c75248", normal: "#2878a9", reduce: "#1f5f8b", no_data: "#9aa7a1" };
  rain.forEach((cell) => L.circle([cell.latitude, cell.longitude], { radius: 900, color: rainColour[cell.level], weight: 2, fillOpacity: 0.18 })
    .bindPopup(`<strong>${escapeHtml(cell.cell)}</strong><br />${cell.rainfall_mm} mm in 7 days (${cell.readings} readings)<br /><small>${cell.level === "irrigate_more" ? "Dry spell warning" : humanize(cell.level)}</small>`).addTo(layers.rain));
  layers.food.clearLayers();
  food.filter((row) => row.latitude !== null && row.latitude !== undefined).forEach((row) => L.circle([row.latitude, row.longitude], { radius: 500 + row.households * 120, color: row.average_risk >= 3.5 ? "#8e3b8a" : row.average_risk >= 2.5 ? "#b07cc6" : "#c9b6d6", weight: 1, fillOpacity: 0.35 })
    .bindPopup(`<strong>${escapeHtml(row.cell)}</strong><br />Average stunting risk ${row.average_risk} / 5<br />${row.households} households, ${row.high_risk} high risk`).addTo(layers.food));
  syncLayerVisibility();
}

function syncLayerVisibility() {
  if (!liveMap) return;
  document.querySelectorAll("[data-layer]").forEach((input) => {
    const layer = input.dataset.layer === "heat" ? heatLayer : layers[input.dataset.layer];
    if (!layer) return;
    if (input.checked) layer.addTo(liveMap); else liveMap.removeLayer(layer);
  });
}

async function loadMap() {
  if (mode !== "live") { renderMap(BUGESERA_VIEW); return; }
  try {
    const [mapData, heat, rain] = await Promise.all([apiJson("map-data"), apiJson("analytics/pest-heatmap"), apiJson("analytics/rainfall-map")]);
    renderMap(mapData);
    renderAnalysisLayers({ heat, rain, food: cache.nutrition?.by_cell || [] });
  } catch (_) {
    renderMap(BUGESERA_VIEW);
    $("#map-status").textContent = "Map data is unavailable right now. The base map shows Bugesera only.";
  }
}

/* ---------- Loading data ---------- */
function setMode(next) {
  mode = next;
  const badge = $("#data-mode");
  badge.dataset.i18n = next === "live" ? "data.live" : "data.demo";
  badge.textContent = t(badge.dataset.i18n);
  badge.classList.toggle("live", next === "live");
  $("#demo-banner").hidden = next === "live";
  $("#live-pulse").hidden = next !== "live";
  $("#load-live-data").hidden = next === "live";
  window.clearInterval(refreshTimer);
  if (next === "live") refreshTimer = window.setInterval(() => { if (!document.querySelector("dialog[open]") && !document.hidden) loadLive({ quiet: true }); }, REFRESH_MS);
}

function showDemo() {
  setMode("demo");
  window.CSTrends?.clear("Sign in to see month-by-month trends from the live database.");
  $("#scheme-filter").replaceChildren(new Option(t("top.allSchemes"), "all"), new Option("PADAB", "1"), new Option("APEFA Solar", "2"));
  $("#scheme-filter-help").hidden = true;
  showSummary(demo.summary);
  showQueue(demo.queue);
  renderPerformance(demo.performance);
  renderHealth(demo.health);
  renderAdvice(demo.schedule);
  renderFood(demo.nutrition);
  renderFeed(demo.activity);
  loadMap();
}

async function loadLive({ quiet = false } = {}) {
  const results = await Promise.allSettled([
    apiJson("analytics/dashboard-summary"), (readOnly ? Promise.resolve(null) : apiJson("analytics/act-now")), apiJson("irrigation-schemes"), apiJson("analytics/scheme-performance"),
    apiJson("analytics/response-health"), apiJson("advisory/irrigation-schedule"), apiJson("analytics/nutrition-summary"), apiJson("channels/activity?limit=15")
  ]);
  const [summary, queue, schemes, performance, health, schedule, nutrition, activity] = results.map((r) => (r.status === "fulfilled" ? r.value : null));
  if (!summary) throw results[0].reason;
  const previousQueue = cache.queue?.length;
  const filter = $("#scheme-filter");
  const selected = filter.value;
  if (schemes) {
    filter.replaceChildren(new Option(t("top.allSchemes"), "all"), ...schemes.map((scheme) => new Option(`${scheme.name}${scheme.is_active ? "" : " (reference)"}`, String(scheme.id))));
    filter.value = selected;
    if (filter.selectedIndex < 0) filter.value = "all";
    $("#scheme-filter-help").hidden = schemes.length > 0;
  }
  showSummary(summary);
  if (queue) showQueue(queue);
  if (performance) renderPerformance(performance);
  if (health) renderHealth(health);
  if (schedule) renderAdvice(schedule);
  if (nutrition) renderFood(nutrition);
  if (activity) renderFeed(activity);
  if (quiet && queue && previousQueue !== undefined && queue.length > previousQueue) toast(`${queue.length - previousQueue} new item${queue.length - previousQueue === 1 ? "" : "s"} in Act Now`, "warn");
  if (!quiet) { window.CSTrends?.load(); await loadMap(); }
}

async function connect({ interactive = false } = {}) {
  const button = $("#load-live-data");
  button.textContent = "Connecting…";
  try {
    try {
      await apiJson("analytics/dashboard-summary");
    } catch (error) {
      if (error.status === 403) throw error;
      if (error.status !== 401 || !interactive) throw error;
      // People sign in with their account; service API keys are for integrations, not the browser.
      if (CS.session.token()) { CS.session.clear(); toast("Your session expired. Please sign in again.", "warn"); }
      window.location.href = "login.html?next=planner.html";
      return;
    }
    setMode("live");
    await loadLive();
    if (interactive) toast("Live database connected", "success");
  } catch (error) {
    showDemo();
    button.textContent = t("data.connect");
    $("#data-mode").title = error.message;
    if (interactive) toast(error.status === 403 ? `${error.message}. Ask an administrator to give you the District Planner role.` : error.status === 401 ? "Sign in to see live data." : "The API is not reachable. Start the platform with start-local.ps1.", "error");
  }
}

/* ---------- Case and feedback dialog ---------- */
function openRecordDialog(item) {
  if (mode !== "live") { toast("Connect live data to manage cases. This is a demonstration item.", "warn"); return; }
  const kind = item.item_type === "community_feedback" ? "feedback" : "case";
  openRecord = { kind, id: item.item_id, item };
  const form = $("#case-form");
  form.reset();
  $("#case-kind").textContent = kind === "feedback" ? "COMMUNITY FEEDBACK" : item.item_type === "infrastructure" ? "INFRASTRUCTURE CASE" : "CROP RISK CASE";
  $("#case-title").textContent = kind === "feedback" ? `FB-${String(item.item_id).padStart(3, "0")} · ${item.title}` : `Case #${item.item_id} · ${item.title}`;
  $("#case-summary").textContent = `${item.details || ""} (${item.priority} priority, reported ${formatDate(item.created_at)})`;
  form.status.value = item.status === "open" ? "triaged" : item.status;
  form.assigned_to_user_id.value = item.assigned_to_user_id || "";
  $("#case-message").textContent = "";
  $("#notify-box").hidden = true;
  $("#case-notify").dataset.stage = "preview";
  $("#case-notify").querySelector("span").textContent = t("case.notify");
  loadHistory();
  $("#case-dialog").showModal();
  if (kind === "case") apiJson(`cases/${item.item_id}`).then((record) => { form.action_taken.value = record.action_taken || ""; }).catch(() => {});
}

async function loadHistory() {
  const path = openRecord.kind === "feedback" ? `feedback/${openRecord.id}/history` : `cases/${openRecord.id}/history`;
  try {
    const events = await apiJson(path);
    $("#case-history-wrap").hidden = !events.length;
    $("#case-history").innerHTML = events.map((event) => `<li>${formatDate(event.created_at)} · ${escapeHtml(humanize(event.previous_status || "new"))} → <b>${escapeHtml(humanize(event.new_status))}</b>${event.action_taken ? ` — ${escapeHtml(event.action_taken)}` : ""}</li>`).join("");
  } catch (_) { $("#case-history-wrap").hidden = true; }
}

$("#case-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = { status: form.get("status"), action_taken: form.get("action_taken") || null };
  if (form.get("assigned_to_user_id")) payload.assigned_to_user_id = Number(form.get("assigned_to_user_id"));
  if (form.get("due_at")) payload.due_at = new Date(form.get("due_at")).toISOString();
  try {
    await apiJson(openRecord.kind === "feedback" ? `feedback/${openRecord.id}` : `cases/${openRecord.id}`, { method: "PATCH", body: payload });
    openRecord.item.status = payload.status;
    $("#case-message").textContent = ["resolved", "closed"].includes(payload.status) ? "Saved. Now notify the community so they know what was done." : "Saved.";
    toast("Case updated", "success");
    loadHistory();
    loadLive({ quiet: true });
  } catch (error) { $("#case-message").textContent = error.message; }
});

$("#case-notify").addEventListener("click", async () => {
  const button = $("#case-notify");
  const base = openRecord.kind === "feedback" ? `feedback/${openRecord.id}` : `cases/${openRecord.id}`;
  const preview = button.dataset.stage !== "send";
  try {
    const result = await apiJson(`${base}/notify-cell`, { method: "POST", body: { preview } });
    $("#notify-box").hidden = false;
    $("#notify-preview").textContent = result.message;
    if (preview) {
      $("#notify-meta").textContent = `${result.recipients} registered ${result.recipients === 1 ? "person" : "people"} in ${result.cell}`;
      button.dataset.stage = "send";
      button.querySelector("span").textContent = `Send to ${result.recipients} ${result.recipients === 1 ? "person" : "people"}`;
      button.disabled = result.recipients === 0;
    } else {
      $("#notify-meta").textContent = `Sent to ${result.sent} people in ${result.cell}`;
      button.dataset.stage = "done";
      button.querySelector("span").textContent = "✓ Community notified";
      button.disabled = true;
      toast(`Closing-the-loop SMS sent to ${result.sent} people in ${result.cell}`, "success");
      loadLive({ quiet: true });
    }
  } catch (error) { $("#case-message").textContent = error.message; }
});

$("#case-cancel").addEventListener("click", () => { $("#case-dialog").close(); $("#case-notify").disabled = false; });

/* ---------- Advice broadcast ---------- */
$("#send-advice").addEventListener("click", async () => {
  if (mode !== "live") { toast("Connect live data to send advice. The rows above are demonstration values.", "warn"); return; }
  try {
    const preview = await apiJson("advisory/irrigation-schedule/send", { method: "POST", body: { preview: true } });
    $("#advice-preview").innerHTML = preview.sectors.map((row) => `<p class="dialog-note"><strong>${escapeHtml(row.sector)}</strong> · ${row.recipients} recipient${row.recipients === 1 ? "" : "s"}</p><div class="sms-preview">${escapeHtml(row.message_rw)}</div>`).join("") || "<p>No sector has rain-gauge readings this week.</p>";
    $("#advice-message").textContent = `${preview.total_recipients} SMS will be sent to cooperative leaders, monitors, and farmers in these sectors.`;
    $("#advice-confirm").disabled = preview.total_recipients === 0;
    $("#advice-dialog").showModal();
  } catch (error) { toast(error.message, "error"); }
});
$("#advice-cancel").addEventListener("click", () => $("#advice-dialog").close());
$("#advice-confirm").addEventListener("click", async () => {
  try {
    const result = await apiJson("advisory/irrigation-schedule/send", { method: "POST", body: { preview: false } });
    $("#advice-dialog").close();
    toast(`Irrigation advice sent to ${result.total_recipients} people`, "success");
    loadLive({ quiet: true });
  } catch (error) { $("#advice-message").textContent = error.message; }
});

/* ---------- Other interactions ---------- */
$("#load-live-data").addEventListener("click", () => connect({ interactive: true }));
$("#banner-connect").addEventListener("click", () => connect({ interactive: true }));
$("#map-reset-view").addEventListener("click", resetBugeseraView);
$("#refresh-queue").addEventListener("click", () => (mode === "live" ? loadLive().then(() => toast("Dashboard refreshed", "success")) : connect({ interactive: true })));
$("#scheme-filter").addEventListener("change", () => {
  applyQueueFilters();
  if (cache.performance) renderPerformance(cache.performance);
  if (currentMapData) renderMap(currentMapData);
});
document.querySelectorAll("[data-queue-filter]").forEach((chip) => chip.addEventListener("click", () => {
  queueFilter = chip.dataset.queueFilter;
  document.querySelectorAll("[data-queue-filter]").forEach((other) => other.classList.toggle("active", other === chip));
  applyQueueFilters();
}));
$("#act-now-list").addEventListener("click", (event) => {
  const button = event.target.closest(".case-open");
  if (button) openRecordDialog(cache.queue[Number(button.dataset.index)]);
});
document.querySelectorAll("[data-layer]").forEach((input) => input.addEventListener("change", syncLayerVisibility));
$("#phone-demo-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  try {
    const report = await apiJson("irrigation-reports", { method: "POST", body: payload });
    $("#phone-demo-message").textContent = `Report #${report.id} saved.${payload.operational_status !== "operational" ? " It is now in Act Now." : ""}`;
    if (mode !== "live") await connect(); else await loadLive();
  } catch (error) { $("#phone-demo-message").textContent = error.status ? error.message : "Could not save the report. Start the platform first."; }
});

// Highlight the sidebar link for the section on screen.
const navLinks = [...document.querySelectorAll('.nav-link[href^="#"]')];
const observer = new IntersectionObserver((entries) => {
  entries.filter((entry) => entry.isIntersecting).forEach((entry) => {
    navLinks.forEach((link) => link.classList.toggle("active", link.getAttribute("href") === `#${entry.target.id}`));
  });
}, { rootMargin: "-35% 0px -60% 0px" });
navLinks.forEach((link) => { const section = document.querySelector(link.getAttribute("href")); if (section) observer.observe(section); });

document.addEventListener("cs:lang", () => {
  setGreeting();
  if (cache.queue) showQueue(cache.queue);
  if (cache.schedule) renderAdvice(cache.schedule);
  if (cache.activity) renderFeed(cache.activity);
});

/* ---------- Presentation tour ---------- */
const TOUR = [
  { target: "#overview", title: "Citizens are the sensors", text: "Farmers, Citizen Science Monitors and cooperative leaders report from feature phones. These totals come straight from their USSD and SMS reports. Airtime rewards keep them reporting." },
  { target: "#channels", title: "No internet needed", text: "A farmer dials *801# or texts 8448. Africa's Talking forwards each step to our API, which stores it centrally and replies in Kinyarwanda. Open the phone simulator to try it live." },
  { target: "#act-now", title: "Automatic triage", text: "A severe pest report or an offline pump becomes a ranked case on its own. Planners assign an owner, record the action, and keep a full audit trail." },
  { target: "#schemes", title: "Outcome verification: Objectives 1 and 2", text: "Farmer-reported harvests are compared with each scheme's feasibility-study yield target. Bottlenecks that recur are flagged automatically, scheme by scheme." },
  { target: "#advice", title: "Irrigation Scheduling Assistant", text: "Rain-gauge readings from cooperative leaders become a seven-day rainfall picture per sector, and the advice goes out by SMS in Kinyarwanda." },
  { target: "#food", title: "Household nutrition", text: "Three USSD questions about meals, diet and food stocks give a stunting-risk score, so the district can see where food insecurity is growing." },
  { target: "#map", title: "Spatial intelligence", text: "Switch layers to compare pest hotspots, dry-spell warnings and nutrition risk across Bugesera's sectors and cells." },
  { target: "#feedback", title: "Closing the loop", text: "When a grievance is resolved, every registered person in the affected cell receives an SMS saying what was done. This builds trust and keeps reports coming." }
];
$("#start-tour").addEventListener("click", () => window.CSTour.start(TOUR));

/* ---------- Start ---------- */
document.body.classList.toggle("read-only", readOnly);
$("#role-note").hidden = !readOnly;
setGreeting();
showDemo();
connect();
