// CS-IRCFS dashboard pages: planner.html (overview), act-now, channels, schemes, trends, advice, nutrition, map, feedback.
// Every page loads this one script; <body data-page> says which page it is, and only that page's data is fetched.
// Shared API/session/language helpers come from shared.js (window.CS); the sidebar, top bar and footer from app-shell.js.
// Every figure comes from the API: there is no demonstration data.
const { apiFetch, apiJson, escapeHtml, toast, t } = window.CS;
const $ = (selector) => document.querySelector(selector);
const on = (selector, event, handler) => $(selector)?.addEventListener(event, handler);
const page = document.body.dataset.page || "overview";
const BUGESERA_VIEW = { center: [-2.28, 30.15], zoom: 10, features: [] };
const REFRESH_MS = 15000;
const SCHEME_KEY = "cs_ircfs_scheme";

// Connection state: "connecting", "live", "signed-out", "forbidden" or "offline".
let mode = "connecting";
let refreshTimer = null;
let liveMap;
let currentMapData = null;
let queueFilter = "all";
let feedbackFilter = "open";
let feedFilter = "all";
let openRecord = null; // { kind: "case" | "feedback", id, item }
const cache = {};
// Citizen Science Monitors see the same live data read-only; acting on it stays with planners.
const PLANNER_ROLES = ["district_officer", "district_planner", "administrator"];
const signedIn = CS.session.account();
const readOnly = Boolean(signedIn) && !PLANNER_ROLES.includes(signedIn.role);
// Adding and editing schemes is for administrators (local development without sign-in also acts as one).
const canAdminister = !signedIn || signedIn.role === "administrator";

// What each page needs from the API. The summary and the Act Now queue feed the sidebar badge on every page.
const NEEDS = {
  overview: ["summary", "queue", "performance", "schedule", "publicOverview"],
  "act-now": ["summary", "queue", "schemes"],
  channels: ["summary", "queue", "activity"],
  schemes: ["summary", "queue", "schemes", "performance", "sectors"],
  trends: ["summary", "queue"],
  advice: ["summary", "queue", "schedule", "weeklyAdvice"],
  food: ["summary", "queue", "nutrition"],
  map: ["summary", "queue", "schemes", "nutrition"],
  feedback: ["summary", "queue", "health"],
  cooperatives: ["summary", "queue", "cooperatives", "training"],
}[page] || ["summary", "queue"];
const needs = (key) => NEEDS.includes(key);

const formatDate = (value) => new Intl.DateTimeFormat(CS.lang === "rw" ? "rw" : "en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
const humanize = (value) => String(value ?? "").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
const number = (value, digits = 0) => (value === null || value === undefined ? "–" : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits }));
const setText = (selector, value) => { const node = $(selector); if (node) node.textContent = value; };
const setHtml = (selector, html) => { const node = $(selector); if (node) node.innerHTML = html; };
const emptyState = (icon, title, text, action = "") => `<div class="empty-insight"><span class="bi bi-${icon}" aria-hidden="true"></span><div><strong>${title}</strong><p>${text}</p>${action}</div></div>`;
const schemeFilterValue = () => $("#scheme-filter")?.value || "all";

function setGreeting() {
  if (!$("#greeting")) return;
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
  if (!element) return;
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
  cache.summary = summary;
  countUp($("#metric-farmers"), summary.registered_farmers);
  countUp($("#metric-reports"), summary.total_reports);
  countUp($("#metric-schemes"), summary.active_schemes);
  countUp($("#metric-complaints"), summary.open_complaints);
  countUp($("#metric-households"), summary.households_surveyed ?? 0);
  countUp($("#metric-rewards"), summary.rewards_paid_rwf ?? 0, " RWF");
  setText("#metric-complaints-note", `${summary.faulty_or_offline_assets} fault report${summary.faulty_or_offline_assets === 1 ? "" : "s"} received (all time)`);
  setText("#metric-households-note", summary.average_stunting_risk ? `Average stunting risk ${summary.average_stunting_risk} / 5` : "Collected through USSD option 6");
  setText("#mod-channels", number(summary.field_messages));
  setText("#mod-feedback", number(summary.open_complaints));
  setText("#mod-food", number(summary.households_surveyed ?? 0));
  // Page headers
  setText("#stat-messages", number(summary.field_messages));
  setText("#stat-reports", number(summary.total_reports));
  setText("#stat-rewards", `${number(summary.rewards_paid_rwf ?? 0)} RWF`);
  setText("#stat-households", number(summary.households_surveyed ?? 0));
  setText("#stat-open-feedback", number(summary.open_complaints));
}

/* ---------- Act Now queue ---------- */
function showQueue(items) {
  cache.queue = items;
  setText("#nav-alert-count", items.length);
  setText("#mod-actnow", number(items.length));
  const list = $("#act-now-list");
  if (!list) return;
  const counts = { all: items.length, infrastructure: 0, pest_or_disease: 0, community_feedback: 0 };
  items.forEach((item) => { counts[item.item_type] = (counts[item.item_type] || 0) + 1; });
  document.querySelectorAll("[data-queue-count]").forEach((badge) => { badge.textContent = counts[badge.dataset.queueCount] || 0; });
  if (!items.length) {
    list.innerHTML = emptyState("check2-circle", "No urgent reports", "The queue is clear. New offline pumps, severe pests and grievances appear here automatically.");
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

const QUEUE_PREVIEW = 10;
let queueExpanded = false;

function applyQueueFilters() {
  const list = $("#act-now-list");
  if (!list) return;
  const scheme = schemeFilterValue();
  let shown = 0;
  let matching = 0;
  list.querySelectorAll(".alert-row[data-type]").forEach((row) => {
    const match = !((scheme !== "all" && row.dataset.scheme !== scheme) || (queueFilter !== "all" && row.dataset.type !== queueFilter));
    matching += match ? 1 : 0;
    row.hidden = !match || (!queueExpanded && shown >= QUEUE_PREVIEW);
    if (!row.hidden) shown += 1;
  });
  list.querySelector(".show-more")?.remove();
  if (matching > QUEUE_PREVIEW) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "secondary-button show-more";
    button.textContent = queueExpanded ? "Show fewer" : `Show all ${matching} items`;
    button.addEventListener("click", () => { queueExpanded = !queueExpanded; applyQueueFilters(); });
    list.append(button);
  }
}

/* ---------- Scheme performance (Objectives 1-2) ---------- */
const STATUS_LABEL = { on_track: "On track", watch: "Watch", below_target: "Below target", no_target: "Target needed", no_data: "No harvest data" };

function renderPerformance(rows) {
  cache.performance = rows;
  setText("#mod-schemes", number(rows.length));
  setText("#stat-schemes", number(rows.length));
  setText("#stat-on-track", number(rows.filter((row) => row.status === "on_track").length));
  setText("#stat-below", number(rows.filter((row) => row.status === "below_target").length));
  setText("#stat-flagged", number(rows.reduce((total, row) => total + (row.flagged_bottlenecks || []).length, 0)));
  const host = $("#scheme-performance");
  if (!host) return;
  const demoWarning = $("#demo-warning");
  if (demoWarning) demoWarning.hidden = !rows.some((row) => /demonstration/i.test(row.target_source || ""));
  const scheme = schemeFilterValue();
  const visible = rows.filter((row) => scheme === "all" || String(row.scheme_id) === scheme);
  if (!visible.length) {
    host.innerHTML = emptyState("droplet-half", "No schemes yet", canAdminister ? 'Open <a href="#manage">Manage schemes</a> and add PADAB and APEFA Solar to start outcome verification.' : "An administrator adds the irrigation schemes in Manage schemes.");
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
      <div class="bar-label"><span>${row.basis === "reported" ? "Reported harvest" : "Forecast harvest"} <b>${number(achieved, 1)} t</b></span><span>Target <b>${number(row.target_tons, 1)} t</b> · <b>${number(row.achievement_percent, 1)}%</b> <small title="Harvests reported by a sample of farmers, compared with the whole-scheme target. Not a verified yield achievement.">(sample, not verified)</small></span></div>
      <div class="track big" role="img" aria-label="${escapeHtml(`${row.name}: ${number(achieved, 1)} of ${number(row.target_tons, 1)} tons`)}"><div class="fill ${escapeHtml(row.status)}" style="width:${fill}%"></div><span class="target" style="left:${marker}%"></span></div>
      <p class="perf-source">${/demonstration/i.test(row.target_source || "") ? "⚠ " : ""}Target source: ${escapeHtml(row.target_source || "not recorded")}</p>`
      : `<p class="perf-missing">Forecast so far: <b>${number(row.expected_tons, 1)} t</b>. Add the feasibility-study yield target in <a href="#manage">Manage schemes</a> to verify this outcome.</p>`}
      <div class="perf-stats"><span><b>${number(row.crop_reports)}</b> crop reports</span><span><b>${number(row.pest_alerts)}</b> pest alerts</span><span><b>${number(row.infrastructure_faults)}</b> asset faults</span><span><b>${number(row.open_grievances)}</b> open grievances</span></div>
      ${renderHarvestCalendar(row)}
      ${bottlenecks.length ? `      <div class="bottlenecks"><p class="mini-title">Bottlenecks reported (${number(row.bottleneck_window_days || 90)} days)</p>${bottlenecks.map(([name, n]) => `<div class="bn-row ${row.flagged_bottlenecks.includes(name) ? "flagged" : ""}"><span>${escapeHtml(humanize(name))}${row.flagged_bottlenecks.includes(name) ? " ⚑" : ""}${(row.baseline_bottlenecks || []).includes(name) ? " ↑" : ""}</span><i style="width:${(n / maxBottleneck) * 100}%"></i><b>${n}</b></div>`).join("")}
      ${row.flagged_bottlenecks.length ? `<p class="flag-note">⚑ Auto-flagged: recurring ${escapeHtml(row.flagged_bottlenecks.join(", "))} bottleneck. Review before the next season.</p>` : ""}
      ${(row.baseline_bottlenecks || []).length ? `<p class="flag-note">↑ Above the historical baseline from the imported AfDB evaluation findings.</p>` : ""}</div>` : ""}
    </div>`;
  }).join("");
}

/* ---------- Scheme management (schemes.html) ---------- */
// Expected harvest by month, from the yield-forecaster inputs farmers send over USSD/SMS.
function renderHarvestCalendar(row) {
  const calendar = row.harvest_calendar || [];
  if (!calendar.length) return "";
  const max = Math.max(...calendar.map((entry) => entry.tons), 1);
  const monthLabel = (month) => new Intl.DateTimeFormat(CS.lang === "rw" ? "rw" : "en", { month: "short", year: "numeric" }).format(new Date(`${month}-01T00:00:00`));
  return `<div class="harvest-calendar"><p class="mini-title">Expected harvest by month</p>${calendar.slice(0, 8).map((entry) => `
    <div class="bn-row"><span>${escapeHtml(monthLabel(entry.month))}</span><i style="width:${(entry.tons / max) * 100}%"></i><b>${number(entry.tons, 1)} t</b></div>`).join("")}
    <p class="data-note">From farmer planting dates and weeks-to-harvest reports.</p></div>`;
}
function renderSchemeTable() {
  const body = $("#scheme-table");
  if (!body) return;
  const schemes = cache.schemes || [];
  const sectorName = Object.fromEntries((cache.sectors || []).map((sector) => [sector.id, sector.name]));
  setText("#scheme-admin-note", canAdminister
    ? "Verified figures used for outcome checks. Record where each yield target comes from."
    : "Verified figures used for outcome checks. Only administrators can add or edit schemes.");
  if (!schemes.length) {
    body.innerHTML = `<tr><td colspan="8" class="empty-row">No irrigation schemes yet.${canAdminister ? " Use Add scheme to create PADAB and APEFA Solar." : ""}</td></tr>`;
    return;
  }
  body.innerHTML = schemes.map((scheme) => `<tr>
      <td><strong>${escapeHtml(scheme.name)}</strong></td>
      <td>${escapeHtml(scheme.implementing_partner || "–")}</td>
      <td>${escapeHtml(sectorName[scheme.sector_id] || (scheme.sector_id ? `Sector #${scheme.sector_id}` : "–"))}</td>
      <td class="num">${scheme.hectares_developed ? `${number(scheme.hectares_developed)} ha` : "–"}</td>
      <td class="num">${scheme.baseline_yield_target_tons ? `${number(scheme.baseline_yield_target_tons, 1)} t` : '<span class="muted-note">Not set</span>'}</td>
      <td class="source-cell">${escapeHtml(scheme.baseline_source || "–")}</td>
      <td><span class="status-chip ${scheme.is_active ? "on_track" : "no_data"}">${scheme.is_active ? "Active pilot" : "Reference"}</span></td>
      <td data-admin-only><button type="button" class="row-action" data-edit-scheme="${scheme.id}"><i class="bi bi-pencil" aria-hidden="true"></i> Edit</button></td>
    </tr>`).join("");
}

function openSchemeDialog(scheme = null) {
  const form = $("#scheme-form");
  form.reset();
  form.dataset.schemeId = scheme ? String(scheme.id) : "";
  $("#scheme-dialog-title").textContent = scheme ? `Edit ${scheme.name}` : "Add irrigation scheme";
  setText("#scheme-message", "");
  const sectors = $("#scheme-sector");
  sectors.replaceChildren(new Option("Not set", ""), ...(cache.sectors || []).map((sector) => new Option(sector.name, String(sector.id))));
  form.name.readOnly = Boolean(scheme);
  form.name.title = scheme ? "The scheme name cannot be changed after it is created." : "";
  if (scheme) {
    ["name", "implementing_partner", "hectares_developed", "baseline_yield_target_tons", "baseline_source", "latitude", "longitude"].forEach((field) => { form[field].value = scheme[field] ?? ""; });
    form.sector_id.value = scheme.sector_id ? String(scheme.sector_id) : "";
    form.is_active.value = String(Boolean(scheme.is_active));
  }
  $("#scheme-dialog").showModal();
  (scheme ? form.implementing_partner : form.name).focus();
}

async function saveScheme(event) {
  event.preventDefault();
  const form = event.currentTarget;
  const id = form.dataset.schemeId;
  const numbers = ["hectares_developed", "baseline_yield_target_tons", "latitude", "longitude"];
  const payload = {};
  for (const [name, raw] of new FormData(form).entries()) {
    const value = String(raw).trim();
    if (name === "name" && id) continue;  // names are fixed once created
    if (name === "is_active") { payload.is_active = value === "true"; continue; }
    if (name === "sector_id") { payload.sector_id = value ? Number(value) : null; continue; }
    if (value === "") { if (id) payload[name] = null; continue; }
    payload[name] = numbers.includes(name) ? Number(value) : value;
  }
  try {
    await apiJson(id ? `irrigation-schemes/${id}` : "irrigation-schemes", { method: id ? "PATCH" : "POST", body: payload });
    $("#scheme-dialog").close();
    toast(id ? "Scheme updated" : "Scheme added", "success");
    await loadLive({ quiet: true });
  } catch (error) {
    setText("#scheme-message", error.status === 403 ? "Only administrators can add or edit schemes." : error.message);
  }
}

function showSchemeTab(name) {
  if (!$("[data-tab-panel]")) return;
  const tab = name === "manage" ? "manage" : "performance";
  document.querySelectorAll("[data-tab-panel]").forEach((panel) => { panel.hidden = panel.dataset.tabPanel !== tab; });
  document.querySelectorAll("[data-tab]").forEach((link) => link.classList.toggle("active", link.dataset.tab === tab));
}

/* ---------- Response health (Module 3) ---------- */
function renderHealth(health) {
  cache.health = health;
  setText("#stat-resolution", health.feedback_total ? `${health.resolution_rate ?? 0}%` : "–");
  setText("#stat-median", health.median_days_to_resolve ?? "–");
  setText("#stat-loop", number(health.close_loop_messages));
  const host = $("#response-health");
  if (!host) return;
  if (!health.feedback_total && !health.cases_total) {
    host.innerHTML = emptyState("chat-left-text", "No feedback cases yet", "Grievances sent by USSD option 5 or SMS IKIBAZO will appear here.");
    return;
  }
  const rate = health.resolution_rate ?? 0;
  const categories = Object.entries(health.by_category || {}).slice(0, 6);
  host.innerHTML = `
    <div class="ring" style="--rate:${rate}%"><span><b>${rate}%</b><small>grievances resolved</small></span></div>
    <div class="response-stats"><span><b>${health.median_days_to_resolve ?? "–"}</b>median days</span><span><b>${number(health.feedback_open)}</b>still open</span><span><b>${number(health.close_loop_messages)}</b>loop-closing SMS</span></div>
    <p class="mini-title">Grievances by category</p>
    <div class="category-list">${categories.map(([name, n]) => `<div><span>${escapeHtml(name)}</span><b>${n}</b></div>`).join("")}</div>
    <p class="data-note">${number(health.cases_resolved)} of ${number(health.cases_total)} crop/infrastructure cases resolved · ${number(health.cases_notified)} communities notified.</p>`;
}

/* ---------- Community feedback list ---------- */
const OPEN_STATES = ["open", "triaged", "assigned", "in_progress"];

async function loadFeedbackList() {
  const host = $("#feedback-list");
  if (!host || mode !== "live") return;
  if (readOnly) {
    host.innerHTML = emptyState("shield-lock", "Grievance details are for district staff", "District Planners and officers see each grievance and act on it. Response figures are shared with everyone.");
    return;
  }
  try {
    const [rows, cells] = await Promise.all([apiJson("feedback"), cache.cells ? Promise.resolve(cache.cells) : apiJson("cells").catch(() => [])]);
    cache.cells = cells;
    cache.feedback = rows;
    renderFeedbackList();
  } catch (error) {
    host.innerHTML = emptyState("exclamation-circle", "Grievances could not be loaded", escapeHtml(error.message));
  }
}

function renderFeedbackList() {
  const host = $("#feedback-list");
  if (!host) return;
  const rows = cache.feedback || [];
  const cellName = Object.fromEntries((cache.cells || []).map((cell) => [cell.id, cell.name]));
  const counts = { open: rows.filter((r) => OPEN_STATES.includes(r.status)).length, resolved: rows.filter((r) => !OPEN_STATES.includes(r.status)).length, all: rows.length };
  document.querySelectorAll("[data-feedback-count]").forEach((badge) => { badge.textContent = counts[badge.dataset.feedbackCount]; });
  const term = ($("#feedback-search")?.value || "").trim().toLowerCase();
  const visible = rows.filter((r) => (feedbackFilter === "all" || (feedbackFilter === "open") === OPEN_STATES.includes(r.status))
    && (!term || `${r.category} ${r.message}`.toLowerCase().includes(term)));
  if (!visible.length) {
    host.innerHTML = emptyState("inbox", rows.length ? "Nothing matches" : "No grievances yet", rows.length ? "Change the filter or search term." : "Grievances sent by USSD option 5 or SMS IKIBAZO will appear here.");
    return;
  }
  host.innerHTML = visible.slice(0, 60).map((r) => `
    <article class="feedback-row">
      <div class="feedback-id">FB-${String(r.id).padStart(3, "0")}</div>
      <div class="feedback-body">
        <p class="row-type">${escapeHtml(r.category)}${r.cell_id ? ` · ${escapeHtml(cellName[r.cell_id] || `Cell #${r.cell_id}`)}` : ""}</p>
        <p>${escapeHtml(r.message)}</p>
        <small>Received ${formatDate(r.created_at)}${r.assigned_to_field_user_id ? ` · owner #${r.assigned_to_field_user_id}` : ""}${r.action_taken ? ` · Action: ${escapeHtml(r.action_taken)}` : ""}</small>
      </div>
      <div class="feedback-side"><span class="status-chip ${escapeHtml(r.status)}">${escapeHtml(humanize(r.status))}</span><button type="button" class="secondary-button feedback-open" data-id="${r.id}">${escapeHtml(t("btn.open"))} →</button></div>
    </article>`).join("") + (visible.length > 60 ? `<p class="data-note">Showing the newest 60 of ${visible.length}. Narrow the search to find older grievances.</p>` : "");
}

/* ---------- Irrigation Scheduling Assistant ---------- */
const ADVICE_LABEL = { irrigate_more: ["Irrigate more", "Ongera kuhira"], normal: ["Normal schedule", "Gahunda isanzwe"], reduce: ["Reduce irrigation", "Gabanya kuhira"], no_data: ["No readings", "Nta bipimo"] };

function renderAdvice(rows) {
  cache.schedule = rows;
  const order = { irrigate_more: 0, reduce: 1, normal: 2, no_data: 3 };
  const withData = rows.filter((row) => row.level !== "no_data").sort((a, b) => order[a.level] - order[b.level]);
  const missing = rows.length - withData.length;
  setText("#mod-advice", number(withData.length));
  setText("#stat-dry", number(rows.filter((row) => row.level === "irrigate_more").length));
  setText("#stat-normal", number(rows.filter((row) => row.level === "normal").length));
  setText("#stat-wet", number(rows.filter((row) => row.level === "reduce").length));
  setText("#stat-nodata", number(missing));
  const host = $("#advice-list");
  if (!host) return;
  const forecasts = rows.filter((row) => row.level === "no_data" && row.forecast_mm_7d != null).map((row) => row.forecast_mm_7d);
  const forecastRange = forecasts.length ? ` Forecast for them: ${number(Math.min(...forecasts), 0)}–${number(Math.max(...forecasts), 0)} mm over the next 7 days.` : "";
  host.innerHTML = withData.length
    ? withData.map((row) => `<div class="advice-row level-${row.level}">
        <div class="advice-rain"><b>${number(row.rainfall_mm_7d, 1)}</b><small>mm / 7 days</small></div>
        <div><strong>${escapeHtml(row.sector)}</strong> <span class="level-chip ${row.level}">${escapeHtml(ADVICE_LABEL[row.level][CS.lang === "rw" ? 1 : 0])}</span><p>${escapeHtml(CS.lang === "rw" ? row.message_rw : row.message_en)}</p><small>${row.readings} gauge reading${row.readings === 1 ? "" : "s"}${row.forecast_mm_7d != null ? ` · forecast ${number(row.forecast_mm_7d, 1)} mm next 7 days` : ""}${row.threshold_source ? ` · calibrated thresholds ${number(row.threshold_dry_mm, 1)}–${number(row.threshold_wet_mm, 1)} mm` : ""}</small></div>
      </div>`).join("") + (missing ? `<p class="data-note">${missing} sector${missing === 1 ? "" : "s"} without rain-gauge readings this week.${forecastRange}</p>` : "")
    : emptyState("cloud-rain", "No rain-gauge readings this week", `Cooperative leaders text IMVURA &lt;mm&gt; or use USSD option 3.${escapeHtml(forecastRange)}`);
  if ($("#send-advice")) $("#send-advice").disabled = !withData.length;
}

/* ---------- Weekly automatic advice (WP2) ---------- */
function renderWeeklyAdvice(status) {
  const note = $("#weekly-advice-status");
  if (!note) return;
  const last = status.last_run
    ? `Last automatic send: ${formatDate(status.last_run.sent_at)} · ${number(status.last_run.recipients)} recipients across ${number(status.last_run.sectors)} sector${status.last_run.sectors === 1 ? "" : "s"} (week of ${status.last_run.week_key})`
    : "No automatic advice has been sent yet.";
  const next = status.enabled && status.next_run
    ? ` Next scheduled run: ${formatDate(status.next_run)} (${humanize(status.weekday)} ${status.time} ${status.timezone}).`
    : " Automatic sending is off — use Send advice to cooperatives, or run scripts/send_weekly_advice.py.";
  note.textContent = `${last}${next}`;
}

/* ---------- Cooperatives, Data Champions and training (WP5) ---------- */
function renderCooperatives(rows) {
  cache.cooperatives = rows;
  const total = (key) => rows.reduce((sum, row) => sum + (row[key] || 0), 0);
  setText("#stat-coops", number(rows.length));
  setText("#stat-coop-reports", number(total("reports_30d")));
  setText("#stat-coop-members", number(total("members")));
  setText("#stat-champions", number(total("data_champions")));
  const sectorName = Object.fromEntries((cache.sectors || []).map((sector) => [sector.id, sector.name]));
  const body = $("#coop-ranking");
  if (body) {
    if (!rows.length) {
      body.innerHTML = `<tr><td colspan="9" class="empty-row">No cooperatives yet. Register them in Platform Management → Cooperatives.</td></tr>`;
    } else {
      body.innerHTML = rows.map((row, index) => `<tr>
        <td><b>${index + 1}</b></td>
        <td><strong>${escapeHtml(row.name)}</strong>${row.is_pilot ? ' <span class="status-chip on_track">pilot</span>' : ""}</td>
        <td>${escapeHtml(sectorName[row.sector_id] || "–")}</td>
        <td>${number(row.members)}</td>
        <td>${number(row.data_champions)}</td>
        <td><b>${number(row.reports_30d)}</b></td>
        <td>${number(row.reports_mtd)}</td>
        <td>${number(row.active_reporters_30d)}</td>
        <td>${row.last_report_at ? escapeHtml(formatDate(row.last_report_at)) : "never"}</td>
      </tr>`).join("");
    }
  }
  const chart = $("#coop-chart");
  if (chart) {
    if (!rows.length) {
      chart.innerHTML = emptyState("people", "No cooperatives yet", "Once cooperatives are registered, their 30-day reports are ranked here for the Inteko z'Abaturage meeting.");
    } else {
      const max = Math.max(...rows.map((row) => row.reports_30d), 1);
      chart.innerHTML = rows.map((row) => `<div class="bn-row"><span title="${escapeHtml(row.name)}">${escapeHtml(row.name)}</span><i style="width:${(row.reports_30d / max) * 100}%"></i><b>${row.reports_30d}</b></div>`).join("")
        + `<p class="data-note">Reports filed by members in the last 30 days (crop, rainfall/infrastructure and nutrition).</p>`;
    }
  }
  renderPilots();
}

function renderPilots() {
  const host = $("#pilot-list");
  if (!host || !cache.cooperatives) return;
  const pilots = cache.cooperatives.filter((row) => row.is_pilot);
  const target = cache.training?.pilot_target;
  setText("#pilot-note", target != null
    ? `${pilots.length} of ${target} cooperatives in the pilot (PILOT_COOPERATIVE_TARGET).`
    : `${pilots.length} cooperative${pilots.length === 1 ? "" : "s"} marked as pilot.`);
  host.innerHTML = pilots.length
    ? pilots.map((row) => `<div class="bn-row"><span>${escapeHtml(row.name)}</span><i style="width:${Math.min(100, row.reports_30d)}%"></i><b>${row.members} mem</b></div><p class="data-note">${number(row.reports_30d)} reports in 30 days · ${number(row.data_champions)} Data Champion${row.data_champions === 1 ? "" : "s"}</p>`).join("")
    : emptyState("people", "No pilot cooperative yet", "Administrators mark the pilot cooperatives in Platform Management → Cooperatives.");
}

function renderTraining(data) {
  cache.training = data;
  setText("#stat-trained", `${number(data.trained_monitors)} / ${number(data.target)}`);
  const fill = $("#training-fill");
  if (fill) fill.style.width = `${Math.min(100, data.percent)}%`;
  setText("#training-note", `${data.percent}% of the ${number(data.target)}-monitor target · ${number(data.monitors_total)} monitors registered · ${number(data.data_champions)} Data Champion${data.data_champions === 1 ? "" : "s"}${data.trained_on ? ` · last training recorded ${formatDate(data.trained_on)}` : " · no training recorded yet"}`);
  renderPilots();
}

/* ---------- Household nutrition ---------- */
function renderFood(data) {
  cache.nutrition = data;
  setText("#stat-avg-risk", data.households ? `${data.average_risk} / 5` : "–");
  setText("#stat-high-risk", number(data.high_risk_households));
  setText("#stat-short", number(data.food_insufficient));
  const host = $("#food-summary");
  if (!host) return;
  if (!data.households) {
    host.innerHTML = emptyState("heart-pulse", "No household surveys yet", "Households answer three questions through USSD option 6.");
    return;
  }
  const level = data.average_risk >= 3.5 ? "high" : data.average_risk >= 2.5 ? "medium" : "low";
  host.innerHTML = `
    <div class="food-top">
      <div class="risk-gauge ${level}" style="--risk:${(data.average_risk / 5) * 100}%"><b>${data.average_risk}</b><small>average risk (1–5)</small></div>
      <div class="food-stats"><span><b>${number(data.households)}</b> households</span><span class="warn"><b>${number(data.high_risk_households)}</b> high risk (4–5)</span><span><b>${number(data.one_meal_households)}</b> ate once a day</span><span><b>${number(data.food_insufficient)}</b> short of food until harvest</span></div>
    </div>
    <p class="mini-title">Cells needing attention</p>
    ${data.by_cell.slice(0, 15).map((row) => row.suppressed
      ? `<div class="cell-risk"><span>${escapeHtml(row.cell)}</span><i style="width:0"></i><b>–</b><small>${row.households} hh · too few to show</small></div>`
      : `<div class="cell-risk"><span>${escapeHtml(row.cell)}</span><i style="width:${(row.average_risk / 5) * 100}%" class="${row.average_risk >= 3.5 ? "high" : row.average_risk >= 2.5 ? "medium" : "low"}"></i><b>${row.average_risk}</b><small>${row.households} hh</small></div>`).join("")}`;
}

/* ---------- Field channel feed ---------- */
const RECORD_LABEL = { crop_report: "Crop report", irrigation_report: "Water report", community_feedback: "Grievance", nutrition_survey: "Nutrition survey" };

function renderFeed(activity) {
  cache.activity = activity;
  const feed = $("#channel-feed");
  if (!feed) return;
  const items = [
    ...activity.inbound.map((m) => ({ ...m, kind: m.channel })),
    ...activity.outbound.filter((m) => m.purpose !== "auto_reply").map((m) => ({ ...m, kind: "out", text: m.message })),
    ...activity.rewards.map((r) => ({ ...r, kind: "reward", text: `${r.amount_rwf} RWF airtime — ${r.reason}` }))
  ].filter((m) => feedFilter === "all" || m.kind === feedFilter)
    .sort((a, b) => new Date(b.created_at) - new Date(a.created_at)).slice(0, 30);
  if (!items.length) { feed.innerHTML = `<li class="feed-empty">${escapeHtml(feedFilter === "all" ? t("channels.empty") : "No messages of this type yet.")}</li>`; return; }
  const icon = { ussd: "hash", sms: "chat-dots", out: "send", reward: "cash-coin" };
  const label = { ussd: "USSD *801#", sms: "SMS 8448", out: "SMS sent", reward: "Airtime reward" };
  feed.innerHTML = items.map((m) => `<li class="feed-item ${m.kind}">
    <span class="feed-icon bi bi-${icon[m.kind]}" aria-hidden="true"></span>
    <div><p><strong>${label[m.kind]}</strong> · ${escapeHtml(maskPhone(m.phone_number))}${m.purpose ? ` · ${escapeHtml(humanize(m.purpose))}` : ""}${m.record_type ? ` → <em>${escapeHtml(RECORD_LABEL[m.record_type] || m.record_type)}</em>` : ""}</p>
    <code>${escapeHtml(m.text || "")}</code>${m.reply ? `<small>${escapeHtml(m.reply.replace(/^(CON|END) /, ""))}</small>` : ""}</div>
    <time>${formatDate(m.created_at)}</time></li>`).join("");
}

const maskPhone = (phone) => String(phone || "").replace(/(\+?\d{6})\d{3}(\d{3})/, "$1•••$2");

/* ---------- Trends header totals ---------- */
document.addEventListener("cs:trends", (event) => {
  const months = event.detail?.months || [];
  const total = (key) => months.reduce((sum, m) => sum + (Number(m[key]) || 0), 0);
  setText("#stat-trend-reports", number(total("reports")));
  setText("#stat-trend-rain", number(total("rainfall_mm"), 1));
  setText("#stat-trend-cases", number(total("cases_resolved")));
  setText("#stat-trend-harvest", number(total("reported_tons"), 1));
});

/* ---------- Map (Mapbox GL) ---------- */
// The Mapbox token comes from MAPBOX_ACCESS_TOKEN through /public/map-config (public pk. tokens only).
const FEATURE_LAYER = { scheme: "schemes", irrigation: "infrastructure", crop: "crops", rainfall: "rain", farmer: "farmers" };
// Map layer ids behind each layer chip on map.html.
const MAP_GROUPS = {
  schemes: ["points-schemes"], infrastructure: ["points-infrastructure"], crops: ["points-crops"],
  rain: ["points-rain", "rain-cells"], food: ["food-cells"], farmers: ["points-farmers"], heat: ["pest-heat"],
};
const RAIN_COLOUR = { irrigate_more: "#c75248", normal: "#2878a9", reduce: "#1f5f8b", no_data: "#9aa7a1" };
const METRES_PER_PIXEL_Z10 = 150; // at Bugesera's latitude, Mapbox zoom 10
// Base maps. "map" uses MAPBOX_STYLE from the server; the others are Mapbox's own styles.
const BASE_STYLES = { satellite: "mapbox://styles/mapbox/satellite-streets-v12", terrain: "mapbox://styles/mapbox/outdoors-v12" };
const BASE_LABELS = { map: "Map", satellite: "Satellite", terrain: "Terrain" };
const MAP_PREFS_KEY = "cs_ircfs_map_view"; // shared with the React dashboard
const TERRAIN_EXAGGERATION = 1.8; // Bugesera's hills are gentle; lift them so 3D reads clearly
const OUR_SOURCES = ["boundary", "sectors-geo", "cells-geo", "district-label", "food", "rain", "heat", "points"];
const emptyCollection = () => ({ type: "FeatureCollection", features: [] });
let mapInit = null;
let boundaryBounds = null;
let defaultStyle = "mapbox://styles/mapbox/light-v11";
// The latest data per source: a base-map switch replaces the style, so everything is redrawn from here.
const mapSourceData = {};
const reduceMotion = () => window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function mapPrefs() {
  try {
    const saved = JSON.parse(window.localStorage.getItem(MAP_PREFS_KEY) || "{}");
    return { base: BASE_LABELS[saved.base] ? saved.base : "map", threeD: saved.threeD === true };
  } catch (_) { return { base: "map", threeD: false }; }
}
function saveMapPrefs(prefs) {
  try { window.localStorage.setItem(MAP_PREFS_KEY, JSON.stringify(prefs)); } catch (_) { /* storage blocked: the choice lasts for this visit */ }
}
let mapView = mapPrefs();
const styleUrl = (base) => BASE_STYLES[base] || defaultStyle;

function pointColour(feature) {
  if (feature.feature_type === "scheme") return "#167052";
  if (feature.feature_type === "farmer") return "#6b5ca5";
  if (feature.feature_type === "crop") return feature.status === "pest alert" ? "#c75248" : "#d59223";
  if (feature.feature_type === "rainfall") return "#2878a9";
  return feature.status === "offline" ? "#c75248" : feature.status === "faulty" ? "#e08a2c" : "#2f9e6e";
}

// A circle of a real-world size: its pixel radius at zoom 10 ("r10"), doubled per zoom level.
// Mapbox only accepts ["zoom"] as the input of a top-level interpolate, and base-2
// exponential interpolation between these two stops is exactly r10 * 2^(zoom - 10).
const metresRadius = ["interpolate", ["exponential", 2], ["zoom"], 5, ["*", ["get", "r10"], 1 / 32], 18, ["*", ["get", "r10"], 256]];
const point = (lat, lng, properties) => ({ type: "Feature", geometry: { type: "Point", coordinates: [lng, lat] }, properties });

function boundsOf(geo) {
  let west = Infinity, south = Infinity, east = -Infinity, north = -Infinity;
  const visit = (value) => {
    if (Array.isArray(value) && typeof value[0] === "number") {
      west = Math.min(west, value[0]); south = Math.min(south, value[1]); east = Math.max(east, value[0]); north = Math.max(north, value[1]);
    } else if (Array.isArray(value)) value.forEach(visit);
  };
  (geo.features || [geo]).forEach((feature) => feature.geometry && visit(feature.geometry.coordinates));
  return Number.isFinite(west) ? [[west, south], [east, north]] : null;
}

function mapMessage(text) {
  const status = $("#map-status");
  if (status) { status.textContent = text; status.classList.add("empty"); }
}

/** Remember a source's data and draw it if the map is ready. */
function setSourceData(id, data) {
  mapSourceData[id] = data;
  const source = liveMap && liveMap.getSource(id);
  if (source) source.setData(data);
}

/** Map / Satellite / Terrain and 3D, as one Mapbox control in the map's corner. */
class ViewControl {
  onAdd(map) {
    this.container = document.createElement("div");
    this.container.className = "mapboxgl-ctrl cs-view-ctrl";
    const group = document.createElement("div");
    group.className = "cs-view-bases";
    group.setAttribute("role", "group");
    group.setAttribute("aria-label", "Base map");
    this.baseButtons = Object.entries(BASE_LABELS).map(([base, label]) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => setBaseMap(base));
      group.append(button);
      return [base, button];
    });
    this.threeD = document.createElement("button");
    this.threeD.type = "button";
    this.threeD.className = "cs-view-3d";
    this.threeD.textContent = "3D";
    this.threeD.title = "Tilt the map and show the land's relief";
    this.threeD.addEventListener("click", () => setThreeD(!mapView.threeD));
    this.container.append(group, this.threeD);
    this.update();
    return this.container;
  }
  update() {
    this.baseButtons.forEach(([base, button]) => button.setAttribute("aria-pressed", String(mapView.base === base)));
    this.threeD.setAttribute("aria-pressed", String(mapView.threeD));
  }
  onRemove() { this.container.remove(); }
}
let viewControl = null;

/** Create the map once. Resolves to the map when it is ready, or null when it cannot be shown. */
function ensureMap() {
  if (mapInit) return mapInit;
  if (!$("#map-canvas")) return Promise.resolve(null);
  mapInit = (async () => {
    if (!window.mapboxgl) { mapMessage("The map library could not load. Check the internet connection, then reload."); return null; }
    const config = await apiJson("public/map-config").catch(() => ({ mapbox_token: null }));
    if (!config.mapbox_token) { mapMessage("The map appears once a Mapbox public token is added: MAPBOX_ACCESS_TOKEN in .env, then restart the platform."); return null; }
    mapboxgl.accessToken = config.mapbox_token;
    defaultStyle = config.style || defaultStyle;
    liveMap = new mapboxgl.Map({
      container: "map-canvas", style: styleUrl(mapView.base),
      center: [BUGESERA_VIEW.center[1], BUGESERA_VIEW.center[0]], zoom: 9.2, cooperativeGestures: true,
      maxPitch: 75,
    });
    liveMap.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");
    liveMap.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");
    viewControl = new ViewControl();
    liveMap.addControl(viewControl, "top-left");
    registerMapEvents();
    // Every style load (the first one and each base-map switch) redraws our layers and 3D.
    liveMap.on("style.load", () => { addMapLayers(); applyThreeD(false); });
    await new Promise((resolve) => liveMap.once("load", resolve));
    loadBugeseraBoundary();
    return liveMap;
  })();
  return mapInit;
}

function addMapLayers() {
  OUR_SOURCES.forEach((id) => { if (!liveMap.getSource(id)) liveMap.addSource(id, { type: "geojson", data: mapSourceData[id] || emptyCollection() }); });
  const satellite = mapView.base === "satellite";
  const outline = satellite ? "#ffffff" : "#0d6b4f";
  const add = (layer) => { if (!liveMap.getLayer(layer.id)) liveMap.addLayer(layer); };
  add({ id: "boundary-fill", type: "fill", source: "boundary", paint: { "fill-color": "#3a9b72", "fill-opacity": satellite ? 0.04 : 0.08 } });
  add({ id: "cells-line", type: "line", source: "cells-geo", paint: { "line-color": satellite ? "#d6efe1" : "#4d8aa3", "line-width": 0.5 } });
  add({ id: "sectors-fill", type: "fill", source: "sectors-geo", paint: { "fill-color": "#167052", "fill-opacity": 0.02 } });
  add({ id: "sectors-line", type: "line", source: "sectors-geo", paint: { "line-color": satellite ? "#e9f7ef" : "#167052", "line-width": 1 } });
  add({ id: "boundary-line", type: "line", source: "boundary", paint: { "line-color": outline, "line-width": 3 } });
  add({ id: "food-cells", type: "circle", source: "food", paint: { "circle-radius": metresRadius, "circle-color": ["get", "colour"], "circle-opacity": 0.35, "circle-stroke-color": ["get", "colour"], "circle-stroke-width": 1, "circle-pitch-alignment": "map" } });
  add({ id: "rain-cells", type: "circle", source: "rain", paint: { "circle-radius": metresRadius, "circle-color": ["get", "colour"], "circle-opacity": 0.18, "circle-stroke-color": ["get", "colour"], "circle-stroke-width": 2, "circle-pitch-alignment": "map" } });
  add({ id: "pest-heat", type: "heatmap", source: "heat", paint: {
    "heatmap-weight": ["get", "weight"],
    "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 8, 14, 13, 40],
    "heatmap-opacity": 0.75,
    "heatmap-color": ["interpolate", ["linear"], ["heatmap-density"], 0, "rgba(243, 211, 107, 0)", 0.3, "#f3d36b", 0.6, "#e08a2c", 0.9, "#c0392b"],
  } });
  [["points-schemes", "schemes"], ["points-infrastructure", "infrastructure"], ["points-crops", "crops"], ["points-rain", "rain"], ["points-farmers", "farmers"]].forEach(([id, group]) => {
    add({ id, type: "circle", source: "points", filter: ["==", ["get", "group"], group],
      paint: { "circle-radius": ["get", "radius"], "circle-color": ["get", "colour"], "circle-opacity": 0.92, "circle-stroke-color": "#ffffff", "circle-stroke-width": 2 } });
  });
  add({ id: "district-label", type: "symbol", source: "district-label",
    layout: { "text-field": "Bugesera District", "text-size": 13, "text-font": ["DIN Pro Bold", "Arial Unicode MS Bold"] },
    paint: { "text-color": satellite ? "#ffffff" : "#0d4e3b", "text-halo-color": satellite ? "#0d4e3b" : "#ffffff", "text-halo-width": 2 } });
  syncLayerVisibility();
}

/** Click and hover handlers live on the map, not the style, so they are bound once. */
function registerMapEvents() {
  ["points-schemes", "points-infrastructure", "points-crops", "points-rain", "points-farmers", "rain-cells", "food-cells"].forEach((id) => {
    liveMap.on("click", id, (event) => {
      const feature = event.features && event.features[0];
      if (feature) new mapboxgl.Popup({ offset: 10 }).setLngLat(feature.geometry.coordinates).setHTML(feature.properties.popup).addTo(liveMap);
    });
    liveMap.on("mouseenter", id, () => { liveMap.getCanvas().style.cursor = "pointer"; });
    liveMap.on("mouseleave", id, () => { liveMap.getCanvas().style.cursor = ""; });
  });
  const hover = new mapboxgl.Popup({ closeButton: false, closeOnClick: false });
  liveMap.on("mousemove", "sectors-fill", (event) => {
    const feature = event.features && event.features[0];
    if (feature) hover.setLngLat(event.lngLat).setText(feature.properties.name).addTo(liveMap);
  });
  liveMap.on("mouseleave", "sectors-fill", () => hover.remove());
}

function setBaseMap(base) {
  if (!liveMap || mapView.base === base) return;
  mapView = { ...mapView, base };
  saveMapPrefs(mapView);
  viewControl && viewControl.update();
  liveMap.setStyle(styleUrl(base)); // "style.load" redraws our layers
}

function setThreeD(on) {
  mapView = { ...mapView, threeD: on };
  saveMapPrefs(mapView);
  viewControl && viewControl.update();
  applyThreeD(true);
}

/** Terrain elevation, sky and tilt for 3D; flat and top-down otherwise. */
function applyThreeD(move) {
  if (!liveMap) return;
  if (mapView.threeD) {
    if (!liveMap.getSource("mapbox-dem")) liveMap.addSource("mapbox-dem", { type: "raster-dem", url: "mapbox://mapbox.mapbox-terrain-dem-v1", tileSize: 512, maxzoom: 14 });
    liveMap.setTerrain({ source: "mapbox-dem", exaggeration: TERRAIN_EXAGGERATION });
    liveMap.setFog({ range: [1, 12], color: "#eef4f0", "horizon-blend": 0.08 });
  } else {
    liveMap.setTerrain(null);
    liveMap.setFog(null);
  }
  if (!move) return;
  const camera = mapView.threeD ? { pitch: 62, bearing: -18 } : { pitch: 0, bearing: 0 };
  if (reduceMotion()) liveMap.jumpTo(camera); else liveMap.easeTo({ ...camera, duration: 900 });
}

async function loadBugeseraBoundary() {
  try {
    const boundary = await fetch("assets/data/bugesera-boundary.geojson").then((response) => { if (!response.ok) throw new Error("Boundary unavailable"); return response.json(); });
    setSourceData("boundary", boundary);
    boundaryBounds = boundsOf(boundary);
    if (boundaryBounds) {
      const [[west, south], [east, north]] = boundaryBounds;
      setSourceData("district-label", { type: "FeatureCollection", features: [point((south + north) / 2, (west + east) / 2, {})] });
    }
    resetBugeseraView();
  } catch (_) { /* the base map still shows Bugesera */ }
  try {
    const [sectorResponse, cellResponse] = await Promise.all([apiFetch("geography/sectors"), apiFetch("geography/cells")]);
    const asCollection = (items) => ({ type: "FeatureCollection", features: items.filter((item) => item.geometry).map((item) => ({ type: "Feature", properties: { name: item.name }, geometry: item.geometry })) });
    if (sectorResponse.ok) setSourceData("sectors-geo", asCollection(await sectorResponse.json()));
    if (cellResponse.ok) setSourceData("cells-geo", asCollection(await cellResponse.json()));
  } catch (_) { /* sector and cell outlines need PostGIS; the district outline is enough without it */ }
}

function resetBugeseraView() {
  if (!liveMap) return;
  const camera = mapView.threeD ? { pitch: 62, bearing: -18 } : { pitch: 0, bearing: 0 };
  if (boundaryBounds) liveMap.fitBounds(boundaryBounds, { padding: 18, ...camera, animate: !reduceMotion() });
  else liveMap.jumpTo({ center: [30.10, -2.20], zoom: 9.2, ...camera });
}

function renderMap(data) {
  currentMapData = data;
  const scheme = schemeFilterValue();
  const visible = data.features.filter((feature) => scheme === "all" || feature.feature_type === "farmer" || String(feature.scheme_id) === scheme);
  setText("#stat-mapped", mode === "live" ? number(visible.length) : "–");
  const status = $("#map-status");
  if (status) {
    status.classList.toggle("empty", visible.length === 0);
    status.textContent = visible.length === 0
      ? (mode === "live" ? "No mapped locations yet. Reports appear once they are linked to a cell or have coordinates." : "Connect to the platform to show schemes, reports and farmers. The base map shows Bugesera.")
      : `${visible.length} mapped location${visible.length === 1 ? "" : "s"}${scheme === "all" ? " across Bugesera" : " for this scheme"}. Use the layer chips to compare pests, rainfall, and nutrition risk; switch to satellite, terrain or 3D in the map's corner.`;
  }
  setSourceData("points", { type: "FeatureCollection", features: visible.map((feature) => point(feature.latitude, feature.longitude, {
    group: FEATURE_LAYER[feature.feature_type] || "infrastructure",
    colour: pointColour(feature),
    radius: feature.feature_type === "scheme" ? 10 : feature.feature_type === "rainfall" ? 4 : 7,
    popup: `<strong>${escapeHtml(feature.name)}</strong>${feature.status ? `<br />${escapeHtml(feature.status)}` : ""}${feature.details ? `<br /><small>${escapeHtml(feature.details)}</small>` : ""}`,
  })) });
  ensureMap().then((map) => map && map.resize());
}

function renderAnalysisLayers({ heat = [], rain = [], food = [] }) {
  setSourceData("heat", { type: "FeatureCollection", features: heat.map((p) => point(p.latitude, p.longitude, { weight: p.weight })) });
  setSourceData("rain", { type: "FeatureCollection", features: rain.map((cell) => point(cell.latitude, cell.longitude, {
    colour: RAIN_COLOUR[cell.level] || RAIN_COLOUR.no_data, r10: 900 / METRES_PER_PIXEL_Z10,
    popup: `<strong>${escapeHtml(cell.cell)}</strong><br />${escapeHtml(cell.rainfall_mm)} mm in 7 days (${escapeHtml(cell.readings)} readings)<br /><small>${cell.level === "irrigate_more" ? "Dry spell warning" : escapeHtml(humanize(cell.level))}</small>`,
  })) });
  // Cells with too few households are not drawn (privacy: see MIN_HOUSEHOLDS_PER_GROUP in analytics.py).
  setSourceData("food", { type: "FeatureCollection", features: food.filter((row) => !row.suppressed && row.latitude !== null && row.latitude !== undefined).map((row) => point(row.latitude, row.longitude, {
    colour: row.average_risk >= 3.5 ? "#8e3b8a" : row.average_risk >= 2.5 ? "#b07cc6" : "#c9b6d6", r10: (500 + row.households * 120) / METRES_PER_PIXEL_Z10,
    popup: `<strong>${escapeHtml(row.cell)}</strong><br />Average stunting risk ${escapeHtml(row.average_risk)} / 5<br />${escapeHtml(row.households)} households, ${escapeHtml(row.high_risk)} high risk`,
  })) });
}

function syncLayerVisibility() {
  if (!liveMap || !liveMap.getLayer("pest-heat")) return;
  document.querySelectorAll("[data-layer]").forEach((input) => {
    (MAP_GROUPS[input.dataset.layer] || []).forEach((id) => {
      if (liveMap.getLayer(id)) liveMap.setLayoutProperty(id, "visibility", input.checked ? "visible" : "none");
    });
  });
}

async function loadMap() {
  if (!$("#map-canvas")) return;
  ensureMap(); // start loading the base map while the data is fetched
  if (mode !== "live") { renderMap(BUGESERA_VIEW); return; }
  try {
    const [mapData, heat, rain] = await Promise.all([apiJson("map-data"), apiJson("analytics/pest-heatmap"), apiJson("analytics/rainfall-map")]);
    renderAnalysisLayers({ heat, rain, food: cache.nutrition?.by_cell || [] });
    renderMap(mapData);
  } catch (_) {
    renderMap(BUGESERA_VIEW);
    setText("#map-status", "Map data is unavailable right now. The base map shows Bugesera only.");
  }
}

/* ---------- Connection state ---------- */
const here = `${location.pathname.split("/").pop() || "planner.html"}${location.hash}`;
const NOTICE = {
  "signed-out": ["box-arrow-in-right", "Sign in to see live data", "These pages only show records from the platform database. Sign in with your CS-IRCFS account to load them.", `<a class="primary-button" href="login.html?next=${encodeURIComponent(here.split("#")[0])}">Sign in</a>`],
  forbidden: ["shield-lock", "Your account cannot open the dashboard", "Ask an administrator to give you the District Planner, officer or Citizen Science Monitor role.", `<a class="secondary-button" href="login.html?next=${encodeURIComponent(here.split("#")[0])}">Use another account</a>`],
  offline: ["wifi-off", "The platform is not reachable", "Start the platform with start-local.ps1, then reconnect. No figures are shown until it answers.", '<button type="button" class="primary-button" data-reconnect>Reconnect</button>'],
};

function setMode(next) {
  mode = next;
  const live = next === "live";
  const badge = $("#data-mode");
  if (badge) {
    badge.textContent = live ? t("data.live") : next === "connecting" ? "CONNECTING…" : next === "signed-out" || next === "forbidden" ? t("data.signin") : t("data.offline");
    badge.classList.toggle("live", live);
  }
  if ($("#live-pulse")) $("#live-pulse").hidden = !live;
  const reconnect = $("#load-live-data");
  if (reconnect) {
    reconnect.hidden = live || next === "connecting";
    reconnect.textContent = next === "signed-out" ? "Sign in" : "Reconnect";
  }
  const notice = $("#connection-notice");
  if (notice) {
    notice.hidden = !NOTICE[next];
    if (NOTICE[next]) {
      const [icon, title, text, action] = NOTICE[next];
      notice.className = `connection-notice ${next}`;
      notice.innerHTML = `<span class="bi bi-${icon}" aria-hidden="true"></span><div><strong>${title}</strong><p>${text}</p></div>${action}`;
    }
  }
  window.clearInterval(refreshTimer);
  if (live) refreshTimer = window.setInterval(() => { if (!document.querySelector("dialog[open]") && !document.hidden) loadLive({ quiet: true }); }, REFRESH_MS);
}

// Without a connection, every module explains why it is empty instead of showing figures.
function showDisconnected() {
  const reason = mode === "offline" ? "Waiting for the platform to come online." : mode === "forbidden" ? "This account does not have access to these records." : "Sign in to load live records.";
  ["#metric-farmers", "#metric-reports", "#metric-schemes", "#metric-complaints", "#metric-households", "#metric-rewards"].forEach((id) => { const node = $(id); if (node) { node.textContent = "–"; node.dataset.value = 0; } });
  document.querySelectorAll('[id^="mod-"]:not(#mod-trends), [id^="stat-"]').forEach((node) => { node.textContent = "–"; });
  setText("#nav-alert-count", "–");
  document.querySelectorAll("[data-queue-count], [data-feedback-count]").forEach((badge) => { badge.textContent = "–"; });
  setHtml("#act-now-list", emptyState("lock", "Act Now is empty", reason));
  setHtml("#channel-feed", `<li class="feed-empty">${escapeHtml(reason)}</li>`);
  setHtml("#scheme-performance", emptyState("lock", "No scheme figures", reason));
  setHtml("#scheme-table", `<tr><td colspan="8" class="empty-row">${escapeHtml(reason)}</td></tr>`);
  setHtml("#response-health", emptyState("lock", "No response figures", reason));
  setHtml("#feedback-list", emptyState("lock", "No grievances loaded", reason));
  setHtml("#advice-list", emptyState("lock", "No irrigation advice", reason));
  setText("#weekly-advice-status", reason);
  setHtml("#food-summary", emptyState("lock", "No household surveys", reason));
  setHtml("#coop-ranking", `<tr><td colspan="9" class="empty-row">${escapeHtml(reason)}</td></tr>`);
  setHtml("#coop-chart", emptyState("lock", "No participation figures", reason));
  setHtml("#pilot-list", emptyState("lock", "No pilot cooperatives", reason));
  setText("#training-note", reason);
  if ($("#send-advice")) $("#send-advice").disabled = true;
  if ($("#scheme-add")) $("#scheme-add").disabled = true;
  window.CSTrends?.clear(reason);
  loadMap();
}

async function loadLive({ quiet = false } = {}) {
  const requests = {
    summary: () => apiJson("analytics/dashboard-summary"),
    queue: () => (readOnly ? Promise.resolve(null) : apiJson("analytics/act-now")),
    schemes: () => apiJson("irrigation-schemes"),
    performance: () => apiJson("analytics/scheme-performance"),
    health: () => apiJson("analytics/response-health"),
    schedule: () => apiJson("advisory/irrigation-schedule"),
    weeklyAdvice: () => apiJson("advisory/weekly-advice"),
    nutrition: () => apiJson("analytics/nutrition-summary"),
    activity: () => apiJson("channels/activity?limit=40"),
    sectors: () => (cache.sectors ? Promise.resolve(cache.sectors) : apiJson("sectors")),
    publicOverview: () => apiJson("public/overview"),
    cooperatives: () => apiJson("cooperatives/participation"),
    training: () => apiJson("cooperatives/training-progress"),
  };
  const keys = NEEDS.filter((key) => requests[key]);
  const results = await Promise.allSettled(keys.map((key) => requests[key]()));
  const data = Object.fromEntries(keys.map((key, index) => [key, results[index].status === "fulfilled" ? results[index].value : null]));
  if (!data.summary) throw results[keys.indexOf("summary")].reason;
  const previousQueue = cache.queue?.length;

  if (data.schemes) {
    cache.schemes = data.schemes;
    const filter = $("#scheme-filter");
    if (filter) {
      const selected = filter.value !== "all" ? filter.value : (sessionStorage.getItem(SCHEME_KEY) || "all");
      filter.replaceChildren(new Option(t("top.allSchemes"), "all"), ...data.schemes.map((scheme) => new Option(`${scheme.name}${scheme.is_active ? "" : " (reference)"}`, String(scheme.id))));
      filter.value = selected;
      if (filter.selectedIndex < 0) filter.value = "all";
      if ($("#scheme-filter-help")) $("#scheme-filter-help").hidden = data.schemes.length > 0;
    }
  }
  if (data.sectors) cache.sectors = data.sectors;
  showSummary(data.summary);
  if (data.queue) showQueue(data.queue);
  if (data.performance) renderPerformance(data.performance);
  if (data.health) renderHealth(data.health);
  if (data.schedule) renderAdvice(data.schedule);
  if (data.weeklyAdvice) renderWeeklyAdvice(data.weeklyAdvice);
  if (data.cooperatives) renderCooperatives(data.cooperatives);
  if (data.training) renderTraining(data.training);
  if (data.nutrition) renderFood(data.nutrition);
  if (data.activity) renderFeed(data.activity);
  if (data.publicOverview) setText("#mod-map", `${data.publicOverview.sectors_reporting} / ${data.publicOverview.sectors_total}`);
  if (page === "schemes") { renderSchemeTable(); if ($("#scheme-add")) $("#scheme-add").disabled = false; }
  if (page === "feedback") loadFeedbackList();
  if (page === "act-now" && readOnly) setHtml("#act-now-list", emptyState("shield-lock", "Act Now is for district staff", "District Planners and officers act on these cases. Field figures on the other pages are shared with everyone."));
  if (quiet && data.queue && previousQueue !== undefined && data.queue.length > previousQueue) toast(`${data.queue.length - previousQueue} new item${data.queue.length - previousQueue === 1 ? "" : "s"} in Act Now`, "warn");
  if (!quiet) { window.CSTrends?.load(); await loadMap(); }
}

async function connect({ interactive = false } = {}) {
  try {
    await apiJson("analytics/dashboard-summary");
    setMode("live");
    await loadLive();
    if (interactive) toast("Connected to the platform", "success");
  } catch (error) {
    if (error.status === 401 && CS.session.token()) { CS.session.clear(); toast("Your session expired. Please sign in again.", "warn"); }
    if (error.status === 401 && interactive) { window.location.href = `login.html?next=${encodeURIComponent(here.split("#")[0])}`; return; }
    setMode(error.status === 401 ? "signed-out" : error.status === 403 ? "forbidden" : "offline");
    showDisconnected();
    if ($("#data-mode")) $("#data-mode").title = error.message;
    if (interactive && error.status !== 401) toast(error.status === 403 ? `${error.message}. Ask an administrator for access.` : "The platform is not reachable. Start it with start-local.ps1.", "error");
  }
}

/* ---------- Case and feedback dialog ---------- */
function openRecordDialog(item) {
  if (mode !== "live") { toast("Connect to the platform to manage cases.", "warn"); return; }
  const kind = item.item_type === "community_feedback" ? "feedback" : "case";
  openRecord = { kind, id: item.item_id, item };
  const form = $("#case-form");
  form.reset();
  $("#case-kind").textContent = kind === "feedback" ? "COMMUNITY FEEDBACK" : item.item_type === "infrastructure" ? "INFRASTRUCTURE CASE" : "CROP RISK CASE";
  $("#case-title").textContent = kind === "feedback" ? `FB-${String(item.item_id).padStart(3, "0")} · ${item.title}` : `Case #${item.item_id} · ${item.title}`;
  $("#case-summary").textContent = `${item.details || ""} (${item.priority ? `${item.priority} priority, ` : ""}reported ${formatDate(item.created_at)})`;
  // Cases are owned by a platform account; grievances by a field user (for example a cooperative leader).
  $("#owner-label").textContent = kind === "feedback" ? "Owner (field user ID)" : "Owner (account ID)";
  form.status.value = item.status === "open" ? "triaged" : item.status;
  form.owner_id.value = item.owner_id || "";
  $("#case-message").textContent = "";
  $("#notify-box").hidden = true;
  $("#case-notify").dataset.stage = "preview";
  $("#case-notify").disabled = false;
  $("#case-notify").querySelector("span").textContent = t("case.notify");
  loadHistory();
  $("#case-dialog").showModal();
  if (kind === "case") apiJson(`cases/${item.item_id}`).then((record) => { form.action_taken.value = record.action_taken || ""; form.owner_id.value = record.assigned_to_account_id || ""; }).catch(() => {});
  else if (item.action_taken) form.action_taken.value = item.action_taken;
}

async function loadHistory() {
  const path = openRecord.kind === "feedback" ? `feedback/${openRecord.id}/history` : `cases/${openRecord.id}/history`;
  try {
    const events = await apiJson(path);
    $("#case-history-wrap").hidden = !events.length;
    $("#case-history").innerHTML = events.map((event) => `<li>${formatDate(event.created_at)} · ${escapeHtml(humanize(event.previous_status || "new"))} → <b>${escapeHtml(humanize(event.new_status))}</b>${event.action_taken ? ` — ${escapeHtml(event.action_taken)}` : ""}</li>`).join("");
  } catch (_) { $("#case-history-wrap").hidden = true; }
}

on("#case-form", "submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = { status: form.get("status"), action_taken: form.get("action_taken") || null };
  if (form.get("owner_id")) payload[openRecord.kind === "feedback" ? "assigned_to_field_user_id" : "assigned_to_account_id"] = Number(form.get("owner_id"));
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

on("#case-notify", "click", async () => {
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

on("#case-cancel", "click", () => { $("#case-dialog").close(); $("#case-notify").disabled = false; });

/* ---------- Advice broadcast ---------- */
on("#send-advice", "click", async () => {
  if (mode !== "live") { toast("Connect to the platform to send advice.", "warn"); return; }
  try {
    const preview = await apiJson("advisory/irrigation-schedule/send", { method: "POST", body: { preview: true } });
    $("#advice-preview").innerHTML = preview.sectors.map((row) => `<p class="dialog-note"><strong>${escapeHtml(row.sector)}</strong> · ${row.recipients} recipient${row.recipients === 1 ? "" : "s"}</p><div class="sms-preview">${escapeHtml(row.message_rw)}</div>`).join("") || "<p>No sector has rain-gauge readings this week.</p>";
    $("#advice-message").textContent = `${preview.total_recipients} SMS will be sent to cooperative leaders, monitors, and farmers in these sectors.`;
    $("#advice-confirm").disabled = preview.total_recipients === 0;
    $("#advice-dialog").showModal();
  } catch (error) { toast(error.message, "error"); }
});
on("#advice-cancel", "click", () => $("#advice-dialog").close());
on("#advice-confirm", "click", async () => {
  try {
    const result = await apiJson("advisory/irrigation-schedule/send", { method: "POST", body: { preview: false } });
    $("#advice-dialog").close();
    toast(`Irrigation advice sent to ${result.total_recipients} people`, "success");
    loadLive({ quiet: true });
  } catch (error) { $("#advice-message").textContent = error.message; }
});

/* ---------- Other interactions ---------- */
on("#load-live-data", "click", () => connect({ interactive: true }));
on("#print-coops", "click", () => window.print());
on("#connection-notice", "click", (event) => { if (event.target.closest("[data-reconnect]")) connect({ interactive: true }); });
on("#map-reset-view", "click", resetBugeseraView);
on("#refresh-queue", "click", () => (mode === "live" ? loadLive().then(() => toast("Queue refreshed", "success")) : connect({ interactive: true })));
on("#scheme-filter", "change", () => {
  sessionStorage.setItem(SCHEME_KEY, schemeFilterValue());
  applyQueueFilters();
  if (cache.performance) renderPerformance(cache.performance);
  if (currentMapData) renderMap(currentMapData);
});
document.querySelectorAll("[data-queue-filter]").forEach((chip) => chip.addEventListener("click", () => {
  queueFilter = chip.dataset.queueFilter;
  document.querySelectorAll("[data-queue-filter]").forEach((other) => other.classList.toggle("active", other === chip));
  applyQueueFilters();
}));
on("#act-now-list", "click", (event) => {
  const button = event.target.closest(".case-open");
  if (button) openRecordDialog(cache.queue[Number(button.dataset.index)]);
});
document.querySelectorAll("[data-feed-filter]").forEach((chip) => chip.addEventListener("click", () => {
  feedFilter = chip.dataset.feedFilter;
  document.querySelectorAll("[data-feed-filter]").forEach((other) => other.classList.toggle("active", other === chip));
  if (cache.activity) renderFeed(cache.activity);
}));
document.querySelectorAll("[data-feedback-filter]").forEach((chip) => chip.addEventListener("click", () => {
  feedbackFilter = chip.dataset.feedbackFilter;
  document.querySelectorAll("[data-feedback-filter]").forEach((other) => other.classList.toggle("active", other === chip));
  renderFeedbackList();
}));
on("#feedback-search", "input", () => renderFeedbackList());
on("#feedback-list", "click", (event) => {
  const button = event.target.closest(".feedback-open");
  if (!button) return;
  const row = (cache.feedback || []).find((item) => item.id === Number(button.dataset.id));
  if (row) openRecordDialog({ item_type: "community_feedback", item_id: row.id, title: row.category, details: row.message, status: row.status,
                              created_at: row.created_at, owner_id: row.assigned_to_field_user_id, action_taken: row.action_taken });
});
document.querySelectorAll("[data-layer]").forEach((input) => input.addEventListener("change", syncLayerVisibility));
on("#phone-demo-form", "submit", async (event) => {
  event.preventDefault();
  const formElement = event.currentTarget;
  const payload = Object.fromEntries(new FormData(formElement));
  try {
    const report = await apiJson("irrigation-reports", { method: "POST", body: payload });
    setText("#phone-demo-message", `Report #${report.id} saved.${payload.operational_status !== "operational" ? " It is now in Act Now." : ""}`);
    formElement.reset();
    if (mode !== "live") await connect(); else await loadLive({ quiet: true });
  } catch (error) { setText("#phone-demo-message", error.status ? error.message : "Could not save the report. Start the platform first."); }
});

// Scheme page: performance and management tabs, and the add/edit form.
on("#scheme-add", "click", () => openSchemeDialog());
on("#scheme-table", "click", (event) => {
  const button = event.target.closest("[data-edit-scheme]");
  if (!button) return;
  const scheme = (cache.schemes || []).find((item) => item.id === Number(button.dataset.editScheme));
  if (scheme) openSchemeDialog(scheme);
});
on("#scheme-form", "submit", saveScheme);
on("#scheme-cancel", "click", () => $("#scheme-dialog").close());
window.addEventListener("hashchange", () => showSchemeTab(location.hash.slice(1)));

document.addEventListener("cs:lang", () => {
  setGreeting();
  if (cache.queue) showQueue(cache.queue);
  if (cache.schedule) renderAdvice(cache.schedule);
  if (cache.activity) renderFeed(cache.activity);
  if (cache.cooperatives) renderCooperatives(cache.cooperatives);
  if (cache.training) renderTraining(cache.training);
  setMode(mode);
});

/* ---------- Start ---------- */
document.body.classList.toggle("read-only", readOnly);
document.body.classList.toggle("no-admin", !canAdminister);
if ($("#role-note")) $("#role-note").hidden = !readOnly;
if (signedIn?.sector_ids?.length && $("#area-note")) {
  $("#area-note").textContent = `Your area: ${signedIn.area}. Cases, grievances, people and reports are limited to it; district totals and trends cover all of Bugesera.`;
  $("#area-note").hidden = false;
}
setGreeting();
showSchemeTab(location.hash.slice(1));
if (page === "map") ensureMap();
setMode("connecting");
connect();
