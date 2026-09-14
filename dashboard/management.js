// Local PostgreSQL/PostGIS API. Change to the deployed HTTPS API at rollout.
const API = new URLSearchParams(window.location.search).get("api") || (window.location.port === "8080" ? "http://127.0.0.1:8002/api/v1" : `${window.location.origin}/api/v1`);
sessionStorage.setItem("cs_ircfs_api_url", API);
const apiFetch = (path, options = {}) => fetch(`${API}/${path}`, { ...options, headers: { ...(options.headers || {}), ...(sessionStorage.getItem("cs_ircfs_api_key") ? { "X-API-Key": sessionStorage.getItem("cs_ircfs_api_key") } : {}) } });
let activeModule = "users";
let liveMode = false;
let renderedRows = [];
let renderedLive = false;

const modules = {
  users: {
    title: "Users", subtitle: "Manage the people who report, monitor, and use district information.", add: "+ Add user", search: "Search users...",
    cards: [["Registered users", "250", "Across 3 pilot cooperatives", ""], ["Farmers", "208", "Community reporters", "blue"], ["Citizen monitors", "24", "Field observation team", "gold"], ["Active this month", "186", "74% participation", "coral"]],
    columns: ["User", "Role", "Cooperative", "Location", "Status"],
    rows: [["Aline Umutoni", "AU", "farmer", "Koperative Mwesa", "Nyamata", "active"], ["Jean Habineza", "JH", "citizen science monitor", "Mwesa Data Team", "Nyamata", "active"], ["Claudine Mukamana", "CM", "cooperative leader", "APEFA Growers", "Ngeruka", "active"], ["David Niyonzima", "DN", "district planner", "Bugesera District", "Nyamata", "active"]],
  },
  schemes: {
    title: "Irrigation schemes", subtitle: "Manage irrigation investments and verify their outcomes.", add: "+ Add scheme", search: "Search schemes...",
    cards: [["Active schemes", "2", "Pilot investments", ""], ["PADAB coverage", "650 ha", "Verify official figure", "blue"], ["Infrastructure assets", "2", "Pumping stations recorded", "gold"], ["Outcome status", "Watch", "Needs verified field data", "coral"]],
    columns: ["Scheme", "Partner", "Location", "Area", "Status"],
    rows: [["PADAB", "PD", "AfDB", "Mwesa Valley", "650 ha", "operational"], ["APEFA Solar", "AS", "APEFA", "Ngeruka & Mareba", "To verify", "operational"]],
    helper: ["Scheme data must be verified", "PADAB and APEFA figures are presentation examples until official scheme records, asset lists, and yield targets are approved."]
  },
  citizen: {
    title: "Citizen reports", subtitle: "Review crop production, harvest, pest, and disease observations.", add: "+ New report", search: "Search citizen reports...",
    cards: [["Total reports", "1,250", "All crop observations", ""], ["Pest alerts", "27", "Need extension review", "coral"], ["Expected harvest", "418 t", "Reported by farmers", "blue"], ["High severity", "5", "Act Now priority", "gold"]],
    columns: ["Reporter", "Crop", "Observation", "Scheme", "Location", "Severity"],
    rows: [["Jean Habineza", "JH", "Maize", "Fall armyworm", "APEFA Solar", "Ngeruka", "critical"], ["Aline Umutoni", "AU", "Rice", "Planting update", "PADAB", "Nyamata", "active"], ["Claudine Mukamana", "CM", "Beans", "Expected harvest", "APEFA Solar", "Mareba", "triaged"]],
    helper: ["Citizen science creates evidence", "Reports show what is happening in the field and help planners compare real outcomes with expected irrigation benefits."]
  },
  irrigation: {
    title: "Rainfall & irrigation", subtitle: "Monitor rain gauges, water availability, pumps, canals, and faults.", add: "+ New observation", search: "Search irrigation reports...",
    cards: [["Irrigation reports", "84", "This reporting period", ""], ["Rainfall readings", "49", "Local gauge network", "blue"], ["Offline assets", "3", "Critical follow-up", "coral"], ["Operational assets", "18", "Reported this month", "gold"]],
    columns: ["Asset / observation", "Scheme", "Condition", "Rainfall", "Bottleneck", "Status"],
    rows: [["Mwesa Pump A", "MP", "PADAB", "offline", "12.5 mm", "technical", "offline"], ["Ngeruka solar pump", "NS", "APEFA Solar", "operational", "8.0 mm", "—", "operational"], ["Canal section 4", "C4", "PADAB", "faulty", "15.0 mm", "environmental", "faulty"]],
    helper: ["Water reliability is visible", "Infrastructure failures and rainfall observations become priority cases so the responsible team can act quickly."]
  },
  feedback: {
    title: "Community feedback", subtitle: "Follow every concern from community report to final response.", add: "+ New feedback", search: "Search feedback cases...",
    cards: [["Open cases", "35", "Need planner response", "coral"], ["Resolved cases", "18", "Action recorded", ""], ["Assigned cases", "12", "Owners identified", "blue"], ["Median response", "1.8d", "Pilot indicator", "gold"]],
    columns: ["Case", "Category", "Scheme", "Location", "Assigned to", "Status"],
    rows: [["FB-058", "F5", "Water pricing", "PADAB", "Nyamata", "District Planner", "open"], ["FB-052", "F5", "Canal access", "APEFA Solar", "Ngeruka", "Water Officer", "triaged"], ["FB-041", "F4", "Input distribution", "PADAB", "Mwesa", "Cooperative Lead", "resolved"]],
    helper: ["Closing the loop builds trust", "Every community issue needs an owner, action record, and response. Anonymous feedback remains protected."]
  },
  analytics: {
    title: "Analytics", subtitle: "Use validated reports to prioritise district decisions.", add: "View Act Now", search: "Search analytics...",
    cards: [["Act Now alerts", "3", "Critical and high priority", "coral"], ["Harvest performance", "71%", "Illustrative pilot trend", ""], ["Data quality", "94%", "Valid submitted reports", "blue"], ["Report coverage", "74%", "Active reporter rate", "gold"]],
    columns: ["Priority item", "Type", "Scheme", "Location", "Reported", "Priority"],
    rows: [["Mwesa Pump A offline", "MP", "Infrastructure", "PADAB", "Nyamata", "Today", "critical"], ["Fall armyworm alert", "FA", "Pest / disease", "APEFA Solar", "Ngeruka", "Today", "critical"], ["Water pricing", "WP", "Feedback", "PADAB", "Nyamata", "Yesterday", "triaged"]],
    helper: ["Analytics support, not replace, decisions", "The platform shows transparent signals. District Planners still confirm bottlenecks and decide what action to take."]
  }
};

const statusValues = new Set(["active", "open", "resolved", "triaged", "offline", "operational", "faulty", "critical"]);
const initials = (name) => name.split(" ").map((word) => word[0]).join("").slice(0, 2).toUpperCase();
const slug = (value) => String(value).toLowerCase().replace(/[^a-z0-9]+/g, "-");
const badge = (value) => `<span class="status-badge status-${slug(value)}">${escapeHtml(String(value).replaceAll("_", " "))}</span>`;
const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (character) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[character]);

function normalCell(value) {
  return statusValues.has(String(value).toLowerCase()) ? badge(value) : escapeHtml(value || "—");
}

function draw(data, rows, isLive = false) {
  renderedRows = rows;
  renderedLive = isLive;
  document.querySelector("#page-title").textContent = data.title;
  document.querySelector("#page-subtitle").textContent = data.subtitle;
  document.querySelector("#add-button").textContent = data.add;
  document.querySelector("#add-button").disabled = false;
  document.querySelector("#add-button").title = activeModule === "analytics" ? "Open the planner Act Now queue" : `Add ${data.title.toLowerCase()}`;
  document.querySelector("#table-search").placeholder = data.search;
  const cards = isLive ? data.cards.map((card, index) => [card[0], index === 0 ? rows.length.toLocaleString() : "—", index === 0 ? "Live PostgreSQL records" : "Calculated when records are entered", card[3]]) : data.cards;
  document.querySelector("#summary-row").innerHTML = cards.map((card) => `<article class="summary-card ${card[3]}"><p>${card[0]}</p><strong>${card[1]}</strong><small>${card[2]}</small></article>`).join("");
  document.querySelector("#table-head").innerHTML = `<tr>${data.columns.map((column) => `<th>${column}</th>`).join("")}${activeModule === "users" ? "<th>Actions</th>" : ""}</tr>`;
  const body = document.querySelector("#table-body");
  if (!rows.length) {
    body.innerHTML = `<tr><td class="empty-row" colspan="${data.columns.length}">No ${data.title.toLowerCase()} have been entered in the local database yet.</td></tr>`;
  } else if (activeModule === "users") {
    body.innerHTML = rows.map((row) => `<tr><td><div class="user-cell"><span class="mini-avatar">${escapeHtml(row[1])}</span><span><strong>${escapeHtml(row[0])}</strong><small>${escapeHtml(row[2].replaceAll("_", " "))}</small></span></div></td><td>${badge(row[2])}</td><td>${escapeHtml(row[3] || "—")}</td><td>${escapeHtml(row[4] || "—")}</td><td><button class="row-action" data-action="edit" data-id="${Number(row[6])}">Edit</button><button class="row-action danger" data-action="delete" data-id="${Number(row[6])}">Delete</button></td></tr>`).join("");
  } else {
    body.innerHTML = rows.map((row) => `<tr><td><div class="user-cell"><span class="mini-avatar">${escapeHtml(row[1])}</span><strong>${escapeHtml(row[0])}</strong></div></td>${row.slice(2).map(normalCell).map((value) => `<td>${value}</td>`).join("")}</tr>`).join("");
  }
  updateVisibleRows();
}

function updateVisibleRows() {
  const term = document.querySelector("#table-search").value.trim().toLowerCase();
  document.querySelectorAll("#table-body tr").forEach((row, index) => {
    row.hidden = Boolean(renderedRows[index] && term && !row.textContent.toLowerCase().includes(term));
  });
  const count = [...document.querySelectorAll("#table-body tr")].filter((row, index) => renderedRows[index] && !row.hidden).length;
  document.querySelector("#table-count").textContent = `Showing ${count} ${renderedLive ? "PostgreSQL" : "demonstration"} record${count === 1 ? "" : "s"}`;
}

function sampleRows(module) { return modules[module].rows; }

async function fetchLiveRows(module) {
  const endpoints = { users: "users", schemes: "irrigation-schemes", citizen: "citizen-reports", irrigation: "irrigation-reports", feedback: "feedback", analytics: "analytics/act-now" };
  const response = await apiFetch(endpoints[module]);
  if (!response.ok) throw new Error("API request failed");
  const records = await response.json();
  if (module === "users") return records.map((item) => [item.full_name || "Unnamed user", initials(item.full_name || "User"), item.role, item.cooperative_name, item.cell_id ? `Cell #${item.cell_id}` : "—", item.is_active ? "active" : "inactive", item.id]);
  if (module === "schemes") return records.map((item) => [item.name, initials(item.name), item.implementing_partner || "—", item.sector_id ? `Sector #${item.sector_id}` : "—", item.hectares_developed ? `${item.hectares_developed} ha` : "—", item.is_active ? "active" : "reference only"]);
  if (module === "citizen") return records.map((item) => [`${item.crop_type} report`, initials(item.crop_type), item.crop_type, item.pest_or_disease || "Crop update", item.scheme_id ? `Scheme #${item.scheme_id}` : "—", item.cell_id ? `Cell #${item.cell_id}` : "—", item.severity ? (item.severity >= 5 ? "critical" : "triaged") : "active"]);
  if (module === "irrigation") return records.map((item) => [item.infrastructure_name || "Rainfall observation", initials(item.infrastructure_name || "Rain"), item.scheme_id ? `Scheme #${item.scheme_id}` : "—", item.operational_status || "reported", item.rainfall_mm === null ? "—" : `${item.rainfall_mm} mm`, item.bottleneck_category || "—", item.operational_status || "active"]);
  if (module === "feedback") return records.map((item) => [`FB-${String(item.id).padStart(3, "0")}`, "FB", item.category, item.scheme_id ? `Scheme #${item.scheme_id}` : "—", item.cell_id ? `Cell #${item.cell_id}` : "—", item.assigned_to_user_id ? `User #${item.assigned_to_user_id}` : "Unassigned", item.status]);
  return records.map((item) => [item.title, initials(item.item_type), item.item_type, item.scheme_id ? `Scheme #${item.scheme_id}` : "—", item.cell_id ? `Cell #${item.cell_id}` : "—", new Date(item.created_at).toLocaleDateString(), item.priority]);
}

async function render(module) {
  activeModule = module;
  document.querySelectorAll(".module-link").forEach((button) => button.classList.toggle("active", button.dataset.module === module));
  try { draw(modules[module], liveMode ? await fetchLiveRows(module) : sampleRows(module), liveMode); }
  catch (_) { liveMode = false; document.querySelector("#data-label").textContent = "SAMPLE DATA"; document.querySelector("#data-label").classList.remove("live"); draw(modules[module], sampleRows(module)); }
}

async function refreshNavigationCounts() {
  const endpoints = { users: "users", schemes: "irrigation-schemes", citizen: "citizen-reports", irrigation: "irrigation-reports", feedback: "feedback" };
  await Promise.all(Object.entries(endpoints).map(async ([module, endpoint]) => {
    const response = await apiFetch(endpoint);
    if (!response.ok) throw new Error("Unable to load navigation counts");
    const records = await response.json();
    document.querySelector(`[data-count="${module}"]`).textContent = records.length.toLocaleString();
  }));
}

document.querySelectorAll(".module-link").forEach((button) => button.addEventListener("click", () => render(button.dataset.module)));
document.querySelector("#table-search").addEventListener("input", updateVisibleRows);
document.querySelector("#table-body").addEventListener("click", async (event) => {
  const action = event.target.dataset.action;
  const userId = event.target.dataset.id;
  if (!action || !userId) return;
  if (action === "delete") {
    if (!confirm("Permanently delete this user? Users linked to reports can only be deactivated.")) return;
    const response = await apiFetch(`users/${userId}`, { method: "DELETE" });
    if (response.status === 204) { await refreshNavigationCounts(); await render("users"); return; }
    if (response.status === 409) {
      if (!confirm("This user has report or case history. Deactivate the account instead?")) return;
      const deactivated = await apiFetch(`users/${userId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ is_active: false }) });
      if (deactivated.ok) { await render("users"); return; }
      alert(`Could not deactivate user: ${deactivated.status}`);
      return;
    }
    alert(`Could not delete user: ${response.status}`);
  }
  if (action === "edit") {
    const name = prompt("Full name", event.target.closest("tr").querySelector("strong").textContent);
    if (name === null) return;
    const response = await apiFetch(`users/${userId}`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ full_name: name }) });
    if (response.ok) await render("users"); else alert(`Could not update user: ${response.status}`);
  }
});
async function connectApi() {
  const label = document.querySelector("#data-label");
  const button = document.querySelector("#connect-api");
  try {
    let probe = await apiFetch("users");
    if (probe.status === 401) {
      sessionStorage.removeItem("cs_ircfs_api_key");
      const key = prompt("Enter the administrator API key for this API (the secret before :administrator in API_KEY_ROLES):");
      if (!key) throw new Error("API key required");
      sessionStorage.setItem("cs_ircfs_api_key", key.trim());
      probe = await apiFetch("users");
    }
    if (probe.status === 401) { sessionStorage.removeItem("cs_ircfs_api_key"); throw new Error("API key rejected"); }
    if (!probe.ok) throw new Error(`API returned ${probe.status}`);
    liveMode = true;
    await refreshNavigationCounts();
    await render(activeModule);
    if (!liveMode) throw new Error("Could not load management records");
    label.textContent = "POSTGRESQL CONNECTED";
    label.title = API;
    label.classList.add("live");
    button.textContent = "API connected ✓";
  } catch (error) {
    liveMode = false;
    label.textContent = error.message === "API key rejected" ? "API KEY REJECTED" : "API UNAVAILABLE";
    label.title = `${error.message}. Endpoint: ${API}`;
    label.classList.remove("live");
    button.textContent = "Reconnect PostgreSQL ↗";
  }
}
document.querySelector("#connect-api").addEventListener("click", connectApi);

const dialog = document.querySelector("#user-dialog");
document.querySelectorAll('a[href="index.html"]').forEach((link) => { link.href = `index.html${window.location.search}`; });
const csvCell = (value) => {
  let cell = String(value ?? "");
  if (/^\s*[=+\-@]/.test(cell)) cell = `'${cell}`;
  return `"${cell.replaceAll('"', '""')}"`;
};
document.querySelector("#export-button").addEventListener("click", () => {
  const headers = activeModule === "users" ? [...modules.users.columns, "User ID"] : modules[activeModule].columns;
  const records = renderedRows.flatMap((row, index) => {
    const tableRow = document.querySelectorAll("#table-body tr")[index];
    if (!tableRow || tableRow.hidden) return [];
    return [activeModule === "users" ? [row[0], row[2], row[3], row[4], row[5], row[6]] : [row[0], ...row.slice(2)]];
  });
  const csv = "\uFEFF" + [headers, ...records].map((row) => row.map(csvCell).join(",")).join("\r\n") + "\r\n";
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const link = document.createElement("a");
  link.href = url;
  link.download = `cs-ircfs-${activeModule}-${renderedLive ? "postgresql" : "demonstration"}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
});
document.querySelector(".filter-button").disabled = true;
document.querySelector(".filter-button").title = "Filters are planned; use search for now";
const entryDefinitions = {
  schemes: { title: "Add irrigation scheme", endpoint: "irrigation-schemes", fields: [
    ["name", "Scheme name", "text", true], ["implementing_partner", "Implementing partner", "text"],
    ["hectares_developed", "Developed hectares", "number"], ["baseline_yield_target_tons", "Verified yield target (tons)", "number"],
    ["baseline_source", "Yield target source", "text"], ["sector_id", "Sector ID", "integer"],
    ["latitude", "Latitude", "number"], ["longitude", "Longitude", "number"]
  ] },
  citizen: { title: "Add citizen report", endpoint: "citizen-reports", fields: [
    ["crop_type", "Crop type", "text", true], ["reporter_id", "Reporter user ID", "integer"],
    ["scheme_id", "Scheme ID", "integer"], ["cell_id", "Cell ID", "integer"],
    ["planting_date", "Planting date", "date"], ["expected_harvest_tons", "Expected harvest (tons)", "number"],
    ["reported_harvest_tons", "Reported harvest (tons)", "number"], ["pest_or_disease", "Pest or disease", "text"],
    ["severity", "Severity (1–5)", "severity"], ["notes", "Notes", "textarea"]
  ] },
  irrigation: { title: "Add rainfall or irrigation report", endpoint: "irrigation-reports", fields: [
    ["reporter_id", "Reporter user ID", "integer"], ["scheme_id", "Scheme ID", "integer"], ["cell_id", "Cell ID", "integer"],
    ["infrastructure_name", "Asset or rain gauge name", "text"],
    ["operational_status", "Operational status", "select", false, ["", "operational", "faulty", "offline"]],
    ["bottleneck_category", "Bottleneck category", "select", false, ["", "technical", "social", "institutional", "environmental"]],
    ["rainfall_mm", "Rainfall (mm)", "number"], ["fault_description", "Fault description", "textarea"]
  ] },
  feedback: { title: "Add community feedback", endpoint: "feedback", fields: [
    ["category", "Category", "text", true], ["message", "Message", "textarea", true],
    ["reporter_id", "Reporter user ID (optional for anonymous feedback)", "integer"],
    ["scheme_id", "Scheme ID", "integer"], ["cell_id", "Cell ID", "integer"]
  ] }
};
const entryDialog = document.querySelector("#entry-dialog");
const entryForm = document.querySelector("#entry-form");
document.querySelector("#add-button").addEventListener("click", () => {
  if (activeModule === "analytics") { window.location.href = `index.html${window.location.search}#act-now`; return; }
  if (activeModule === "users") { document.querySelector("#form-message").textContent = ""; dialog.showModal(); return; }
  const definition = entryDefinitions[activeModule];
  document.querySelector("#entry-title").textContent = definition.title;
  document.querySelector("#entry-message").textContent = "";
  entryForm.reset();
  const container = document.querySelector("#entry-fields");
  container.replaceChildren();
  for (const [name, title, type, required, options] of definition.fields) {
    const label = document.createElement("label");
    label.textContent = title;
    const field = document.createElement(type === "textarea" ? "textarea" : type === "select" ? "select" : "input");
    field.name = name;
    field.required = Boolean(required);
    if (type === "number" || type === "integer" || type === "severity") {
      field.type = "number";
      field.step = type === "number" ? "any" : "1";
      field.min = type === "severity" || type === "integer" ? "1" : name === "latitude" ? "-90" : name === "longitude" ? "-180" : "0";
      if (type === "severity") field.max = "5";
      if (name === "rainfall_mm") field.max = "500";
      if (name === "latitude") field.max = "90";
      if (name === "longitude") field.max = "180";
    } else if (type === "date") field.type = "date";
    else if (type === "text") field.type = "text";
    if (type === "select") options.forEach((option) => field.add(new Option(option || "Select…", option)));
    if (name === "message") field.minLength = 5;
    if (name === "category") field.minLength = 2;
    label.append(field);
    container.append(label);
  }
  entryDialog.showModal();
});
document.querySelector("#entry-close").addEventListener("click", () => entryDialog.close());
document.querySelector("#entry-cancel").addEventListener("click", () => entryDialog.close());
entryForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const definition = entryDefinitions[activeModule];
  const payload = {};
  for (const [name, , type] of definition.fields) {
    const value = new FormData(entryForm).get(name);
    if (value === null || String(value).trim() === "") continue;
    payload[name] = ["number", "integer", "severity"].includes(type) ? Number(value) : String(value).trim();
  }
  const message = document.querySelector("#entry-message");
  if (activeModule === "schemes" && payload.baseline_yield_target_tons !== undefined && !payload.baseline_source) {
    message.textContent = "Enter a source for the verified yield target.";
    return;
  }
  try {
    if (!liveMode) await connectApi();
    if (!liveMode) throw new Error("Connect to PostgreSQL before saving.");
    const response = await apiFetch(definition.endpoint, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(Array.isArray(error.detail) ? error.detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join("; ") : error.detail || `Save failed (${response.status})`);
    }
    entryDialog.close();
    await refreshNavigationCounts();
    await render(activeModule);
  } catch (error) { message.textContent = error.message; }
});
document.querySelector("#close-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#cancel-dialog").addEventListener("click", () => dialog.close());
document.querySelector("#user-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  const payload = Object.fromEntries([...new FormData(event.currentTarget)].filter(([, value]) => String(value).trim() !== ""));
  for (const name of ["cell_id", "latitude", "longitude"]) if (name in payload) payload[name] = Number(payload[name]);
  const message = document.querySelector("#form-message");
  try {
    if (!liveMode) await connectApi();
    if (!liveMode) throw new Error("Connect to PostgreSQL before saving.");
    const result = await apiFetch("users", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
    if (!result.ok) {
      const error = await result.json();
      throw new Error(Array.isArray(error.detail) ? error.detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join("; ") : error.detail || "Could not save user");
    }
    await refreshNavigationCounts();
    dialog.close();
    event.currentTarget.reset();
    await render("users");
  } catch (error) { message.textContent = error.message; }
});

render("users");
if (sessionStorage.getItem("cs_ircfs_api_key")) connectApi();
