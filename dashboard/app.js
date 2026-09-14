// Local PostgreSQL/PostGIS API. Change to the deployed HTTPS API at rollout.
const API_URL = new URLSearchParams(window.location.search).get("api") || (window.location.port === "8080" ? "http://127.0.0.1:8002/api/v1" : `${window.location.origin}/api/v1`);
sessionStorage.setItem("cs_ircfs_api_url", API_URL);
const apiFetch = (path, options = {}) => fetch(`${API_URL}/${path}`, { ...options, headers: { ...(options.headers || {}), ...(sessionStorage.getItem("cs_ircfs_api_key") ? { "X-API-Key": sessionStorage.getItem("cs_ircfs_api_key") } : {}) } });
function apiKeyFromInput(value) {
  let input = String(value || "").trim();
  if (input.startsWith("API_KEY_ROLES=")) input = input.slice("API_KEY_ROLES=".length).trim();
  input = input.replace(/^['"]|['"]$/g, "");
  if (input.endsWith(":administrator")) input = input.slice(0, -":administrator".length);
  return input.trim();
}
document.querySelectorAll('a[href="management.html"]').forEach((link) => { link.href = `management.html${window.location.search}`; });
let liveMap;
let selectedCaseId = null;
let currentMapData = null;
const BUGESERA_VIEW = { center: [-2.28, 30.15], zoom: 10, features: [] };
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);

const demo = {
  summary: { registered_farmers: 250, total_reports: 1250, active_schemes: 2, open_complaints: 35, faulty_or_offline_assets: 3 },
  queue: [
    { item_type: "infrastructure", item_id: 21, priority: "critical", title: "Mwesa Pump A is offline", status: "offline", scheme_id: 1, cell_id: 12, created_at: "2026-09-08T07:25:00", details: "Technical: pressure loss reported by scheme operator." },
    { item_type: "pest_or_disease", item_id: 47, priority: "critical", title: "Fall armyworm reported for maize", status: "reported", scheme_id: 2, cell_id: 19, created_at: "2026-09-08T06:40:00", details: "High-severity observation from a Citizen Science Monitor." },
    { item_type: "community_feedback", item_id: 58, priority: "medium", title: "Water pricing", status: "open", scheme_id: 1, cell_id: 10, created_at: "2026-09-07T12:00:00", details: "Community feedback needs planner triage." }
  ]
};

const formatDate = (value) => new Intl.DateTimeFormat("en", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(new Date(value));
const humanize = (value) => value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());

function showSummary(summary) {
  document.querySelector("#metric-farmers").textContent = summary.registered_farmers.toLocaleString();
  document.querySelector("#metric-reports").textContent = summary.total_reports.toLocaleString();
  document.querySelector("#metric-schemes").textContent = summary.active_schemes.toLocaleString();
  document.querySelector("#metric-complaints").textContent = summary.open_complaints.toLocaleString();
  document.querySelector("#metric-complaints-note").textContent = `${summary.faulty_or_offline_assets} asset${summary.faulty_or_offline_assets === 1 ? "" : "s"} need attention`;
}

function showQueue(items) {
  const list = document.querySelector("#act-now-list");
  document.querySelector("#nav-alert-count").textContent = items.length;
  if (!items.length) {
    list.innerHTML = '<div class="alert-row"><div class="alert-band medium"></div><div><h3>No urgent reports</h3><p>The current queue is clear.</p></div></div>';
    return;
  }
  list.innerHTML = items.map((item) => `
    <article class="alert-row" data-scheme="${item.scheme_id ?? "other"}">
      <div class="alert-band ${escapeHtml(item.priority)}"></div>
      <div><h3>${escapeHtml(item.title)}</h3><p>${escapeHtml(item.details || "No additional details provided.")}</p>${modeForCase(item) ? `<button type="button" class="case-open secondary-button" data-case-id="${Number(item.item_id)}">Open case</button>` : ""}</div>
      <div class="alert-meta"><span class="priority ${escapeHtml(item.priority)}">${escapeHtml(item.priority)}</span><br />${escapeHtml(humanize(item.status))} · ${formatDate(item.created_at)}</div>
    </article>`).join("");
  document.querySelector("#scheme-filter").dispatchEvent(new Event("change"));
}

function modeForCase(item) { return item.item_type !== "community_feedback" && document.querySelector("#data-mode").classList.contains("live"); }

function display(data, mode) {
  const badge = document.querySelector("#data-mode");
  badge.textContent = mode === "live" ? "LOCAL API CONNECTED" : "DEMONSTRATION DATA";
  badge.classList.toggle("live", mode === "live");
  if (mode === "demo") {
    document.querySelector("#scheme-filter").replaceChildren(new Option("All schemes", "all"), new Option("PADAB", "1"), new Option("APEFA Solar", "2"));
    document.querySelector("#scheme-filter-help").hidden = true;
  }
  showSummary(data.summary);
  showQueue(data.queue);
}

function markerStyle(feature) {
  if (feature.feature_type === "scheme") return { color: "#ffffff", fillColor: "#167052" };
  if (feature.feature_type === "farmer") return { color: "#ffffff", fillColor: "#6b5ca5" };
  if (feature.feature_type === "crop") return { color: "#ffffff", fillColor: "#d59223" };
  return { color: "#ffffff", fillColor: feature.status === "offline" ? "#c75248" : "#2878a9" };
}

function renderMap(data) {
  currentMapData = data;
  const selectedScheme = document.querySelector("#scheme-filter").value;
  const visibleFeatures = data.features.filter((feature) => selectedScheme === "all" || String(feature.scheme_id) === selectedScheme);
  const mapStatus = document.querySelector("#map-status");
  const empty = visibleFeatures.length === 0;
  mapStatus.classList.toggle("empty", empty);
  mapStatus.textContent = empty
    ? selectedScheme === "all"
      ? "No verified scheme, farmer, or observation coordinates are available yet. Add real locations to PostgreSQL to show them here."
      : "No mapped locations are available for this scheme yet. Add its verified coordinates or linked observations to show them here."
    : `${visibleFeatures.length} mapped location${visibleFeatures.length === 1 ? "" : "s"} shown${selectedScheme === "all" ? " across Bugesera" : " for this scheme"}.`;
  if (!window.L) return;
  if (!liveMap) {
    liveMap = L.map("map-canvas", { zoomControl: false, scrollWheelZoom: false }).setView(data.center, data.zoom);
    L.control.zoom({ position: "topright" }).addTo(liveMap);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 19
    }).addTo(liveMap);
  } else {
    liveMap.setView(data.center, data.zoom);
    liveMap.eachLayer((layer) => { if (layer instanceof L.CircleMarker) liveMap.removeLayer(layer); });
  }
  visibleFeatures.forEach((feature) => {
    const style = markerStyle(feature);
    L.circleMarker([feature.latitude, feature.longitude], { radius: feature.feature_type === "scheme" ? 9 : 7, weight: 2, ...style })
      .bindPopup(`<strong>${escapeHtml(feature.name)}</strong>${feature.status ? `<br />${escapeHtml(feature.status)}` : ""}${feature.details ? `<br /><small>${escapeHtml(feature.details)}</small>` : ""}`)
      .addTo(liveMap);
  });
  window.setTimeout(() => liveMap.invalidateSize(), 0);
}

async function loadMapData() {
  try {
    const mapData = await apiFetch("map-data").then((response) => response.ok ? response.json() : Promise.reject(response.status));
    renderMap(mapData);
  } catch (_) {
    renderMap(BUGESERA_VIEW);
    const mapStatus = document.querySelector("#map-status");
    mapStatus.textContent = "Map data is unavailable until the local API connects. The base map shows Bugesera only.";
  }
}

async function loadLiveData() {
  const button = document.querySelector("#load-live-data");
  button.textContent = "Connecting…";
  try {
    let summaryResponse = await apiFetch("analytics/dashboard-summary");
    if (summaryResponse.status === 401) {
      sessionStorage.removeItem("cs_ircfs_api_key");
      const key = apiKeyFromInput(window.prompt("Enter your Render API_KEY_ROLES value (secret:administrator), or just the secret:"));
      if (!key) throw new Error("API key required");
      sessionStorage.setItem("cs_ircfs_api_key", key);
      summaryResponse = await apiFetch("analytics/dashboard-summary");
    }
    if (summaryResponse.status === 401) {
      sessionStorage.removeItem("cs_ircfs_api_key");
      const status = await apiFetch("auth-status").then((response) => response.ok ? response.json() : null).catch(() => null);
      throw new Error(status?.api_keys_configured === false ? "No API keys configured on Render" : "API key rejected");
    }
    if (!summaryResponse.ok) throw new Error(`API returned ${summaryResponse.status}`);
    const summary = await summaryResponse.json();
    const [queue, schemes] = await Promise.all([
      apiFetch("analytics/act-now").then((response) => response.ok ? response.json() : Promise.reject(response.status)),
      apiFetch("irrigation-schemes").then((response) => response.ok ? response.json() : Promise.reject(response.status))
    ]);
    const filter = document.querySelector("#scheme-filter");
    const selected = filter.value;
    filter.replaceChildren(new Option("All schemes", "all"), ...schemes.map((scheme) => new Option(`${scheme.name}${scheme.is_active ? "" : " (reference)"}`, String(scheme.id))));
    if (!schemes.length) {
      const emptyOption = new Option("No schemes in PostgreSQL", "none");
      emptyOption.disabled = true;
      filter.add(emptyOption);
    }
    filter.value = selected;
    if (filter.selectedIndex < 0) filter.value = "all";
    document.querySelector("#scheme-filter-help").hidden = schemes.length > 0;
    display({ summary, queue }, "live");
    await loadMapData();
    button.textContent = "PostgreSQL API connected ✓";
  } catch (error) {
    display(demo, "demo");
    button.textContent = error.message === "API key required" ? "Enter API key to connect ↗" : error.message === "API key rejected" ? "Key rejected — try again ↗" : error.message === "No API keys configured on Render" ? "Set API_KEY_ROLES on Render ↗" : "API unavailable — retry ↗";
    document.querySelector("#data-mode").title = error.message;
  }
}

document.querySelector("#load-live-data").addEventListener("click", loadLiveData);
document.querySelector("#map-reset-view").addEventListener("click", () => liveMap?.setView(BUGESERA_VIEW.center, BUGESERA_VIEW.zoom));
document.querySelector("#refresh-queue").addEventListener("click", loadLiveData);
document.querySelector("#scheme-filter").addEventListener("change", (event) => {
  const selected = event.target.value;
  document.querySelectorAll("#act-now-list .alert-row").forEach((row) => { row.hidden = selected !== "all" && row.dataset.scheme !== selected; });
  if (currentMapData) renderMap(currentMapData);
});
document.querySelector("#act-now-list").addEventListener("click", async (event) => {
  const button = event.target.closest(".case-open");
  if (!button) return;
  selectedCaseId = Number(button.dataset.caseId);
  const response = await apiFetch(`cases/${selectedCaseId}`);
  if (!response.ok) return;
  const record = await response.json();
  document.querySelector("#case-title").textContent = `Case #${record.id}`;
  document.querySelector("#case-summary").textContent = `${record.source_type} report · ${record.priority} priority`;
  document.querySelector("#case-form [name=status]").value = record.status === "open" ? "triaged" : record.status;
  document.querySelector("#case-form [name=assigned_to_user_id]").value = record.assigned_to_user_id || "";
  document.querySelector("#case-form [name=action_taken]").value = record.action_taken || "";
  document.querySelector("#case-message").textContent = "";
  document.querySelector("#case-dialog").showModal();
});
document.querySelector("#case-cancel").addEventListener("click", () => document.querySelector("#case-dialog").close());
document.querySelector("#case-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const form = new FormData(event.currentTarget);
  const payload = { status: form.get("status"), action_taken: form.get("action_taken") || null };
  if (form.get("assigned_to_user_id")) payload.assigned_to_user_id = Number(form.get("assigned_to_user_id"));
  if (form.get("due_at")) payload.due_at = new Date(form.get("due_at")).toISOString();
  const response = await apiFetch(`cases/${selectedCaseId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  if (!response.ok) { document.querySelector("#case-message").textContent = JSON.stringify((await response.json()).detail); return; }
  document.querySelector("#case-message").textContent = "Case saved. You can record a simulated SMS response after resolution.";
  await loadLiveData();
});
document.querySelector("#case-notify").addEventListener("click", async () => {
  const response = await apiFetch(`cases/${selectedCaseId}/simulate-notification`, { method: "POST" });
  document.querySelector("#case-message").textContent = response.ok ? "Simulated response recorded. No SMS was sent." : "Resolve the case before recording a response.";
});
document.querySelector("#phone-demo-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries(new FormData(event.currentTarget));
  const response = await apiFetch("irrigation-reports", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }).catch(() => null);
  document.querySelector("#phone-demo-message").textContent = response?.ok ? `Report #${(await response.json()).id} saved to local API.` : "Could not save report. Start the local API first.";
  if (response?.ok) await loadLiveData();
});
display(demo, "demo");
renderMap(BUGESERA_VIEW);
loadMapData();
if (new URLSearchParams(window.location.search).has("api")) loadLiveData();
